from __future__ import annotations

from typing import Any, Iterable

from src.agent.artifacts.base import Artifact
from src.agent.artifacts.schemas import artifact_from_record
from src.agent.core.state_access import sget


def get_base_state(cfg: dict[str, Any]) -> dict[str, Any]:
    base_state = cfg.get("_skill_state", {})
    if isinstance(base_state, dict):
        return dict(base_state)
    return {}


def get_cfg_for_stage(cfg: dict[str, Any]) -> dict[str, Any]:
    stage_cfg = dict(cfg)
    stage_cfg.pop("_skill_state", None)
    return stage_cfg


def ensure_artifact(item: Any) -> Artifact | None:
    if isinstance(item, Artifact):
        return item
    if isinstance(item, dict) and item.get("artifact_type"):
        return artifact_from_record(item)
    return None


def find_artifact(items: Iterable[Any], artifact_type: str) -> Artifact | None:
    matches: list[Artifact] = []
    for item in items:
        artifact = ensure_artifact(item)
        if artifact is not None and artifact.artifact_type == artifact_type:
            matches.append(artifact)
    if not matches:
        return None
    return matches[-1]


def list_artifacts(items: Iterable[Any], artifact_type: str) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for item in items:
        artifact = ensure_artifact(item)
        if artifact is not None and artifact.artifact_type == artifact_type:
            artifacts.append(artifact)
    return artifacts


def get_topic(base_state: dict[str, Any]) -> str:
    topic = base_state.get("topic", "")
    return str(topic or "")


def get_artifact_records(base_state: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = base_state.get("artifacts", [])
    if isinstance(artifacts, list):
        return [item for item in artifacts if isinstance(item, dict)]
    return []


def get_research_questions(base_state: dict[str, Any]) -> list[str]:
    return [str(item) for item in sget(base_state, "research_questions", []) if str(item).strip()]


def get_search_queries(base_state: dict[str, Any]) -> list[str]:
    return [str(item) for item in sget(base_state, "search_queries", []) if str(item).strip()]
