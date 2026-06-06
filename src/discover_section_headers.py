"""
Improved Section Header Discovery Script

Purpose:
- Read extracted resume text files from data/real_resumes/extracted_text/
- Detect likely section headings
- Avoid obvious noise such as page markers, names, ISBN lines, contact lines, organizations
- Save:
  1. Detailed heading inventory
  2. Unique heading frequency summary

This is still heuristic-based. The output must be reviewed before creating
the final section normalization map.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEXT_INPUT_DIR = PROJECT_ROOT / "data" / "real_resumes" / "extracted_text"

DETAIL_OUTPUT_PATH = (
    PROJECT_ROOT
    / "output"
    / "section_discovery"
    / "section_heading_inventory.csv"
)

UNIQUE_OUTPUT_PATH = (
    PROJECT_ROOT
    / "output"
    / "section_discovery"
    / "unique_section_headings.csv"
)


CANONICAL_HINT_KEYWORDS = [
    "education",
    "educational",
    "qualification",
    "qualifications",
    "academic",
    "academics",
    "profile",
    "experience",
    "employment",
    "professional",
    "internship",
    "internships",
    "research",
    "teaching",
    "skill",
    "skills",
    "technical",
    "competencies",
    "project",
    "projects",
    "publication",
    "publications",
    "journal",
    "conference",
    "conferences",
    "proceedings",
    "certification",
    "certifications",
    "course",
    "courses",
    "achievement",
    "achievements",
    "award",
    "awards",
    "honors",
    "honours",
    "responsibility",
    "responsibilities",
    "activities",
    "workshop",
    "workshops",
    "seminar",
    "seminars",
    "personal",
    "contact",
    "objective",
    "summary",
    "interest",
    "interests",
    "hobbies",
    "references",
    "declaration",
    "patent",
    "patents",
    "grant",
    "grants",
    "fellowship",
    "fellowships",
    "membership",
    "memberships",
    "training",
    "trainings",
    "positions",
    "position",
]


NOISE_PATTERNS = [
    r"^page\s+\d+$",
    r"^\d+$",
    r"^isbn\b",
    r"^issn\b",
    r"^doi\b",
    r"^http",
    r"^www\.",
    r"^email\b",
    r"^e-mail\b",
    r"^mobile\b",
    r"^phone\b",
    r"^contact\s*[:\-]",
    r"^\+?\d[\d\s\-\(\)]{6,}$",
    r"^dr\.\s+[a-z]+",
    r"^mr\.\s+[a-z]+",
    r"^mrs\.\s+[a-z]+",
    r"^ms\.\s+[a-z]+",
    r"^prof\.\s+[a-z]+",
    r"^curriculum vitae$",
    r"^curiculam vitae$",
    r"^resume$",
    r"^cv$",
]


ORG_NOISE = {
    "gujcost",
    "drdo",
    "barc",
    "ugc",
    "dst",
    "csir",
    "isro",
    "iit",
    "iim",
    "nirma",
    "daiict",
}


def clean_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\s+", " ", line)

    # Remove page markers like --- PAGE 1 ---
    line = re.sub(r"^-+\s*page\s+\d+\s*-+$", "", line, flags=re.IGNORECASE)

    # Strip common heading border characters
    line = line.strip(":-–—|•●■□* ")

    return line.strip()


def has_noise_pattern(line: str) -> bool:
    lower = line.lower().strip()

    for pattern in NOISE_PATTERNS:
        if re.search(pattern, lower):
            return True

    if lower in ORG_NOISE:
        return True

    return False


def looks_like_person_name(line: str) -> bool:
    """
    Heuristic to avoid capturing candidate names as headings.
    Example: DR. MITESHKUMAR SOLANKI
    """
    cleaned = re.sub(r"^(dr|mr|mrs|ms|prof)\.?\s+", "", line.strip(), flags=re.IGNORECASE)
    words = cleaned.split()

    if 2 <= len(words) <= 4:
        title_case_count = sum(w[:1].isupper() for w in words)
        alpha_words = all(re.search(r"[A-Za-z]", w) for w in words)

        # Names are often 2-4 words, mostly title case/uppercase, without section keywords
        lower = line.lower()
        has_section_keyword = any(k in lower for k in CANONICAL_HINT_KEYWORDS)

        if alpha_words and title_case_count == len(words) and not has_section_keyword:
            return True

        if cleaned.isupper() and not has_section_keyword:
            return True

    return False


def is_probable_section_heading(raw_line: str) -> bool:
    raw = raw_line.strip()

    if not raw:
        return False

    cleaned = clean_line(raw)

    if not cleaned:
        return False

    lower = cleaned.lower()

    # Ignore page markers after cleaning
    if re.match(r"^page\s+\d+$", lower):
        return False

    if has_noise_pattern(cleaned):
        return False

    if looks_like_person_name(cleaned):
        return False

    # Very long lines are usually content, not headings
    if len(cleaned) > 85:
        return False

    words = cleaned.split()

    if len(words) == 0:
        return False

    # Headings are usually short
    if len(words) > 7:
        return False

    # Ignore sentence-like lines
    if cleaned.endswith("."):
        return False

    # Ignore lines with too little alphabetic content
    alpha_chars = sum(ch.isalpha() for ch in cleaned)
    if alpha_chars < 4:
        return False

    has_keyword = any(keyword in lower for keyword in CANONICAL_HINT_KEYWORDS)

    is_all_caps = cleaned.isupper() and len(words) <= 6
    is_title_like = sum(1 for w in words if w[:1].isupper()) >= max(1, len(words) - 1)
    ends_with_colon = raw.endswith(":")
    numbered_heading = bool(re.match(r"^\d+[\.\)]\s+[A-Za-z]", cleaned))

    # Main rule: must contain a resume-section keyword
    if has_keyword and (is_all_caps or is_title_like or ends_with_colon or numbered_heading or len(words) <= 5):
        return True

    return False


def discover_headings_from_file(txt_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    text = txt_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    for line_number, line in enumerate(lines, start=1):
        cleaned = clean_line(line)

        if is_probable_section_heading(line):
            rows.append({
                "file_name": txt_path.name,
                "line_number": line_number,
                "raw_line": line.strip(),
                "candidate_heading": cleaned,
                "normalized_lower": cleaned.lower(),
            })

    return rows


def write_detail_inventory(rows: List[Dict[str, Any]]) -> None:
    DETAIL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file_name",
        "line_number",
        "raw_line",
        "candidate_heading",
        "normalized_lower",
    ]

    with DETAIL_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_unique_headings(rows: List[Dict[str, Any]]) -> None:
    UNIQUE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    counter = Counter(row["normalized_lower"] for row in rows)

    with UNIQUE_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["normalized_lower", "frequency"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for heading, freq in counter.most_common():
            writer.writerow({
                "normalized_lower": heading,
                "frequency": freq,
            })


def main() -> None:
    txt_files = sorted(TEXT_INPUT_DIR.glob("*.txt"))

    if not txt_files:
        print(f"No extracted text files found in: {TEXT_INPUT_DIR}")
        print("Run src/extract_text_audited.py first.")
        return

    print(f"Found {len(txt_files)} extracted text file(s). Discovering section headings...\n")

    all_rows: List[Dict[str, Any]] = []

    for index, txt_path in enumerate(txt_files, start=1):
        rows = discover_headings_from_file(txt_path)
        all_rows.extend(rows)

        print(f"[{index}/{len(txt_files)}] {txt_path.name}: {len(rows)} candidate heading(s)")

    write_detail_inventory(all_rows)
    write_unique_headings(all_rows)

    unique_headings = sorted(set(row["normalized_lower"] for row in all_rows))

    print("\nSection discovery complete.")
    print(f"Total candidate heading occurrences: {len(all_rows)}")
    print(f"Unique candidate headings: {len(unique_headings)}")
    print(f"Detail inventory saved to: {DETAIL_OUTPUT_PATH}")
    print(f"Unique heading summary saved to: {UNIQUE_OUTPUT_PATH}")


if __name__ == "__main__":
    main()