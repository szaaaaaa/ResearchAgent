from __future__ import annotations

from typing import TYPE_CHECKING

from src.agent.artifacts.base import Artifact
from src.agent.core.artifact_utils import make_artifact, records_to_artifacts
from src.agent.core.query_planning import _load_budget_and_scope
from src.agent.roles.base import RoleAgent, RolePolicy

if TYPE_CHECKING:
    from src.agent.runtime.context import RunContext

_INITIAL_LITERATURE_SKILLS = [
    "search_literature",
    "parse_paper_bundle",
    "extract_paper_notes",
    "build_related_work_matrix",
]

_REVISION_LITERATURE_SKILLS = [
    "search_literature",
    "parse_paper_bundle",
    "extract_paper_notes",
    "build_related_work_matrix",
]


def _latest_artifact(artifacts: list[Artifact], artifact_type: str) -> Artifact | None:
    matches = [artifact for artifact in artifacts if artifact.artifact_type == artifact_type]
    if not matches:
        return None
    return matches[-1]


def _apply_search_plan_state(state: dict[str, object], output_artifacts: list[Artifact]) -> None:
    topic_brief = _latest_artifact(output_artifacts, "TopicBrief")
    search_plan = _latest_artifact(output_artifacts, "SearchPlan")
    if search_plan is None:
        raise RuntimeError("Conductor update requires SearchPlan")

    payload = dict(search_plan.payload)
    query_routes = dict(payload.get("query_routes", {}))
    search_queries = list(payload.get("search_queries", []))
    cfg = state.get("_cfg", {})
    _, budget = _load_budget_and_scope(state, cfg if isinstance(cfg, dict) else {})
    if topic_brief is not None:
        state["scope"] = dict(topic_brief.payload.get("scope", {}))
    state["budget"] = budget
    state["research_questions"] = list(payload.get("research_questions", []))
    state["search_queries"] = search_queries
    state["query_routes"] = query_routes
    state["_academic_queries"] = [
        query for query in search_queries if query_routes.get(query, {}).get("use_academic", True)
    ]
    state["_web_queries"] = [
        query for query in search_queries if query_routes.get(query, {}).get("use_web", False)
    ]


class ConductorAgent(RoleAgent):
    def __init__(self, *, context: RunContext, state: dict[str, Any]) -> None:
        super().__init__(
            policy=RolePolicy(
                role_id="conductor",
                system_prompt="Plan literature-review skill execution from topic and critic feedback.",
                allowed_skills=["plan_research"],
                max_retries=int(state.get("_cfg", {}).get("reviewer", {}).get("retrieval", {}).get("max_retries", 1)),
                budget_limit_tokens=int(state.get("_cfg", {}).get("budget_guard", {}).get("max_tokens", 500000)),
            ),
            context=context,
            state=state,
        )

    def plan(self, context: RunContext) -> list[str]:
        artifacts = list(self.state.get("_artifact_objects", []))
        search_plan = _latest_artifact(artifacts, "SearchPlan")
        if search_plan is None:
            output_artifacts = self.execute("plan_research", [str(self.state.get("topic", ""))])
            artifacts.extend(output_artifacts)
            self.state["_artifact_objects"] = artifacts
            self.state["artifacts"] = [artifact.to_record() for artifact in artifacts]
            _apply_search_plan_state(self.state, output_artifacts)
            self.state["status"] = "Conductor planned literature review"
            return list(_INITIAL_LITERATURE_SKILLS)

        critique_report = _latest_artifact(artifacts, "CritiqueReport")
        if critique_report is None:
            return list(_INITIAL_LITERATURE_SKILLS)

        verdict = dict(critique_report.payload.get("verdict", {}))
        if str(verdict.get("action", "")).strip().lower() != "retry_upstream":
            return list(_INITIAL_LITERATURE_SKILLS)

        details = dict(critique_report.payload.get("details", {}))
        suggested_queries = [str(item) for item in details.get("suggested_queries", []) if str(item).strip()]
        if suggested_queries:
            payload = dict(search_plan.payload)
            existing_queries = [str(item) for item in payload.get("search_queries", []) if str(item).strip()]
            payload["search_queries"] = list(dict.fromkeys(existing_queries + suggested_queries))
            payload["query_routes"] = dict(payload.get("query_routes", {}))
            record = make_artifact(
                artifact_type="SearchPlan",
                producer="conductor_revise_search_plan",
                payload=payload,
                source_inputs=list(search_plan.source_inputs) + suggested_queries,
            )
            revised_artifact = records_to_artifacts([record])[0]
            self.context.artifact_registry.save(revised_artifact)
            artifacts.append(revised_artifact)
            self.state["_artifact_objects"] = artifacts
            self.state["artifacts"] = [artifact.to_record() for artifact in artifacts]
            _apply_search_plan_state(self.state, [revised_artifact])
            self.state["status"] = "Conductor revised search plan"

        return list(_REVISION_LITERATURE_SKILLS)
