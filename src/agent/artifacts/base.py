from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.agent.core.schemas import ArtifactRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ArtifactMeta:
    artifact_type: str
    artifact_id: str
    producer: str
    source_inputs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)


@dataclass(frozen=True)
class Artifact:
    meta: ArtifactMeta
    payload: Any

    @property
    def artifact_type(self) -> str:
        return self.meta.artifact_type

    @property
    def artifact_id(self) -> str:
        return self.meta.artifact_id

    @property
    def producer(self) -> str:
        return self.meta.producer

    @property
    def source_inputs(self) -> list[str]:
        return list(self.meta.source_inputs)

    @property
    def created_at(self) -> str:
        return self.meta.created_at

    def to_record(self) -> ArtifactRecord:
        return ArtifactRecord(
            artifact_type=self.meta.artifact_type,
            artifact_id=self.meta.artifact_id,
            producer=self.meta.producer,
            source_inputs=list(self.meta.source_inputs),
            payload=self.payload,
            created_at=self.meta.created_at,
        )
