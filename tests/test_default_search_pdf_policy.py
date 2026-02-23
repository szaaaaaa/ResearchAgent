from __future__ import annotations

import time
import unittest
import sys
import types
from unittest.mock import patch

if "feedparser" not in sys.modules:
    fake_feedparser = types.ModuleType("feedparser")
    fake_feedparser.parse = lambda *args, **kwargs: type("Feed", (), {"entries": []})()
    sys.modules["feedparser"] = fake_feedparser

from src.agent.plugins.search import default_search


class DefaultSearchPdfPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        default_search._PDF_DOMAIN_DENY_CACHE.clear()

    def test_skip_direct_download_for_non_whitelisted_doi_host(self) -> None:
        item = {
            "uid": "doi:10.1002/example",
            "doi": "10.1002/example",
            "pdf_url": "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/example",
        }
        with patch("src.agent.plugins.search.default_search.download_pdf") as mock_download:
            out = default_search._download_pdf_from_url_if_any(
                item,
                cfg={},
                papers_dir="data/papers",
                allow_download=True,
                polite_delay_sec=0.0,
            )
        mock_download.assert_not_called()
        self.assertFalse(bool(out.get("pdf_path")))
        self.assertEqual(out.get("pdf_source"), "metadata_only")

    def test_allow_direct_download_for_whitelisted_host(self) -> None:
        item = {
            "uid": "arxiv:2401.12345",
            "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
        }
        with patch(
            "src.agent.plugins.search.default_search.download_pdf",
            return_value="data/papers/arxiv_2401.12345.pdf",
        ) as mock_download:
            out = default_search._download_pdf_from_url_if_any(
                item,
                cfg={},
                papers_dir="data/papers",
                allow_download=True,
                polite_delay_sec=0.0,
            )
        mock_download.assert_called_once()
        self.assertEqual(out.get("pdf_path"), "data/papers/arxiv_2401.12345.pdf")
        self.assertEqual(out.get("pdf_source"), "arxiv")

    def test_forbidden_domain_is_temporarily_blocked_after_403(self) -> None:
        item = {
            "uid": "arxiv:2401.54321",
            "pdf_url": "https://arxiv.org/pdf/2401.54321.pdf",
        }

        class _Err(Exception):
            pass

        err = _Err("403 Client Error")
        err.response = type("Resp", (), {"status_code": 403})()

        with patch(
            "src.agent.plugins.search.default_search.download_pdf",
            side_effect=err,
        ) as first_download:
            out1 = default_search._download_pdf_from_url_if_any(
                dict(item),
                cfg={"sources": {"pdf_download": {"forbidden_host_ttl_sec": 10}}},
                papers_dir="data/papers",
                allow_download=True,
                polite_delay_sec=0.0,
            )
        self.assertFalse(bool(out1.get("pdf_path")))
        self.assertEqual(first_download.call_count, 1)
        blocked_until = default_search._PDF_DOMAIN_DENY_CACHE.get("arxiv.org", 0.0)
        self.assertGreater(blocked_until, time.time())
        self.assertLessEqual(blocked_until - time.time(), 10.5)

        with patch("src.agent.plugins.search.default_search.download_pdf") as second_download:
            out2 = default_search._download_pdf_from_url_if_any(
                dict(item),
                cfg={"sources": {"pdf_download": {"forbidden_host_ttl_sec": 10}}},
                papers_dir="data/papers",
                allow_download=True,
                polite_delay_sec=0.0,
            )
        second_download.assert_not_called()
        self.assertFalse(bool(out2.get("pdf_path")))

    def test_configurable_allow_hosts_can_enable_specific_publisher_download(self) -> None:
        item = {
            "uid": "doi:10.1002/example",
            "doi": "10.1002/example",
            "pdf_url": "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/example",
        }
        cfg = {
            "sources": {
                "pdf_download": {
                    "only_allowed_hosts": True,
                    "allowed_hosts": ["onlinelibrary.wiley.com"],
                }
            }
        }
        with patch(
            "src.agent.plugins.search.default_search.download_pdf",
            return_value="data/papers/doi_10.1002_example.pdf",
        ) as mock_download:
            out = default_search._download_pdf_from_url_if_any(
                item,
                cfg=cfg,
                papers_dir="data/papers",
                allow_download=True,
                polite_delay_sec=0.0,
            )
        mock_download.assert_called_once()
        self.assertEqual(out.get("pdf_path"), "data/papers/doi_10.1002_example.pdf")

    def test_only_allowed_hosts_false_allows_non_whitelisted_host(self) -> None:
        item = {
            "uid": "doi:10.1002/example",
            "doi": "10.1002/example",
            "pdf_url": "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/example",
        }
        cfg = {
            "sources": {
                "pdf_download": {
                    "only_allowed_hosts": False,
                }
            }
        }
        with patch(
            "src.agent.plugins.search.default_search.download_pdf",
            return_value="data/papers/doi_10.1002_example.pdf",
        ) as mock_download:
            out = default_search._download_pdf_from_url_if_any(
                item,
                cfg=cfg,
                papers_dir="data/papers",
                allow_download=True,
                polite_delay_sec=0.0,
            )
        mock_download.assert_called_once()
        self.assertEqual(out.get("pdf_path"), "data/papers/doi_10.1002_example.pdf")


if __name__ == "__main__":
    unittest.main()
