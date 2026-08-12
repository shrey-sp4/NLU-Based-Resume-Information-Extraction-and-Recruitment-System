from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .config import ExtractionConfig
from .models import PageStatus, TextMetrics


_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = _CONTROL_RE.sub(" ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compute_text_metrics(text: str) -> TextMetrics:
    normalized = normalize_text(text)
    char_count = len(normalized)
    word_count = len(_WORD_RE.findall(normalized))
    line_count = len([line for line in normalized.splitlines() if line.strip()])
    alpha_count = sum(1 for ch in normalized if ch.isalpha())
    digit_count = sum(1 for ch in normalized if ch.isdigit())
    whitespace_count = sum(1 for ch in normalized if ch.isspace())
    punctuation_count = sum(1 for ch in normalized if not ch.isalnum() and not ch.isspace())
    replacement_char_count = normalized.count("\uFFFD")
    non_ascii_count = sum(1 for ch in normalized if ord(ch) > 127)
    alpha_ratio = alpha_count / char_count if char_count else 0.0
    replacement_ratio = replacement_char_count / char_count if char_count else 0.0

    return TextMetrics(
        char_count=char_count,
        word_count=word_count,
        line_count=line_count,
        alpha_count=alpha_count,
        digit_count=digit_count,
        whitespace_count=whitespace_count,
        punctuation_count=punctuation_count,
        replacement_char_count=replacement_char_count,
        non_ascii_count=non_ascii_count,
        alpha_ratio=alpha_ratio,
        replacement_ratio=replacement_ratio,
    )


@dataclass(slots=True)
class ValidationDecision:
    accepted: bool
    reason: str
    page_status: PageStatus
    metrics: TextMetrics


def evaluate_text(
    text: str,
    config: ExtractionConfig,
    page_number: int,
    page_count: Optional[int] = None,
) -> ValidationDecision:
    metrics = compute_text_metrics(text)
    normalized = normalize_text(text)

    if not normalized:
        return ValidationDecision(
            accepted=False,
            reason="no_text_extracted",
            page_status=PageStatus.REVIEW,
            metrics=metrics,
        )

    if metrics.char_count < config.min_chars and metrics.word_count < config.min_words:
        return ValidationDecision(
            accepted=False,
            reason="text_too_sparse",
            page_status=PageStatus.REVIEW,
            metrics=metrics,
        )

    if metrics.replacement_ratio > config.max_replacement_ratio:
        return ValidationDecision(
            accepted=False,
            reason="too_many_replacement_characters",
            page_status=PageStatus.REVIEW,
            metrics=metrics,
        )

    if metrics.alpha_ratio < config.min_alpha_ratio:
        return ValidationDecision(
            accepted=False,
            reason="alpha_ratio_too_low",
            page_status=PageStatus.REVIEW,
            metrics=metrics,
        )

    return ValidationDecision(
        accepted=True,
        reason="usable_text_extracted",
        page_status=PageStatus.PASS_,
        metrics=metrics,
    )
