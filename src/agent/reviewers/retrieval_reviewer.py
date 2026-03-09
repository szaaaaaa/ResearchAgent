"""LLM-backed retrieval critic."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List

from src.agent.core.artifact_utils import append_artifacts, make_artifact, records_to_artifacts
from src.agent.core.schemas import ResearchState, RetrievalReview, ReviewerVerdict, SourceDiversityStats
from src.agent.core.source_ranking import _extract_domain
from src.agent.core.state_access import sget, to_namespaced_update
from src.agent.prompts import RETRIEVAL_CRITIC_SYSTEM, RETRIEVAL_CRITIC_USER
from src.agent.stages.runtime import llm_call as _runtime_llm_call, parse_json as _runtime_parse_json

logger = logging.getLogger(__name__)

_VALID_STATUSES = {"pass", "warn", "fail"}
_VALID_ACTIONS = {"continue", "retry_upstream", "degrade", "block"}


def _extract_year(source: Dict[str, Any]) -> int | None:
    year = source.get("year")
    if isinstance(year, int) and 1900 < year < 2100:
        return year
    for field in ("title", "uid", "url"):
        value = str(source.get(field) or "")
        match = re.search(r"(19|20)\d{2}", value)
        if match:
            candidate = int(match.group())
            if 1900 < candidate < 2100:
                return candidate
    return None


def _extract_venue(source: Dict[str, Any]) -> str:
    for field in ("venue", "journal", "source"):
        value = str(source.get(field) or "").strip()
        if value and value.lower() not in {"arxiv", "web", "unknown", ""}:
            return value
    return ""


def _compute_diversity(
    papers: List[Dict[str, Any]],
    web_sources: List[Dict[str, Any]],
) -> SourceDiversityStats:
    all_sources = list(papers) + list(web_sources)
    venues: List[str] = []
    domains: List[str] = []
    years: List[int] = []

    for source in all_sources:
        venue = _extract_venue(source)
        if venue:
            venues.append(venue)
        domain = _extract_domain(str(source.get("url") or ""))
        if domain:
            domains.append(domain)
        year = _extract_year(source)
        if year:
            years.append(year)

    year_dist: Dict[str, int] = {}
    for year in years:
        key = str(year)
        year_dist[key] = year_dist.get(key, 0) + 1

    return SourceDiversityStats(
        total_sources=len(all_sources),
        academic_count=len(papers),
        web_count=len(web_sources),
        unique_venues=sorted(set(venues)),
        unique_domains=sorted(set(domains)),
        year_range=[min(years), max(years)] if years else [],
        year_distribution=year_dist,
    )


def _limit_text(value: Any, *, limit: int = 240) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _dedupe_keep_order(values: List[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for value in values:
        text = _limit_text(value, limit=400)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _normalize_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return _dedupe_keep_order([str(item) for item in value if str(item).strip()])


def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.5
    return max(0.0, min(1.0, confidence))


def _paper_brief(paper: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "uid": str(paper.get("uid") or ""),
        "title": _limit_text(paper.get("title")),
        "year": _extract_year(paper),
        "source": str(paper.get("source") or ""),
        "venue": _limit_text(_extract_venue(paper), limit=120),
        "peer_reviewed": bool(paper.get("peer_reviewed", False)),
        "query_origins": list(paper.get("query_origins", []) or [])[:3],
        "abstract": _limit_text(paper.get("abstract"), limit=320),
    }


def _web_brief(web_source: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "uid": str(web_source.get("uid") or ""),
        "title": _limit_text(web_source.get("title")),
        "url": _limit_text(web_source.get("url"), limit=180),
        "snippet": _limit_text(web_source.get("snippet"), limit=240),
    }


def _analysis_brief(analysis: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "uid": str(analysis.get("uid") or ""),
        "title": _limit_text(analysis.get("title")),
        "source": str(analysis.get("source") or analysis.get("source_type") or ""),
        "summary": _limit_text(analysis.get("summary"), limit=260),
        "key_findings": [_limit_text(item, limit=180) for item in list(analysis.get("key_findings", []) or [])[:3]],
        "relevance_score": analysis.get("relevance_score"),
        "source_tier": str(analysis.get("source_tier") or ""),
        "year": analysis.get("year"),
        "peer_reviewed": bool(analysis.get("peer_reviewed", False)),
    }


def _normalize_verdict(verdict_raw: Dict[str, Any], *, has_usable_sources: bool) -> ReviewerVerdict:
    status = str(verdict_raw.get("status", "")).strip().lower()
    action = str(verdict_raw.get("action", "")).strip().lower()
    if status not in _VALID_STATUSES:
        status = "warn" if has_usable_sources else "fail"
    if action not in _VALID_ACTIONS:
        action = "continue" if has_usable_sources else "block"

    if action == "block":
        status = "fail"
    elif action == "degrade":
        status = "warn"

    return ReviewerVerdict(
        reviewer="retrieval_reviewer",
        status=status,
        action=action,
        issues=_normalize_string_list(verdict_raw.get("issues", [])),
        suggested_fix=_normalize_string_list(verdict_raw.get("suggested_fix", [])),
        confidence=_normalize_confidence(verdict_raw.get("confidence")),
    )


def _fallback_review(*, has_usable_sources: bool, message: str) -> Dict[str, Any]:
    return {
        "verdict": {
            "status": "warn" if has_usable_sources else "fail",
            "action": "degrade" if has_usable_sources else "block",
            "issues": [message],
            "suggested_fix": ["Inspect the critic response and rerun if needed."],
            "confidence": 0.2,
        },
        "missing_key_topics": [],
        "year_coverage_gaps": [],
        "venue_coverage_gaps": [],
        "suggested_queries": [],
    }


def review_retrieval(
    state: ResearchState,
    *,
    llm_call: Callable[..., str] | None = None,
    parse_json: Callable[[str], Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Run the retrieval critic using an LLM verdict."""
    llm_call = llm_call or _runtime_llm_call
    parse_json = parse_json or _runtime_parse_json

    cfg = state.get("_cfg", {})
    reviewer_cfg = cfg.get("reviewer", {}).get("retrieval", {})
    max_retries = int(reviewer_cfg.get("max_retries", 1))
    current_retries = int(state.get("_retrieval_review_retries", 0) or 0)

    papers: List[Dict[str, Any]] = list(sget(state, "papers", []))
    web_sources: List[Dict[str, Any]] = list(sget(state, "web_sources", []))
    analyses: List[Dict[str, Any]] = list(sget(state, "analyses", []))
    research_questions = [str(item) for item in sget(state, "research_questions", []) if str(item).strip()]
    existing_queries = [str(item) for item in sget(state, "search_queries", []) if str(item).strip()]
    has_usable_sources = bool(analyses or papers or web_sources)

    diversity = _compute_diversity(papers, web_sources)
    model = cfg.get("llm", {}).get("model", "gpt-4.1-mini")
    temperature = float(cfg.get("llm", {}).get("temperature", 0.0) or 0.0)
    context = {
        "topic": str(state.get("topic") or ""),
        "research_questions": research_questions,
        "search_queries": existing_queries,
        "current_retry_count": current_retries,
        "max_retry_count": max_retries,
        "diversity_stats": dict(diversity),
        "papers_preview": [_paper_brief(item) for item in papers[:10]],
        "web_sources_preview": [_web_brief(item) for item in web_sources[:8]],
        "analyses_preview": [_analysis_brief(item) for item in analyses[:10]],
    }

    raw = llm_call(
        RETRIEVAL_CRITIC_SYSTEM,
        RETRIEVAL_CRITIC_USER.format(context=json.dumps(context, ensure_ascii=False, indent=2)),
        cfg=cfg,
        model=model,
        temperature=temperature,
    )
    try:
        result = parse_json(raw)
    except json.JSONDecodeError:
        result = _fallback_review(
            has_usable_sources=has_usable_sources,
            message="LLM critic returned invalid JSON.",
        )

    if not isinstance(result, dict):
        result = _fallback_review(
            has_usable_sources=has_usable_sources,
            message="LLM critic returned an invalid payload.",
        )

    verdict = _normalize_verdict(dict(result.get("verdict", {})), has_usable_sources=has_usable_sources)
    missing_key_topics = _normalize_string_list(result.get("missing_key_topics", []))
    year_coverage_gaps = _normalize_string_list(result.get("year_coverage_gaps", []))
    venue_coverage_gaps = _normalize_string_list(result.get("venue_coverage_gaps", []))
    suggested_queries = _normalize_string_list(result.get("suggested_queries", []))

    if verdict["action"] == "retry_upstream" and current_retries >= max_retries:
        if has_usable_sources:
            verdict["status"] = "warn"
            verdict["action"] = "degrade"
            verdict["issues"] = _dedupe_keep_order(
                list(verdict.get("issues", []))
                + ["Retrieval retry budget exhausted; proceeding with explicit caveats."]
            )
        else:
            verdict["status"] = "fail"
            verdict["action"] = "block"
            verdict["issues"] = _dedupe_keep_order(
                list(verdict.get("issues", []))
                + ["Retrieval retry budget exhausted with no usable sources."]
            )

    retrieval_review = RetrievalReview(
        verdict=verdict,
        diversity_stats=diversity,
        missing_key_topics=missing_key_topics,
        year_coverage_gaps=year_coverage_gaps,
        venue_coverage_gaps=venue_coverage_gaps,
        suggested_queries=suggested_queries,
    )

    logger.info(
        "[RetrievalReviewer] status=%s action=%s issues=%d suggested_queries=%d",
        verdict.get("status"),
        verdict.get("action"),
        len(verdict.get("issues", [])),
        len(suggested_queries),
    )
    for issue in verdict.get("issues", []):
        logger.info("[RetrievalReviewer]   - %s", issue)

    existing_log = list(sget(state, "reviewer_log", []))
    existing_log.append(dict(verdict))

    new_artifacts = [
        make_artifact(
            artifact_type="CritiqueReport",
            producer="review_retrieval",
            payload={
                "verdict": dict(verdict),
                "details": dict(retrieval_review),
            },
            source_inputs=list(existing_queries),
        )
    ]

    update: Dict[str, Any] = {
        "review": {
            "retrieval_review": dict(retrieval_review),
            "reviewer_log": existing_log,
        },
        "artifacts": append_artifacts(state.get("artifacts", []), new_artifacts),
        "_artifacts": records_to_artifacts(new_artifacts),
        "status": f"Retrieval review: {verdict.get('status', 'unknown')} ({len(verdict.get('issues', []))} issues)",
    }

    if verdict.get("action") == "retry_upstream" and suggested_queries:
        merged_queries = list(dict.fromkeys(existing_queries + suggested_queries))
        update["search_queries"] = merged_queries
        update["_academic_queries"] = merged_queries
        update["_web_queries"] = merged_queries
        logger.info(
            "[RetrievalReviewer] Injecting %d supplemental queries for retry",
            len(suggested_queries),
        )

    update["_retrieval_review_retries"] = current_retries + 1 if verdict.get("action") == "retry_upstream" else 0
    return to_namespaced_update(update)
