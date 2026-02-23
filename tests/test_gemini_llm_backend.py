from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.agent.core.factories import create_llm_backend
from src.agent.infra.llm.gemini_chat_client import generate_gemini_chat_completion


class GeminiLLMBackendTest(unittest.TestCase):
    def test_create_gemini_backend_resolvable(self) -> None:
        backend = create_llm_backend({"providers": {"llm": {"backend": "gemini_chat"}}})
        self.assertTrue(callable(getattr(backend, "generate", None)))

    @patch("src.agent.infra.llm.gemini_chat_client._sdk_generate_content")
    def test_generate_gemini_chat_completion_success(self, mock_sdk) -> None:
        mock_sdk.return_value = SimpleNamespace(text="hello\nworld")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            out = generate_gemini_chat_completion(
                system_prompt="sys",
                user_prompt="usr",
                model="gemini-2.0-flash",
                temperature=0.2,
                cfg={},
            )
        self.assertEqual(out, "hello\nworld")
        kwargs = mock_sdk.call_args.kwargs
        self.assertEqual(kwargs["api_key"], "test-key")
        self.assertEqual(kwargs["model"], "gemini-2.0-flash")
        self.assertEqual(kwargs["system_prompt"], "sys")
        self.assertEqual(kwargs["user_prompt"], "usr")

    @patch("src.agent.infra.llm.gemini_chat_client._sdk_generate_content")
    def test_generate_gemini_chat_completion_uses_google_api_key_fallback(self, mock_sdk) -> None:
        mock_sdk.return_value = SimpleNamespace(text="ok")
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "g-key"}, clear=True):
            out = generate_gemini_chat_completion(
                system_prompt="",
                user_prompt="usr",
                model="gemini-2.0-flash",
                temperature=0.2,
                cfg={},
            )
        self.assertEqual(out, "ok")
        self.assertEqual(mock_sdk.call_args.kwargs["api_key"], "g-key")

    @patch("src.agent.infra.llm.gemini_chat_client._sdk_generate_content")
    def test_generate_gemini_chat_completion_empty_text_raises(self, mock_sdk) -> None:
        mock_sdk.return_value = SimpleNamespace(text="")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            with self.assertRaises(RuntimeError):
                generate_gemini_chat_completion(
                    system_prompt="",
                    user_prompt="usr",
                    model="gemini-2.0-flash",
                    temperature=0.2,
                    cfg={},
                )

    def test_generate_gemini_chat_completion_requires_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                generate_gemini_chat_completion(
                    system_prompt="sys",
                    user_prompt="usr",
                    model="gemini-2.0-flash",
                    temperature=0.2,
                    cfg={},
                )


if __name__ == "__main__":
    unittest.main()
