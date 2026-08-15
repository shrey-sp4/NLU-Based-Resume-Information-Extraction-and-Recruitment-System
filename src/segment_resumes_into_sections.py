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

    "achievement": "achievements",
    "achievements": "achievements",
    "awards": "achievements",
    "award": "achievements",

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
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    line = re.sub(r"^-+\s*page\s+\d+\s*-+$", "", line, flags=re.IGNORECASE)
    line = line.strip(":-–—|•●■□* ")
    return line.strip()


def normalize_for_match(text: str) -> str:
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


def is_structural_heading(line: str, line_number: int = 10) -> bool:
    """
    Checks if a line has structural attributes of a standalone heading.
    Enforces section boundary closure even for headings not in normalization map.
    Excludes top 3 lines of document to avoid matching candidate name header.
    """
    if line_number <= 3:
        return False

    cleaned = clean_line(line)
    if not cleaned:
        return False
    if cleaned.endswith((".", ",", ";")):
        return False
    if re.match(r"^\s*(?:[-•*➢|o\+]|\d+[\.\)])", line):
        return False
    if "@" in cleaned or "http" in cleaned or "www." in cleaned:
        return False
    if re.match(r"^\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}", cleaned, re.IGNORECASE):
        return False
    if re.match(r"^\s*(?:19|20)\d{2}\s*[-–—]", cleaned):
        return False
    
    words = cleaned.split()
    if len(words) > 6:
        return False
    
    is_caps = cleaned.isupper()
    is_title = cleaned.istitle() or all(w[0].isupper() for w in words if len(w) > 2 and w.isalpha())
    ends_colon = cleaned.endswith(":")

    return is_caps or is_title or ends_colon


def detect_standalone_heading(
    line: str,
    heading_lookup: Dict[str, str],
    line_number: int = 10,
) -> Optional[Dict[str, str]]:
    cleaned = clean_line(line)
    if not cleaned:
        return None

    normalized_raw = cleaned.lower()
    normalized_soft = normalize_for_match(cleaned)

    canonical = heading_lookup.get(normalized_raw) or heading_lookup.get(normalized_soft)

    if canonical is not None:
        return {
            "type": "standalone",
            "raw_heading": line.strip(),
            "clean_heading": cleaned,
            "canonical_section": canonical,
            "remaining_text": "",
        }

    if is_structural_heading(line, line_number):
        return {
            "type": "standalone",
            "raw_heading": line.strip(),
            "clean_heading": cleaned,
            "canonical_section": "other_sections",
            "remaining_text": "",
        }

    return None


def detect_inline_heading(
    line: str,
    heading_lookup: Dict[str, str],
) -> Optional[Dict[str, str]]:
    cleaned = clean_line(line)
    if not cleaned:
        return None

    first_part = cleaned[:60]
    has_upper_start = bool(re.match(r"^[A-Z][A-Z\s/&.-]{2,}", first_part))

    if not has_upper_start:
        return None

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

        if normalized_line == alias_norm or normalized_line.startswith(alias_norm + " "):
            pattern = re.compile(
                r"^\s*" + re.escape(alias).replace("\\ ", r"\s+") + r"\b\s*[:\-–—/]?\s*",
                flags=re.IGNORECASE,
            )
            remaining = pattern.sub("", cleaned).strip()

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

    words = cleaned.split()
    for n in range(min(4, len(words)), 0, -1):
        candidate = " ".join(words[:n])
        candidate_norm = normalize_for_match(candidate)
        canonical = heading_lookup.get(candidate_norm)

        if canonical and canonical != "ignore":
            remaining = " ".join(words[n:]).strip()
            if n == 1 and candidate_norm not in {
                "education", "experience", "research", "objective",
                "publications", "publication", "skills", "projects",
                "course", "workshop", "personal", "references", "declaration",
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
    line_number: int = 10,
) -> Optional[Dict[str, str]]:
    standalone = detect_standalone_heading(line, heading_lookup, line_number)
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

    for line_number, line in enumerate(lines, start=1):
        raw_line = line.rstrip("\n")
        cleaned = clean_line(raw_line)

        if not cleaned:
            continue

        if is_page_marker(raw_line):
            continue

        heading_info = detect_heading(raw_line, heading_lookup, line_number)

        if heading_info is not None:
            canonical = heading_info["canonical_section"]

            if canonical == "ignore":
                ignored_headings.append({
                    "line_number": line_number,
                    "raw_heading": heading_info["raw_heading"],
                    "clean_heading": heading_info["clean_heading"],
                    "previous_active_section": current_section,
                })
                current_section = "ignore"
                continue

            current_section = canonical
            boundaries.append({
                "line_number": line_number,
                "raw_heading": heading_info["raw_heading"],
                "clean_heading": heading_info["clean_heading"],
                "canonical_section": canonical,
            })

            remaining = heading_info.get("remaining_text", "").strip()
            if remaining:
                append_line(sections, current_section, remaining)
        else:
            append_line(sections, current_section, raw_line)

    sections_dict = {
        sec: "\n".join(sec_lines).strip()
        for sec, sec_lines in sections.items()
        if "\n".join(sec_lines).strip()
    }

    return {
        "file_name": txt_path.name,
        "sections": sections_dict,
        "boundaries": boundaries,
        "ignored_headings": ignored_headings,
    }


def main():
    SECTION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    txt_files = sorted(TEXT_INPUT_DIR.glob("*.txt"))
    heading_lookup = load_heading_lookup()

    print(f"Found {len(txt_files)} extracted text file(s). Segmenting resumes...\n")

    for idx, txt_path in enumerate(txt_files, start=1):
        res = segment_one_resume(txt_path, heading_lookup)
        output_file = SECTION_OUTPUT_DIR / f"{txt_path.stem}_sections.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        print(f"[{idx}/{len(txt_files)}] {txt_path.name}: {len(res['sections'])} sections detected")

if __name__ == "__main__":
    main()