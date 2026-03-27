from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from src.dynamic_os.contracts.artifact import ArtifactRecord

if TYPE_CHECKING:
    from src.dynamic_os.tools.gateway import ToolGateway


@dataclass(frozen=True)
class SkillContext:
    skill_id: str
    role_id: str
    run_id: str
    node_id: str
    goal: str
    input_artifacts: list[ArtifactRecord]
    tools: "ToolGateway"
    user_request: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    timeout_sec: int = 120
    knowledge_graph: Any = None


class SkillOutput(BaseModel):
    model_config = {"frozen": True}

    success: bool
    output_artifacts: list[ArtifactRecord] = Field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def find_artifact(ctx: SkillContext, artifact_type: str) -> ArtifactRecord | None:
    for artifact in ctx.input_artifacts:
        if artifact.artifact_type == artifact_type:
            return artifact
    return None


def serialize_payload(artifact: ArtifactRecord) -> str:
    return json.dumps(artifact.payload, ensure_ascii=False, indent=2, default=str)
