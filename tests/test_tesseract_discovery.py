from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.extraction.config import ExtractionConfig
from src.extraction.methods.ocr import TesseractOcrExtractor


class TesseractDiscoveryTests(unittest.TestCase):
    def test_explicit_tesseract_path_wins_over_path_lookup(self) -> None:
        extractor = TesseractOcrExtractor()
        with tempfile.TemporaryDirectory() as temp_dir:
            explicit = Path(temp_dir) / "tesseract.exe"
            explicit.write_text("", encoding="utf-8")
            config = ExtractionConfig(tesseract_executable=explicit)

            with patch("src.extraction.methods.ocr.which", return_value=r"C:\\Windows\\System32\\tesseract.exe"):
                resolved = extractor.resolve_tesseract_executable(config)

        self.assertEqual(resolved, explicit)

    def test_env_var_tesseract_path_is_used_when_config_is_missing(self) -> None:
        extractor = TesseractOcrExtractor()
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / "tesseract.exe"
            env_path.write_text("", encoding="utf-8")

            with patch.dict(os.environ, {"TESSERACT_CMD": str(env_path)}, clear=False):
                resolved = extractor.resolve_tesseract_executable(ExtractionConfig())

        self.assertEqual(resolved, env_path)


if __name__ == "__main__":
    unittest.main()
