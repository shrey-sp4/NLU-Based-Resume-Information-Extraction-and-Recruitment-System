"""
Section Segmentation Quality Check

Input:
- output/sections/*_sections.json

Output:
- output/quality_checks/section_quality_report.csv
- output/quality_checks/section_boundary_report.csv

Purpose:
Evaluate whether section segmentation looks reasonable before field extraction.
This does not require manual ground truth.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SECTION_INPUT_DIR = PROJECT_ROOT / "output" / "sections"
QUALITY_OUTPUT_PATH = PROJECT_ROOT / "output" / "quality_checks" / "section_quality_report.csv"
BOUNDARY_OUTPUT_PATH = PROJECT_ROOT / "output" / "quality_checks" / "section_boundary_report.csv"


IMPORTANT_SECTIONS = [
    "education",
    "experience",
    "skills",
    "publications",
    "personal_details",
    "summary",
    "research_interests",
    "projects",
    "achievements",
    "certifications",
]


def count_chars(text: str) -> int:
    return len(text.strip()) if text else 0


def count_words(text: str) -> int:
    if not text:
        return 0
    return len(text.split())


def load_section_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_status_and_flags(data: Dict[str, Any]) -> Dict[str, Any]:
    file_name = data["file_name"]
    sections: Dict[str, str] = data.get("sections", {})
    quality: Dict[str, Any] = data.get("quality", {})

    section_names = sorted(sections.keys())
    num_sections = len(section_names)

    total_chars = quality.get("total_content_chars", 0)
    coverage = quality.get("section_coverage_ratio", 0)

    preamble_chars = count_chars(sections.get("preamble", ""))
    preamble_ratio = round(preamble_chars / total_chars, 4) if total_chars else 0

    missing_important = [
        section for section in IMPORTANT_SECTIONS
        if section not in sections
    ]

    present_important = [
        section for section in IMPORTANT_SECTIONS
        if section in sections
    ]

    largest_section = ""
    largest_section_chars = 0

    for section, text in sections.items():
        chars = count_chars(text)
        if chars > largest_section_chars:
            largest_section = section
            largest_section_chars = chars

    flags: List[str] = []

    if num_sections < 4:
        flags.append("too_few_sections")

    if preamble_ratio > 0.30:
        flags.append("large_preamble")

    if coverage < 0.90:
        flags.append("low_coverage")

    if "education" not in sections:
        flags.append("missing_education")

    if "experience" not in sections and "publications" not in sections:
        flags.append("missing_experience_and_publications")

    if largest_section_chars > 0 and total_chars > 0:
        largest_ratio = largest_section_chars / total_chars
        if largest_ratio > 0.70:
            flags.append(f"dominant_section:{largest_section}")

    if not flags:
        status = "pass"
    elif len(flags) <= 2:
        status = "review"
    else:
        status = "high_review"

    return {
        "file_name": file_name,
        "num_sections": num_sections,
        "section_coverage_ratio": coverage,
        "total_chars": total_chars,
        "preamble_chars": preamble_chars,
        "preamble_ratio": preamble_ratio,
        "largest_section": largest_section,
        "largest_section_chars": largest_section_chars,
        "detected_sections": "; ".join(section_names),
        "present_important_sections": "; ".join(present_important),
        "missing_important_sections": "; ".join(missing_important),
        "flags": "; ".join(flags),
        "status": status,
    }


def write_quality_report(rows: List[Dict[str, Any]]) -> None:
    QUALITY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file_name",
        "num_sections",
        "section_coverage_ratio",
        "total_chars",
        "preamble_chars",
        "preamble_ratio",
        "largest_section",
        "largest_section_chars",
        "detected_sections",
        "present_important_sections",
        "missing_important_sections",
        "flags",
        "status",
    ]

    with QUALITY_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_boundary_report(section_files: List[Path]) -> None:
    BOUNDARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file_name",
        "line_number",
        "raw_heading",
        "clean_heading",
        "canonical_section",
    ]

    rows: List[Dict[str, Any]] = []

    for path in section_files:
        data = load_section_json(path)
        file_name = data["file_name"]

        for boundary in data.get("section_boundaries", []):
            rows.append({
                "file_name": file_name,
                "line_number": boundary.get("line_number", ""),
                "raw_heading": boundary.get("raw_heading", ""),
                "clean_heading": boundary.get("clean_heading", ""),
                "canonical_section": boundary.get("canonical_section", ""),
            })

    with BOUNDARY_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    section_files = sorted(SECTION_INPUT_DIR.glob("*_sections.json"))

    if not section_files:
        print(f"No section JSON files found in: {SECTION_INPUT_DIR}")
        print("Run src/segment_resumes_into_sections.py first.")
        return

    rows: List[Dict[str, Any]] = []

    print(f"Found {len(section_files)} section JSON file(s). Running quality checks...\n")

    for index, path in enumerate(section_files, start=1):
        data = load_section_json(path)
        row = get_status_and_flags(data)
        rows.append(row)

        print(
            f"[{index}/{len(section_files)}] {row['file_name']}: "
            f"status={row['status']}, flags={row['flags'] or 'none'}"
        )

    write_quality_report(rows)
    write_boundary_report(section_files)

    pass_count = sum(1 for row in rows if row["status"] == "pass")
    review_count = sum(1 for row in rows if row["status"] == "review")
    high_review_count = sum(1 for row in rows if row["status"] == "high_review")

    print("\nQuality check complete.")
    print(f"Pass: {pass_count}")
    print(f"Review: {review_count}")
    print(f"High review: {high_review_count}")
    print(f"Quality report saved to: {QUALITY_OUTPUT_PATH}")
    print(f"Boundary report saved to: {BOUNDARY_OUTPUT_PATH}")


if __name__ == "__main__":
    main()