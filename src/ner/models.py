from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


@dataclass(slots=True)
class ExtractedEntity:
    value: str
    entity_type: str
    confidence: float
    source_section_id: str
    source_section_type: str
    page_number: int
    line_number: int
    line_index: int
    start_char: int
    end_char: int
    raw_line_text: str
    raw_value: str = ""
    extractor_name: str = "hybrid"

    def __post_init__(self) -> None:
        if not self.raw_value:
            self.raw_value = self.value

    def to_dict(self) -> Dict[str, Any]:
        return json_safe(asdict(self))


@dataclass(slots=True)
class PersonalDetails:
    name: Optional[ExtractedEntity] = None
    email: Optional[ExtractedEntity] = None
    phone: Optional[ExtractedEntity] = None
    location: Optional[ExtractedEntity] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.to_dict() if self.name else None,
            "email": self.email.to_dict() if self.email else None,
            "phone": self.phone.to_dict() if self.phone else None,
            "location": self.location.to_dict() if self.location else None,
        }


@dataclass(slots=True)
class EducationEntry:
    degree: Optional[ExtractedEntity] = None
    major: Optional[ExtractedEntity] = None
    university: Optional[ExtractedEntity] = None
    graduation_year: Optional[ExtractedEntity] = None
    cgpa: Optional[ExtractedEntity] = None
    source_section_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "degree": self.degree.to_dict() if self.degree else None,
            "major": self.major.to_dict() if self.major else None,
            "university": self.university.to_dict() if self.university else None,
            "graduation_year": self.graduation_year.to_dict() if self.graduation_year else None,
            "cgpa": self.cgpa.to_dict() if self.cgpa else None,
            "source_section_id": self.source_section_id,
        }


@dataclass(slots=True)
class ExperienceEntry:
    job_title: Optional[ExtractedEntity] = None
    company: Optional[ExtractedEntity] = None
    start_date: Optional[ExtractedEntity] = None
    end_date: Optional[ExtractedEntity] = None
    source_section_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_title": self.job_title.to_dict() if self.job_title else None,
            "company": self.company.to_dict() if self.company else None,
            "start_date": self.start_date.to_dict() if self.start_date else None,
            "end_date": self.end_date.to_dict() if self.end_date else None,
            "source_section_id": self.source_section_id,
        }


@dataclass(slots=True)
class CandidateProfile:
    resume_id: str
    document_id: str
    source_run_id: str
    personal_details: PersonalDetails = field(default_factory=PersonalDetails)
    education_entries: List[EducationEntry] = field(default_factory=list)
    experience_entries: List[ExperienceEntry] = field(default_factory=list)
    skills: List[ExtractedEntity] = field(default_factory=list)
    projects: List[ExtractedEntity] = field(default_factory=list)
    publications: List[ExtractedEntity] = field(default_factory=list)
    certifications: List[ExtractedEntity] = field(default_factory=list)
    research_interests: List[ExtractedEntity] = field(default_factory=list)
    awards: List[ExtractedEntity] = field(default_factory=list)
    languages: List[ExtractedEntity] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resume_id": self.resume_id,
            "document_id": self.document_id,
            "source_run_id": self.source_run_id,
            "personal_details": self.personal_details.to_dict(),
            "education_entries": [e.to_dict() for e in self.education_entries],
            "experience_entries": [e.to_dict() for e in self.experience_entries],
            "skills": [s.to_dict() for s in self.skills],
            "projects": [p.to_dict() for p in self.projects],
            "publications": [p.to_dict() for p in self.publications],
            "certifications": [c.to_dict() for c in self.certifications],
            "research_interests": [r.to_dict() for r in self.research_interests],
            "awards": [a.to_dict() for a in self.awards],
            "languages": [l.to_dict() for l in self.languages],
        }


@dataclass(slots=True)
class Stage4ExtractionResult:
    resume_id: str
    document_id: str
    run_id: str
    profile: CandidateProfile
    total_entities: int
    conflict_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return json_safe(asdict(self))
