from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agent.core.config import normalize_and_validate_config
from src.agent.core.events import emit_event
from src.agent.core.secret_redaction import REDACTED, redact_data, redact_text
from src.agent.tracing.trace_logger import TraceLogger


class SecretRedactionTest(unittest.TestCase):
    def _tmp_dir(self, name: str) -> Path:
        path = Path("tests") / f".tmp_{name}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_config_rejects_inline_api_key(self) -> None:
        with self.assertRaises(ValueError):
            normalize_and_validate_config(
                {"providers": {"llm": {"api_key": "sk-test-secret-value"}}}
            )

    def test_config_allows_env_name_only(self) -> None:
        cfg = normalize_and_validate_config(
            {"providers": {"llm": {"backend": "gemini_chat", "gemini_api_key_env": "GEMINI_API_KEY"}}}
        )
        self.assertEqual(cfg["providers"]["llm"]["gemini_api_key_env"], "GEMINI_API_KEY")

    def test_redact_data_masks_sensitive_fields(self) -> None:
        out = redact_data(
            {
                "providers": {"llm": {"api_key": "secret-value", "gemini_api_key_env": "GEMINI_API_KEY"}},
                "token": "abc",
            }
        )
        self.assertEqual(out["providers"]["llm"]["api_key"], REDACTED)
        self.assertEqual(out["providers"]["llm"]["gemini_api_key_env"], "GEMINI_API_KEY")
        self.assertEqual(out["token"], REDACTED)

    def test_redact_text_masks_env_secret_values(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-secret-value"}, clear=False):
            out = redact_text("failure with sk-test-secret-value")
        self.assertEqual(out, f"failure with {REDACTED}")

    def test_event_file_masks_secret_text(self) -> None:
        path = self._tmp_dir("secret_redaction") / "events.log"
        if path.exists():
            path.unlink()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-secret-value"}, clear=False):
            emit_event({"_events_file": str(path)}, {"event": "x", "error": "Bearer sk-test-secret-value"})
        text = path.read_text(encoding="utf-8")
        self.assertIn(REDACTED, text)
        self.assertNotIn("sk-test-secret-value", text)

    def test_trace_logger_masks_secret_text(self) -> None:
        run_dir = self._tmp_dir("secret_trace")
        path = run_dir / "trace.jsonl"
        if path.exists():
            path.unlink()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-secret-value"}, clear=False):
            trace = TraceLogger(run_dir=run_dir)
            trace.log_stage("plan_research", {"iteration": 1, "status": "ok"}, error="bad sk-test-secret-value")
        text = path.read_text(encoding="utf-8")
        self.assertIn(REDACTED, text)
        self.assertNotIn("sk-test-secret-value", text)


if __name__ == "__main__":
    unittest.main()
