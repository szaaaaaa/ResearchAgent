from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List
from uuid import uuid4

from src.agent.artifacts.base import Artifact
from src.agent.artifacts.schemas import artifact_from_record
from src.agent.core.schemas import ArtifactRecord


def make_artifact(
    *,
    artifact_type: str,
    producer: str,
    payload: Dict[str, Any],
    source_inputs: Iterable[str] | None = None,
) -> ArtifactRecord:
    return ArtifactRecord(
        artifact_type=artifact_type,
        artifact_id=f"{artifact_type.lower()}_{uuid4().hex[:12]}",
        producer=producer,
        source_inputs=list(source_inputs or []),
        payload=payload,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def append_artifacts(existing: List[ArtifactRecord] | None, new_items: Iterable[ArtifactRecord]) -> List[ArtifactRecord]:
    merged: List[ArtifactRecord] = list(existing or [])
    merged.extend(list(new_items))
    return merged


def record_to_artifact(record: ArtifactRecord) -> Artifact:
    return artifact_from_record(record)


def records_to_artifacts(records: Iterable[ArtifactRecord]) -> List[Artifact]:
    return [record_to_artifact(record) for record in records]
