from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from .detector import SectionBoundaryDecision, SectionBoundaryDetector
from .models import LineRecord, RawLineRecord, ResumeSectioningResult, SectionSpan
from .normalization import SectionNormalizer


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
        *,
        default_section: str = "other",
    ) -> None:
        self.detector = detector or SectionBoundaryDetector()
        self.normalizer = normalizer or SectionNormalizer()
        self.default_section = default_section

    def segment(self, lines: Sequence[RawLineRecord]) -> SegmentationArtifact:
        spans: List[SectionSpan] = []
        decisions: List[SectionBoundaryDecision] = []
        current_span: Optional[SectionSpan] = None
        current_section = self.default_section

        for index, line in enumerate(lines):
            previous_blank = index == 0 or not lines[index - 1].text.strip()
            next_blank = index == len(lines) - 1 or not lines[index + 1].text.strip()
            decision = self.detector.predict_line(line, previous_blank=previous_blank, next_blank=next_blank)
            decisions.append(decision)

            if decision.is_heading:
                current_section = decision.canonical_section or self.default_section
                current_span = SectionSpan(
                    resume_id=line.resume_id,
                    section=current_section,
                    raw_heading=line.text.strip(),
                    confidence=decision.confidence,
                    method=decision.method,
                    review_required=decision.review_required,
                )
                current_span.add_line(
                    LineRecord(
                        resume_id=line.resume_id,
                        document_id=line.document_id,
                        page_number=line.page_number,
                        line_number=line.line_number,
                        line_index=line.line_index,
                        text=line.text,
                        section_label=current_section,
                        is_heading=True,
                        raw_heading=line.text.strip(),
                        heading_confidence=decision.confidence,
                        heading_method=decision.method,
                        review_required=decision.review_required,
                    )
                )
                spans.append(current_span)
                continue

            if current_span is None:
                current_span = SectionSpan(
                    resume_id=line.resume_id,
                    section=current_section,
                    raw_heading="",
                    confidence=0.0,
                    method="pre_heading",
                    review_required=True,
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

        summary = {
            "num_sections": len(spans),
            "unmapped_rate": round(
                sum(1 for decision in decisions if decision.canonical_section == "other") / len(decisions), 4
            ) if decisions else 0.0,
            "low_confidence_rate": round(
                sum(1 for decision in decisions if decision.review_required) / len(decisions), 4
            ) if decisions else 0.0,
        }
        result = ResumeSectioningResult(
            resume_id=lines[0].resume_id if lines else "",
            document_id=lines[0].document_id if lines else "",
            sections=spans,
            summary=summary,
        )
        return SegmentationArtifact(result=result, decisions=decisions)

