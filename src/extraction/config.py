from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple


def utc_run_id(prefix: str = "run") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{stamp}"


@dataclass(frozen=True, slots=True)
class ExtractionConfig:
    input_root: Path = Path("data/real_resumes/original")
    output_root: Path = Path("output/extraction")
    run_prefix: str = "run"
    page_render_dpi: int = 220
    min_chars: int = 40
    min_words: int = 6
    min_alpha_ratio: float = 0.20
    max_replacement_ratio: float = 0.02
    tesseract_executable: Optional[Path] = None
    method_order: Tuple[str, ...] = (
        "native_pymupdf",
        "native_pypdf",
        "layout_pdfplumber",
        "ocr_tesseract",
    )

    def run_id(self) -> str:
        return utc_run_id(self.run_prefix)

    def as_dict(self) -> Dict[str, object]:
        return {
            "input_root": str(self.input_root),
            "output_root": str(self.output_root),
            "run_prefix": self.run_prefix,
            "page_render_dpi": self.page_render_dpi,
            "min_chars": self.min_chars,
            "min_words": self.min_words,
            "min_alpha_ratio": self.min_alpha_ratio,
            "max_replacement_ratio": self.max_replacement_ratio,
            "tesseract_executable": str(self.tesseract_executable) if self.tesseract_executable else None,
            "method_order": list(self.method_order),
        }


def build_default_config() -> ExtractionConfig:
    return ExtractionConfig()
