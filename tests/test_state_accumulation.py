"""Tests for S1: state accumulation semantics.

Verify that fetch_sources, index_sources, and analyze_sources return
cumulative lists so that later iterations with 0 new items do NOT
wipe historical data.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from src.agent import nodes
from src.agent.core.executor import TaskResult


class FetchSourcesCumulativeTest(unittest.TestCase):
    """S1: fetch_sources must return existing + new papers."""

    def _base_state(self):
        return {
            "topic": "RAG",
            "papers": [
                {"uid": "existing-1", "title": "Old Paper", "authors": [], "source": "arxiv"},
            ],
            "web_sources": [
                {"uid": "existing-web-1", "title": "Old Web", "source": "web"},
            ],
            "search_queries": ["RAG survey"],
            "_cfg": {
                "agent": {},
                "sources": {"arxiv": {"enabled": True}, "web": {"enabled": True}},
            },
        }

    @patch("src.agent.nodes.dispatch")
    def test_no_new_results_preserves_existing(self, mock_dispatch):
        """Second iteration with 0 new results must NOT wipe papers/web_sources."""
        mock_dispatch.return_value = TaskResult(
            success=True,
            data={"papers": [], "web_sources": []},
        )
        state = self._base_state()
        result = nodes.fetch_sources(state)
        # Cumulative: should still have the existing paper
        papers = result.get("papers") or result.get("research", {}).get("papers", [])
        web = result.get("web_sources") or result.get("research", {}).get("web_sources", [])
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["uid"], "existing-1")
        self.assertEqual(len(web), 1)
        self.assertEqual(web[0]["uid"], "existing-web-1")

    @patch("src.agent.nodes.dispatch")
    def test_new_results_merge_with_existing(self, mock_dispatch):
        """New papers are appended to existing cumulative list."""
        mock_dispatch.return_value = TaskResult(
            success=True,
            data={
                "papers": [
                    {"uid": "new-1", "title": "New Paper", "authors": [], "abstract": "RAG stuff", "source": "arxiv"},
                ],
                "web_sources": [],
            },
        )
        state = self._base_state()
        result = nodes.fetch_sources(state)
        papers = result.get("papers") or result.get("research", {}).get("papers", [])
        self.assertEqual(len(papers), 2)
        uids = {p["uid"] for p in papers}
        self.assertIn("existing-1", uids)
        self.assertIn("new-1", uids)

    @patch("src.agent.nodes.dispatch")
    def test_fetch_failure_preserves_existing(self, mock_dispatch):
        """Fetch failure must NOT wipe existing data."""
        mock_dispatch.return_value = TaskResult(success=False, error="timeout")
        state = self._base_state()
        result = nodes.fetch_sources(state)
        papers = result.get("papers") or result.get("research", {}).get("papers", [])
        self.assertEqual(len(papers), 1)


class AnalyzeSourcesCumulativeTest(unittest.TestCase):
    """S1: analyze_sources must return existing + new analyses."""

    @patch("src.agent.nodes._llm_call")
    @patch("src.agent.nodes.dispatch")
    def test_no_new_analyses_preserves_existing(self, mock_dispatch, mock_llm):
        existing_analysis = {
            "uid": "old-1",
            "title": "Existing",
            "summary": "old",
            "key_findings": ["old finding"],
            "source": "arxiv",
        }
        state = {
            "topic": "RAG",
            "papers": [],
            "web_sources": [],
            "analyses": [existing_analysis],
            "findings": ["old finding"],
            "_cfg": {"agent": {}, "llm": {"model": "gpt-4.1-mini"}, "index": {}},
        }
        result = nodes.analyze_sources(state)
        analyses = result.get("analyses") or result.get("research", {}).get("analyses", [])
        findings = result.get("findings") or result.get("research", {}).get("findings", [])
        self.assertEqual(len(analyses), 1)
        self.assertEqual(analyses[0]["uid"], "old-1")
        self.assertEqual(len(findings), 1)


class IndexSourcesCumulativeTest(unittest.TestCase):
    """S1: index_sources must return cumulative indexed IDs."""

    @patch("src.agent.nodes.dispatch")
    def test_no_new_indexes_preserves_existing_ids(self, mock_dispatch):
        mock_dispatch.return_value = TaskResult(success=True, data={})
        state = {
            "topic": "RAG",
            "papers": [],
            "web_sources": [],
            "indexed_paper_ids": ["old-paper-id"],
            "indexed_web_ids": ["old-web-id"],
            "_cfg": {
                "_root": ".",
                "_run_id": "",
                "index": {},
                "metadata_store": {},
            },
        }
        result = nodes.index_sources(state)
        paper_ids = (
            result.get("indexed_paper_ids")
            or result.get("research", {}).get("indexed_paper_ids", [])
        )
        web_ids = (
            result.get("indexed_web_ids")
            or result.get("research", {}).get("indexed_web_ids", [])
        )
        self.assertIn("old-paper-id", paper_ids)
        self.assertIn("old-web-id", web_ids)


if __name__ == "__main__":
    unittest.main()
