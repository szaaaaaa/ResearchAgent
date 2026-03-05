from __future__ import annotations

import unittest
from pathlib import Path

from src.ingest.latex_loader import ArxivSource, parse_latex


class LatexLoaderTest(unittest.TestCase):
    def test_parse_latex_extracts_sections_math_and_figures(self) -> None:
        root = Path("tests/fixtures/latex").resolve()
        main = root / "main.tex"
        body = root / "body.tex"
        img = root / "fig1.png"
        source = ArxivSource(
            arxiv_id="1234.5678",
            source_dir=root,
            tex_files=[main, body],
            main_tex=main,
            image_files=[img],
        )

        parsed = parse_latex(source)

        self.assertIn("## Intro", parsed.text)
        self.assertIn("$$", parsed.text)
        self.assertEqual(len(parsed.figures), 1)
        self.assertEqual(parsed.figures[0].figure_id, "fig:arch")
        self.assertEqual(parsed.figures[0].caption, "Model architecture overview")
        self.assertTrue(parsed.figures[0].context_paragraphs)


if __name__ == "__main__":
    unittest.main()
