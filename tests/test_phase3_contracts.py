from __future__ import annotations

import unittest

from src.agent.core.config import normalize_and_validate_config
from src.agent.core.factories import create_llm_backend, create_retriever_backend, create_search_backend
from src.agent.plugins.registry import (
    register_llm_backend,
    register_retriever_backend,
    register_search_backend,
)


class _DummyLLMBackend:
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        cfg: dict,
    ) -> str:
        return "ok"


class _DummySearchBackend:
    def fetch(
        self,
        *,
        cfg: dict,
        root,
        academic_queries,
        web_queries,
        query_routes,
    ):
        return {"papers": [], "web_sources": []}


class _DummyRetrieverBackend:
    def retrieve(
        self,
        *,
        persist_dir: str,
        collection_name: str,
        query: str,
        top_k: int,
        candidate_k,
        reranker_model,
        allowed_doc_ids,
        cfg: dict,
    ):
        return [{"text": "x"}]


class Phase3ContractsTest(unittest.TestCase):
    def test_normalize_config_defaults(self) -> None:
        cfg = normalize_and_validate_config({})
        self.assertEqual(cfg["llm"]["provider"], "gemini")
        self.assertEqual(cfg["providers"]["llm"]["backend"], "gemini_chat")
        self.assertEqual(cfg["providers"]["search"]["backend"], "default_search")
        self.assertEqual(cfg["providers"]["retrieval"]["backend"], "default_retriever")
        self.assertIn("analysis_web_content_max_chars", cfg["agent"]["limits"])
        self.assertIn("arxiv", cfg["sources"])
        self.assertIn("web", cfg["sources"])

    def test_builtin_backends_are_resolvable(self) -> None:
        cfg = normalize_and_validate_config({})
        try:
            search = create_search_backend(cfg)
        except ValueError as exc:
            self.assertIn("Unknown search backend", str(exc))
        else:
            self.assertTrue(callable(getattr(search, "fetch", None)))
        try:
            llm = create_llm_backend(cfg)
        except ValueError as exc:
            self.assertIn("Unknown LLM backend", str(exc))
        else:
            self.assertTrue(callable(getattr(llm, "generate", None)))
        try:
            retriever = create_retriever_backend(cfg)
        except ValueError as exc:
            self.assertIn("Unknown retriever backend", str(exc))
        else:
            self.assertTrue(callable(getattr(retriever, "retrieve", None)))

    def test_custom_backend_registration(self) -> None:
        register_llm_backend("dummy_llm_contract", _DummyLLMBackend())
        register_search_backend("dummy_search_contract", _DummySearchBackend())
        register_retriever_backend("dummy_retriever_contract", _DummyRetrieverBackend())
        cfg = normalize_and_validate_config(
            {
                "llm": {"provider": "openai"},
                "providers": {
                    "llm": {"backend": "dummy_llm_contract"},
                    "search": {"backend": "dummy_search_contract"},
                    "retrieval": {"backend": "dummy_retriever_contract"},
                }
            }
        )
        llm = create_llm_backend(cfg)
        search = create_search_backend(cfg)
        retriever = create_retriever_backend(cfg)
        self.assertEqual(llm.generate(system_prompt="", user_prompt="", model="m", temperature=0.0, cfg={}), "ok")
        self.assertEqual(search.fetch(cfg={}, root=".", academic_queries=[], web_queries=[], query_routes={}), {"papers": [], "web_sources": []})
        self.assertEqual(
            retriever.retrieve(
                cfg={},
                persist_dir=".",
                collection_name="papers",
                query="x",
                top_k=1,
                candidate_k=None,
                reranker_model=None,
                allowed_doc_ids=None,
            ),
            [{"text": "x"}],
        )


if __name__ == "__main__":
    unittest.main()
