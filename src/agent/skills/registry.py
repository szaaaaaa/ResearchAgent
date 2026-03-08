from __future__ import annotations

from typing import Any, Callable

from src.agent.artifacts.base import Artifact
from src.agent.skills.contract import SkillResult, SkillSpec

SkillHandler = Callable[[list[Any], dict[str, Any]], SkillResult]


def _artifact_type(item: Any) -> str | None:
    if isinstance(item, Artifact):
        return item.artifact_type
    if isinstance(item, dict):
        artifact_type = item.get("artifact_type")
        if isinstance(artifact_type, str) and artifact_type.strip():
            return artifact_type
    return None


class SkillRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, SkillSpec] = {}
        self._handlers: dict[str, SkillHandler] = {}

    def register(self, skill_id: str, spec: SkillSpec, handler: SkillHandler) -> None:
        key = str(skill_id).strip()
        if not key:
            raise ValueError("Skill id cannot be empty")
        self._specs[key] = spec
        self._handlers[key] = handler

    def invoke(self, skill_id: str, input_artifacts: list[Any], cfg: dict[str, Any]) -> SkillResult:
        key = str(skill_id).strip()
        try:
            spec = self._specs[key]
            handler = self._handlers[key]
        except KeyError as exc:
            supported = ", ".join(sorted(self._specs)) or "(none)"
            raise ValueError(f"Unknown skill: {skill_id}. Supported: {supported}") from exc

        if spec.input_artifact_types:
            present_types = {
                artifact_type
                for item in input_artifacts
                for artifact_type in [_artifact_type(item)]
                if artifact_type
            }
            missing = [artifact_type for artifact_type in spec.input_artifact_types if artifact_type not in present_types]
            if missing:
                raise ValueError(f"Skill {skill_id} missing required input artifacts: {', '.join(missing)}")

        try:
            result = handler(list(input_artifacts), dict(cfg))
        except Exception as exc:
            return SkillResult(success=False, output_artifacts=[], error=str(exc))
        if not result.success:
            return result

        if spec.output_artifact_types:
            produced_types = {
                artifact_type
                for item in result.output_artifacts
                for artifact_type in [_artifact_type(item)]
                if artifact_type
            }
            missing = [artifact_type for artifact_type in spec.output_artifact_types if artifact_type not in produced_types]
            unexpected = sorted(
                artifact_type
                for artifact_type in produced_types
                if artifact_type not in spec.output_artifact_types
            )
            if missing or unexpected:
                parts: list[str] = []
                if missing:
                    parts.append(f"missing required output artifacts: {', '.join(missing)}")
                if unexpected:
                    parts.append(f"unexpected output artifacts: {', '.join(unexpected)}")
                return SkillResult(success=False, output_artifacts=[], error=f"Skill {skill_id} {'; '.join(parts)}")
        return result

    def list(self) -> list[SkillSpec]:
        return [self._specs[key] for key in sorted(self._specs)]


_SKILL_REGISTRY = SkillRegistry()


def get_skill_registry() -> SkillRegistry:
    return _SKILL_REGISTRY
