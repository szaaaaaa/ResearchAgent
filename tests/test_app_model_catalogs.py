from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import app


class AppModelCatalogTest(unittest.TestCase):
    def test_first_secret_value_reads_only_environment(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}, clear=True), patch.object(
            app,
            "_read_env_file",
            return_value={"GEMINI_API_KEY": "file-key"},
        ):
            out = app._first_secret_value("GEMINI_API_KEY", "GOOGLE_API_KEY")

        self.assertEqual(out, "env-key")

    def test_credential_status_ignores_dotenv(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch.object(
            app,
            "_read_env_file",
            return_value={"GEMINI_API_KEY": "file-key"},
        ):
            out = app._credential_status()

        self.assertEqual(out["GEMINI_API_KEY"], {"present": False, "source": "missing"})

    def test_save_credentials_does_not_write_dotenv(self) -> None:
        request = MagicMock()
        request.json = AsyncMock(return_value={"GEMINI_API_KEY": "browser-key"})

        with patch.object(app, "_write_env_file") as write_mock:
            out = asyncio.run(app.save_credentials(request))

        write_mock.assert_not_called()
        self.assertEqual(out["status"], "success")

    def test_build_openai_catalog_keeps_only_llm_models(self) -> None:
        payload = [
            {"id": "gpt-4o"},
            {"id": "o4-mini"},
            {"id": "text-embedding-3-small"},
            {"id": "gpt-image-1"},
            {"id": "whisper-1"},
        ]

        out = app._build_openai_catalog(payload)

        self.assertEqual(out["vendors"], [{"value": "openai", "label": "OpenAI"}])
        self.assertEqual(
            [item["value"] for item in out["modelsByVendor"]["openai"]],
            ["gpt-4o", "o4-mini"],
        )

    def test_build_gemini_catalog_keeps_generate_content_models(self) -> None:
        payload = [
            {
                "name": "models/gemini-2.5-pro",
                "displayName": "Gemini 2.5 Pro",
                "supportedGenerationMethods": ["generateContent", "countTokens"],
            },
            {
                "name": "models/text-embedding-004",
                "displayName": "Text Embedding 004",
                "supportedGenerationMethods": ["embedContent"],
            },
            {
                "name": "models/aqa",
                "displayName": "AQA",
                "supportedGenerationMethods": ["generateContent"],
            },
        ]

        out = app._build_gemini_catalog(payload)

        self.assertEqual(out["vendors"], [{"value": "google", "label": "Google"}])
        self.assertEqual(
            [item["value"] for item in out["modelsByVendor"]["google"]],
            ["gemini-2.5-pro"],
        )

    def test_openai_models_endpoint_requires_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch.object(app, "_read_env_file", return_value={}):
            out = app.get_openai_models()

        self.assertTrue(out["missing_api_key"])
        self.assertEqual(out["model_count"], 0)

    def test_gemini_models_endpoint_uses_google_api_key_fallback(self) -> None:
        payload = [
            {
                "name": "models/gemini-2.5-flash",
                "displayName": "Gemini 2.5 Flash",
                "supportedGenerationMethods": ["generateContent"],
            }
        ]
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=True), patch.object(
            app,
            "_read_env_file",
            return_value={},
        ), patch.object(app, "_request_paginated_json", return_value=payload) as request_mock:
            out = app.get_gemini_models()

        request_mock.assert_called_once()
        self.assertEqual(out["model_count"], 1)
        self.assertEqual(out["modelsByVendor"]["google"][0]["value"], "gemini-2.5-flash")


if __name__ == "__main__":
    unittest.main()
