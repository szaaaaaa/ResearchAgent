from __future__ import annotations

from typing import Any

from src.agent.reviewers.retrieval_reviewer import review_retrieval
from src.agent.skills.contract import SkillResult, SkillSpec
from src.agent.skills.wrappers import (
    find_artifact,
    get_artifact_records,
    get_base_state,
    get_cfg_for_stage,
    get_research_questions,
    get_search_queries,
)

SPEC = SkillSpec(
    skill_id="critique_retrieval",
    purpose="Review retrieval coverage and produce a critique report.",
    input_artifact_types=["CorpusSnapshot"],
    output_artifact_types=["CritiqueReport"],
)


def handle(input_artifacts: list[Any], cfg: dict[str, Any]) -> SkillResult:
    corpus_snapshot = find_artifact(input_artifacts, "CorpusSnapshot")
    if corpus_snapshot is None:
        raise ValueError("critique_retrieval requires a CorpusSnapshot artifact")

    base_state = get_base_state(cfg)
    payload = dict(corpus_snapshot.payload)
    state = {
        "papers": list(payload.get("papers", [])),
        "web_sources": list(payload.get("web_sources", [])),
        "analyses": list(base_state.get("analyses", [])),
        "research_questions": get_research_questions(base_state),
        "search_queries": get_search_queries(base_state),
        "_retrieval_review_retries": int(base_state.get("_retrieval_review_retries", 0) or 0),
        "artifacts": get_artifact_records(base_state),
        "_cfg": get_cfg_for_stage(cfg),
    }
    update = review_retrieval(state)
    return SkillResult(success=True, output_artifacts=list(update.get("_artifacts", [])))
