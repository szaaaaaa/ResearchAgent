from __future__ import annotations

import json
from pathlib import Path
import unittest
import uuid

from src.agent.core.events import instrument_node


class CoreEventsTest(unittest.TestCase):
    def test_instrument_node_writes_start_and_end_events(self) -> None:
        events_path = Path(f".events_test_{uuid.uuid4().hex}.log")
        try:
            def _node(state):
                return {"status": "ok", "papers": [{"uid": "p1"}]}

            wrapped = instrument_node("dummy_node", _node)
            wrapped({"run_id": "r1", "iteration": 2, "_cfg": {"_events_file": str(events_path)}})

            lines = [json.loads(x) for x in events_path.read_text(encoding="utf-8").splitlines() if x.strip()]
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0]["event"], "node_start")
            self.assertEqual(lines[0]["node"], "dummy_node")
            self.assertEqual(lines[1]["event"], "node_end")
            self.assertEqual(lines[1]["papers_count"], 1)
            self.assertEqual(lines[1]["status"], "ok")
        finally:
            if events_path.exists():
                events_path.unlink()

    def test_instrument_node_writes_error_event(self) -> None:
        events_path = Path(f".events_test_{uuid.uuid4().hex}.log")
        try:
            def _node(state):
                raise RuntimeError("boom")

            wrapped = instrument_node("failing_node", _node)
            with self.assertRaises(RuntimeError):
                wrapped({"run_id": "r1", "_cfg": {"_events_file": str(events_path)}})

            lines = [json.loads(x) for x in events_path.read_text(encoding="utf-8").splitlines() if x.strip()]
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0]["event"], "node_start")
            self.assertEqual(lines[1]["event"], "node_error")
            self.assertIn("boom", lines[1]["error"])
        finally:
            if events_path.exists():
                events_path.unlink()


if __name__ == "__main__":
    unittest.main()
