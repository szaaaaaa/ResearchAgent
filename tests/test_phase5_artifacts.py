from __future__ import annotations

from pathlib import Path
import shutil
import unittest

from src.agent.artifacts.registry import ArtifactRegistry
from src.agent.artifacts.serializers import from_json, to_json
from src.agent.core.artifact_utils import make_artifact, records_to_artifacts


def _artifact(artifact_type: str, payload: dict) -> object:
    return records_to_artifacts(
        [make_artifact(artifact_type=artifact_type, producer="unit_test", payload=payload, source_inputs=["seed"])]
    )[0]


class Phase5ArtifactsTest(unittest.TestCase):
    def test_all_phase1_artifacts_roundtrip_json(self) -> None:
        fixtures = {
            "TopicBrief": {"topic": "t", "scope": {"intent": "review"}},
            "SearchPlan": {"research_questions": ["rq"], "search_queries": ["q"], "query_routes": {"q": {}}},
            "CorpusSnapshot": {"papers": [], "web_sources": [], "indexed_paper_ids": []},
            "PaperNote": {"uid": "p1", "title": "Paper", "key_findings": []},
            "RelatedWorkMatrix": {"narrative": "n", "claims": []},
            "GapMap": {"gaps": ["g1"]},
            "ExperimentPlan": {"domain": "machine_learning", "rq_experiments": [{"research_question": "rq"}]},
            "ExperimentResults": {"status": "validated", "runs": [{"run_id": "run-1"}], "summaries": []},
            "ExperimentAnalysis": {"summary": "Validated one run.", "key_findings": ["f1"]},
            "PerformanceMetrics": {"validated": True, "run_count": 1},
            "ResearchReport": {"report": "# Report\n\ncontent"},
            "CritiqueReport": {"verdict": {"action": "continue"}, "details": {}},
        }
        for artifact_type, payload in fixtures.items():
            with self.subTest(artifact_type=artifact_type):
                artifact = _artifact(artifact_type, payload)
                restored = from_json(to_json(artifact))
                self.assertEqual(restored.artifact_type, artifact_type)
                self.assertEqual(restored.payload, payload)

    def test_artifact_registry_save_load_and_list(self) -> None:
        tmpdir = Path("tests/.tmp_phase5_artifacts")
        shutil.rmtree(tmpdir, ignore_errors=True)
        tmpdir.mkdir(parents=True, exist_ok=True)
        try:
            registry = ArtifactRegistry(tmpdir)
            older = _artifact("PaperNote", {"uid": "p1", "title": "Older"})
            newer = _artifact("PaperNote", {"uid": "p2", "title": "Newer"})
            registry.save(older)
            registry.save(newer)

            loaded = registry.load(newer.artifact_id)
            listed = registry.list_by_type("PaperNote")

            self.assertEqual(loaded.artifact_id, newer.artifact_id)
            self.assertEqual([artifact.artifact_type for artifact in listed], ["PaperNote", "PaperNote"])
            self.assertEqual(registry.get_latest("PaperNote").artifact_id, newer.artifact_id)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
