from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from src.agent.core.budget import BudgetGuard
from src.agent.core import factories
from src.agent.providers.llm_adapter import ModelResponse
from src.agent.providers import llm_provider, retrieval_provider, search_provider


class FactoriesAndProvidersTest(unittest.TestCase):
    def test_create_llm_backend_resolves_name_from_config(self) -> None:
        dummy_backend = object()
        cfg = {"providers": {"llm": {"backend": "custom_llm"}}}
        with patch("src.agent.core.factories.ensure_plugins_registered") as ensure_mock:
            with patch("src.agent.core.factories.get_llm_backend", return_value=dummy_backend) as get_mock:
                out = factories.create_llm_backend(cfg)
        ensure_mock.assert_called_once()
        get_mock.assert_called_once_with("custom_llm")
        self.assertIs(out, dummy_backend)

    def test_create_search_backend_resolves_name_from_config(self) -> None:
        dummy_backend = object()
        cfg = {"providers": {"search": {"backend": "custom_search"}}}
        with patch("src.agent.core.factories.ensure_plugins_registered") as ensure_mock:
            with patch("src.agent.core.factories.get_search_backend", return_value=dummy_backend) as get_mock:
                out = factories.create_search_backend(cfg)
        ensure_mock.assert_called_once()
        get_mock.assert_called_once_with("custom_search")
        self.assertIs(out, dummy_backend)

    def test_create_retriever_backend_resolves_name_from_config(self) -> None:
        dummy_backend = object()
        cfg = {"providers": {"retrieval": {"backend": "custom_retriever"}}}
        with patch("src.agent.core.factories.ensure_plugins_registered") as ensure_mock:
            with patch("src.agent.core.factories.get_retriever_backend", return_value=dummy_backend) as get_mock:
                out = factories.create_retriever_backend(cfg)
        ensure_mock.assert_called_once()
        get_mock.assert_called_once_with("custom_retriever")
        self.assertIs(out, dummy_backend)

    def test_call_llm_uses_provider_defaults(self) -> None:
        provider = Mock()
        provider.generate.return_value = ModelResponse(content="ok", usage={}, model="provider-model")
        cfg = {
            "llm": {"provider": "openai"},
            "providers": {"llm": {"default_model": "provider-model", "default_temperature": 0.65}},
        }
        with patch("src.agent.providers.llm_provider.ensure_plugins_registered"):
            with patch("src.agent.providers.llm_provider.get_llm_provider", return_value=provider):
                result = llm_provider.call_llm(system_prompt="sys", user_prompt="usr", cfg=cfg)

        self.assertEqual(result, "ok")
        request = provider.generate.call_args.args[0]
        self.assertEqual(request.model, "provider-model")
        self.assertAlmostEqual(request.temperature, 0.65, places=6)
        self.assertEqual(request.system_prompt, "sys")
        self.assertEqual(request.user_prompt, "usr")

    def test_call_llm_retries_then_succeeds(self) -> None:
        provider = Mock()
        provider.generate.side_effect = [RuntimeError("first"), ModelResponse(content="ok-after-retry", usage={}, model="m")]
        cfg = {"llm": {"provider": "gemini"}, "providers": {"llm": {"retries": 1, "retry_backoff_sec": 0.01, "backend": "dummy"}}}
        with patch("src.agent.providers.llm_provider.ensure_plugins_registered"):
            with patch("src.agent.providers.llm_provider.get_llm_provider", return_value=provider):
                with patch("src.agent.providers.llm_provider.time.sleep") as sleep_mock:
                    out = llm_provider.call_llm(system_prompt="s", user_prompt="u", cfg=cfg)

        self.assertEqual(out, "ok-after-retry")
        self.assertEqual(provider.generate.call_count, 2)
        sleep_mock.assert_called_once_with(0.01)

    def test_call_llm_exhausts_retries_and_raises(self) -> None:
        provider = Mock()
        provider.generate.side_effect = RuntimeError("always-fail")
        cfg = {"llm": {"provider": "gemini"}, "providers": {"llm": {"retries": 2, "retry_backoff_sec": 0, "backend": "dummy"}}}
        with patch("src.agent.providers.llm_provider.ensure_plugins_registered"):
            with patch("src.agent.providers.llm_provider.get_llm_provider", return_value=provider):
                with self.assertRaises(RuntimeError):
                    llm_provider.call_llm(system_prompt="s", user_prompt="u", cfg=cfg)
        self.assertEqual(provider.generate.call_count, 3)

    def test_call_llm_records_budget_usage_when_guard_present(self) -> None:
        provider = Mock()
        provider.generate.return_value = ModelResponse(
            content="hello world",
            usage={"prompt_tokens": 3, "completion_tokens": 2},
            model="m",
        )
        guard = BudgetGuard(max_tokens=1000, max_api_calls=100, max_wall_time_sec=600)
        cfg = {"llm": {"provider": "gemini"}, "providers": {"llm": {"backend": "dummy"}}, "_budget_guard": guard}
        with patch("src.agent.providers.llm_provider.ensure_plugins_registered"):
            with patch("src.agent.providers.llm_provider.get_llm_provider", return_value=provider):
                out = llm_provider.call_llm(system_prompt="sys", user_prompt="usr", cfg=cfg)
        self.assertEqual(out, "hello world")
        usage = guard.usage()
        self.assertEqual(usage["api_calls"], 1)
        self.assertGreater(usage["tokens_used"], 0)

    def test_fetch_candidates_delegates_to_selected_backend(self) -> None:
        backend = Mock()
        expected = {"papers": [{"uid": "p1"}], "web_sources": [{"uid": "w1"}]}
        backend.fetch.return_value = expected
        cfg = {"providers": {"search": {"backend": "dummy_search"}}}
        query_routes = {"q1": {"use_web": True, "use_academic": True}}
        with patch("src.agent.providers.search_provider.create_search_backend", return_value=backend):
            out = search_provider.fetch_candidates(
                cfg=cfg,
                root=Path("."),
                academic_queries=["q1"],
                web_queries=["q1"],
                query_routes=query_routes,
            )
        self.assertEqual(out, expected)
        kwargs = backend.fetch.call_args.kwargs
        self.assertEqual(kwargs["cfg"], cfg)
        self.assertEqual(kwargs["academic_queries"], ["q1"])
        self.assertEqual(kwargs["web_queries"], ["q1"])
        self.assertEqual(kwargs["query_routes"], query_routes)

    def test_retrieve_chunks_delegates_to_selected_backend(self) -> None:
        backend = Mock()
        backend.retrieve.return_value = [{"text": "chunk"}]
        with patch("src.agent.providers.retrieval_provider.create_retriever_backend", return_value=backend):
            out = retrieval_provider.retrieve_chunks(
                cfg={"providers": {"retrieval": {"backend": "dummy"}}},
                persist_dir="p",
                collection_name="c",
                query="q",
                top_k=4,
                candidate_k=8,
                reranker_model="rm",
                allowed_doc_ids=["d1"],
            )
        self.assertEqual(out, [{"text": "chunk"}])
        kwargs = backend.retrieve.call_args.kwargs
        self.assertEqual(kwargs["persist_dir"], "p")
        self.assertEqual(kwargs["collection_name"], "c")
        self.assertEqual(kwargs["query"], "q")
        self.assertEqual(kwargs["top_k"], 4)
        self.assertEqual(kwargs["candidate_k"], 8)
        self.assertEqual(kwargs["reranker_model"], "rm")
        self.assertEqual(kwargs["allowed_doc_ids"], ["d1"])


if __name__ == "__main__":
    unittest.main()
