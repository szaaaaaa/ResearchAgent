from __future__ import annotations

import unittest
from unittest.mock import patch

from src.agent.core.executor import TaskRequest, TaskResult
from src.agent.core.executor_router import dispatch, register_executor
from src.agent.executors.index_executor import IndexExecutor
from src.agent.executors.llm_executor import LLMExecutor
from src.agent.executors.retrieval_executor import RetrievalExecutor
from src.agent.executors.search_executor import SearchExecutor


class _DummyExecutor:
    def supported_actions(self) -> list[str]:
        return ["unit_dummy_action"]

    def execute(self, task: TaskRequest, cfg: dict) -> TaskResult:
        return TaskResult(success=True, data={"action": task.action, "params": task.params})


class ExecutorCoreTest(unittest.TestCase):
    def test_task_request_and_result_construct(self) -> None:
        req = TaskRequest(action="search", params={"q": "rag"}, timeout_sec=12.5)
        self.assertEqual(req.action, "search")
        self.assertEqual(req.params["q"], "rag")
        self.assertAlmostEqual(req.timeout_sec, 12.5)

        ok = TaskResult(success=True, data={"x": 1})
        self.assertTrue(ok.success)
        self.assertEqual(ok.data["x"], 1)
        self.assertIsNone(ok.error)
        self.assertEqual(ok.metadata, {})

    def test_register_and_dispatch_routes(self) -> None:
        register_executor(_DummyExecutor())
        out = dispatch(TaskRequest(action="unit_dummy_action", params={"k": "v"}), cfg={})
        self.assertTrue(out.success)
        self.assertEqual(out.data["action"], "unit_dummy_action")
        self.assertEqual(out.data["params"], {"k": "v"})

    def test_dispatch_unregistered_action_fails(self) -> None:
        out = dispatch(TaskRequest(action="unit_unknown_action_404", params={}), cfg={})
        self.assertFalse(out.success)
        self.assertIn("No executor registered", out.error or "")

    def test_dispatch_triggers_bootstrap(self) -> None:
        with patch("src.agent.plugins.bootstrap.ensure_plugins_registered") as ensure_mock:
            dispatch(TaskRequest(action="unit_unknown_action_bootstrap_check", params={}), cfg={})
        ensure_mock.assert_called_once()


class ExecutorDelegationTest(unittest.TestCase):
    def test_search_executor_delegates_to_provider(self) -> None:
        executor = SearchExecutor()
        with patch(
            "src.agent.executors.search_executor.fetch_candidates",
            return_value={"papers": [{"uid": "p1"}], "web_sources": [{"uid": "w1"}]},
        ) as mock_fetch:
            out = executor.execute(
                TaskRequest(
                    action="search",
                    params={
                        "root": ".",
                        "academic_queries": ["qa"],
                        "web_queries": ["qw"],
                        "query_routes": {},
                    },
                ),
                cfg={},
            )
        self.assertTrue(out.success)
        self.assertEqual(out.data["papers"][0]["uid"], "p1")
        self.assertEqual(out.data["web_sources"][0]["uid"], "w1")
        self.assertEqual(mock_fetch.call_args.kwargs["academic_queries"], ["qa"])

    def test_retrieval_executor_delegates_to_provider(self) -> None:
        executor = RetrievalExecutor()
        with patch(
            "src.agent.executors.retrieval_executor.retrieve_chunks",
            return_value=[{"text": "chunk"}],
        ) as mock_retrieve:
            out = executor.execute(
                TaskRequest(
                    action="retrieve_chunks",
                    params={
                        "persist_dir": "tmp",
                        "collection_name": "papers",
                        "query": "rag",
                        "top_k": 3,
                        "candidate_k": 8,
                        "reranker_model": None,
                        "allowed_doc_ids": ["doc1"],
                    },
                ),
                cfg={},
            )
        self.assertTrue(out.success)
        self.assertEqual(len(out.data["hits"]), 1)
        self.assertEqual(mock_retrieve.call_args.kwargs["top_k"], 3)

    def test_llm_executor_delegates_to_provider(self) -> None:
        executor = LLMExecutor()
        with patch("src.agent.executors.llm_executor.call_llm", return_value="ok") as mock_call:
            out = executor.execute(
                TaskRequest(
                    action="llm_generate",
                    params={
                        "system_prompt": "sys",
                        "user_prompt": "usr",
                        "model": "gpt-4.1-mini",
                        "temperature": 0.2,
                    },
                ),
                cfg={},
            )
        self.assertTrue(out.success)
        self.assertEqual(out.data["text"], "ok")
        self.assertEqual(mock_call.call_args.kwargs["model"], "gpt-4.1-mini")

    def test_index_executor_delegates_pdf_index(self) -> None:
        executor = IndexExecutor()
        with patch(
            "src.agent.executors.index_executor.index_pdf_documents",
            return_value={"indexed_docs": ["doc1"]},
        ) as mock_index:
            out = executor.execute(
                TaskRequest(
                    action="index_pdf_documents",
                    params={
                        "persist_dir": "tmp",
                        "collection_name": "papers",
                        "pdfs": ["a.pdf"],
                        "chunk_size": 1200,
                        "overlap": 200,
                        "run_id": "r1",
                    },
                ),
                cfg={},
            )
        self.assertTrue(out.success)
        self.assertEqual(out.data["indexed_docs"], ["doc1"])
        self.assertEqual(mock_index.call_args.kwargs["collection_name"], "papers")

    def test_index_executor_delegates_chunk_text(self) -> None:
        executor = IndexExecutor()
        with patch(
            "src.agent.executors.index_executor.chunk_text",
            return_value=["c1", "c2"],
        ) as mock_chunk:
            out = executor.execute(
                TaskRequest(
                    action="chunk_text",
                    params={"text": "hello world", "chunk_size": 10, "overlap": 2},
                ),
                cfg={},
            )
        self.assertTrue(out.success)
        self.assertEqual(out.data["chunks"], ["c1", "c2"])
        self.assertEqual(mock_chunk.call_args.kwargs["chunk_size"], 10)


if __name__ == "__main__":
    unittest.main()
