"""
Create Manual Section Review Shortlist

Input:
- output/quality_checks/section_quality_report.csv
- output/sections/section_segmentation_summary.csv

Output:
- output/quality_checks/manual_section_review_shortlist.csv

Purpose:
Select the resumes that should be manually inspected first based on:
- quality status
- suspicious flags
- too few sections
- dominant section
- large preamble
- low or unusual section coverage
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict, Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

QUALITY_REPORT_PATH = (
    PROJECT_ROOT
    / "output"
    / "quality_checks"
    / "section_quality_report.csv"
)

SEGMENTATION_SUMMARY_PATH = (
    PROJECT_ROOT
    / "output"
    / "sections"
    / "section_segmentation_summary.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "output"
    / "quality_checks"
    / "manual_section_review_shortlist.csv"
)


def read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as csvfile:
        return list(csv.DictReader(csvfile))


def to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def to_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def get_priority(row: Dict[str, Any]) -> Dict[str, Any]:
    reasons = []
    score = 0

    status = row.get("status", "").strip().lower()
    flags = row.get("flags", "").strip()

    num_sections = to_int(row.get("num_sections", "0"))
    coverage = to_float(row.get("section_coverage_ratio", "0"))
    preamble_ratio = to_float(row.get("preamble_ratio", "0"))

    missing_important = row.get("missing_important_sections", "")

    if status == "high_review":
        score += 100
        reasons.append("high_review_status")

    if status == "review":
        score += 60
        reasons.append("review_status")

    if "dominant_section" in flags:
        score += 50
        reasons.append("dominant_section")

    if "large_preamble" in flags:
        score += 50
        reasons.append("large_preamble")

    if "too_few_sections" in flags:
        score += 50
        reasons.append("too_few_sections")

    if coverage < 0.90:
        score += 40
        reasons.append("coverage_below_0.90")

    if num_sections < 5:
        score += 30
        reasons.append("less_than_5_sections")

    if preamble_ratio > 0.20:
        score += 30
        reasons.append("preamble_above_20_percent")

    if "education" in missing_important:
        score += 20
        reasons.append("missing_education")

    if "experience" in missing_important and "publications" in missing_important:
        score += 20
        reasons.append("missing_experience_and_publications")

    if not reasons:
        reasons.append("sample_pass_case")

    return {
        "priority_score": score,
        "review_reasons": "; ".join(reasons),
    }


def main() -> None:
    if not QUALITY_REPORT_PATH.exists():
        print(f"Missing quality report: {QUALITY_REPORT_PATH}")
        print("Run src/quality_check_sections.py first.")
        return

    rows = read_csv(QUALITY_REPORT_PATH)

    shortlist = []

    for row in rows:
        priority = get_priority(row)

        section_json_file = (
            "output/sections/"
            + Path(row["file_name"]).stem
            + "_sections.json"
        )

        shortlist.append({
            "file_name": row["file_name"],
            "priority_score": priority["priority_score"],
            "review_reasons": priority["review_reasons"],
            "status": row.get("status", ""),
            "flags": row.get("flags", ""),
            "num_sections": row.get("num_sections", ""),
            "section_coverage_ratio": row.get("section_coverage_ratio", ""),
            "preamble_ratio": row.get("preamble_ratio", ""),
            "largest_section": row.get("largest_section", ""),
            "largest_section_chars": row.get("largest_section_chars", ""),
            "detected_sections": row.get("detected_sections", ""),
            "missing_important_sections": row.get("missing_important_sections", ""),
            "section_json_file": section_json_file,
        })

    shortlist.sort(
        key=lambda row: (
            -int(row["priority_score"]),
            row["file_name"],
        )
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file_name",
        "priority_score",
        "review_reasons",
        "status",
        "flags",
        "num_sections",
        "section_coverage_ratio",
        "preamble_ratio",
        "largest_section",
        "largest_section_chars",
        "detected_sections",
        "missing_important_sections",
        "section_json_file",
    ]

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(shortlist)

    print("Manual section review shortlist created.")
    print(f"Total resumes ranked: {len(shortlist)}")
    print(f"Saved to: {OUTPUT_PATH}")

    print("\nTop 10 files to review:")
    for row in shortlist[:10]:
        print(
            f"- {row['file_name']} | "
            f"score={row['priority_score']} | "
            f"reasons={row['review_reasons']}"
        )


if __name__ == "__main__":
    main()