from __future__ import annotations

import unittest

from src.agent.core.state_access import sget, to_namespaced_update, with_flattened_legacy_view


class StateAccessTest(unittest.TestCase):
    def test_sget_prefers_namespaced_then_fallback_flat(self) -> None:
        state = {
            "research": {"papers": [{"uid": "p1"}]},
            "papers": [{"uid": "legacy"}],
        }
        self.assertEqual(sget(state, "papers", []), [{"uid": "p1"}])
        self.assertEqual(sget({"papers": [{"uid": "legacy"}]}, "papers", []), [{"uid": "legacy"}])
        self.assertEqual(sget({}, "papers", []), [])

    def test_with_flattened_legacy_view_materializes_aliases(self) -> None:
        state = {
            "planning": {"research_questions": ["rq1"], "_academic_queries": ["qa"]},
            "research": {"papers": [{"uid": "p1"}]},
        }
        view = with_flattened_legacy_view(state)
        self.assertEqual(view["research_questions"], ["rq1"])
        self.assertEqual(view["_academic_queries"], ["qa"])
        self.assertEqual(view["papers"], [{"uid": "p1"}])

    def test_to_namespaced_update_converts_flat_patch(self) -> None:
        update = {
            "papers": [{"uid": "p1"}],
            "gaps": ["g1"],
            "report": "body",
            "status": "ok",
        }
        out = to_namespaced_update(update)
        self.assertEqual(out["research"]["papers"], [{"uid": "p1"}])
        self.assertEqual(out["evidence"]["gaps"], ["g1"])
        self.assertEqual(out["report"]["report"], "body")
        self.assertEqual(out["status"], "ok")

    def test_to_namespaced_update_merges_existing_namespace_payload(self) -> None:
        update = {
            "research": {"findings": ["f1"]},
            "findings": ["f2"],
        }
        out = to_namespaced_update(update)
        self.assertEqual(out["research"]["findings"], ["f2"])


if __name__ == "__main__":
    unittest.main()

