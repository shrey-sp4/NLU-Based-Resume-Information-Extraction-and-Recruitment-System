from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .candidates import SECTION_PROTOTYPES, suggest_canonical_label
from .features import SparseTfidfVectorizer
from .models import CANONICAL_SECTION_LABELS, normalize_section_label


DEFAULT_LABEL_PROFILES: Dict[str, List[str]] = {
    "education": ["education academic background qualifications degree university college"],
    "experience": ["experience work history employment career professional journey"],
    "skills": ["skills technical skills competencies expertise software tools"],
    "projects": ["projects project work implementations research projects"],
    "publications": ["publications journal articles conference papers research articles"],
    "certifications": ["certifications courses workshops training certificates"],
    "research_interests": ["research interests research areas topics focus"],
    "achievements": ["achievements awards honors recognitions distinctions"],
    "personal_details": ["personal details contact information profile summary"],
    "summary": ["summary professional summary objective profile"],
    "references": ["references professional references"],
    "responsibilities": ["responsibilities roles service activities"],
    "memberships": ["memberships affiliations professional bodies"],
    "patents": ["patents patent inventions"],
    "declaration": ["declaration"],
    "other": ["other"],
}


@dataclass(slots=True)
class NormalizationResult:
    raw_heading: str
    canonical_section: str
    confidence: float
    method: str
    review_required: bool
    label_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "raw_heading": self.raw_heading,
            "canonical_section": self.canonical_section,
            "confidence": round(self.confidence, 4),
            "method": self.method,
            "review_required": self.review_required,
            "label_scores": {k: round(v, 4) for k, v in self.label_scores.items()},
        }


class SectionNormalizer:
    def __init__(
        self,
        *,
        threshold: float = 0.45,
        label_profiles: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        self.threshold = threshold
        self.label_profiles = label_profiles or DEFAULT_LABEL_PROFILES
        self.vectorizer = SparseTfidfVectorizer()
        self._fit_ready = False
        self._label_vectors: Dict[str, Dict[str, float]] = {}

    def fit(self, headings: Iterable[str]) -> "SectionNormalizer":
        texts = list(headings)
        profile_texts = [profile for profiles in self.label_profiles.values() for profile in profiles]
        self.vectorizer.fit(texts + profile_texts)
        self._label_vectors = {}
        for label, profiles in self.label_profiles.items():
            combined = " ".join(profiles)
            self._label_vectors[label] = self.vectorizer.transform_one(combined)
        self._fit_ready = True
        return self

    def _similarity(self, heading: str, label: str) -> float:
        heading_vector = self.vectorizer.transform_one(heading)
        label_vector = self._label_vectors.get(label, {})
        if not heading_vector or not label_vector:
            return 0.0

        numerator = 0.0
        for feature, value in heading_vector.items():
            if feature in label_vector:
                numerator += value * label_vector[feature]

        heading_norm = sum(v * v for v in heading_vector.values()) ** 0.5
        label_norm = sum(v * v for v in label_vector.values()) ** 0.5
        if not heading_norm or not label_norm:
            return 0.0
        return numerator / (heading_norm * label_norm)

    def normalize(self, raw_heading: str) -> NormalizationResult:
        heading = (raw_heading or "").strip()
        if not heading:
            return NormalizationResult(
                raw_heading="",
                canonical_section="other",
                confidence=0.0,
                method="empty_heading",
                review_required=True,
                label_scores={},
            )

        if not self._fit_ready:
            self.fit([heading])

        similarity_scores = {label: self._similarity(heading, label) for label in CANONICAL_SECTION_LABELS}
        prototype_label, prototype_score = suggest_canonical_label(heading)
        best_label = max(similarity_scores, key=similarity_scores.get, default="other")
        best_score = similarity_scores.get(best_label, 0.0)

        if prototype_score > best_score:
            best_label = prototype_label
            best_score = prototype_score
            method = "prototype_similarity"
        else:
            method = "tfidf_prototype_similarity"

        if best_score < self.threshold:
            return NormalizationResult(
                raw_heading=heading,
                canonical_section="other",
                confidence=round(best_score, 4),
                method=method,
                review_required=True,
                label_scores=similarity_scores,
            )

        return NormalizationResult(
            raw_heading=heading,
            canonical_section=normalize_section_label(best_label),
            confidence=round(best_score, 4),
            method=method,
            review_required=best_score < max(self.threshold + 0.15, 0.75),
            label_scores=similarity_scores,
        )

