from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .candidates import CandidateLine, score_heading_likeness, suggest_canonical_label
from .features import SparseTfidfVectorizer, merge_feature_dicts
from .models import HeadingPrediction, RawLineRecord
from .normalization import SectionNormalizer


def softmax(scores: Mapping[str, float]) -> Dict[str, float]:
    if not scores:
        return {}
    max_score = max(scores.values())
    exp_scores = {label: math.exp(score - max_score) for label, score in scores.items()}
    total = sum(exp_scores.values()) or 1.0
    return {label: value / total for label, value in exp_scores.items()}


class SparseLinearOVRClassifier:
    def __init__(self, learning_rate: float = 0.08, epochs: int = 20, l2: float = 0.0005) -> None:
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.l2 = l2
        self.classes_: List[str] = []
        self.weights: Dict[str, Dict[str, float]] = {}
        self.bias: Dict[str, float] = {}
        self.fitted = False

    def fit(self, X: Sequence[Mapping[str, float]], y: Sequence[str]) -> "SparseLinearOVRClassifier":
        self.classes_ = sorted(set(y))
        self.weights = {label: defaultdict(float) for label in self.classes_}
        self.bias = {label: 0.0 for label in self.classes_}

        for _ in range(self.epochs):
            for features, target in zip(X, y):
                for label in self.classes_:
                    score = self._score(label, features)
                    prob = 1.0 / (1.0 + math.exp(-max(min(score, 20.0), -20.0)))
                    desired = 1.0 if label == target else 0.0
                    error = desired - prob
                    self.bias[label] += self.learning_rate * error
                    weights = self.weights[label]
                    for feature, value in features.items():
                        if feature == "bias":
                            continue
                        update = self.learning_rate * (error * value - self.l2 * weights.get(feature, 0.0))
                        weights[feature] = weights.get(feature, 0.0) + update

        self.fitted = True
        return self

    def _score(self, label: str, features: Mapping[str, float]) -> float:
        score = self.bias.get(label, 0.0)
        weights = self.weights.get(label, {})
        for feature, value in features.items():
            score += weights.get(feature, 0.0) * value
        return score

    def decision_function(self, features: Mapping[str, float]) -> Dict[str, float]:
        return {label: self._score(label, features) for label in self.classes_}

    def predict_proba(self, features: Mapping[str, float]) -> Dict[str, float]:
        return softmax(self.decision_function(features))

    def predict(self, features: Mapping[str, float]) -> Tuple[str, float]:
        probs = self.predict_proba(features)
        if not probs:
            return "other", 0.0
        label = max(probs, key=probs.get)
        return label, probs[label]


@dataclass(slots=True)
class SectionBoundaryDecision:
    line: RawLineRecord
    is_heading: bool
    heading_probability: float
    canonical_section: str
    confidence: float
    method: str
    review_required: bool
    reasons: List[str] = field(default_factory=list)
    candidate: Optional[CandidateLine] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "line": self.line.to_dict(),
            "is_heading": self.is_heading,
            "heading_probability": round(self.heading_probability, 4),
            "canonical_section": self.canonical_section,
            "confidence": round(self.confidence, 4),
            "method": self.method,
            "review_required": self.review_required,
            "reasons": list(self.reasons),
            "candidate": self.candidate.to_dict() if self.candidate else None,
        }


class SectionBoundaryDetector:
    def __init__(
        self,
        *,
        heading_threshold: float = 0.55,
        review_threshold: float = 0.65,
    ) -> None:
        self.heading_threshold = heading_threshold
        self.review_threshold = review_threshold
        self.vectorizer = SparseTfidfVectorizer()
        self.binary_model = SparseLinearOVRClassifier()
        self.section_model = SparseLinearOVRClassifier()
        self.normalizer = SectionNormalizer()
        self.fitted = False

    def _build_candidate(
        self,
        line: RawLineRecord,
        *,
        previous_blank: bool = False,
        next_blank: bool = False,
    ) -> CandidateLine:
        heading_likeness = score_heading_likeness(
            line,
            previous_blank=previous_blank,
            next_blank=next_blank,
        )
        structural_score = float(heading_likeness["structural_score"])
        prototype_label, prototype_similarity = suggest_canonical_label(line.text)
        heading_score = min(1.0, structural_score + (prototype_similarity * 0.35))
        confidence = max(structural_score, prototype_similarity)
        reasons = list(heading_likeness["reasons"])
        if prototype_label != "other" and prototype_similarity > 0:
            reasons.append(f"prototype:{prototype_label}")
        return CandidateLine(
            line=line,
            structural_score=structural_score,
            prototype_similarity=prototype_similarity,
            heading_score=heading_score,
            suggested_label=prototype_label,
            confidence=confidence,
            reasons=reasons,
        )

    def fit(self, records: Sequence[Mapping[str, object]]) -> "SectionBoundaryDetector":
        texts: List[str] = []
        heading_examples: List[Mapping[str, float]] = []
        heading_labels: List[str] = []
        section_examples: List[Mapping[str, float]] = []
        section_labels: List[str] = []

        for record in records:
            text = str(record.get("text", ""))
            texts.append(text)

        self.vectorizer.fit(texts)

        for record in records:
            text = str(record.get("text", ""))
            is_heading = bool(record.get("is_heading", False))
            label = str(record.get("section_label") or "other")
            raw_line = RawLineRecord(
                resume_id=str(record.get("resume_id", "")),
                document_id=str(record.get("document_id", "")),
                source_file=str(record.get("source_file", "")),
                source_run_id=str(record.get("source_run_id", "")),
                page_number=int(record.get("page_number", 0)),
                line_number=int(record.get("line_number", 0)),
                line_index=int(record.get("line_index", 0)),
                text=text,
                preceded_by_blank=bool(record.get("preceded_by_blank", False)),
                followed_by_blank=bool(record.get("followed_by_blank", False)),
            )
            candidate = self._build_candidate(
                raw_line,
                previous_blank=bool(record.get("preceded_by_blank", False)),
                next_blank=bool(record.get("followed_by_blank", False)),
            )
            feature_map = merge_feature_dicts(
                self.vectorizer.transform_one(text),
                {
                    "bias": 1.0,
                    "line_length": float(len(text.strip())),
                    "word_count": float(len(text.split())),
                    "heading_candidate_score": candidate.heading_score,
                    "prototype_similarity": candidate.prototype_similarity,
                    "structural_score": candidate.structural_score,
                },
            )
            heading_examples.append(feature_map)
            heading_labels.append("heading" if is_heading else "content")
            if is_heading:
                section_examples.append(feature_map)
                section_labels.append(label)

        if heading_examples:
            self.binary_model.fit(heading_examples, heading_labels)
        if section_examples:
            self.section_model.fit(section_examples, section_labels)
        self.normalizer.fit(texts)
        self.fitted = True
        return self

    def predict_line(self, line: RawLineRecord, previous_blank: bool = False, next_blank: bool = False) -> SectionBoundaryDecision:
        candidate = self._build_candidate(
            line,
            previous_blank=previous_blank,
            next_blank=next_blank,
        )
        features = merge_feature_dicts(
            self.vectorizer.transform_one(line.text),
            {
                "bias": 1.0,
                "line_length": float(len(line.text.strip())),
                "word_count": float(len(line.text.split())),
                "heading_candidate_score": candidate.heading_score,
                "prototype_similarity": candidate.prototype_similarity,
                "structural_score": candidate.structural_score,
                "preceded_by_blank": 1.0 if previous_blank else 0.0,
                "followed_by_blank": 1.0 if next_blank else 0.0,
            },
        )

        heading_probs = self.binary_model.predict_proba(features) if self.fitted and self.binary_model.fitted else {}
        heading_probability = heading_probs.get("heading", candidate.heading_score)
        is_heading = heading_probability >= self.heading_threshold

        normalized = self.normalizer.normalize(line.text) if is_heading else None
        canonical_section = normalized.canonical_section if normalized else "other"
        confidence = normalized.confidence if normalized else heading_probability
        review_required = (
            (not is_heading)
            or heading_probability < self.review_threshold
            or (normalized.review_required if normalized else True)
        )
        reasons = list(candidate.reasons)
        if is_heading:
            reasons.append("heading_classifier")
            if normalized:
                reasons.append(f"normalized:{normalized.method}")
        else:
            reasons.append("content_line")

        return SectionBoundaryDecision(
            line=line,
            is_heading=is_heading,
            heading_probability=heading_probability,
            canonical_section=canonical_section,
            confidence=confidence,
            method="tfidf_linear+heuristic" if self.fitted else "heuristic_only",
            review_required=review_required,
            reasons=reasons,
            candidate=candidate,
        )
