from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from .detector import SectionBoundaryDecision, SectionBoundaryDetector
from .models import LineRecord, RawLineRecord, ResumeSectioningResult, SectionSpan
from .normalization import SectionNormalizer

# Common academic & technical subsection header patterns that belong under specific parent sections
SUBSECTION_PARENT_DOMAINS: Dict[str, Tuple[str, ...]] = {
    "publications": (
        "journal", "conference", "article", "paper", "book", "chapter", "proceedings",
        "peer-reviewed", "patent", "scopus", "ugc", "volume", "editor", "author", "manuscript"
    ),
    "experience": (
        "teaching", "research assistant", "teaching assistant", "postdoctoral", "fellowship",
        "internship", "industry", "academic experience", "positions held", "key responsibilities"
    ),
    "education": (
        "marks", "grade", "percentage", "board", "university", "school", "coursework",
        "degree", "diploma", "matriculation", "intermediate", "higher secondary"
    ),
    "projects": (
        "major project", "mini project", "academic project", "industrial project", "software project"
    ),
    "awards": (
        "scholarship", "fellowship", "grant", "medal", "merit", "rank"
    ),
}


def is_evidence_based_subsection(raw_heading: str, parent_canonical: str) -> bool:
    cleaned = raw_heading.strip().lower()
    if not cleaned or not parent_canonical:
        return False

    keywords = SUBSECTION_PARENT_DOMAINS.get(parent_canonical)
    if not keywords:
        return False

    return any(kw in cleaned for kw in keywords)


@dataclass(slots=True)
class SegmentationArtifact:
    result: ResumeSectioningResult
    decisions: List[SectionBoundaryDecision]

    def to_dict(self) -> Dict[str, object]:
        return {
            "result": self.result.to_dict(),
            "decisions": [decision.to_dict() for decision in self.decisions],
        }


class SectionSegmenter:
    def __init__(
        self,
        detector: Optional[SectionBoundaryDetector] = None,
        normalizer: Optional[SectionNormalizer] = None,
    ) -> None:
        self.detector = detector or SectionBoundaryDetector()
        self.normalizer = normalizer or SectionNormalizer()

    def segment(self, lines: Sequence[RawLineRecord]) -> SegmentationArtifact:
        spans: List[SectionSpan] = []
        decisions: List[SectionBoundaryDecision] = []
        current_span: Optional[SectionSpan] = None
        active_parent_span: Optional[SectionSpan] = None
        section_counter = 0

        for i, line in enumerate(lines):
            prev_decision = decisions[-1] if decisions else None
            prev_is_heading = prev_decision.is_heading if prev_decision else False
            previous_blank = (
                i == 0
                or line.preceded_by_blank
                or (i > 0 and not lines[i - 1].text.strip())
                or prev_is_heading
            )
            next_blank = (i < len(lines) - 1 and not lines[i + 1].text.strip()) or line.followed_by_blank
            decision = self.detector.predict_line(line, previous_blank=previous_blank, next_blank=next_blank)
            decisions.append(decision)

            if decision.is_heading:
                section_counter += 1
                sec_id = f"section_{section_counter:03d}"
                orig_heading = line.text.strip()
                canonical_label = decision.canonical_section or "other"

                # Hierarchy & Section Type determination
                if canonical_label != "other":
                    # Known canonical top-level section
                    level = 1
                    sec_type = "canonical"
                    parent_id = None
                    norm_label = canonical_label
                elif active_parent_span and is_evidence_based_subsection(orig_heading, active_parent_span.normalized_heading):
                    # Genuine evidence-based subsection
                    level = 2
                    sec_type = "subsection"
                    parent_id = active_parent_span.section_id
                    norm_label = "other"
                else:
                    # Custom / Unmapped top-level section
                    level = 1
                    sec_type = "custom"
                    parent_id = None
                    norm_label = "other"

                detection_meta = {
                    "rule_name": decision.method,
                    "matched_alias": decision.reasons[0] if decision.reasons else "",
                    "confidence": round(decision.confidence, 4),
                    "review_required": decision.review_required,
                    "evidence": {
                        "reasons": list(decision.reasons),
                        "preceded_by_blank": previous_blank,
                        "followed_by_blank": next_blank,
                    },
                }

                current_span = SectionSpan(
                    resume_id=line.resume_id,
                    section=canonical_label,
                    raw_heading=orig_heading,
                    original_heading=orig_heading,
                    normalized_heading=norm_label,
                    level=level,
                    section_type=sec_type,
                    parent_section_id=parent_id,
                    confidence=decision.confidence,
                    method=decision.method,
                    review_required=decision.review_required,
                    section_id=sec_id,
                    detection_metadata=detection_meta,
                )

                if level == 1 and sec_type == "canonical":
                    active_parent_span = current_span

                current_span.add_line(
                    LineRecord(
                        resume_id=line.resume_id,
                        document_id=line.document_id,
                        page_number=line.page_number,
                        line_number=line.line_number,
                        line_index=line.line_index,
                        text=line.text,
                        section_label=canonical_label,
                        is_heading=True,
                        raw_heading=orig_heading,
                        heading_confidence=decision.confidence,
                        heading_method=decision.method,
                        review_required=decision.review_required,
                    )
                )
                spans.append(current_span)
                continue

            if current_span is None:
                # Pre-heading Preamble section (explicit preamble, not contact)
                section_counter += 1
                sec_id = f"section_{section_counter:03d}"
                current_span = SectionSpan(
                    resume_id=line.resume_id,
                    section="preamble",
                    raw_heading="",
                    original_heading="",
                    normalized_heading="preamble",
                    level=1,
                    section_type="preamble",
                    parent_section_id=None,
                    confidence=1.0,
                    method="preamble_region",
                    review_required=False,
                    section_id=sec_id,
                    detection_metadata={"rule_name": "preamble_unsectioned_content"},
                )
                spans.append(current_span)

            current_span.add_line(
                LineRecord(
                    resume_id=line.resume_id,
                    document_id=line.document_id,
                    page_number=line.page_number,
                    line_number=line.line_number,
                    line_index=line.line_index,
                    text=line.text,
                    section_label=current_span.section,
                    is_heading=False,
                )
            )

        total_lines_input = len(lines)
        total_lines_spanned = sum(len(span.lines) for span in spans)
        text_coverage_ratio = 1.0 if total_lines_input == total_lines_spanned else (total_lines_spanned / total_lines_input if total_lines_input > 0 else 1.0)

        # Disambiguated Section Diagnostics
        top_level_canonical = sum(1 for span in spans if span.level == 1 and span.section_type == "canonical")
        subsections = sum(1 for span in spans if span.level == 2 and span.section_type == "subsection")
        custom_sections = sum(1 for span in spans if span.level == 1 and span.section_type == "custom")
        preamble_sections = sum(1 for span in spans if span.section_type == "preamble")

        summary = {
            "num_sections": len(spans),
            "top_level_canonical_sections": top_level_canonical,
            "subsections": subsections,
            "custom_sections": custom_sections,
            "preamble_sections": preamble_sections,
            "total_lines_covered": total_lines_spanned,
            "total_lines_input": total_lines_input,
            "text_coverage_ratio": round(text_coverage_ratio, 4),
            "detected_canonical_sections": [span.normalized_heading for span in spans if span.original_heading and span.normalized_heading != "other"],
            "unmapped_headings_count": sum(1 for span in spans if span.normalized_heading == "other" and span.original_heading),
        }

        result = ResumeSectioningResult(
            resume_id=lines[0].resume_id if lines else "",
            document_id=lines[0].document_id if lines else "",
            sections=spans,
            summary=summary,
        )
        return SegmentationArtifact(result=result, decisions=decisions)
