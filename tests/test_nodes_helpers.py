from __future__ import annotations

import json
import unittest

from src.agent import nodes


class NodesHelpersTest(unittest.TestCase):
    def test_parse_json_handles_markdown_fence(self) -> None:
        raw = "```json\n{\"a\": 1, \"b\": \"x\"}\n```"
        out = nodes._parse_json(raw)
        self.assertEqual(out, {"a": 1, "b": "x"})

    def test_parse_json_invalid_raises(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            nodes._parse_json("not-json")

    def test_infer_intent_and_default_sections(self) -> None:
        self.assertEqual(nodes._infer_intent("A vs B"), "comparison")
        self.assertEqual(nodes._infer_intent("RAG migration roadmap"), "roadmap")
        self.assertEqual(nodes._infer_intent("Plain topic"), "survey")
        self.assertEqual(len(nodes._default_sections_for_intent("comparison")), 5)
        self.assertEqual(len(nodes._default_sections_for_intent("roadmap")), 5)
        self.assertEqual(len(nodes._default_sections_for_intent("other")), 5)

    def test_load_budget_and_scope_respects_existing_state(self) -> None:
        state = {"topic": "x", "scope": {"intent": "custom"}, "budget": {"max_sections": 2}}
        cfg = {"agent": {"budget": {"max_sections": 9}}}
        scope, budget = nodes._load_budget_and_scope(state, cfg)
        self.assertEqual(scope, {"intent": "custom"})
        self.assertEqual(budget, {"max_sections": 2})

    def test_load_budget_and_scope_builds_from_cfg(self) -> None:
        state = {"topic": "A vs B in RAG"}
        cfg = {"agent": {"budget": {"max_research_questions": 2, "max_sections": 2, "max_references": 8}}}
        scope, budget = nodes._load_budget_and_scope(state, cfg)
        self.assertEqual(scope["intent"], "comparison")
        self.assertEqual(len(scope["allowed_sections"]), 2)
        self.assertEqual(budget["max_research_questions"], 2)
        self.assertEqual(budget["max_sections"], 2)
        self.assertEqual(budget["max_references"], 8)

    def test_load_budget_and_scope_reads_namespaced_state(self) -> None:
        state = {
            "planning": {
                "scope": {"intent": "custom"},
                "budget": {"max_sections": 1},
            }
        }
        scope, budget = nodes._load_budget_and_scope(state, {"agent": {"budget": {"max_sections": 9}}})
        self.assertEqual(scope, {"intent": "custom"})
        self.assertEqual(budget, {"max_sections": 1})

    def test_route_query_for_simple_and_deep_cases(self) -> None:
        simple = nodes._route_query("what is retrieval augmented generation", {"agent": {}})
        self.assertTrue(simple["simple"])
        self.assertTrue(simple["use_web"])
        self.assertFalse(simple["use_academic"])
        self.assertFalse(simple["download_pdf"])

        deep = nodes._route_query("rag benchmark latency tradeoff", {"agent": {}})
        self.assertFalse(deep["simple"])
        self.assertTrue(deep["use_web"])
        self.assertTrue(deep["use_academic"])
        self.assertTrue(deep["download_pdf"])

        simple_override = nodes._route_query(
            "what is retrieval augmented generation",
            {"agent": {"dynamic_retrieval": {"simple_query_academic": True, "simple_query_pdf": True}}},
        )
        self.assertTrue(simple_override["use_academic"])
        self.assertTrue(simple_override["download_pdf"])

    def test_route_query_uses_configurable_terms(self) -> None:
        cfg = {
            "agent": {
                "dynamic_retrieval": {
                    "simple_query_terms": ["plain"],
                    "deep_query_terms": ["hardcore"],
                }
            }
        }
        out_simple = nodes._route_query("plain overview", cfg)
        out_deep = nodes._route_query("plain hardcore benchmark", cfg)
        self.assertTrue(out_simple["simple"])
        self.assertFalse(out_deep["simple"])

    def test_is_topic_relevant_with_block_terms(self) -> None:
        kws = {"rag", "retrieval", "generation"}
        self.assertTrue(
            nodes._is_topic_relevant(
                text="A retrieval augmented generation tutorial",
                topic_keywords=kws,
                block_terms=[],
                min_hits=2,
            )
        )
        self.assertFalse(
            nodes._is_topic_relevant(
                text="Hanabi benchmark and game agents",
                topic_keywords=kws,
                block_terms=["hanabi"],
                min_hits=1,
            )
        )

    def test_uid_to_resolvable_url(self) -> None:
        self.assertEqual(
            nodes._uid_to_resolvable_url("arxiv:2401.12345"),
            "https://arxiv.org/abs/2401.12345",
        )
        self.assertEqual(
            nodes._uid_to_resolvable_url("doi:10.1000/xyz"),
            "https://doi.org/10.1000/xyz",
        )
        self.assertEqual(nodes._uid_to_resolvable_url("x"), "")

    def test_dedupe_and_rank_analyses(self) -> None:
        analyses = [
            {"uid": "arxiv:1", "title": "Old", "relevance_score": 0.1, "source": "arxiv"},
            {"uid": "arxiv:1", "title": "New", "relevance_score": 0.9, "source": "arxiv"},
            {"uid": "doi:10.1/x", "title": "DOI", "relevance_score": 0.8, "source": "web", "url": ""},
            {"title": "Web", "url": "https://example.com/path/", "relevance_score": 0.7, "source": "web"},
        ]
        out = nodes._dedupe_and_rank_analyses(analyses, max_items=10)
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0]["title"], "New")
        doi_item = next(x for x in out if x.get("uid") == "doi:10.1/x")
        self.assertEqual(doi_item["url"], "https://doi.org/10.1/x")

    def test_clean_reference_section_dedupes_and_limits(self) -> None:
        report = (
            "# Title\n\n"
            "## References\n"
            "- [A](https://example.com/a)\n"
            "- Duplicate https://example.com/a/\n"
            "- C https://example.com/c\n"
            "\n"
            "## Appendix\n"
            "ignored\n"
        )
        out = nodes._clean_reference_section(report, max_refs=2)
        self.assertIn("## References", out)
        self.assertIn("1. [A](https://example.com/a)", out)
        self.assertIn("2. C https://example.com/c", out)
        self.assertNotIn("Duplicate", out)
        self.assertNotIn("Appendix", out)

    def test_strip_outer_markdown_fence_removes_wrapper(self) -> None:
        report = (
            "```markdown\n"
            "# Title\n\n"
            "## References\n"
            "1. A https://example.com/a\n"
            "```\n"
        )
        out = nodes._strip_outer_markdown_fence(report)
        self.assertTrue(out.startswith("# Title"))
        self.assertNotIn("```markdown", out)
        self.assertNotIn("\n```\n", out)

        inner_code = "# Title\n\n```python\nprint(1)\n```\n"
        untouched = nodes._strip_outer_markdown_fence(inner_code)
        self.assertEqual(untouched, inner_code)

    def test_build_claim_evidence_map_avoids_duplicate_claims(self) -> None:
        analyses = [
            {
                "uid": "arxiv:1",
                "title": "Paper A",
                "summary": "Agentic RAG differs from traditional RAG through adaptive retrieval.",
                "key_findings": [
                    "Agentic RAG differs from traditional RAG through adaptive retrieval."
                ],
                "relevance_score": 0.9,
                "limitations": [],
                "source": "arxiv",
            },
            {
                "uid": "arxiv:2",
                "title": "Paper B",
                "summary": "Agentic RAG differs from traditional RAG through adaptive retrieval.",
                "key_findings": [
                    "Agentic RAG differs from traditional RAG through adaptive retrieval."
                ],
                "relevance_score": 0.8,
                "limitations": [],
                "source": "arxiv",
            },
        ]
        out = nodes._build_claim_evidence_map(
            research_questions=[
                "What are architecture differences in agentic RAG?",
                "How should we evaluate trajectories in agentic RAG?",
            ],
            analyses=analyses,
            core_min_a_ratio=0.7,
        )
        claims = [x["claim"] for x in out]
        self.assertEqual(len(claims), 2)
        self.assertEqual(len(set(claims)), 2)

    def test_compute_acceptance_metrics(self) -> None:
        empty = nodes._compute_acceptance_metrics(evidence_audit_log=[], report_critic={"issues": []})
        self.assertFalse(empty["a_ratio_pass"])
        self.assertFalse(empty["rq_coverage_pass"])
        self.assertTrue(empty["reference_budget_compliant"])

        metrics = nodes._compute_acceptance_metrics(
            evidence_audit_log=[
                {"a_ratio": 0.8, "evidence_count": 2},
                {"a_ratio": 0.6, "evidence_count": 1},
            ],
            report_critic={"issues": ["reference_budget_exceeded"]},
        )
        self.assertAlmostEqual(metrics["avg_a_evidence_ratio"], 0.7, places=6)
        self.assertTrue(metrics["a_ratio_pass"])
        self.assertAlmostEqual(metrics["rq_min2_evidence_rate"], 0.5, places=6)
        self.assertFalse(metrics["rq_coverage_pass"])
        self.assertFalse(metrics["reference_budget_compliant"])


if __name__ == "__main__":
    unittest.main()
