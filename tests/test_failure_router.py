from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from src.agent.core.executor import TaskRequest
from src.agent.core.executor_router import dispatch, register_executor
from src.agent.core.failure import FailureAction, classify_failure
from src.agent.providers import llm_provider


class FailureRouterTest(unittest.TestCase):
    def test_classify_failure_actions(self) -> None:
        self.assertEqual(
            classify_failure(RuntimeError("request timed out"), context="llm_call"),
            FailureAction.RETRY,
        )
        self.assertEqual(
            classify_failure(RuntimeError("401 unauthorized"), context="llm_call"),
            FailureAction.ABORT,
        )
        self.assertEqual(
            classify_failure(RuntimeError("content_policy blocked"), context="llm_call"),
            FailureAction.BACKOFF,
        )
        self.assertEqual(
            classify_failure(RuntimeError("parser failed"), context="scrape"),
            FailureAction.SKIP,
        )

    def test_llm_provider_backoff_to_fallback_model(self) -> None:
        backend = Mock()
        backend.generate.side_effect = [RuntimeError("content_policy refused"), "ok-fallback"]
        cfg = {
            "providers": {
                "llm": {"backend": "dummy", "retries": 0, "fallback_model": "gpt-4.1-mini"}
            }
        }
        with patch("src.agent.providers.llm_provider.create_llm_backend", return_value=backend):
            with patch("src.agent.providers.llm_provider.emit_event") as emit_mock:
                out = llm_provider.call_llm(
                    system_prompt="sys",
                    user_prompt="usr",
                    cfg=cfg,
                    model="gpt-4.1",
                )
        self.assertEqual(out, "ok-fallback")
        self.assertEqual(backend.generate.call_count, 2)
        self.assertEqual(backend.generate.call_args_list[0].kwargs["model"], "gpt-4.1")
        self.assertEqual(backend.generate.call_args_list[1].kwargs["model"], "gpt-4.1-mini")
        self.assertGreaterEqual(emit_mock.call_count, 1)
        first_payload = emit_mock.call_args_list[0].args[1]
        self.assertEqual(first_payload["event"], "failure_routed")
        self.assertEqual(first_payload["action"], "backoff")

    def test_llm_provider_abort_does_not_retry(self) -> None:
        backend = Mock()
        backend.generate.side_effect = RuntimeError("401 unauthorized")
        cfg = {"providers": {"llm": {"backend": "dummy", "retries": 3}}}
        with patch("src.agent.providers.llm_provider.create_llm_backend", return_value=backend):
            with patch("src.agent.providers.llm_provider.emit_event") as emit_mock:
                with self.assertRaises(RuntimeError):
                    llm_provider.call_llm(system_prompt="sys", user_prompt="usr", cfg=cfg)
        self.assertEqual(backend.generate.call_count, 1)
        payload = emit_mock.call_args.args[1]
        self.assertEqual(payload["event"], "failure_routed")
        self.assertEqual(payload["action"], "abort")

    def test_dispatch_emits_failure_routed_metadata_on_executor_exception(self) -> None:
        class _BadExecutor:
            def supported_actions(self):
                return ["unit_phase8_boom"]

            def execute(self, task, cfg):
                raise TimeoutError("timed out")

        register_executor(_BadExecutor())
        with patch("src.agent.core.executor_router.emit_event") as emit_mock:
            out = dispatch(TaskRequest(action="unit_phase8_boom", params={}), cfg={})
        self.assertFalse(out.success)
        self.assertEqual(out.metadata.get("failure_action"), "retry")
        payload = emit_mock.call_args.args[1]
        self.assertEqual(payload["event"], "failure_routed")
        self.assertIn("executor_dispatch:unit_phase8_boom", payload["context"])


if __name__ == "__main__":
    unittest.main()

