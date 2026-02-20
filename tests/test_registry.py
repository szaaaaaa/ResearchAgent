from __future__ import annotations

import unittest

from src.agent.plugins import registry


class RegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._llm_backup = dict(registry._LLM_BACKENDS)
        self._search_backup = dict(registry._SEARCH_BACKENDS)
        self._retriever_backup = dict(registry._RETRIEVER_BACKENDS)
        registry._LLM_BACKENDS.clear()
        registry._SEARCH_BACKENDS.clear()
        registry._RETRIEVER_BACKENDS.clear()

    def tearDown(self) -> None:
        registry._LLM_BACKENDS.clear()
        registry._LLM_BACKENDS.update(self._llm_backup)
        registry._SEARCH_BACKENDS.clear()
        registry._SEARCH_BACKENDS.update(self._search_backup)
        registry._RETRIEVER_BACKENDS.clear()
        registry._RETRIEVER_BACKENDS.update(self._retriever_backup)

    def test_register_and_get_llm_backend_case_insensitive(self) -> None:
        backend = object()
        registry.register_llm_backend("  My_LLM  ", backend)
        self.assertIs(registry.get_llm_backend("my_llm"), backend)
        self.assertIs(registry.get_llm_backend("MY_LLM"), backend)

    def test_register_and_get_search_backend_case_insensitive(self) -> None:
        backend = object()
        registry.register_search_backend("  My_Search  ", backend)
        self.assertIs(registry.get_search_backend("my_search"), backend)
        self.assertIs(registry.get_search_backend("MY_SEARCH"), backend)

    def test_empty_backend_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            registry.register_llm_backend("  ", object())
        with self.assertRaises(ValueError):
            registry.register_search_backend("", object())
        with self.assertRaises(ValueError):
            registry.register_retriever_backend(" ", object())

    def test_register_and_get_retriever_backend_case_insensitive(self) -> None:
        backend = object()
        registry.register_retriever_backend("  My_Retriever  ", backend)
        self.assertIs(registry.get_retriever_backend("my_retriever"), backend)
        self.assertIs(registry.get_retriever_backend("MY_RETRIEVER"), backend)

    def test_unknown_backend_error_contains_supported(self) -> None:
        registry.register_llm_backend("alpha", object())
        registry.register_llm_backend("beta", object())
        with self.assertRaises(ValueError) as cm_llm:
            registry.get_llm_backend("missing")
        self.assertIn("Unknown LLM backend", str(cm_llm.exception))
        self.assertIn("alpha", str(cm_llm.exception))
        self.assertIn("beta", str(cm_llm.exception))

        registry.register_search_backend("s1", object())
        with self.assertRaises(ValueError) as cm_search:
            registry.get_search_backend("missing")
        self.assertIn("Unknown search backend", str(cm_search.exception))
        self.assertIn("s1", str(cm_search.exception))

        registry.register_retriever_backend("r1", object())
        with self.assertRaises(ValueError) as cm_retriever:
            registry.get_retriever_backend("missing")
        self.assertIn("Unknown retriever backend", str(cm_retriever.exception))
        self.assertIn("r1", str(cm_retriever.exception))


if __name__ == "__main__":
    unittest.main()
