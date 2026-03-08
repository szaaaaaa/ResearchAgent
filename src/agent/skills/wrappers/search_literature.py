from __future__ import annotations

from typing import Any

from src.agent.skills.contract import SkillResult, SkillSpec
from src.agent.skills.wrappers import (
    find_artifact,
    get_artifact_records,
    get_base_state,
    get_cfg_for_stage,
    get_topic,
)
from src.agent.stages.retrieval import fetch_sources

SPEC = SkillSpec(
    skill_id="search_literature",
    purpose="Fetch literature and web sources from the current search plan.",
    input_artifact_types=["SearchPlan"],
    output_artifact_types=["CorpusSnapshot"],
)


def handle(input_artifacts: list[Any], cfg: dict[str, Any]) -> SkillResult:
    search_plan = find_artifact(input_artifacts, "SearchPlan")
    if search_plan is None:
        raise ValueError("search_literature requires a SearchPlan artifact")

    base_state = get_base_state(cfg)
    payload = dict(search_plan.payload)
    query_routes = dict(payload.get("query_routes", {}))
    search_queries = list(payload.get("search_queries", []))
    academic_queries = [query for query in search_queries if query_routes.get(query, {}).get("use_academic", True)]
    web_queries = [query for query in search_queries if query_routes.get(query, {}).get("use_web", False)]

    state = {
        "topic": get_topic(base_state),
        "search_queries": search_queries,
        "query_routes": query_routes,
        "_academic_queries": academic_queries,
        "_web_queries": web_queries,
        "papers": list(base_state.get("papers", [])),
        "web_sources": list(base_state.get("web_sources", [])),
        "indexed_paper_ids": list(base_state.get("indexed_paper_ids", [])),
        "artifacts": get_artifact_records(base_state),
        "_cfg": get_cfg_for_stage(cfg),
    }
    update = fetch_sources(state)
    return SkillResult(success=True, output_artifacts=list(update.get("_artifacts", [])))
