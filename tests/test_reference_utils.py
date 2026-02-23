"""Tests for S2/S3: shared reference extraction and URL normalization."""
from __future__ import annotations

import unittest

from src.agent.core.reference_utils import (
    extract_reference_urls,
    normalize_reference_line,
    normalize_references_in_report,
)


class ExtractReferenceUrlsTest(unittest.TestCase):
    def test_only_counts_references_section(self):
        report = (
            "## Experimental Blueprint\n"
            "- Dataset https://github.com/example/data\n"
            "## References\n"
            "1. Paper A https://arxiv.org/abs/2110.08902v5\n"
        )
        urls = extract_reference_urls(report)
        self.assertEqual(urls, ["https://arxiv.org/abs/2110.08902v5"])

    def test_deduplicates_urls(self):
        report = (
            "## References\n"
            "1. A https://example.com/a\n"
            "* A2 https://example.com/a\n"
        )
        urls = extract_reference_urls(report)
        self.assertEqual(urls, ["https://example.com/a"])

    def test_fallback_to_full_report_if_no_ref_section(self):
        report = "1. Paper https://example.com/a\n2. Paper https://example.com/b\n"
        urls = extract_reference_urls(report)
        self.assertEqual(len(urls), 2)

    def test_stops_at_next_heading(self):
        report = (
            "## References\n"
            "1. A https://example.com/a\n"
            "## Appendix\n"
            "- B https://example.com/b\n"
        )
        urls = extract_reference_urls(report)
        self.assertEqual(urls, ["https://example.com/a"])

    def test_arxiv_identifier_resolved_to_url(self):
        """S3: arXiv:xxxx without URL is resolved."""
        report = (
            "## References\n"
            "1. Paper A. arXiv:2401.12345\n"
        )
        urls = extract_reference_urls(report)
        self.assertIn("https://arxiv.org/abs/2401.12345", urls)

    def test_doi_resolved_to_url(self):
        """S3: Bare DOI is resolved."""
        report = (
            "## References\n"
            "1. Paper B. 10.1000/test123\n"
        )
        urls = extract_reference_urls(report)
        self.assertIn("https://doi.org/10.1000/test123", urls)


class ConsistencyTest(unittest.TestCase):
    """S2: critic and validator should produce the same reference counts."""

    def test_nodes_and_validator_agree(self):
        """Both implementations delegate to the same shared function."""
        from src.agent.nodes import _extract_reference_urls
        from scripts.validate_run_outputs import extract_reference_urls as validator_fn

        report = (
            "## Experimental Blueprint\n"
            "- Dataset https://github.com/example/data\n"
            "## References\n"
            "1. Paper https://arxiv.org/abs/2110.08902v5\n"
            "2. Paper https://example.com/b\n"
        )
        nodes_refs = _extract_reference_urls(report)
        validator_refs = validator_fn(report)
        self.assertEqual(nodes_refs, validator_refs)


class NormalizeReferenceLineTest(unittest.TestCase):
    def test_arxiv_to_url(self):
        line = "1. Paper A. arXiv:2401.12345"
        result, _ = normalize_reference_line(line)
        self.assertIn("https://arxiv.org/abs/2401.12345", result)

    def test_doi_to_url(self):
        line = "2. Paper B. 10.1000/xyz123"
        result, _ = normalize_reference_line(line)
        self.assertIn("https://doi.org/10.1000/xyz123", result)

    def test_existing_url_not_duplicated(self):
        line = "1. Paper https://arxiv.org/abs/2401.12345 arXiv:2401.12345"
        result, _ = normalize_reference_line(line)
        # Should not double the URL
        self.assertEqual(result.count("https://arxiv.org/abs/2401.12345"), 1)


class NormalizeReferencesInReportTest(unittest.TestCase):
    def test_normalizes_references_section(self):
        report = (
            "## Introduction\n\nBody\n\n"
            "## References\n"
            "1. Paper A. arXiv:2401.12345\n"
        )
        result = normalize_references_in_report(report)
        self.assertIn("https://arxiv.org/abs/2401.12345", result)

    def test_no_references_section_unchanged(self):
        report = "## Introduction\n\nBody\n"
        result = normalize_references_in_report(report)
        self.assertEqual(result, report)


if __name__ == "__main__":
    unittest.main()
