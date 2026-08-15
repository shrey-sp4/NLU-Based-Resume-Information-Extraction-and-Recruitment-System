from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import RawLineRecord, ResumeSectioningResult
from .output import build_raw_line_records_from_run, ensure_directory, write_json
from .segmenter import SectionSegmenter, SegmentationArtifact


@dataclass(slots=True)
class SectioningPipelineResult:
    run_id: str
    run_dir: Path
    total_processed: int
    resumes_with_sections: int
    resumes_without_sections: int
    top_level_canonical_sections_count: int
    subsections_count: int
    custom_sections_count: int
    preamble_sections_count: int
    section_frequencies: Dict[str, int]
    unmapped_headings_count: int
    repeated_category_occurrences: int
    duplicate_identical_spans_count: int
    overlapping_spans_count: int
    avg_text_coverage_ratio: float
    review_required_count: int
    document_results: List[Dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "total_processed": self.total_processed,
            "resumes_with_sections": self.resumes_with_sections,
            "resumes_without_sections": self.resumes_without_sections,
            "top_level_canonical_sections_count": self.top_level_canonical_sections_count,
            "subsections_count": self.subsections_count,
            "custom_sections_count": self.custom_sections_count,
            "preamble_sections_count": self.preamble_sections_count,
            "section_frequencies": self.section_frequencies,
            "unmapped_headings_count": self.unmapped_headings_count,
            "repeated_category_occurrences": self.repeated_category_occurrences,
            "duplicate_identical_spans_count": self.duplicate_identical_spans_count,
            "overlapping_spans_count": self.overlapping_spans_count,
            "avg_text_coverage_ratio": round(self.avg_text_coverage_ratio, 4),
            "review_required_count": self.review_required_count,
            "document_results": self.document_results,
        }


class SectioningPipeline:
    def __init__(
        self,
        segmenter: Optional[SectionSegmenter] = None,
        output_root: Path = Path("output/sectioning"),
    ) -> None:
        self.segmenter = segmenter or SectionSegmenter()
        self.output_root = output_root

    def run_on_extraction(self, extraction_run_dir: Path) -> SectioningPipelineResult:
        if not extraction_run_dir.exists():
            raise FileNotFoundError(f"Extraction run directory not found: {extraction_run_dir}")

        all_line_records = build_raw_line_records_from_run(extraction_run_dir)
        doc_records: Dict[str, List[RawLineRecord]] = defaultdict(list)
        for record in all_line_records:
            doc_records[record.document_id].append(record)

        run_id = f"sectioning_{extraction_run_dir.name}"
        run_output_dir = ensure_directory(self.output_root / run_id)

        total_processed = 0
        resumes_with_sections = 0
        resumes_without_sections = 0

        top_canonical_total = 0
        subsections_total = 0
        custom_total = 0
        preamble_total = 0

        section_freq: Counter[str] = Counter()
        unmapped_count = 0
        repeated_category_occurrences = 0
        duplicate_identical_spans = 0
        overlapping_spans_total = 0

        total_text_coverage = 0.0
        review_required_count = 0

        document_results: List[Dict[str, object]] = []

        for doc_id, lines in sorted(doc_records.items()):
            total_processed += 1
            artifact = self.segmenter.segment(lines)
            res = artifact.result

            has_detected_sections = any(span.original_heading for span in res.sections)
            if has_detected_sections:
                resumes_with_sections += 1
            else:
                resumes_without_sections += 1

            doc_canonical_freq: Counter[str] = Counter()
            doc_spans_tuples = []
            assigned_line_indices = set()

            for span in res.sections:
                if span.section_type == "canonical":
                    top_canonical_total += 1
                elif span.section_type == "subsection":
                    subsections_total += 1
                elif span.section_type == "custom":
                    custom_total += 1
                elif span.section_type == "preamble":
                    preamble_total += 1

                if span.review_required:
                    review_required_count += 1

                if span.original_heading:
                    cat = span.normalized_heading
                    section_freq[cat] += 1
                    doc_canonical_freq[cat] += 1
                    if span.normalized_heading == "other":
                        unmapped_count += 1

                span_tuple = (span.start_line, span.end_line)
                if span_tuple in doc_spans_tuples:
                    duplicate_identical_spans += 1
                doc_spans_tuples.append(span_tuple)

                for l_rec in span.lines:
                    idx = l_rec.line_index
                    if idx in assigned_line_indices:
                        overlapping_spans_total += 1
                    assigned_line_indices.add(idx)

            for cat, count in doc_canonical_freq.items():
                if count > 1:
                    repeated_category_occurrences += (count - 1)

            cov_ratio = res.summary.get("text_coverage_ratio", 1.0)
            total_text_coverage += cov_ratio

            doc_out_dir = ensure_directory(run_output_dir / "documents" / doc_id)
            write_json(doc_out_dir / "sections.json", res.to_dict())

            document_results.append({
                "document_id": doc_id,
                "num_sections": len(res.sections),
                "num_detected_headings": sum(1 for span in res.sections if span.original_heading),
                "canonical_sections": [span.normalized_heading for span in res.sections if span.original_heading],
                "text_coverage_ratio": cov_ratio,
                "review_required": any(span.review_required for span in res.sections),
            })

        avg_text_coverage = (total_text_coverage / total_processed) if total_processed > 0 else 1.0

        pipeline_result = SectioningPipelineResult(
            run_id=run_id,
            run_dir=run_output_dir,
            total_processed=total_processed,
            resumes_with_sections=resumes_with_sections,
            resumes_without_sections=resumes_without_sections,
            top_level_canonical_sections_count=top_canonical_total,
            subsections_count=subsections_total,
            custom_sections_count=custom_total,
            preamble_sections_count=preamble_total,
            section_frequencies=dict(section_freq.most_common()),
            unmapped_headings_count=unmapped_count,
            repeated_category_occurrences=repeated_category_occurrences,
            duplicate_identical_spans_count=duplicate_identical_spans,
            overlapping_spans_count=overlapping_spans_total,
            avg_text_coverage_ratio=avg_text_coverage,
            review_required_count=review_required_count,
            document_results=document_results,
        )

        write_json(run_output_dir / "manifest.json", pipeline_result.to_dict())

        latest_dir = self.output_root / "latest"
        ensure_directory(latest_dir)
        write_json(latest_dir / "manifest.json", pipeline_result.to_dict())

        return pipeline_result
