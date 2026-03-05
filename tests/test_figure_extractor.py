from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import fitz

from src.ingest.figure_extractor import (
    ExtractedFigure,
    build_figure_contexts_from_text,
    extract_figures_from_pdf,
)
from src.ingest.latex_loader import ArxivSource, LatexFigure
from src.ingest.figure_extractor import extract_figures_from_latex


def _make_png_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=120, height=120)
    pix = page.get_pixmap()
    data = pix.tobytes("png")
    doc.close()
    return data


class FigureExtractorTest(unittest.TestCase):
    def test_extract_figures_from_latex_uses_image_refs(self) -> None:
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            root = Path(tmp)
            image = root / "figure.png"
            image.write_bytes(_make_png_bytes())
            source = ArxivSource(
                arxiv_id="1234.5678",
                source_dir=root,
                tex_files=[],
                main_tex=root / "main.tex",
                image_files=[image],
            )
            figures = [
                LatexFigure(
                    figure_id="fig:one",
                    caption="Architecture",
                    image_ref="figure.png",
                    image_path=image,
                    context_paragraphs=["See Figure 1."],
                )
            ]

            extracted = extract_figures_from_latex(source, figures, str(root / "out"), "doc1", min_width=1, min_height=1)

            self.assertEqual(len(extracted), 1)
            self.assertEqual(extracted[0].figure_id, "fig:one")
            self.assertTrue(extracted[0].image_path.exists())

    def test_extract_figures_from_pdf_and_build_contexts(self) -> None:
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            root = Path(tmp)
            pdf_path = root / "paper.pdf"
            png_bytes = _make_png_bytes()
            doc = fitz.open()
            page = doc.new_page()
            rect = fitz.Rect(50, 50, 170, 170)
            page.insert_image(rect, stream=png_bytes)
            doc.save(pdf_path)
            doc.close()

            extracted = extract_figures_from_pdf(str(pdf_path), str(root / "images"), "doc1", min_width=1, min_height=1)
            contexts = build_figure_contexts_from_text(
                "Figure 1: Model architecture.\n\nAs shown in Figure 1, the encoder feeds the decoder.",
                extracted,
            )

            self.assertEqual(len(extracted), 1)
            self.assertEqual(extracted[0].page_number, 1)
            self.assertEqual(len(contexts), 1)
            self.assertEqual(contexts[0].caption, "Model architecture.")
            self.assertTrue(contexts[0].context_paragraphs)


if __name__ == "__main__":
    unittest.main()
