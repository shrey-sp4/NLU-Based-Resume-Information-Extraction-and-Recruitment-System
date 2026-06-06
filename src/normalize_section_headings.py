"""
Normalize Discovered Section Headings

Input:
- output/section_discovery/section_heading_inventory.csv
- config/section_normalization_map.json

Output:
- output/section_discovery/normalized_section_inventory.csv
- output/section_discovery/normalized_section_summary.csv
- output/section_discovery/unmapped_section_headings.csv

Purpose:
Map raw section headings into canonical resume sections.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_INVENTORY = (
    PROJECT_ROOT
    / "output"
    / "section_discovery"
    / "section_heading_inventory.csv"
)

NORMALIZATION_MAP_PATH = (
    PROJECT_ROOT
    / "config"
    / "section_normalization_map.json"
)

NORMALIZED_OUTPUT = (
    PROJECT_ROOT
    / "output"
    / "section_discovery"
    / "normalized_section_inventory.csv"
)

SUMMARY_OUTPUT = (
    PROJECT_ROOT
    / "output"
    / "section_discovery"
    / "normalized_section_summary.csv"
)

UNMAPPED_OUTPUT = (
    PROJECT_ROOT
    / "output"
    / "section_discovery"
    / "unmapped_section_headings.csv"
)


def load_normalization_map() -> Dict[str, str]:
    """
    Convert:
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

    lookup = {}

    for canonical_section, variants in raw_map.items():
        for variant in variants:
            lookup[variant.strip().lower()] = canonical_section

    return lookup


def read_inventory() -> List[Dict[str, Any]]:
    with INPUT_INVENTORY.open("r", encoding="utf-8", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not INPUT_INVENTORY.exists():
        print(f"Missing input file: {INPUT_INVENTORY}")
        print("Run src/discover_section_headers.py first.")
        return

    if not NORMALIZATION_MAP_PATH.exists():
        print(f"Missing normalization map: {NORMALIZATION_MAP_PATH}")
        return

    normalization_lookup = load_normalization_map()
    inventory_rows = read_inventory()

    normalized_rows = []
    unmapped_counter = Counter()
    canonical_counter = Counter()

    for row in inventory_rows:
        heading = row["normalized_lower"].strip().lower()

        canonical_section = normalization_lookup.get(heading, "unmapped")

        if canonical_section == "ignore":
            status = "ignored"
        elif canonical_section == "unmapped":
            status = "unmapped"
            unmapped_counter[heading] += 1
        else:
            status = "mapped"
            canonical_counter[canonical_section] += 1

        normalized_rows.append({
            "file_name": row["file_name"],
            "line_number": row["line_number"],
            "raw_line": row["raw_line"],
            "candidate_heading": row["candidate_heading"],
            "normalized_lower": heading,
            "canonical_section": canonical_section,
            "status": status,
        })

    write_csv(
        NORMALIZED_OUTPUT,
        normalized_rows,
        [
            "file_name",
            "line_number",
            "raw_line",
            "candidate_heading",
            "normalized_lower",
            "canonical_section",
            "status",
        ],
    )

    summary_rows = [
        {
            "canonical_section": section,
            "frequency": freq,
        }
        for section, freq in canonical_counter.most_common()
    ]

    write_csv(
        SUMMARY_OUTPUT,
        summary_rows,
        ["canonical_section", "frequency"],
    )

    unmapped_rows = [
        {
            "heading": heading,
            "frequency": freq,
        }
        for heading, freq in unmapped_counter.most_common()
    ]

    write_csv(
        UNMAPPED_OUTPUT,
        unmapped_rows,
        ["heading", "frequency"],
    )

    total = len(normalized_rows)
    mapped = sum(1 for row in normalized_rows if row["status"] == "mapped")
    ignored = sum(1 for row in normalized_rows if row["status"] == "ignored")
    unmapped = sum(1 for row in normalized_rows if row["status"] == "unmapped")

    print("Section heading normalization complete.")
    print(f"Total candidate headings: {total}")
    print(f"Mapped headings: {mapped}")
    print(f"Ignored headings: {ignored}")
    print(f"Unmapped headings: {unmapped}")
    print()
    print(f"Normalized inventory saved to: {NORMALIZED_OUTPUT}")
    print(f"Canonical summary saved to: {SUMMARY_OUTPUT}")
    print(f"Unmapped headings saved to: {UNMAPPED_OUTPUT}")


if __name__ == "__main__":
    main()