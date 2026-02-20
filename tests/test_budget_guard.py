from __future__ import annotations

import unittest
from unittest.mock import patch

from src.agent.core.budget import BudgetGuard


class BudgetGuardTest(unittest.TestCase):
    def test_check_not_exceeded(self) -> None:
        guard = BudgetGuard(max_tokens=100, max_api_calls=10, max_wall_time_sec=600)
        guard.record_llm_call(prompt_tokens=10, completion_tokens=5)
        out = guard.check()
        self.assertFalse(out["exceeded"])
        self.assertIsNone(out["reason"])
        self.assertEqual(out["usage"]["tokens_used"], 15)
        self.assertEqual(out["usage"]["api_calls"], 1)

    def test_token_budget_exceeded(self) -> None:
        guard = BudgetGuard(max_tokens=10, max_api_calls=100, max_wall_time_sec=600)
        guard.record_llm_call(prompt_tokens=8, completion_tokens=3)
        out = guard.check()
        self.assertTrue(out["exceeded"])
        self.assertIn("Token budget exhausted", out["reason"])

    def test_api_call_budget_exceeded(self) -> None:
        guard = BudgetGuard(max_tokens=1000, max_api_calls=2, max_wall_time_sec=600)
        guard.record_llm_call(prompt_tokens=1, completion_tokens=1)
        guard.record_llm_call(prompt_tokens=1, completion_tokens=1)
        out = guard.check()
        self.assertTrue(out["exceeded"])
        self.assertIn("API call budget exhausted", out["reason"])

    def test_wall_time_budget_exceeded(self) -> None:
        guard = BudgetGuard(max_tokens=1000, max_api_calls=100, max_wall_time_sec=5)
        with patch("src.agent.core.budget.time.time", return_value=guard._start_time + 7):
            out = guard.check()
        self.assertTrue(out["exceeded"])
        self.assertIn("Wall time exceeded", out["reason"])


if __name__ == "__main__":
    unittest.main()

