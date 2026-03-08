from __future__ import annotations

from typing import Any

from src.agent.skills.contract import SkillResult, SkillSpec
from src.agent.skills.wrappers import get_artifact_records, get_base_state, get_cfg_for_stage
from src.agent.stages.planning import plan_research

SPEC = SkillSpec(
    skill_id="plan_research",
    purpose="Plan the research topic into scoped research questions and routed queries.",
    input_artifact_types=[],
    output_artifact_types=["TopicBrief", "SearchPlan"],
)


def handle(input_artifacts: list[Any], cfg: dict[str, Any]) -> SkillResult:
    topic = next((item for item in input_artifacts if isinstance(item, str) and item.strip()), "")
    if not topic:
        raise ValueError("plan_research requires a topic string input")

    base_state = get_base_state(cfg)
    state = {
        "topic": topic,
        "iteration": int(base_state.get("iteration", 0) or 0),
        "findings": list(base_state.get("findings", [])),
        "gaps": list(base_state.get("gaps", [])),
        "search_queries": list(base_state.get("search_queries", [])),
        "_focus_research_questions": list(base_state.get("_focus_research_questions", [])),
        "artifacts": get_artifact_records(base_state),
        "_cfg": get_cfg_for_stage(cfg),
    }
    update = plan_research(state)
    return SkillResult(success=True, output_artifacts=list(update.get("_artifacts", [])))
