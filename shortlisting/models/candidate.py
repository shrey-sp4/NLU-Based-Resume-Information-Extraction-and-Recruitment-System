from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EducationEntry:
    degree: str = ""
    stream: str = ""
    institution: str = ""
    university_tier: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "degree": self.degree or "",
            "stream": self.stream or "",
            "institution": self.institution or "",
            "university_tier": self.university_tier or "",
        }


@dataclass
class ExperienceEntry:
    job_title: str = ""
    institution: str = ""
    dates: str = ""
    experience_type: str = "other/unknown"
    duration_years: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_title": self.job_title or "",
            "institution": self.institution or "",
            "dates": self.dates or "",
            "experience_type": self.experience_type or "other/unknown",
            "duration_years": self.duration_years,
        }


@dataclass
class PublicationEntry:
    title: str = ""
    type: str = "other"  # 'journal' | 'conference' | 'other'
    year: Optional[str] = None
    tier: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title or "",
            "type": self.type or "other",
            "year": self.year,
            "tier": self.tier or "",
        }


@dataclass
class NormalizedCandidate:
    candidate_name: str = ""
    education: List[EducationEntry] = field(default_factory=list)
    experience: List[ExperienceEntry] = field(default_factory=list)
    publications: List[PublicationEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_name": self.candidate_name or "",
            "education": [e.to_dict() for e in self.education],
            "experience": [e.to_dict() for e in self.experience],
            "publications": [p.to_dict() for p in self.publications],
        }
