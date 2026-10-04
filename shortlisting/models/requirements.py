from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EducationRequirements:
    required_degrees: List[str] = field(default_factory=list)
    required_streams: List[str] = field(default_factory=list)
    preferred_university_tiers: List[str] = field(default_factory=list)
    tier_aggregation_method: str = "highest_degree"  # highest_degree | weighted_by_degree | average | minimum_tier
    degree_weights_for_aggregation: Dict[str, float] = field(
        default_factory=lambda: {"phd": 0.50, "masters": 0.30, "bachelors": 0.20}
    )
    must_have_degree: bool = False
    minimum_university_tier: Optional[str] = None
    must_verify_stream: bool = False
    degree_match_mode: str = "exact"  # exact | level_or_higher
    minimum_degree_level: Optional[str] = None  # bachelors | masters | doctorate | None


@dataclass
class ExperienceRequirements:
    min_total_experience_years: float = 0.0
    min_academic_experience_years: float = 0.0
    min_industry_experience_years: float = 0.0
    relevant_roles: List[str] = field(default_factory=list)
    must_meet_min_experience: bool = False


@dataclass
class PublicationRequirements:
    min_total_publications: int = 0
    must_have_min_total: bool = False

    min_journal_publications: int = 0
    must_have_min_journals: bool = False

    min_conference_publications: int = 0
    must_have_min_conferences: bool = False

    required_publication_tiers: List[str] = field(default_factory=list)

    min_tier1_publications: int = 0
    must_have_min_tier1: bool = False

    recent_years_window: Optional[int] = None
    min_recent_publications: int = 0
    must_have_min_recent: bool = False

    # Backwards compatibility alias
    must_have_min_publications: Optional[bool] = None

    def __post_init__(self) -> None:
        if self.must_have_min_publications is not None and not self.must_have_min_total:
            self.must_have_min_total = self.must_have_min_publications
        elif self.must_have_min_total and self.must_have_min_publications is None:
            self.must_have_min_publications = self.must_have_min_total


@dataclass
class RecruiterRequirements:
    job_title: str = "Academic / Faculty Position"
    education: EducationRequirements = field(default_factory=EducationRequirements)
    experience: ExperienceRequirements = field(default_factory=ExperienceRequirements)
    publications: PublicationRequirements = field(default_factory=PublicationRequirements)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_title": self.job_title,
            "education": {
                "required_degrees": self.education.required_degrees,
                "required_streams": self.education.required_streams,
                "preferred_university_tiers": self.education.preferred_university_tiers,
                "tier_aggregation_method": self.education.tier_aggregation_method,
                "degree_weights_for_aggregation": self.education.degree_weights_for_aggregation,
                "must_have_degree": self.education.must_have_degree,
                "minimum_university_tier": self.education.minimum_university_tier,
                "must_verify_stream": self.education.must_verify_stream,
                "degree_match_mode": self.education.degree_match_mode,
                "minimum_degree_level": self.education.minimum_degree_level,
            },
            "experience": {
                "min_total_experience_years": self.experience.min_total_experience_years,
                "min_academic_experience_years": self.experience.min_academic_experience_years,
                "min_industry_experience_years": self.experience.min_industry_experience_years,
                "relevant_roles": self.experience.relevant_roles,
                "must_meet_min_experience": self.experience.must_meet_min_experience,
            },
            "publications": {
                "min_total_publications": self.publications.min_total_publications,
                "must_have_min_total": self.publications.must_have_min_total,
                "min_journal_publications": self.publications.min_journal_publications,
                "must_have_min_journals": self.publications.must_have_min_journals,
                "min_conference_publications": self.publications.min_conference_publications,
                "must_have_min_conferences": self.publications.must_have_min_conferences,
                "required_publication_tiers": self.publications.required_publication_tiers,
                "min_tier1_publications": self.publications.min_tier1_publications,
                "must_have_min_tier1": self.publications.must_have_min_tier1,
                "recent_years_window": self.publications.recent_years_window,
                "min_recent_publications": self.publications.min_recent_publications,
                "must_have_min_recent": self.publications.must_have_min_recent,
            },
        }
