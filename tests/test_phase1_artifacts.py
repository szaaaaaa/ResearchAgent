from __future__ import annotations

from types import SimpleNamespace
import unittest

from scripts.run_agent import _export_artifacts
from src.agent.core.artifact_utils import make_artifact
from src.agent.reviewers.retrieval_reviewer import review_retrieval
from src.agent.stages.planning import plan_research
from src.agent.stages.retrieval import fetch_sources
from src.agent.stages.synthesis import synthesize


class Phase1ArtifactsTest(unittest.TestCase):
    def test_make_artifact_has_required_fields(self) -> None:
        artifact = make_artifact(
            artifact_type="TopicBrief",
            producer="plan_research",
            payload={"topic": "test"},
            source_inputs=["test"],
        )
        self.assertEqual(artifact["artifact_type"], "TopicBrief")
        self.assertEqual(artifact["producer"], "plan_research")
        self.assertIn("artifact_id", artifact)
        self.assertIn("created_at", artifact)

    def test_plan_research_emits_topic_and_search_plan_artifacts(self) -> None:
        state = {
            "topic": "concept drift forecasting",
            "iteration": 0,
            "findings": [],
            "gaps": [],
            "search_queries": [],
            "artifacts": [],
            "_cfg": {"agent": {"max_queries_per_iteration": 2}},
        }

        update = plan_research(
            state,
            llm_call=lambda *args, **kwargs: "{}",
            parse_json=lambda raw: {
                "research_questions": ["RQ1"],
                "academic_queries": ["q1"],
                "web_queries": [],
            },
        )

        artifacts = update["artifacts"]
        types = [item["artifact_type"] for item in artifacts]
        self.assertEqual(types, ["TopicBrief", "SearchPlan"])

    def test_fetch_sources_emits_corpus_snapshot_artifact(self) -> None:
        state = {
            "topic": "concept drift forecasting",
            "_academic_queries": ["q1"],
            "_web_queries": [],
            "query_routes": {},
            "papers": [],
            "web_sources": [],
            "indexed_paper_ids": [],
            "artifacts": [],
            "_cfg": {"_root": "."},
        }

        update = fetch_sources(
            state,
            dispatch=lambda *args, **kwargs: SimpleNamespace(
                success=True,
                data={
                    "papers": [
                        {
                            "uid": "p1",
                            "title": "Paper 1",
                            "abstract": "concept drift forecasting replay",
                            "source": "arxiv",
                        }
                    ],
                    "web_sources": [],
                },
            ),
            build_topic_keywords=lambda state, cfg: {"concept", "drift", "forecasting"},
            build_topic_anchor_terms=lambda state, cfg: set(),
            is_topic_relevant=lambda **kwargs: True,
        )

        artifacts = update["artifacts"]
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0]["artifact_type"], "CorpusSnapshot")

    def test_synthesize_emits_related_work_and_gap_artifacts(self) -> None:
        state = {
            "topic": "concept drift forecasting",
            "research_questions": ["What methods handle drift?"],
            "analyses": [
                {
                    "uid": "p1",
                    "title": "Paper 1",
                    "summary": "Summary",
                    "key_findings": ["Finding"],
                    "methodology": "Method",
                    "credibility": "high",
                    "relevance_score": 0.9,
                    "source": "arxiv",
                    "url": "https://arxiv.org/abs/1234.5678",
                    "source_tier": "A",
                }
            ],
            "artifacts": [],
            "_cfg": {},
        }

        update = synthesize(
            state,
            llm_call=lambda *args, **kwargs: "{}",
            parse_json=lambda raw: {"synthesis": "Narrative", "gaps": ["Gap 1"]},
        )

        types = [item["artifact_type"] for item in update["artifacts"]]
        self.assertEqual(types, ["RelatedWorkMatrix", "GapMap"])

    def test_review_retrieval_emits_critique_report_artifact(self) -> None:
        state = {
            "papers": [{"uid": "p1", "title": "Paper 1", "year": 2025, "venue": "A", "source": "arxiv"}],
            "web_sources": [],
            "analyses": [],
            "research_questions": ["What methods handle drift robustly online?"],
            "search_queries": ["online drift methods"],
            "artifacts": [],
            "_cfg": {"reviewer": {"retrieval": {"min_sources": 1, "min_unique_venues": 1}}},
        }

        update = review_retrieval(state)
        artifacts = update["artifacts"]
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0]["artifact_type"], "CritiqueReport")

    def test_export_artifacts_filters_non_dict_items(self) -> None:
        exported = _export_artifacts({"artifacts": [{"artifact_type": "TopicBrief"}, "bad"]})
        self.assertEqual(exported, [{"artifact_type": "TopicBrief"}])


if __name__ == "__main__":
    unittest.main()
