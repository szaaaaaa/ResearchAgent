"""Backward-compatible re-exports for stage nodes and shared helpers."""
from __future__ import annotations

from src.agent.core.report_helpers import (
    _claim_evidence_coverage_ratio,
    _claim_mapping_section_exists,
    _clean_reference_section,
    _compute_acceptance_metrics,
    _critic_report,
    _ensure_claim_evidence_mapping_in_report,
    _extract_reference_urls,
    _insert_chapter_before_references,
    _render_claim_evidence_mapping,
    _render_experiment_blueprint,
    _render_experiment_results,
    _strip_outer_markdown_fence,
    _validate_experiment_plan,
    _validate_experiment_results,
)
from src.agent.core.source_ranking import (
    _dedupe_and_rank_analyses,
    _extract_domain,
    _has_traceable_source,
    _is_topic_relevant,
    _normalize_source_url,
    _source_dedupe_key,
    _source_tier,
    _tokenize,
    _uid_to_resolvable_url,
)
from src.agent.core.topic_filter import (
    _build_topic_anchor_terms,
    _build_topic_keywords,
    _extract_table_signals,
)
from src.agent.stages.analysis import analyze_sources
from src.agent.stages.evaluation import evaluate_progress
from src.agent.stages.experiments import ingest_experiment_results, recommend_experiments
from src.agent.stages.indexing import index_sources
from src.agent.stages.planning import plan_research
from src.agent.stages.reporting import (
    _default_repair_report_once as _repair_report_once,
    generate_report,
)
from src.agent.stages.retrieval import fetch_sources
from src.agent.stages.runtime import llm_call as _llm_call, parse_json as _parse_json
from src.agent.stages.synthesis import synthesize
