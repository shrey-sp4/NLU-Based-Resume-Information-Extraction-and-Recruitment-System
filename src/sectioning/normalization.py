from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .models import CANONICAL_SECTION_LABELS, normalize_section_label

CANONICAL_ALIASES: Dict[str, List[str]] = {
    "contact": [
        "contact",
        "contact details",
        "contact info",
        "contact information",
        "personal details",
        "personal info",
        "personal information",
        "personal profile",
        "communication details",
        "address",
        "curriculum vitae",
        "resume",
        "cv",
    ],
    "summary": [
        "summary",
        "profile",
        "profile summary",
        "professional summary",
        "executive summary",
        "career summary",
        "overview",
        "about me",
        "summary of qualifications",
    ],
    "objective": [
        "objective",
        "career objective",
        "professional objective",
    ],
    "education": [
        "education",
        "educational background",
        "academic background",
        "academic qualifications",
        "academic qualification",
        "educational qualifications",
        "qualifications",
        "academic credentials",
        "education & training",
        "scholastic background",
        "scholastic qualification",
        "education and training",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "work history",
        "industry experience",
        "career experience",
        "relevant experience",
        "professional background",
        "working experience",
        "r&d experience",
        "r&d experience during ph.d.",
    ],
    "research_experience": [
        "research experience",
        "research history",
        "research activities",
        "research work",
    ],
    "projects": [
        "projects",
        "academic projects",
        "personal projects",
        "selected projects",
        "relevant projects",
        "key projects",
        "major projects",
        "technical projects",
        "project work",
        "project submitted",
        "projects submitted",
        "r&d projects",
    ],
    "skills": [
        "skills",
        "technical skills",
        "technical skill",
        "core skills",
        "key skills",
        "competencies",
        "technical competencies",
        "core competencies",
        "skills & expertise",
        "areas of expertise",
        "technical proficiency",
        "technical background",
        "skills & tools",
        "programming skills",
        "computer skills",
        "technical qualification",
        "technical qualifications",
        "technical exposure",
    ],
    "certifications": [
        "certifications",
        "certificates",
        "professional certifications",
        "certifications & courses",
        "trainings",
        "workshops & certifications",
        "licenses & certifications",
        "certifications and courses",
        "training certification",
        "training certifications",
    ],
    "publications": [
        "publications",
        "published papers",
        "research publications",
        "selected publications",
        "journal articles",
        "conference publications",
        "papers",
        "book chapters",
        "conference proceeding",
        "conference proceedings",
        "international conference proceeding",
        "journals refereed",
        "publication of research journal",
    ],
    "patents": [
        "patents",
        "patent applications",
        "inventions",
        "intellectual property",
        "patents & publications",
    ],
    "research_interests": [
        "research interests",
        "areas of interest",
        "research areas",
        "research focus",
        "topics of interest",
        "fields of research interest",
        "research interest",
        "current research",
    ],
    "awards": [
        "awards",
        "honors",
        "awards & honors",
        "distinctions",
        "recognitions",
        "honours",
        "awards and honors",
        "fellowships",
        "scholarships and fellowships",
    ],
    "achievements": [
        "achievements",
        "key achievements",
        "milestones",
        "accomplishments",
    ],
    "volunteering": [
        "volunteering",
        "volunteer work",
        "community involvement",
        "social service",
        "volunteer experience",
    ],
    "leadership": [
        "leadership",
        "leadership experience",
        "positions of responsibility",
        "extracurricular leadership",
    ],
    "coursework": [
        "coursework",
        "relevant coursework",
        "key courses",
        "courses",
        "subjects studied",
    ],
    "references": [
        "references",
        "professional references",
        "referees",
    ],
    "other": [
        "other",
        "declaration",
        "miscellaneous",
        "hobbies",
        "interests",
        "languages",
        "extracurricular activities",
        "additional information",
        "memberships",
        "affiliations",
        "responsibilities",
    ],
}


@dataclass(slots=True)
class NormalizationResult:
    raw_heading: str
    canonical_section: str
    confidence: float
    method: str
    review_required: bool
    matched_alias: str = ""
    label_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "raw_heading": self.raw_heading,
            "canonical_section": self.canonical_section,
            "confidence": round(self.confidence, 4),
            "method": self.method,
            "matched_alias": self.matched_alias,
            "review_required": self.review_required,
            "label_scores": {k: round(v, 4) for k, v in self.label_scores.items()},
        }


def clean_heading_text(raw_text: str) -> str:
    cleaned = (raw_text or "").strip()
    # Strip leading bullets or numbering e.g. "1.", "I.", "•", "-"
    cleaned = re.sub(r"^\s*(?:\d+[\.\)]|[I|V|X]+[\.\)]|[-•*➢])\s*", "", cleaned)
    # Strip trailing punctuation e.g. ":", "-", "--"
    cleaned = re.sub(r"[\s:\-–—]+$", "", cleaned).strip().lower()
    return cleaned


class SectionNormalizer:
    def __init__(self, *, aliases: Optional[Dict[str, List[str]]] = None) -> None:
        self.aliases = aliases or CANONICAL_ALIASES

    def normalize(self, raw_heading: str) -> NormalizationResult:
        heading = (raw_heading or "").strip()
        if not heading:
            return NormalizationResult(
                raw_heading="",
                canonical_section="other",
                confidence=0.0,
                method="empty_heading",
                review_required=True,
            )

        core = clean_heading_text(heading)
        if not core:
            return NormalizationResult(
                raw_heading=heading,
                canonical_section="other",
                confidence=0.1,
                method="non_alpha_heading",
                review_required=True,
            )

        # 1. Exact alias match
        for category, alias_list in self.aliases.items():
            for alias in alias_list:
                if core == alias.lower():
                    return NormalizationResult(
                        raw_heading=heading,
                        canonical_section=normalize_section_label(category),
                        confidence=1.0,
                        method="exact_alias_match",
                        matched_alias=alias,
                        review_required=False,
                    )

        # 2. Substring/Word overlap match for short core text (<= 5 words)
        core_words = core.split()
        if len(core_words) <= 5:
            best_cat = "other"
            best_alias = ""
            best_score = 0.0

            for category, alias_list in self.aliases.items():
                for alias in alias_list:
                    alias_clean = alias.lower()
                    alias_words = alias_clean.split()
                    if core.startswith(alias_clean) or core.endswith(alias_clean):
                        score = 0.90
                    elif len(alias_words) > 1 and all(w in core_words for w in alias_words):
                        score = 0.85
                    elif len(alias_words) == 1 and alias_words[0] in core_words and len(core_words) <= 3:
                        score = 0.75
                    else:
                        score = 0.0

                    if score > best_score:
                        best_score = score
                        best_cat = category
                        best_alias = alias

            if best_score >= 0.70:
                return NormalizationResult(
                    raw_heading=heading,
                    canonical_section=normalize_section_label(best_cat),
                    confidence=best_score,
                    method="substring_alias_match",
                    matched_alias=best_alias,
                    review_required=best_score < 0.85,
                )

        # 3. Unmapped / Unknown heading fallback
        return NormalizationResult(
            raw_heading=heading,
            canonical_section="other",
            confidence=0.30,
            method="unmapped_heading",
            matched_alias="",
            review_required=True,
        )
