from __future__ import annotations

import unittest

from scripts.run_agent import _resolve_report_text


class RunAgentReportTextTest(unittest.TestCase):
    def test_returns_final_report_when_present(self) -> None:
        text = _resolve_report_text({"report": {"report": "final body"}})
        self.assertEqual(text, "final body")

    def test_returns_paused_report_when_waiting_for_results(self) -> None:
        text = _resolve_report_text({"await_experiment_results": True})
        self.assertIn("Research Run Paused", text)

    def test_returns_incomplete_report_when_empty(self) -> None:
        text = _resolve_report_text({"status": "Experiment review: warn (7 issues)"})
        self.assertIn("Research Run Incomplete", text)
        self.assertIn("Experiment review: warn (7 issues)", text)


if __name__ == "__main__":
    unittest.main()
