from __future__ import annotations

from typing import Any

from src.agent.skills.contract import SkillResult, SkillSpec
from src.agent.skills.wrappers import (
    find_artifact,
    get_artifact_records,
    get_base_state,
    get_cfg_for_stage,
    get_topic,
    list_artifacts,
)
from src.agent.stages.synthesis import synthesize

SPEC = SkillSpec(
    skill_id="build_related_work_matrix",
    purpose="Synthesize paper notes into a related-work matrix and gap map.",
    input_artifact_types=["PaperNote", "SearchPlan"],
    output_artifact_types=["RelatedWorkMatrix", "GapMap"],
)


def handle(input_artifacts: list[Any], cfg: dict[str, Any]) -> SkillResult:
    search_plan = find_artifact(input_artifacts, "SearchPlan")
    if search_plan is None:
        raise ValueError("build_related_work_matrix requires a SearchPlan artifact")

    paper_notes = list_artifacts(input_artifacts, "PaperNote")
    if not paper_notes:
        raise ValueError("build_related_work_matrix requires at least one PaperNote artifact")

    base_state = get_base_state(cfg)
    payload = dict(search_plan.payload)
    state = {
        "topic": get_topic(base_state),
        "research_questions": list(payload.get("research_questions", [])),
        "analyses": [dict(note.payload) for note in paper_notes],
        "artifacts": get_artifact_records(base_state),
        "_cfg": get_cfg_for_stage(cfg),
    }
    update = synthesize(state)
    return SkillResult(success=True, output_artifacts=list(update.get("_artifacts", [])))
