from __future__ import annotations

from typing import List, Tuple

from ..config import ExtractionConfig
from ..models import AttemptStatus, PageContext
from .base import ExtractionMethod


def _reconstruct_from_words(words: List[Tuple[float, float, float, float, str, int, int, int]]) -> str:
    if not words:
        return ""

    lines: List[List[Tuple[float, float, float, float, str, int, int, int]]] = []
    current_line: List[Tuple[float, float, float, float, str, int, int, int]] = [words[0]]
    current_y = words[0][1]
    for word in words[1:]:
        if abs(word[1] - current_y) <= 3.0:
            current_line.append(word)
        else:
            lines.append(sorted(current_line, key=lambda item: item[0]))
            current_line = [word]
            current_y = word[1]
    lines.append(sorted(current_line, key=lambda item: item[0]))
    return "\n".join(" ".join(word[4] for word in line).strip() for line in lines if line)


class LayoutAwarePdfPlumberExtractor(ExtractionMethod):
    name = "layout_pdfplumber"

    def is_available(self) -> bool:
        try:
            import pdfplumber  # type: ignore  # noqa: F401
            return True
        except Exception:
            return False

    def extract(self, page: PageContext, config: ExtractionConfig):
        try:
            import pdfplumber  # type: ignore
        except Exception as exc:
            return self._build_attempt(
                status=AttemptStatus.SKIPPED,
                reason="pdfplumber_unavailable",
                error=str(exc),
            )

        try:
            with pdfplumber.open(str(page.source_path)) as pdf:
                pdf_page = pdf.pages[page.page_number - 1]
                words = pdf_page.extract_words(use_text_flow=True, keep_blank_chars=False) or []
                if words:
                    words = sorted(words, key=lambda item: (round(item["top"], 1), item["x0"]))
                    lines: List[List[dict]] = []
                    current_line: List[dict] = [words[0]]
                    current_top = words[0]["top"]
                    for word in words[1:]:
                        if abs(word["top"] - current_top) <= 3.0:
                            current_line.append(word)
                        else:
                            lines.append(sorted(current_line, key=lambda item: item["x0"]))
                            current_line = [word]
                            current_top = word["top"]
                    lines.append(sorted(current_line, key=lambda item: item["x0"]))
                    text = "\n".join(" ".join(piece["text"] for piece in line).strip() for line in lines if line)
                else:
                    text = pdf_page.extract_text(layout=True) or ""

            return self._build_attempt(
                text=text,
                status=AttemptStatus.SUCCESS if text.strip() else AttemptStatus.FAILED,
                reason="layout_text_extracted" if text.strip() else "empty_layout_text",
            )
        except Exception as exc:
            return self._build_attempt(
                status=AttemptStatus.FAILED,
                reason="layout_extraction_failed",
                error=str(exc),
            )

