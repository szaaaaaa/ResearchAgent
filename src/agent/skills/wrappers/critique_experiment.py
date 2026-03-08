from __future__ import annotations

from typing import Any

from src.agent.skills.contract import SkillResult, SkillSpec

SPEC = SkillSpec(
    skill_id="critique_experiment",
    purpose="Reserved experiment critique skill stub for Phase 5.",
    input_artifact_types=[],
    output_artifact_types=[],
)


def handle(input_artifacts: list[Any], cfg: dict[str, Any]) -> SkillResult:
    return SkillResult(success=False, output_artifacts=[], error="critique_experiment is reserved for Phase 5")
