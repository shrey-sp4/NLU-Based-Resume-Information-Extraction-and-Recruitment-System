"""
Create Public Evaluation Outputs

This script converts local private pipeline outputs into safe, pushable result files.

It does NOT push:
- raw resumes
- extracted full text
- candidate names/emails/phones
- full section JSON

It creates:
- aggregate pipeline summary
- extraction metrics
- section quality metrics
- profile quality metrics
- README for output/evaluation
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict, Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_EVAL_DIR = PROJECT_ROOT / "output" / "evaluation"

EXTRACTION_SUMMARY = PROJECT_ROOT / "output" / "extraction" / "extraction_summary.csv"
SECTION_QUALITY = PROJECT_ROOT / "output" / "quality_checks" / "section_quality_report.csv"
PROFILE_QUALITY = PROJECT_ROOT / "output" / "quality_checks" / "profile_quality_report.csv"


def read_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def percent(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def create_extraction_metrics() -> Dict[str, Any]:
    rows = read_csv(EXTRACTION_SUMMARY)

    total = len(rows)

    # Try to detect status column names flexibly
    status_values = []
    for row in rows:
        value = (
            row.get("status")
            or row.get("extraction_status")
            or row.get("review_status")
            or ""
        ).strip().lower()
        status_values.append(value)

    pass_count = sum(1 for s in status_values if s == "pass")
    review_count = sum(1 for s in status_values if s == "review")
    other_count = total - pass_count - review_count

    metrics = {
        "metric": "pdf_text_extraction",
        "total_resumes": total,
        "pass_count": pass_count,
        "review_count": review_count,
        "other_count": other_count,
        "pass_rate": percent(pass_count, total),
        "review_rate": percent(review_count, total),
    }

    write_csv(
        OUTPUT_EVAL_DIR / "extraction_metrics.csv",
        [metrics],
        [
            "metric",
            "total_resumes",
            "pass_count",
            "review_count",
            "other_count",
            "pass_rate",
            "review_rate",
        ],
    )

    return metrics


def create_section_quality_metrics() -> Dict[str, Any]:
    rows = read_csv(SECTION_QUALITY)

    total = len(rows)

    status_values = [
        (row.get("status") or row.get("review_status") or "").strip().lower()
        for row in rows
    ]

    pass_count = sum(1 for s in status_values if s == "pass")
    review_count = sum(1 for s in status_values if s == "review")
    high_review_count = sum(1 for s in status_values if s == "high_review")
    other_count = total - pass_count - review_count - high_review_count

    metrics = {
        "metric": "section_segmentation_quality",
        "total_resumes": total,
        "pass_count": pass_count,
        "review_count": review_count,
        "high_review_count": high_review_count,
        "other_count": other_count,
        "pass_rate": percent(pass_count, total),
        "review_rate": percent(review_count + high_review_count, total),
    }

    write_csv(
        OUTPUT_EVAL_DIR / "section_quality_metrics.csv",
        [metrics],
        [
            "metric",
            "total_resumes",
            "pass_count",
            "review_count",
            "high_review_count",
            "other_count",
            "pass_rate",
            "review_rate",
        ],
    )

    return metrics


def create_profile_quality_metrics() -> Dict[str, Any]:
    rows = read_csv(PROFILE_QUALITY)

    total = len(rows)

    status_values = [
        (row.get("status") or "").strip().lower()
        for row in rows
    ]

    pass_count = sum(1 for s in status_values if s == "pass")
    review_count = sum(1 for s in status_values if s == "review")
    other_count = total - pass_count - review_count

    flag_counts = {}

    for row in rows:
        flags = row.get("flags", "")
        for flag in flags.split(";"):
            flag = flag.strip()
            if not flag:
                continue
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

    metrics = {
        "metric": "candidate_profile_quality",
        "total_profiles": total,
        "pass_count": pass_count,
        "review_count": review_count,
        "other_count": other_count,
        "pass_rate": percent(pass_count, total),
        "review_rate": percent(review_count, total),
        "suspicious_name_count": flag_counts.get("suspicious_name", 0),
        "suspicious_or_missing_email_count": flag_counts.get("suspicious_or_missing_email", 0),
        "suspicious_or_missing_phone_count": flag_counts.get("suspicious_or_missing_phone", 0),
        "missing_education_count": flag_counts.get("missing_education", 0),
        "missing_experience_and_publications_count": flag_counts.get("missing_experience_and_publications", 0),
    }

    write_csv(
        OUTPUT_EVAL_DIR / "profile_quality_metrics.csv",
        [metrics],
        [
            "metric",
            "total_profiles",
            "pass_count",
            "review_count",
            "other_count",
            "pass_rate",
            "review_rate",
            "suspicious_name_count",
            "suspicious_or_missing_email_count",
            "suspicious_or_missing_phone_count",
            "missing_education_count",
            "missing_experience_and_publications_count",
        ],
    )

    return metrics


def create_pipeline_run_summary(
    extraction_metrics: Dict[str, Any],
    section_metrics: Dict[str, Any],
    profile_metrics: Dict[str, Any],
) -> None:
    rows = [
        {
            "stage": "PDF text extraction",
            "total_items": extraction_metrics.get("total_resumes", 0),
            "pass_count": extraction_metrics.get("pass_count", 0),
            "review_count": extraction_metrics.get("review_count", 0),
            "pass_rate": extraction_metrics.get("pass_rate", 0),
        },
        {
            "stage": "Section segmentation quality",
            "total_items": section_metrics.get("total_resumes", 0),
            "pass_count": section_metrics.get("pass_count", 0),
            "review_count": section_metrics.get("review_count", 0)
            + section_metrics.get("high_review_count", 0),
            "pass_rate": section_metrics.get("pass_rate", 0),
        },
        {
            "stage": "Candidate profile quality",
            "total_items": profile_metrics.get("total_profiles", 0),
            "pass_count": profile_metrics.get("pass_count", 0),
            "review_count": profile_metrics.get("review_count", 0),
            "pass_rate": profile_metrics.get("pass_rate", 0),
        },
    ]

    write_csv(
        OUTPUT_EVAL_DIR / "pipeline_run_summary.csv",
        rows,
        ["stage", "total_items", "pass_count", "review_count", "pass_rate"],
    )


def create_readme() -> None:
    text = """# Evaluation Outputs

This folder contains safe, pushable evaluation outputs for the NLU-Based Resume Information Extraction and Recruitment System.

The raw resumes, extracted resume text, section-wise JSON files, and candidate-level profile files are intentionally not included because they may contain personal information such as names, emails, phone numbers, education details, and publication records.

## Files

- `pipeline_run_summary.csv`  
  Overall stage-wise summary of the pipeline.

- `extraction_metrics.csv`  
  Aggregate metrics for PDF text extraction.

- `section_quality_metrics.csv`  
  Aggregate metrics for section segmentation quality checks.

- `profile_quality_metrics.csv`  
  Aggregate metrics for candidate profile extraction quality checks.

- `sample_field_metrics.csv`  
  Field-level accuracy metrics from manually verified sample ground truth.  
  This file is generated after sample ground truth evaluation.

- `sample_error_report.csv`  
  Error report from manually verified sample ground truth.  
  This file is generated after sample ground truth evaluation.

## Privacy Note

Only aggregate or anonymized result files should be committed to this folder.
Do not commit raw resumes, extracted full text, candidate profiles containing personal details, or section JSON files.
"""

    (OUTPUT_EVAL_DIR / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUTPUT_EVAL_DIR.mkdir(parents=True, exist_ok=True)

    extraction_metrics = create_extraction_metrics()
    section_metrics = create_section_quality_metrics()
    profile_metrics = create_profile_quality_metrics()

    create_pipeline_run_summary(
        extraction_metrics,
        section_metrics,
        profile_metrics,
    )

    create_readme()

    print("Public evaluation outputs created.")
    print(f"Saved to: {OUTPUT_EVAL_DIR}")


if __name__ == "__main__":
    main()