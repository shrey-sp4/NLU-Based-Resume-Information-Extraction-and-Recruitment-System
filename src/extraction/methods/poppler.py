from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from shutil import which

from ..config import ExtractionConfig
from ..models import AttemptStatus, PageContext
from .base import ExtractionMethod


class PopplerTextExtractor(ExtractionMethod):
    name = "poppler_text"

    def is_available(self) -> bool:
        return which("pdftotext") is not None

    def extract(self, page: PageContext, config: ExtractionConfig):
        if not self.is_available():
            return self._build_attempt(
                status=AttemptStatus.SKIPPED,
                reason="pdftotext_unavailable",
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output = Path(temp_dir) / f"page_{page.page_number:04d}.txt"
            command = [
                "pdftotext",
                "-layout",
                "-f",
                str(page.page_number),
                "-l",
                str(page.page_number),
                str(page.source_path),
                str(temp_output),
            ]
            try:
                completed = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if completed.returncode != 0:
                    return self._build_attempt(
                        status=AttemptStatus.FAILED,
                        reason="pdftotext_failed",
                        error=completed.stderr.strip() or completed.stdout.strip() or "unknown_error",
                    )
                text = temp_output.read_text(encoding="utf-8", errors="replace") if temp_output.exists() else ""
                return self._build_attempt(
                    text=text,
                    status=AttemptStatus.SUCCESS if text.strip() else AttemptStatus.FAILED,
                    reason="poppler_text_extracted" if text.strip() else "empty_poppler_output",
                )
            except Exception as exc:
                return self._build_attempt(
                    status=AttemptStatus.FAILED,
                    reason="pdftotext_execution_failed",
                    error=str(exc),
                )

