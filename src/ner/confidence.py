from __future__ import annotations

from typing import Any, Dict, List, Tuple

class AuditableConfidenceEvaluator:
    """Confidence Scoring and Human Review Routing Engine for Stage 9."""

    def evaluate_field_confidence(
        self,
        field_type: str,
        value: Any,
        extractor_name: str,
        section_type: str,
        has_conflict: bool = False,
    ) -> Tuple[str, float, str]:
        if not value:
            return "LOW", 0.0, "Missing value"

        # Deterministic / Regex Exact Match
        if "regex" in extractor_name or extractor_name in ("doi_extractor", "phone_regex", "email_regex"):
            return "HIGH", 1.0, "Deterministic pattern match with 100% precision"

        # Gazetteer Taxonomy Match
        if "gazetteer" in extractor_name or "degree_tagger" in extractor_name:
            if has_conflict:
                return "MEDIUM", 0.75, "Gazetteer match with minor entity type conflict"
            return "HIGH", 0.95, "Taxonomy gazetteer match"

        # Learned NER / Section Context Match
        if "crf" in extractor_name or "hybrid" in extractor_name:
            if section_type in ("education", "experience", "publications"):
                return "HIGH", 0.90, "Section-aligned sequence model prediction"
            return "MEDIUM", 0.70, "Sequence model prediction outside primary section"

        return "LOW", 0.50, "Low confidence prediction requiring verification"

    def determine_review_routing(
        self,
        record_type: str,
        record: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        review_items: List[Dict[str, Any]] = []

        if record_type == "education":
            if not record.get("institution"):
                review_items.append({
                    "field": "institution",
                    "value": None,
                    "confidence": "REVIEW_REQUIRED",
                    "reason": "Education degree entry missing associated institution name",
                    "source_record": record.get("record_id")
                })
        elif record_type == "experience":
            if not record.get("institution_or_company"):
                review_items.append({
                    "field": "institution_or_company",
                    "value": None,
                    "confidence": "REVIEW_REQUIRED",
                    "reason": "Academic role title entry missing institution/company name",
                    "source_record": record.get("record_id")
                })

        return review_items
