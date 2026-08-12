from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


CANONICAL_SECTION_LABELS = (
    "education",
    "experience",
    "skills",
    "projects",
    "publications",
    "certifications",
    "research_interests",
    "achievements",
    "personal_details",
    "summary",
    "references",
    "responsibilities",
    "memberships",
    "patents",
    "declaration",
    "other",
)


def validate_section_label(label: Optional[str]) -> bool:
    return label in CANONICAL_SECTION_LABELS if label is not None else False


def normalize_section_label(label: Optional[str]) -> str:
    if label is None:
        return "other"

    normalized = str(label).strip().lower().replace(" ", "_")
    if normalized == "unmapped":
        return "other"
    return normalized if normalized in CANONICAL_SECTION_LABELS else "other"


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


@dataclass(slots=True)
class RawLineRecord:
    resume_id: str
    document_id: str
    source_file: str
    source_run_id: str
    page_number: int
    line_number: int
    line_index: int
    text: str
    previous_text: str = ""
    next_text: str = ""
    preceded_by_blank: bool = False
    followed_by_blank: bool = False
    page_status: str = ""
    page_type_guess: str = ""
    final_method: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return json_safe(asdict(self))


@dataclass(slots=True)
class HeadingPrediction:
    is_heading: bool
    heading_probability: float
    canonical_section: str
    section_confidence: float
    method: str
    review_required: bool
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return json_safe(asdict(self))


@dataclass(slots=True)
class SectionAnnotationRecord:
    resume_id: str
    document_id: str
    source_document: str
    source_run_id: str
    page_number: int
    line_number: int
    line_index: int
    text: str
    is_blank: bool = False
    preceded_by_blank: bool = False
    followed_by_blank: bool = False
    machine_suggested_heading: Optional[str] = None
    machine_suggested_section: str = "other"
    machine_confidence: float = 0.0
    machine_suggestion_method: str = ""
    machine_review_required: bool = False
    is_heading: Optional[bool] = None
    section_label: Optional[str] = None
    annotator_notes: str = ""
    review_state: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return json_safe(asdict(self))


@dataclass(slots=True)
class LineRecord:
    resume_id: str
    document_id: str
    page_number: int
    line_number: int
    line_index: int
    text: str
    section_label: str = "other"
    is_heading: bool = False
    raw_heading: str = ""
    heading_confidence: float = 0.0
    heading_method: str = ""
    review_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return json_safe(asdict(self))


@dataclass(slots=True)
class SectionSpan:
    resume_id: str
    section: str
    raw_heading: str
    confidence: float
    method: str
    review_required: bool
    pages: List[int] = field(default_factory=list)
    lines: List[LineRecord] = field(default_factory=list)

    def add_line(self, line: LineRecord) -> None:
        self.lines.append(line)
        if line.page_number not in self.pages:
            self.pages.append(line.page_number)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines if line.text.strip()).strip()

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["text"] = self.text
        payload["lines"] = [line.to_dict() for line in self.lines]
        return json_safe(payload)


@dataclass(slots=True)
class ResumeSectioningResult:
    resume_id: str
    document_id: str
    sections: List[SectionSpan] = field(default_factory=list)
    unassigned_lines: List[LineRecord] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["sections"] = [section.to_dict() for section in self.sections]
        payload["unassigned_lines"] = [line.to_dict() for line in self.unassigned_lines]
        return json_safe(payload)


def validate_annotation_record(record: Dict[str, Any]) -> None:
    required = {
        "resume_id",
        "page_number",
        "line_number",
        "text",
        "is_heading",
        "section_label",
    }
    missing = [field for field in required if field not in record]
    if missing:
        raise ValueError(f"Missing required annotation fields: {', '.join(sorted(missing))}")

    label = record.get("section_label")
    if label is not None and label != "" and not validate_section_label(str(label)):
        raise ValueError(f"Invalid section label: {label}")
