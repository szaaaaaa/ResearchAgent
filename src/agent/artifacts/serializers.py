from __future__ import annotations

import json

from src.agent.artifacts.base import Artifact
from src.agent.artifacts.schemas import artifact_from_record


def to_json(artifact: Artifact) -> str:
    return json.dumps(artifact.to_record(), ensure_ascii=False, indent=2)


def from_json(json_str: str) -> Artifact:
    data = json.loads(json_str)
    return artifact_from_record(data)
