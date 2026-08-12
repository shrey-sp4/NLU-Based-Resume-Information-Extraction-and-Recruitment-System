from __future__ import annotations

from pathlib import Path

from ..config import ExtractionConfig
from ..models import AttemptStatus, PageContext
from .base import ExtractionMethod


class PyMuPdfNativeExtractor(ExtractionMethod):
    name = "native_pymupdf"

    def is_available(self) -> bool:
        try:
            import fitz  # type: ignore  # noqa: F401
            return True
        except Exception:
            return False

    def extract(self, page: PageContext, config: ExtractionConfig):
        try:
            import fitz  # type: ignore
        except Exception as exc:
            return self._build_attempt(
                status=AttemptStatus.SKIPPED,
                reason="pymupdf_unavailable",
                error=str(exc),
            )

        def _read() -> str:
            doc = fitz.open(str(page.source_path))
            pdf_page = doc[page.page_number - 1]
            return pdf_page.get_text("text", sort=True)

        try:
            text, elapsed_ms = self._measure(_read)
            text = text or ""
            return self._build_attempt(
                text=text,
                status=AttemptStatus.SUCCESS if text.strip() else AttemptStatus.FAILED,
                reason="native_text_extracted" if text.strip() else "empty_text_layer",
                elapsed_ms=elapsed_ms,
            )
        except Exception as exc:
            return self._build_attempt(
                status=AttemptStatus.FAILED,
                reason="native_text_extraction_failed",
                error=str(exc),
            )


class PypdfNativeExtractor(ExtractionMethod):
    name = "native_pypdf"

    def is_available(self) -> bool:
        try:
            from pypdf import PdfReader  # type: ignore  # noqa: F401
            return True
        except Exception:
            return False

    def extract(self, page: PageContext, config: ExtractionConfig):
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception as exc:
            return self._build_attempt(
                status=AttemptStatus.SKIPPED,
                reason="pypdf_unavailable",
                error=str(exc),
            )

        def _read() -> str:
            reader = PdfReader(str(page.source_path))
            return reader.pages[page.page_number - 1].extract_text() or ""

        try:
            text, elapsed_ms = self._measure(_read)
            return self._build_attempt(
                text=text,
                status=AttemptStatus.SUCCESS if text.strip() else AttemptStatus.FAILED,
                reason="native_text_extracted" if text.strip() else "empty_text_layer",
                elapsed_ms=elapsed_ms,
            )
        except Exception as exc:
            return self._build_attempt(
                status=AttemptStatus.FAILED,
                reason="native_text_extraction_failed",
                error=str(exc),
            )

