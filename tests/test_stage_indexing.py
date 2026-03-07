from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from src.agent.core.executor import TaskResult
from src.agent.stages.indexing import index_sources


class StageIndexingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path("tests/.tmp_stage_indexing")
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_preserves_existing_ids_when_nothing_new(self) -> None:
        state = {
            "topic": "RAG",
            "papers": [],
            "web_sources": [],
            "indexed_paper_ids": ["old-paper-id"],
            "indexed_web_ids": ["old-web-id"],
            "_cfg": {"_root": ".", "_run_id": "", "index": {}, "metadata_store": {}},
        }

        out = index_sources(
            state,
            state_view=lambda x: x,
            get_cfg=lambda x: x.get("_cfg", {}),
            ns=lambda x: x,
            dispatch=lambda task, cfg: TaskResult(success=True, data={}),
        )

        self.assertIn("old-paper-id", out["indexed_paper_ids"])
        self.assertIn("old-web-id", out["indexed_web_ids"])

    def test_indexes_new_papers_and_web_sources(self) -> None:
        pdf_path = self.tmp_dir / "paper-a.pdf"
        pdf_path.write_text("pdf", encoding="utf-8")
        state = {
            "topic": "RAG",
            "iteration": 0,
            "papers": [{"uid": "paper-a", "pdf_path": str(pdf_path)}],
            "web_sources": [{"uid": "web-a", "body": "x" * 120}],
            "indexed_paper_ids": ["old-paper-id"],
            "indexed_web_ids": ["old-web-id"],
            "_cfg": {
                "_root": ".",
                "_run_id": "run-1",
                "index": {},
                "metadata_store": {},
                "agent": {"staged_indexing": {}},
            },
        }
        actions: list[str] = []
        collection_names: dict[str, str] = {}

        def dispatch(task, cfg):
            actions.append(task.action)
            if "collection_name" in task.params:
                collection_names[task.action] = task.params["collection_name"]
            if task.action == "index_pdf_documents":
                return TaskResult(success=True, data={"indexed_docs": ["paper-doc"]})
            if task.action == "chunk_text":
                return TaskResult(success=True, data={"chunks": ["chunk-1"]})
            return TaskResult(success=True, data={})

        out = index_sources(
            state,
            state_view=lambda x: x,
            get_cfg=lambda x: x.get("_cfg", {}),
            ns=lambda x: x,
            dispatch=dispatch,
        )

        self.assertEqual(out["indexed_paper_ids"], ["old-paper-id", "paper-doc"])
        self.assertEqual(out["indexed_web_ids"], ["old-web-id", "web-a"])
        self.assertIn("init_run_tracking", actions)
        self.assertIn("index_pdf_documents", actions)
        self.assertIn("build_web_index", actions)
        self.assertEqual(collection_names["index_pdf_documents"], "papers__all_minilm_l6_v2")
        self.assertEqual(collection_names["build_web_index"], "web_sources__all_minilm_l6_v2")

    def test_second_iteration_enriches_priority_papers_with_figures(self) -> None:
        pdf_path = self.tmp_dir / "paper-a.pdf"
        pdf_path.write_text("pdf", encoding="utf-8")
        state = {
            "topic": "RAG",
            "iteration": 1,
            "papers": [{"uid": "paper-a", "pdf_path": str(pdf_path)}],
            "web_sources": [],
            "indexed_paper_ids": ["paper-a"],
            "figure_indexed_paper_ids": [],
            "claim_evidence_map": [{"research_question": "RQ1", "claim": "x", "evidence": [{"uid": "paper-a"}]}],
            "analyses": [{"uid": "paper-a", "relevance_score": 0.9}],
            "_cfg": {
                "_root": ".",
                "_run_id": "run-1",
                "ingest": {"figure": {"enabled": True}},
                "index": {},
                "metadata_store": {},
                "agent": {
                    "staged_indexing": {
                        "enabled": True,
                        "figure_enrichment_start_iteration": 1,
                        "figure_top_papers": 2,
                    }
                },
            },
        }
        figure_calls: list[dict] = []

        def dispatch(task, cfg):
            if task.action == "index_pdf_documents":
                figure_calls.append(dict(task.params))
                return TaskResult(success=True, data={"indexed_docs": ["paper-a"], "processed_docs": ["paper-a"]})
            return TaskResult(success=True, data={})

        out = index_sources(
            state,
            state_view=lambda x: x,
            get_cfg=lambda x: x.get("_cfg", {}),
            ns=lambda x: x,
            dispatch=dispatch,
        )

        self.assertEqual(len(figure_calls), 1)
        self.assertFalse(figure_calls[0]["include_text_chunks"])
        self.assertTrue(figure_calls[0]["allow_existing_doc_updates"])
        self.assertEqual(out["figure_indexed_paper_ids"], ["paper-a"])


if __name__ == "__main__":
    unittest.main()
