from __future__ import annotations

import unittest

from src.agent.core import schemas


class CoreSchemasTest(unittest.TestCase):
    def test_search_fetch_result_contract(self) -> None:
        self.assertIn("papers", schemas.SearchFetchResult.__annotations__)
        self.assertIn("web_sources", schemas.SearchFetchResult.__annotations__)

    def test_research_state_includes_internal_orchestration_fields(self) -> None:
        ann = schemas.ResearchState.__annotations__
        self.assertIn("_cfg", ann)
        self.assertIn("_academic_queries", ann)
        self.assertIn("_web_queries", ann)
        self.assertIn("run_id", ann)
        self.assertIn("acceptance_metrics", ann)

    def test_named_schema_types_present(self) -> None:
        self.assertTrue(hasattr(schemas, "PaperRecord"))
        self.assertTrue(hasattr(schemas, "WebResult"))
        self.assertTrue(hasattr(schemas, "AnalysisResult"))
        self.assertTrue(hasattr(schemas, "RunMetrics"))


if __name__ == "__main__":
    unittest.main()
