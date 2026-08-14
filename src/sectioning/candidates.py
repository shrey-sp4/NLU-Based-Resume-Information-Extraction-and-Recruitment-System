from __future__ import annotations

import re
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
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return 0.0

    # Clean leading numbers/bullets and trailing colons for prototype matching
    core = re.sub(r"^\s*(?:\d+[\.\)]|[-•*])\s*", "", cleaned)
    core = re.sub(r":\s*$", "", core).strip()

    best = 0.0
    for prototype in prototypes:
        proto = prototype.lower().strip()
        if core == proto:
            best = max(best, 1.0)
        elif core.startswith(proto) or core.endswith(proto):
            # Only count prefix/suffix if total word count is small (<= 5 words)
            if len(core.split()) <= 5:
                best = max(best, 0.85)
        else:
            # Word overlap ratio for multi-word heading candidates
            proto_words = set(proto.split())
            core_words = set(core.split())
            if proto_words and core_words and len(core_words) <= 5:
                overlap = len(proto_words.intersection(core_words))
                if overlap == len(proto_words):
                    best = max(best, 0.75)
    return best


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

    # Positive heading indicators
    if structural["short_line"]:
        score += 0.20
        reasons.append("short_line")
    if structural["very_short_line"]:
        score += 0.10
        reasons.append("very_short_line")
    if structural["is_all_caps"]:
        score += 0.20
        reasons.append("all_caps")
    if structural["is_title_case"]:
        score += 0.15
        reasons.append("title_case")
    if structural["starts_with_numbering"]:
        score += 0.08
        reasons.append("numbered")
    if structural["ends_with_colon"]:
        score += 0.15
        reasons.append("colon")
    if structural["preceded_by_blank"]:
        score += 0.10
        reasons.append("preceded_by_blank")
    if structural["followed_by_blank"]:
        score += 0.10
        reasons.append("followed_by_blank")
    if structural["lexical_density"] <= 0.85 and structural["word_count"] <= 5:
        score += 0.05
        reasons.append("low_density")

    # Penalties for non-heading prose structures
    if structural.get("has_prose_indicators", 0.0):
        score -= 0.35
        reasons.append("prose_indicators")
    if structural.get("ends_with_period", 0.0):
        score -= 0.25
        reasons.append("ends_with_period")
    if structural.get("has_contact_info", 0.0):
        score -= 0.40
        reasons.append("contact_info")
    if structural.get("has_date_range", 0.0) and structural["word_count"] > 3:
        score -= 0.25
        reasons.append("date_range")
    if structural["bullet_like"]:
        score -= 0.20
        reasons.append("bullet_like")
    if structural["word_count"] > 7:
        score -= 0.30
        reasons.append("long_word_count")
    if structural["char_count"] > 80:
        score -= 0.25
        reasons.append("long_char_count")

    return {
        "structural_score": max(0.0, min(score, 1.0)),
        "reasons": reasons,
        "features": structural,
    }


def suggest_canonical_label(text: str) -> tuple[str, float]:
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return "other", 0.0

    features = extract_line_features(cleaned)
    # If the line is clearly prose/contact info, do not match heading prototypes
    if features.get("has_prose_indicators", 0.0) or features["word_count"] > 7 or features.get("has_contact_info", 0.0):
        return "other", 0.0

    best_label = "other"
    best_score = 0.0
    for label, prototypes in SECTION_PROTOTYPES.items():
        score = prototype_score(cleaned, prototypes)
        if score > best_score:
            best_label = label
            best_score = score

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

        # Whole-line candidate score requires structural plausibility
        # Prototype similarity boosts score only if line is not penalized as prose
        if structural_score < 0.15 and prototype_similarity < 0.8:
            heading_score = 0.0
        else:
            heading_score = min(1.0, (structural_score * 0.65) + (prototype_similarity * 0.35))

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

