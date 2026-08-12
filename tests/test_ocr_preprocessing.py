from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from src.extraction.config import ExtractionConfig
from src.extraction.methods.ocr import TesseractOcrExtractor, _prepare_ocr_image
from src.extraction.models import PageContext


class OcrPreprocessingTests(unittest.TestCase):
    def test_large_white_margins_are_cropped(self) -> None:
        image = Image.new("L", (1819, 2573), 255)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 512, 1819, 1883), fill=0)

        cropped, bbox = _prepare_ocr_image(image)

        self.assertEqual(bbox, (0, 492, 1819, 1904))
        self.assertEqual(cropped.size, (1819, 1412))

    def test_normal_image_remains_full_frame_when_content_spans_page(self) -> None:
        image = Image.new("L", (800, 1000), 255)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 799, 999), fill=0)

        cropped, bbox = _prepare_ocr_image(image)

        self.assertEqual(bbox, (0, 0, 800, 1000))
        self.assertEqual(cropped.size, (800, 1000))

    def test_blank_image_returns_original_image(self) -> None:
        image = Image.new("L", (640, 480), 255)

        cropped, bbox = _prepare_ocr_image(image)

        self.assertIsNone(bbox)
        self.assertEqual(cropped.size, (640, 480))

    def test_extract_passes_cropped_image_to_tesseract(self) -> None:
        extractor = TesseractOcrExtractor()
        config = ExtractionConfig(tesseract_executable=Path("C:/Windows/System32/tesseract.exe"))

        with tempfile.TemporaryDirectory() as temp_dir:
            render_dir = Path(temp_dir)
            image_path = render_dir / "page_0001.png"
            image = Image.new("L", (600, 900), 255)
            draw = ImageDraw.Draw(image)
            draw.rectangle((50, 300, 550, 600), fill=0)
            image.save(image_path)

            page = PageContext(
                document_id="doc",
                source_path=Path("dummy.pdf"),
                page_number=1,
                page_count=1,
                document_dir=render_dir,
                page_dir=render_dir,
                render_dir=render_dir,
                preflight={},
            )

            with patch.object(extractor, "resolve_tesseract_executable", return_value=Path("C:/Windows/System32/tesseract.exe")):
                with patch.object(extractor, "_render_page", return_value=image_path):
                    captured = {}

                    def fake_image_to_string(passed_image):
                        captured["size"] = passed_image.size
                        return "recognized text"

                    with patch("pytesseract.image_to_string", side_effect=fake_image_to_string):
                        result = extractor.extract(page, config)

        self.assertLess(captured["size"][0], 600)
        self.assertLess(captured["size"][1], 900)
        self.assertIn("recognized text", result.text)


if __name__ == "__main__":
    unittest.main()
