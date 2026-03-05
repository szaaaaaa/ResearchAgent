from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from src.ingest.pdf_loader import LoadedPDF, load_pdf_text


class PDFLoaderTest(unittest.TestCase):
    def test_load_pdf_text_with_pymupdf(self) -> None:
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            pdf_path = Path(tmp) / "sample.pdf"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "hello multimodal world")
            doc.save(pdf_path)
            doc.close()

            loaded = load_pdf_text(str(pdf_path), backend="pymupdf")

        self.assertIn("hello multimodal world", loaded.text)
        self.assertEqual(loaded.num_pages, 1)

    def test_load_pdf_text_with_marker_backend_switches_helper(self) -> None:
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            pdf_path = Path(tmp) / "sample.pdf"
            doc = fitz.open()
            doc.new_page()
            doc.save(pdf_path)
            doc.close()

            with patch(
                "src.ingest.pdf_loader._load_with_marker",
                return_value=LoadedPDF(pdf_path=str(pdf_path), text="marker text", num_pages=1),
            ) as helper:
                loaded = load_pdf_text(str(pdf_path), backend="marker")

        self.assertEqual(loaded.text, "marker text")
        helper.assert_called_once()


if __name__ == "__main__":
    unittest.main()
