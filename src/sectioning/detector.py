from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .candidates import CandidateLine, score_heading_likeness, suggest_canonical_label
from .models import RawLineRecord
from .normalization import NormalizationResult, SectionNormalizer


def is_body_sentence(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return True
    # If ends with period, comma, or semicolon -> body sentence (not a heading)
    if cleaned.endswith((".", ",", ";")):
        return True
    # If starts with bullet marker followed by action verbs
    if re.match(
        r"^\s*(?:[-•*➢]|\d+[\.\)])\s*(?:Developed|Implemented|Created|Designed|Worked|Responsible|Led|Managed|Built|Engineered|Utilized|Applied|Assisted|Participated|Studied|Gained|Handled|Achieved|Maintained)\b",
        cleaned,
        re.IGNORECASE,
    ):
        return True
    # Negative Contact Content Filter
    if re.match(r"^\s*(?:contact|contact\s+no|address|e-mail|email|mobile|tel|date\s+of\s+birth|dob)\b", cleaned, re.IGNORECASE):
        if re.search(r"[\d@,]", cleaned) or len(cleaned) > 15:
            return True
    # Negative Publication Metadata Filter
    if re.search(r"\b(?:ISBN|DOI|ISSN|http://|https://|www\.|Digital\s+library\s+URL)\b", cleaned, re.IGNORECASE):
        return True
    # Negative Marksheet / Table Line Filter
    if re.match(r"^\s*(?:CGPA|Percentage|Roll\s+No|Year\s+of\s+passing|Marks\s+Obtained|Board/University|Course\s+Board)\b", cleaned, re.IGNORECASE):
        return True
    # Contains contact elements like email or URL
    if "@" in cleaned or "http" in cleaned or "www." in cleaned:
        return True
    # Long sentences with > 8 words are body text unless strictly heading-like
    words = cleaned.split()
    if len(words) > 8:
        return True
    return False


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


CLASSIFIER_BIAS: float = -3.1127
CLASSIFIER_WEIGHTS: Dict[str, float] = {
    "word_count_le_3": 0.5966,
    "word_count_le_5": -0.0256,
    "word_count_le_8": -0.1112,
    "word_count_gt_8": -0.2462,
    "is_all_caps": 0.6639,
    "is_title_case": 0.2484,
    "ends_with_colon": 0.6668,
    "ends_with_period_or_comma": -0.8992,
    "has_bullet_marker": -0.3731,
    "has_digits_or_email": -1.4254,
    "has_metadata_keyword": -0.2698,
    "has_table_entry_keyword": 0.0,
    "has_contact_prefix": -0.2288,
    "exact_alias_match": 1.1830,
    "substring_alias_match": 0.7400,
    "alias_confidence": 1.4679,
    "previous_blank": 1.1767,
    "next_blank": 0.3075,
    "is_top_of_page": 0.1467,
    "is_repeated_page_header": -2.0,
}


class SectionBoundaryDetector:
    def __init__(
        self,
        *,
        normalizer: Optional[SectionNormalizer] = None,
        heading_threshold: float = 0.55,
        review_threshold: float = 0.65,
    ) -> None:
        self.normalizer = normalizer or SectionNormalizer()
        self.heading_threshold = heading_threshold
        self.review_threshold = review_threshold

    def compute_multi_signal_probability(
        self,
        text: str,
        norm: NormalizationResult,
        previous_blank: bool,
        next_blank: bool,
        line: RawLineRecord,
    ) -> Tuple[float, List[str]]:
        words = text.split()
        w_count = len(words)
        reasons: List[str] = []

        is_all_caps = 1.0 if (text.isupper() and any(c.isalpha() for c in text)) else 0.0
        is_title_case = 1.0 if ((text.istitle() or all(w[0].isupper() for w in words if w and w[0].isalpha())) and w_count <= 8) else 0.0
        ends_with_colon = 1.0 if text.endswith(":") else 0.0
        ends_with_period = 1.0 if text.endswith((".", ",", ";")) else 0.0
        has_bullet = 1.0 if text.startswith(("-", "•", "*", "➢")) else 0.0
        has_digits_email = 1.0 if ("@" in text or any(c.isdigit() for c in text)) else 0.0
        has_metadata = 1.0 if any(k in text.upper() for k in ["ISBN", "DOI", "ISSN", "HTTP", "WWW."]) else 0.0
        has_table = 1.0 if any(text.upper().startswith(k) for k in ["CGPA", "PERCENTAGE", "ROLL NO", "MARKS OBTAINED"]) else 0.0
        has_contact = 1.0 if any(text.upper().startswith(k) for k in ["CONTACT", "ADDRESS", "EMAIL", "MOBILE", "TEL", "DOB"]) else 0.0

        exact_alias = 1.0 if norm.method == "exact_alias_match" else 0.0
        sub_alias = 1.0 if (norm.method == "substring_alias_match" and norm.confidence >= 0.75) else 0.0
        alias_conf = norm.confidence

        prev_b = 1.0 if previous_blank else 0.0
        next_b = 1.0 if next_blank else 0.0
        is_top = 1.0 if line.line_number <= 2 else 0.0
        is_rep_hdr = 1.0 if getattr(line, "is_repeated_page_header", False) else 0.0

        feats = {
            "word_count_le_3": 1.0 if w_count <= 3 else 0.0,
            "word_count_le_5": 1.0 if 3 < w_count <= 5 else 0.0,
            "word_count_le_8": 1.0 if 5 < w_count <= 8 else 0.0,
            "word_count_gt_8": 1.0 if w_count > 8 else 0.0,
            "is_all_caps": is_all_caps,
            "is_title_case": is_title_case,
            "ends_with_colon": ends_with_colon,
            "ends_with_period_or_comma": ends_with_period,
            "has_bullet_marker": has_bullet,
            "has_digits_or_email": has_digits_email,
            "has_metadata_keyword": has_metadata,
            "has_table_entry_keyword": has_table,
            "has_contact_prefix": has_contact,
            "exact_alias_match": exact_alias,
            "substring_alias_match": sub_alias,
            "alias_confidence": alias_conf,
            "previous_blank": prev_b,
            "next_blank": next_b,
            "is_top_of_page": is_top,
            "is_repeated_page_header": is_rep_hdr,
        }

        logit = CLASSIFIER_BIAS
        for k, v in feats.items():
            if v > 0:
                w = CLASSIFIER_WEIGHTS.get(k, 0.0)
                logit += w * v
                reasons.append(f"{k}:{v:.2f}")

        import math
        prob = 1.0 / (1.0 + math.exp(-logit)) if logit >= 0 else math.exp(logit) / (1.0 + math.exp(logit))
        return prob, reasons

    def predict_line(
        self,
        line: RawLineRecord,
        previous_blank: bool = False,
        next_blank: bool = False,
    ) -> SectionBoundaryDecision:
        text = (line.text or "").strip()

        if line.is_repeated_page_header:
            return SectionBoundaryDecision(
                line=line,
                is_heading=False,
                heading_probability=0.0,
                canonical_section="other",
                confidence=0.0,
                method="page_header_artifact_rule",
                review_required=False,
                reasons=["repeated_page_header_artifact"],
            )

        if not text or is_body_sentence(text):
            return SectionBoundaryDecision(
                line=line,
                is_heading=False,
                heading_probability=0.0,
                canonical_section="other",
                confidence=0.0,
                method="body_text_rule",
                review_required=False,
                reasons=["empty_or_body_sentence"],
            )

        # Normalize line against canonical taxonomy
        norm: NormalizationResult = self.normalizer.normalize(text)
        words = text.split()
        word_count = len(words)
        is_all_caps = text.isupper() and any(c.isalpha() for c in text)
        is_title_case = (text.istitle() or all(w[0].isupper() for w in words if w and w[0].isalpha())) and word_count <= 8
        ends_with_colon = text.endswith(":")

        reasons: List[str] = []
        is_heading = False
        heading_prob = 0.0
        method = "rule_based"

        if norm.method == "exact_alias_match":
            is_heading = True
            heading_prob = 1.0
            method = "exact_alias_rule"
            reasons.append(f"exact_alias:{norm.matched_alias}")
        elif norm.method == "substring_alias_match" and norm.confidence >= 0.75:
            is_heading = True
            heading_prob = norm.confidence
            method = "substring_alias_rule"
            reasons.append(f"substring_alias:{norm.matched_alias}")
        else:
            # Multi-signal linear classifier fallback for unmapped candidates
            heading_prob, feature_reasons = self.compute_multi_signal_probability(
                text, norm, previous_blank, next_blank, line
            )
            reasons.extend(feature_reasons)
            if word_count <= 8 and previous_blank and (is_all_caps or ends_with_colon or (is_title_case and norm.canonical_section != "other")):
                is_heading = True
                heading_prob = max(heading_prob, 0.85 if is_all_caps or ends_with_colon else 0.75)
                method = "multi_signal_classifier"
            elif heading_prob >= self.heading_threshold:
                is_heading = True
                method = "multi_signal_classifier"
            else:
                is_heading = False
                method = "multi_signal_classifier"
                reasons.append("low_multi_signal_probability")

        canonical_sec = norm.canonical_section if is_heading else "other"
        confidence = max(heading_prob, norm.confidence) if is_heading else 0.0
        review_req = not is_heading or norm.review_required or confidence < self.review_threshold

        return SectionBoundaryDecision(
            line=line,
            is_heading=is_heading,
            heading_probability=heading_prob,
            canonical_section=canonical_sec,
            confidence=confidence,
            method=method,
            review_required=review_req,
            reasons=reasons,
        )
