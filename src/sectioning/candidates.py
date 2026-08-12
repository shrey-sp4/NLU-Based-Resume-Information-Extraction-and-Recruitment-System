from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .features import extract_line_features, merge_feature_dicts
from .models import RawLineRecord


SECTION_PROTOTYPES: Dict[str, List[str]] = {
    "education": ["education", "academic background", "educational qualifications", "qualifications"],
    "experience": ["experience", "work history", "career experience", "employment history"],
    "skills": ["skills", "technical skills", "core competencies", "areas of expertise"],
    "projects": ["projects", "project experience", "project work", "academic projects"],
    "publications": ["publications", "research publications", "journal publications", "conference papers"],
    "certifications": ["certifications", "training", "workshops", "courses"],
    "research_interests": ["research interests", "research areas", "research statement", "areas of interest"],
    "achievements": ["achievements", "awards", "honors", "recognitions"],
    "personal_details": ["personal details", "contact details", "profile", "summary"],
    "summary": ["summary", "profile summary", "professional summary", "objective"],
    "references": ["references", "professional references"],
    "responsibilities": ["responsibilities", "roles and responsibilities", "service"],
    "memberships": ["memberships", "professional affiliations"],
    "patents": ["patents", "patent"],
    "declaration": ["declaration"],
    "other": ["other"],
}


@dataclass(slots=True)
class CandidateLine:
    line: RawLineRecord
    structural_score: float
    prototype_similarity: float
    heading_score: float
    suggested_label: str
    confidence: float
    reasons: List[str] = field(default_factory=list)

    @property
    def is_candidate(self) -> bool:
        return self.heading_score >= 0.5

    def to_dict(self) -> Dict[str, object]:
        return {
            "line": self.line.to_dict(),
            "structural_score": round(self.structural_score, 4),
            "prototype_similarity": round(self.prototype_similarity, 4),
            "heading_score": round(self.heading_score, 4),
            "suggested_label": self.suggested_label,
            "confidence": round(self.confidence, 4),
            "reasons": list(self.reasons),
            "is_candidate": self.is_candidate,
        }


def prototype_score(text: str, prototypes: Iterable[str]) -> float:
    text_tokens = set(extract_line_features(text).keys())
    cleaned = (text or "").lower()
    score = 0.0
    for prototype in prototypes:
        proto = prototype.lower()
        if proto and proto in cleaned:
            score += 1.0
        elif len(set(proto.split()).intersection(cleaned.split())) >= 2:
            score += 0.5
    return min(score / max(1, len(list(prototypes))), 1.0)


def score_heading_likeness(
    line: RawLineRecord,
    *,
    previous_blank: bool = False,
    next_blank: bool = False,
) -> Dict[str, float]:
    structural = extract_line_features(
        line.text,
        preceded_by_blank=previous_blank,
        followed_by_blank=next_blank,
    )

    score = 0.0
    reasons: List[str] = []

    if structural["short_line"]:
        score += 0.20
        reasons.append("short_line")
    if structural["is_all_caps"]:
        score += 0.20
        reasons.append("all_caps")
    if structural["is_title_case"]:
        score += 0.12
        reasons.append("title_case")
    if structural["starts_with_numbering"]:
        score += 0.10
        reasons.append("numbered")
    if structural["ends_with_colon"]:
        score += 0.10
        reasons.append("colon")
    if structural["preceded_by_blank"]:
        score += 0.10
        reasons.append("preceded_by_blank")
    if structural["followed_by_blank"]:
        score += 0.10
        reasons.append("followed_by_blank")
    if structural["lexical_density"] <= 0.85:
        score += 0.08
        reasons.append("low_density")
    if structural["word_count"] <= 6:
        score += 0.10
        reasons.append("short_word_count")

    if structural["bullet_like"]:
        score -= 0.10
        reasons.append("bullet_like")

    return {
        "structural_score": max(0.0, min(score, 1.0)),
        "reasons": reasons,
        "features": structural,
    }


def suggest_canonical_label(text: str) -> tuple[str, float]:
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return "other", 0.0

    best_label = "other"
    best_score = 0.0
    for label, prototypes in SECTION_PROTOTYPES.items():
        local = 0.0
        for prototype in prototypes:
            proto = prototype.lower()
            if proto and proto in cleaned:
                local = max(local, 1.0)
            else:
                words = set(proto.split())
                overlap = len(words.intersection(cleaned.split()))
                if overlap:
                    local = max(local, min(0.25 * overlap, 0.75))
        if local > best_score:
            best_label = label
            best_score = local

    return best_label, best_score


def generate_heading_candidates(lines: Iterable[RawLineRecord]) -> List[CandidateLine]:
    line_list = list(lines)
    candidates: List[CandidateLine] = []

    for line in line_list:
        heading_likeness = score_heading_likeness(
            line,
            previous_blank=line.preceded_by_blank,
            next_blank=line.followed_by_blank,
        )
        structural_score = heading_likeness["structural_score"]
        prototype_label, prototype_similarity = suggest_canonical_label(line.text)

        heading_score = min(1.0, structural_score + (prototype_similarity * 0.35))
        confidence = max(structural_score, prototype_similarity)
        reasons = list(heading_likeness["reasons"])
        if prototype_label != "other" and prototype_similarity > 0:
            reasons.append(f"prototype:{prototype_label}")

        candidates.append(
            CandidateLine(
                line=line,
                structural_score=structural_score,
                prototype_similarity=prototype_similarity,
                heading_score=heading_score,
                suggested_label=prototype_label,
                confidence=confidence,
                reasons=reasons,
            )
        )

    return candidates
