"""
Segment Resumes into Normalized Sections

Input:
- data/real_resumes/extracted_text/*.txt
- config/section_normalization_map.json

Output:
- output/sections/<resume_name>_sections.json
- output/sections/section_segmentation_summary.csv

Purpose:
Use the normalized section heading map to split each extracted resume text
into canonical sections such as education, experience, skills, publications, etc.

Important:
- This script preserves all readable content.
- Content before the first detected heading goes into "preamble".
- Headings mapped to "ignore" are skipped as heading lines only.
- Ignored headings do NOT stop the current section.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEXT_INPUT_DIR = PROJECT_ROOT / "data" / "real_resumes" / "extracted_text"
NORMALIZATION_MAP_PATH = PROJECT_ROOT / "config" / "section_normalization_map.json"

SECTION_OUTPUT_DIR = PROJECT_ROOT / "output" / "sections"
SUMMARY_OUTPUT_PATH = PROJECT_ROOT / "output" / "sections" / "section_segmentation_summary.csv"


def clean_line(line: str) -> str:
    """
    Clean one line for heading comparison.
    This should not aggressively remove content.
    """
    line = line.strip()
    line = re.sub(r"\s+", " ", line)

    # Remove artificial page markers like --- PAGE 1 ---
    line = re.sub(r"^-+\s*page\s+\d+\s*-+$", "", line, flags=re.IGNORECASE)

    # Remove common heading decoration characters.
    line = line.strip(":-–—|•●■□* ")

    return line.strip()


def is_page_marker(line: str) -> bool:
    """Detect artificial page markers inserted by extraction script."""
    return bool(
        re.match(
            r"^-+\s*page\s+\d+\s*-+$",
            line.strip(),
            flags=re.IGNORECASE,
        )
    )


def load_heading_lookup() -> Dict[str, str]:
    """
    Convert normalization map from:

    {
      "education": ["education", "academic details"]
    }

    into:

    {
      "education": "education",
      "academic details": "education"
    }
    """
    raw_map = json.loads(NORMALIZATION_MAP_PATH.read_text(encoding="utf-8"))

    lookup: Dict[str, str] = {}

    for canonical_section, variants in raw_map.items():
        for variant in variants:
            lookup[variant.strip().lower()] = canonical_section

    return lookup


def detect_heading(line: str, heading_lookup: Dict[str, str]) -> Optional[Dict[str, str]]:
    """
    Return heading information if line exactly matches a known heading variant.
    Otherwise return None.
    """
    cleaned = clean_line(line)

    if not cleaned:
        return None

    normalized = cleaned.lower()
    canonical = heading_lookup.get(normalized)

    if canonical is None:
        return None

    return {
        "raw_heading": line.strip(),
        "clean_heading": cleaned,
        "normalized_heading": normalized,
        "canonical_section": canonical,
    }


def append_line(section_store: Dict[str, List[str]], section_name: str, line: str) -> None:
    """Append line to section."""
    if section_name not in section_store:
        section_store[section_name] = []

    section_store[section_name].append(line)


def segment_one_resume(txt_path: Path, heading_lookup: Dict[str, str]) -> Dict[str, Any]:
    """
    Segment a single extracted resume text file into normalized sections.
    """
    text = txt_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    sections: Dict[str, List[str]] = {}
    boundaries: List[Dict[str, Any]] = []
    ignored_headings: List[Dict[str, Any]] = []

    current_section = "preamble"

    total_content_chars = 0
    mapped_content_chars = 0
    ignored_heading_chars = 0

    for line_number, line in enumerate(lines, start=1):
        raw_line = line.rstrip("\n")
        cleaned = clean_line(raw_line)

        if not cleaned:
            continue

        # Skip artificial page markers.
        if is_page_marker(raw_line):
            continue

        heading_info = detect_heading(raw_line, heading_lookup)

        if heading_info is not None:
            canonical = heading_info["canonical_section"]

            if canonical == "ignore":
                # Important:
                # Ignore only this heading line.
                # Do NOT change current_section.
                # Example:
                # "Publications" starts publication section.
                # "2024 Publication" may be ignored as a subheading,
                # but the publication content after it must remain in publications.
                ignored_heading_chars += len(cleaned)
                ignored_headings.append({
                    "line_number": line_number,
                    "raw_heading": heading_info["raw_heading"],
                    "clean_heading": heading_info["clean_heading"],
                    "previous_active_section": current_section,
                })
                continue

            current_section = canonical

            boundaries.append({
                "line_number": line_number,
                "raw_heading": heading_info["raw_heading"],
                "clean_heading": heading_info["clean_heading"],
                "canonical_section": canonical,
            })

            if current_section not in sections:
                sections[current_section] = []

            continue

        # Normal content line.
        total_content_chars += len(cleaned)

        append_line(sections, current_section, raw_line)
        mapped_content_chars += len(cleaned)

    # Convert section line lists to strings.
    section_text = {
        section: "\n".join(section_lines).strip()
        for section, section_lines in sections.items()
        if "\n".join(section_lines).strip()
    }

    coverage = 0.0
    if total_content_chars > 0:
        coverage = mapped_content_chars / total_content_chars

    result = {
        "file_name": txt_path.name,
        "source_text_path": str(txt_path.relative_to(PROJECT_ROOT)),
        "sections": section_text,
        "section_boundaries": boundaries,
        "ignored_headings": ignored_headings,
        "quality": {
            "total_content_chars": total_content_chars,
            "mapped_content_chars": mapped_content_chars,
            "ignored_heading_chars": ignored_heading_chars,
            "section_coverage_ratio": round(coverage, 4),
            "num_detected_boundaries": len(boundaries),
            "num_ignored_headings": len(ignored_headings),
            "num_sections": len(section_text),
        },
    }

    return result


def write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_summary(rows: List[Dict[str, Any]]) -> None:
    """Write section segmentation summary CSV."""
    SUMMARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file_name",
        "num_sections",
        "num_detected_boundaries",
        "num_ignored_headings",
        "section_coverage_ratio",
        "total_content_chars",
        "mapped_content_chars",
        "detected_sections",
        "status",
    ]

    with SUMMARY_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Main entry point."""
    if not NORMALIZATION_MAP_PATH.exists():
        print(f"Missing normalization map: {NORMALIZATION_MAP_PATH}")
        return

    heading_lookup = load_heading_lookup()

    txt_files = sorted(TEXT_INPUT_DIR.glob("*.txt"))

    if not txt_files:
        print(f"No extracted text files found in: {TEXT_INPUT_DIR}")
        print("Run src/extract_text_audited.py first.")
        return

    SECTION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(txt_files)} extracted text file(s). Segmenting resumes...\n")

    summary_rows: List[Dict[str, Any]] = []

    for index, txt_path in enumerate(txt_files, start=1):
        result = segment_one_resume(txt_path, heading_lookup)

        output_path = SECTION_OUTPUT_DIR / f"{txt_path.stem}_sections.json"
        write_json(output_path, result)

        quality = result["quality"]
        detected_sections = sorted(result["sections"].keys())

        coverage = quality["section_coverage_ratio"]

        if coverage >= 0.90:
            status = "pass"
        elif coverage >= 0.75:
            status = "review"
        else:
            status = "low_coverage"

        summary_rows.append({
            "file_name": txt_path.name,
            "num_sections": quality["num_sections"],
            "num_detected_boundaries": quality["num_detected_boundaries"],
            "num_ignored_headings": quality["num_ignored_headings"],
            "section_coverage_ratio": coverage,
            "total_content_chars": quality["total_content_chars"],
            "mapped_content_chars": quality["mapped_content_chars"],
            "detected_sections": "; ".join(detected_sections),
            "status": status,
        })

        print(
            f"[{index}/{len(txt_files)}] {txt_path.name}: "
            f"{quality['num_sections']} sections, "
            f"{quality['num_detected_boundaries']} boundaries, "
            f"{quality['num_ignored_headings']} ignored headings, "
            f"coverage={coverage}, "
            f"status={status}"
        )

    write_summary(summary_rows)

    print("\nSection segmentation complete.")
    print(f"Section JSON files saved to: {SECTION_OUTPUT_DIR}")
    print(f"Summary saved to: {SUMMARY_OUTPUT_PATH}")


if __name__ == "__main__":
    main()