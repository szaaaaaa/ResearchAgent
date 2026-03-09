from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agent.artifacts.base import Artifact
from src.agent.artifacts.serializers import from_json, to_json


class ArtifactRegistry:
    def __init__(self, artifacts_dir: Path | str) -> None:
        self.artifacts_dir = Path(artifacts_dir)

    @classmethod
    def for_runtime(cls, *, cfg: dict[str, Any], run_id: str | None = None) -> "ArtifactRegistry":
        events_file = str(cfg.get("_events_file", "") or "").strip()
        if events_file:
            return cls(Path(events_file).resolve().parent / "artifacts")

        root = Path(cfg.get("_root", ".")).resolve()
        resolved_run_id = str(run_id or cfg.get("_run_id") or "manual")
        return cls(root / "run_outputs" / resolved_run_id / "artifacts")

    def save(self, artifact: Artifact) -> Path:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = self.artifacts_dir / f"{artifact.artifact_type}_{artifact.artifact_id}.json"
        path.write_text(to_json(artifact), encoding="utf-8")
        return path

    def load(self, artifact_id: str) -> Artifact:
        for path in sorted(self.artifacts_dir.glob(f"*_{artifact_id}.json")):
            return from_json(path.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"Artifact not found: {artifact_id}")

    def list_by_type(self, artifact_type: str) -> list[Artifact]:
        artifacts = [
            from_json(path.read_text(encoding="utf-8"))
            for path in sorted(self.artifacts_dir.glob(f"{artifact_type}_*.json"))
        ]
        artifacts.sort(key=lambda artifact: (artifact.created_at, artifact.artifact_id))
        return artifacts

    def get_latest(self, artifact_type: str) -> Artifact | None:
        paths = list(self.artifacts_dir.glob(f"{artifact_type}_*.json"))
        if not paths:
            return None
        latest_path = max(paths, key=lambda path: (path.stat().st_mtime_ns, path.name))
        return from_json(latest_path.read_text(encoding="utf-8"))
