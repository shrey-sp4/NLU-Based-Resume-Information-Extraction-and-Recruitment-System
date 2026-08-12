from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


class AttemptStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PageStatus(str, Enum):
    PASS_ = "PASS"
    REVIEW = "REVIEW"


class DocumentStatus(str, Enum):
    PASS_ = "PASS"
    REVIEW = "REVIEW"


@dataclass(slots=True)
class TextMetrics:
    char_count: int = 0
    word_count: int = 0
    line_count: int = 0
    alpha_count: int = 0
    digit_count: int = 0
    whitespace_count: int = 0
    punctuation_count: int = 0
    replacement_char_count: int = 0
    non_ascii_count: int = 0
    alpha_ratio: float = 0.0
    replacement_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return json_safe(asdict(self))


@dataclass(slots=True)
class ExtractionAttempt:
    method: str
    status: AttemptStatus
    reason: str
    text: str = ""
    metrics: TextMetrics = field(default_factory=TextMetrics)
    artifact_path: Optional[Path] = None
    error: Optional[str] = None
    fallback_from: Optional[str] = None
    elapsed_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["metrics"] = self.metrics.to_dict()
        payload["artifact_path"] = str(self.artifact_path) if self.artifact_path else None
        return json_safe(payload)


@dataclass(slots=True)
class PageContext:
    document_id: str
    source_path: Path
    page_number: int
    page_count: Optional[int]
    document_dir: Path
    page_dir: Path
    render_dir: Path
    preflight: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PageExtractionResult:
    page_number: int
    status: PageStatus
    final_method: Optional[str]
    final_text: str
    metrics: TextMetrics
    attempts: List[ExtractionAttempt] = field(default_factory=list)
    review_reason: Optional[str] = None
    page_type_guess: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["metrics"] = self.metrics.to_dict()
        payload["attempts"] = [attempt.to_dict() for attempt in self.attempts]
        return json_safe(payload)


@dataclass(slots=True)
class DocumentSource:
    document_id: str
    source_path: Path
    file_hash: str
    file_size: int

    def to_dict(self) -> Dict[str, Any]:
        return json_safe(asdict(self))


@dataclass(slots=True)
class PreflightResult:
    source_path: Path
    file_hash: str
    file_size: int
    is_pdf: bool
    readable: bool
    page_count: Optional[int]
    encrypted: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    backend: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return json_safe(asdict(self))


@dataclass(slots=True)
class DocumentExtractionResult:
    document_id: str
    source_path: Path
    file_hash: str
    file_size: int
    page_count: Optional[int]
    status: DocumentStatus
    pages: List[PageExtractionResult] = field(default_factory=list)
    preflight: Optional[PreflightResult] = None
    review_reason: Optional[str] = None
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str = field(default_factory=utc_now_iso)

    def full_text(self) -> str:
        parts = [page.final_text for page in self.pages if page.final_text.strip()]
        return "\n\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["pages"] = [page.to_dict() for page in self.pages]
        payload["preflight"] = self.preflight.to_dict() if self.preflight else None
        payload["full_text"] = self.full_text()
        return json_safe(payload)


@dataclass(slots=True)
class RunManifest:
    run_id: str
    created_at: str
    source_root: Path
    output_root: Path
    document_count: int
    documents: List[DocumentSource] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["documents"] = [document.to_dict() for document in self.documents]
        return json_safe(payload)
