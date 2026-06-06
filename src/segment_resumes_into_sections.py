"""
Segment Resumes into Normalized Sections

Input:
- data/real_resumes/extracted_text/*.txt
- config/section_normalization_map.json

Output:
- output/sections/<resume_name>_sections.json
- output/sections/section_segmentation_summary.csv

Purpose:
Split extracted resume text into normalized sections such as:
education, experience, skills, publications, etc.

Supports:
1. Standalone headings:
   EDUCATION

2. Inline headings:
   EDUCATION Doctor of Philosophy...
   OBJECTIVE To work in...
   RESEARCH Experimental Neutrino...
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEXT_INPUT_DIR = PROJECT_ROOT / "data" / "real_resumes" / "extracted_text"
NORMALIZATION_MAP_PATH = PROJECT_ROOT / "config" / "section_normalization_map.json"

SECTION_OUTPUT_DIR = PROJECT_ROOT / "output" / "sections"
SUMMARY_OUTPUT_PATH = PROJECT_ROOT / "output" / "sections" / "section_segmentation_summary.csv"


# These are common inline headings that appear at the beginning of a line.
# Example: "EDUCATION Doctor of Philosophy..."
INLINE_HEADING_ALIASES = {
    "objective": "summary",
    "career objective": "summary",
    "professional summary": "summary",
    "summary": "summary",

    "education": "education",
    "academic details": "education",
    "academic qualification": "education",
    "educational qualification": "education",
    "educational qualifications": "education",

    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment": "experience",
    "previous employment": "experience",
    "current employment": "experience",
    "teaching / research experiences": "experience",
    "teaching/research experiences": "experience",
    "teaching research experiences": "experience",
    "teaching experience": "experience",
    "research experience": "experience",

    "research": "research_interests",
    "research interest": "research_interests",
    "research interests": "research_interests",
    "research areas": "research_interests",
    "area of research": "research_interests",
    "area of interest": "research_interests",

    "skills": "skills",
    "technical skills": "skills",
    "technical skill": "skills",
    "technical expertise": "skills",

    "project": "projects",
    "projects": "projects",
    "project submitted": "projects",
    "project undertaken": "projects",

    "publication": "publications",
    "publications": "publications",
    "journal": "publications",
    "conference": "publications",
    "conference paper": "publications",
    "conference papers": "publications",

    "certification": "certifications",
    "certifications": "certifications",
    "course": "certifications",
    "courses": "certifications",
    "training": "certifications",
    "workshop": "certifications",
    "orientation": "certifications",
    "orientation and refresher": "certifications",
    "orientation and refresher course": "certifications",
    "faculty development program": "certifications",

    "achievement": "achievements",
    "achievements": "achievements",
    "awards": "achievements",
    "award": "achievements",
    "reviewer award": "achievements",

    "personal": "personal_details",
    "personal details": "personal_details",
    "personal information": "personal_details",
    "contact": "personal_details",

    "responsibilities": "responsibilities",
    "professional activities": "responsibilities",
    "academic responsibilities": "responsibilities",

    "membership": "memberships",
    "memberships": "memberships",

    "patent": "patents",
    "patents": "patents",

    "references": "references",
    "declaration": "declaration",
}


def clean_line(line: str) -> str:
    """
    Clean one line for heading matching.
    """
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    line = re.sub(r"^-+\s*page\s+\d+\s*-+$", "", line, flags=re.IGNORECASE)
    line = line.strip(":-–—|•●■□* ")
    return line.strip()


def normalize_for_match(text: str) -> str:
    """
    Normalize heading text for comparison.
    """
    text = clean_line(text).lower()
    text = text.replace("&", "and")
    text = re.sub(r"[/]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_page_marker(line: str) -> bool:
    return bool(
        re.match(
            r"^-+\s*page\s+\d+\s*-+$",
            line.strip(),
            flags=re.IGNORECASE,
        )
    )


def load_heading_lookup() -> Dict[str, str]:
    """
    Load section_normalization_map.json and create flat lookup.
    """
    raw_map = json.loads(NORMALIZATION_MAP_PATH.read_text(encoding="utf-8"))

    lookup: Dict[str, str] = {}

    for canonical_section, variants in raw_map.items():
        for variant in variants:
            lookup[variant.strip().lower()] = canonical_section
            lookup[normalize_for_match(variant)] = canonical_section

    for alias, canonical in INLINE_HEADING_ALIASES.items():
        lookup[alias.strip().lower()] = canonical
        lookup[normalize_for_match(alias)] = canonical

    return lookup


def detect_standalone_heading(
    line: str,
    heading_lookup: Dict[str, str],
) -> Optional[Dict[str, str]]:
    """
    Detect if the full line is a known heading.
    """
    cleaned = clean_line(line)

    if not cleaned:
        return None

    normalized_raw = cleaned.lower()
    normalized_soft = normalize_for_match(cleaned)

    canonical = heading_lookup.get(normalized_raw) or heading_lookup.get(normalized_soft)

    if canonical is None:
        return None

    return {
        "type": "standalone",
        "raw_heading": line.strip(),
        "clean_heading": cleaned,
        "canonical_section": canonical,
        "remaining_text": "",
    }


def detect_inline_heading(
    line: str,
    heading_lookup: Dict[str, str],
) -> Optional[Dict[str, str]]:
    """
    Detect headings appearing at the start of a line.

    Example:
    EDUCATION Doctor of Philosophy...
    OBJECTIVE To work in...
    RESEARCH Experimental Neutrino...
    """
    cleaned = clean_line(line)

    if not cleaned:
        return None

    # Avoid treating normal sentence lines as inline headings.
    # Inline headings in resumes are usually uppercase at the start.
    first_part = cleaned[:60]
    has_upper_start = bool(re.match(r"^[A-Z][A-Z\s/&.-]{2,}", first_part))

    if not has_upper_start:
        return None

    # Prepare candidate heading aliases, longest first.
    alias_items = sorted(
        INLINE_HEADING_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    normalized_line = normalize_for_match(cleaned)

    for alias, canonical in alias_items:
        alias_norm = normalize_for_match(alias)

        if not alias_norm:
            continue

        # Match alias at start followed by either end or more content.
        if normalized_line == alias_norm or normalized_line.startswith(alias_norm + " "):
            # Extract remaining text approximately from original cleaned line.
            # This is approximate but works for heading-at-start patterns.
            pattern = re.compile(
                r"^\s*" + re.escape(alias).replace("\\ ", r"\s+") + r"\b\s*[:\-–—/]?\s*",
                flags=re.IGNORECASE,
            )

            remaining = pattern.sub("", cleaned).strip()

            # If regex did not remove due to punctuation difference, use word-count fallback.
            if remaining == cleaned:
                alias_word_count = len(alias.split())
                words = cleaned.split()
                remaining = " ".join(words[alias_word_count:]).strip()

            return {
                "type": "inline",
                "raw_heading": line.strip(),
                "clean_heading": alias,
                "canonical_section": canonical,
                "remaining_text": remaining,
            }

    # Also try first 1 to 4 tokens as possible heading from normalization map.
    words = cleaned.split()

    for n in range(min(4, len(words)), 0, -1):
        candidate = " ".join(words[:n])
        candidate_norm = normalize_for_match(candidate)
        canonical = heading_lookup.get(candidate_norm)

        if canonical and canonical != "ignore":
            remaining = " ".join(words[n:]).strip()

            # Avoid weak one-word false positives inside ordinary lines.
            if n == 1 and candidate_norm not in {
                "education",
                "experience",
                "research",
                "objective",
                "publications",
                "publication",
                "skills",
                "projects",
                "course",
                "workshop",
                "personal",
                "references",
                "declaration",
            }:
                continue

            return {
                "type": "inline",
                "raw_heading": line.strip(),
                "clean_heading": candidate,
                "canonical_section": canonical,
                "remaining_text": remaining,
            }

    return None


def detect_heading(
    line: str,
    heading_lookup: Dict[str, str],
) -> Optional[Dict[str, str]]:
    """
    Detect standalone or inline heading.
    """
    standalone = detect_standalone_heading(line, heading_lookup)

    if standalone:
        return standalone

    inline = detect_inline_heading(line, heading_lookup)

    if inline:
        return inline

    return None


def append_line(section_store: Dict[str, List[str]], section_name: str, line: str) -> None:
    if section_name not in section_store:
        section_store[section_name] = []

    section_store[section_name].append(line)


def segment_one_resume(txt_path: Path, heading_lookup: Dict[str, str]) -> Dict[str, Any]:
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

        if is_page_marker(raw_line):
            continue

        heading_info = detect_heading(raw_line, heading_lookup)

        if heading_info is not None:
            canonical = heading_info["canonical_section"]

            if canonical == "ignore":
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
                "heading_type": heading_info["type"],
            })

            if current_section not in sections:
                sections[current_section] = []

            remaining_text = heading_info.get("remaining_text", "").strip()

            # For inline headings, preserve content after heading.
            if remaining_text:
                append_line(sections, current_section, remaining_text)
                total_content_chars += len(remaining_text)
                mapped_content_chars += len(remaining_text)

            continue

        total_content_chars += len(cleaned)

        append_line(sections, current_section, raw_line)
        mapped_content_chars += len(cleaned)

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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_summary(rows: List[Dict[str, Any]]) -> None:
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