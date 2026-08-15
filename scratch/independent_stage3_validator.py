from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")


def validate_run(run_dir: Path) -> Dict[str, object]:
    print(f"=== INDEPENDENT VALIDATOR (PATH B) ===")
    print(f"Target Run Directory: {run_dir}\n")

    docs_dir = run_dir / "documents"
    if not docs_dir.exists():
        raise FileNotFoundError(f"Documents directory does not exist: {docs_dir}")

    doc_files = sorted(docs_dir.glob("*/sections.json"))
    total_processed = len(doc_files)

    resumes_with_sections = 0
    resumes_without_sections = 0

    top_canonical_total = 0
    subsections_total = 0
    custom_total = 0
    preamble_total = 0

    section_frequencies: Counter[str] = Counter()
    other_headings_counter: Counter[str] = Counter()
    unmapped_headings_count = 0

    repeated_category_occurrences = 0
    duplicate_identical_spans = 0
    overlapping_spans_found = []
    review_required_count = 0

    total_coverage_ratio = 0.0
    coverage_anomalies = []

    for sec_file in doc_files:
        with open(sec_file, "r", encoding="utf-8") as f:
            sec_data = json.load(f)

        doc_id = sec_data["document_id"]
        sections = sec_data.get("sections", [])
        summary = sec_data.get("summary", {})

        has_detected_sections = any(span.get("original_heading") for span in sections)
        if has_detected_sections:
            resumes_with_sections += 1
        else:
            resumes_without_sections += 1

        doc_cat_counts: Counter[str] = Counter()
        assigned_line_indices = set()
        doc_spans_tuples = []

        for span in sections:
            orig = span.get("original_heading", "").strip()
            norm = span.get("normalized_heading", "other").strip()
            stype = span.get("section_type", "canonical")
            lvl = span.get("level", 1)

            if stype == "canonical":
                top_canonical_total += 1
            elif stype == "subsection":
                subsections_total += 1
            elif stype == "custom":
                custom_total += 1
            elif stype == "preamble":
                preamble_total += 1

            if span.get("review_required"):
                review_required_count += 1

            if orig:
                section_frequencies[norm] += 1
                doc_cat_counts[norm] += 1
                if norm == "other":
                    unmapped_headings_count += 1
                    other_headings_counter[orig] += 1

            span_tuple = (span.get("start_line"), span.get("end_line"))
            if span_tuple in doc_spans_tuples:
                duplicate_identical_spans += 1
            doc_spans_tuples.append(span_tuple)

            # Check line index coverage and overlaps
            for line in span.get("lines", []):
                idx = line["line_index"]
                if idx in assigned_line_indices:
                    overlapping_spans_found.append((doc_id, span["section_id"], idx))
                assigned_line_indices.add(idx)

        for cat, count in doc_cat_counts.items():
            if count > 1:
                repeated_category_occurrences += (count - 1)

        cov_ratio = summary.get("text_coverage_ratio", 1.0)
        total_coverage_ratio += cov_ratio

        total_lines_input = summary.get("total_lines_input", 0)
        total_lines_covered = len(assigned_line_indices)
        if total_lines_input != total_lines_covered:
            coverage_anomalies.append({
                "doc_id": doc_id,
                "input": total_lines_input,
                "covered": total_lines_covered,
            })

    avg_coverage = (total_coverage_ratio / total_processed) if total_processed > 0 else 1.0

    return {
        "total_processed": total_processed,
        "resumes_with_sections": resumes_with_sections,
        "resumes_without_sections": resumes_without_sections,
        "top_level_canonical_sections_count": top_canonical_total,
        "subsections_count": subsections_total,
        "custom_sections_count": custom_total,
        "preamble_sections_count": preamble_total,
        "section_frequencies": dict(section_frequencies.most_common()),
        "unmapped_headings_count": unmapped_headings_count,
        "repeated_category_occurrences": repeated_category_occurrences,
        "duplicate_identical_spans_count": duplicate_identical_spans,
        "overlapping_spans_count": len(overlapping_spans_found),
        "avg_text_coverage_ratio": round(avg_coverage, 4),
        "review_required_count": review_required_count,
        "coverage_anomalies_count": len(coverage_anomalies),
        "top_other_headings": dict(other_headings_counter.most_common(20)),
    }


if __name__ == "__main__":
    run_dir = PROJECT_ROOT / "output" / "sectioning" / "clean_stage3_2_run" / "sectioning_run_20260811T100030Z"
    results = validate_run(run_dir)
    print(json.dumps(results, indent=2, ensure_ascii=False))
