from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..config import ExtractionConfig
from ..models import AttemptStatus, ExtractionAttempt, PageContext


class ExtractionMethod(ABC):
    name: str

    def is_available(self) -> bool:
        return True

    @abstractmethod
    def extract(self, page: PageContext, config: ExtractionConfig) -> ExtractionAttempt:
        raise NotImplementedError

    def _build_attempt(
        self,
        *,
        text: str = "",
        status: AttemptStatus,
        reason: str,
        artifact_path: Optional[Path] = None,
        error: Optional[str] = None,
        fallback_from: Optional[str] = None,
        elapsed_ms: Optional[int] = None,
    ) -> ExtractionAttempt:
        from ..validation import compute_text_metrics

        return ExtractionAttempt(
            method=self.name,
            status=status,
            reason=reason,
            text=text,
            metrics=compute_text_metrics(text),
            artifact_path=artifact_path,
            error=error,
            fallback_from=fallback_from,
            elapsed_ms=elapsed_ms,
        )

    def _measure(self, fn):
        started = time.perf_counter()
        result = fn()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return result, elapsed_ms

