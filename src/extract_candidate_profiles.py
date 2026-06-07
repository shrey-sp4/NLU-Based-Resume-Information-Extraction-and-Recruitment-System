"""
Extract Candidate Profiles from Segmented Resume Sections

Input:
- output/sections/*_sections.json

Output:
- output/profiles/candidate_profiles.csv
- output/profiles/candidate_profiles.json

Purpose:
Create normalized candidate profiles from section-wise resume JSON files.

This version improves:
- name extraction
- phone validation
- evidence preservation
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SECTION_INPUT_DIR = PROJECT_ROOT / "output" / "sections"
PROFILE_OUTPUT_CSV = PROJECT_ROOT / "output" / "profiles" / "candidate_profiles.csv"
PROFILE_OUTPUT_JSON = PROJECT_ROOT / "output" / "profiles" / "candidate_profiles.json"


EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)

PHONE_CANDIDATE_PATTERN = re.compile(
    r"(?:\+91[\s\-]*)?(?:[6-9]\d[\d\s\-]{8,12})"
)


BAD_NAME_TERMS = [
    "curriculum vitae",
    "curiculam vitae",
    "resume",
    "cv",
    "bio data",
    "biodata",
    "email",
    "e-mail",
    "mobile",
    "mobileno",
    "mobile no",
    "phone",
    "contact",
    "address",
    "permanent address",
    "department",
    "university",
    "college",
    "school",
    "regular",
    "http",
    "www",
]


TITLE_PREFIX_PATTERN = re.compile(
    r"^(dr|mr|mrs|ms|prof)\.?\s+",
    flags=re.IGNORECASE,
)


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def one_line(text: str, max_chars: int = 500) -> str:
    text = clean_text(text)
    text = re.sub(r"\s+", " ", text)

    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "..."

    return text


def normalize_name_candidate(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\s+", " ", line)

    # Handle "Name: Dr. Amit K Parikh"
    line = re.sub(
        r"^(name|candidate name|full name)\s*[:\-]\s*",
        "",
        line,
        flags=re.IGNORECASE,
    )

    # Remove bullets/arrows
    line = line.strip("➢:-–—|•●■□* ")

    return line.strip()


def is_bad_name_candidate(name: str) -> bool:
    if not name:
        return True

    lower = name.lower().strip()

    if any(term in lower for term in BAD_NAME_TERMS):
        return True

    if "@" in name:
        return True

    if re.search(r"\d{3,}", name):
        return True

    if ":" in name and not lower.startswith(("dr:", "mr:", "ms:", "mrs:", "prof:")):
        return True

    words = name.split()

    if len(words) < 2:
        return True

    if len(words) > 6:
        return True

    alpha_chars = sum(ch.isalpha() for ch in name)

    if alpha_chars < 4:
        return True

    return False


def extract_name_from_personal_details(personal_details: str) -> str:
    """
    Prefer explicit NAME field from personal_details section.
    """
    if not personal_details:
        return ""

    lines = [line.strip() for line in personal_details.splitlines() if line.strip()]

    for line in lines:
        # Examples:
        # NAME : Anil Babubhai Hirpara
        # ➢ NAME : Anil Babubhai Hirpara
        match = re.search(
            r"\bname\s*[:\-]\s*(.+)$",
            line,
            flags=re.IGNORECASE,
        )

        if match:
            candidate = normalize_name_candidate(match.group(1))

            if not is_bad_name_candidate(candidate):
                return candidate

    return ""


def extract_name_from_preamble(preamble: str, file_name: str) -> str:
    """
    Extract name from preamble.
    Avoid generic title lines and contact lines.
    """
    lines = [line.strip() for line in preamble.splitlines() if line.strip()]

    for line in lines[:12]:
        candidate = normalize_name_candidate(line)

        if is_bad_name_candidate(candidate):
            continue

        # Avoid obvious job title lines
        lower = candidate.lower()
        if any(
            phrase in lower
            for phrase in [
                "assistant professor",
                "associate professor",
                "professor",
                "research scholar",
                "postdoctoral",
                "department",
                "institute",
            ]
        ):
            # allow if line starts with Dr./Prof and has name-like structure
            if not TITLE_PREFIX_PATTERN.match(candidate):
                continue

        return candidate

    return extract_name_from_filename(file_name)


def extract_name_from_filename(file_name: str) -> str:
    """
    Last fallback from file name.
    """
    stem = Path(file_name).stem

    stem = re.sub(r"[_\-]+", " ", stem)
    stem = re.sub(r"\([^)]*\)", "", stem)

    # Remove common CV/resume terms
    stem = re.sub(
        r"\b(cv|resume|curriculum|vitae|updated|latest|final|with|scholars|status|docs|doc|pdf)\b",
        "",
        stem,
        flags=re.IGNORECASE,
    )

    # Remove dates/numbers
    stem = re.sub(r"\b\d{2,8}\b", "", stem)
    stem = re.sub(r"\s+", " ", stem).strip()

    if not stem:
        return ""

    if is_bad_name_candidate(stem):
        return ""

    return stem


def extract_name(sections: Dict[str, str], file_name: str) -> str:
    personal_details = sections.get("personal_details", "")
    preamble = sections.get("preamble", "")

    name = extract_name_from_personal_details(personal_details)

    if name:
        return name

    name = extract_name_from_preamble(preamble, file_name)

    return name


def extract_email(full_text: str) -> str:
    matches = EMAIL_PATTERN.findall(full_text)

    if not matches:
        return ""

    seen = []

    for email in matches:
        email = email.strip().rstrip(".;,")
        email_lower = email.lower()

        if email_lower not in seen:
            seen.append(email_lower)

    return seen[0] if seen else ""


def extract_phone(full_text: str) -> str:
    """
    Extract only likely Indian mobile numbers.
    Rules:
    - Must become exactly 10 digits after removing +91
    - Must start with 6/7/8/9
    """
    matches = PHONE_CANDIDATE_PATTERN.findall(full_text)

    candidates = []

    for match in matches:
        digits = re.sub(r"\D", "", match)

        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]

        if len(digits) != 10:
            continue

        if not digits.startswith(("6", "7", "8", "9")):
            continue

        if len(set(digits)) <= 2:
            continue

        candidates.append(digits)

    if not candidates:
        return ""

    return candidates[0]


def count_publications(publications_text: str) -> int:
    """
    Estimate publication count using numbered list patterns.
    Approximate only.
    """
    if not publications_text:
        return 0

    lines = publications_text.splitlines()
    count = 0

    for line in lines:
        if re.match(r"^\s*\d+[\.\)]\s+", line):
            count += 1

    if count > 0:
        return count

    doi_count = len(
        re.findall(
            r"\bdoi\b|https?://doi\.org",
            publications_text,
            flags=re.IGNORECASE,
        )
    )

    return doi_count


def get_section(sections: Dict[str, str], section_name: str) -> str:
    return clean_text(sections.get(section_name, ""))


def build_profile(section_json_path: Path) -> Dict[str, Any]:
    data = json.loads(section_json_path.read_text(encoding="utf-8"))

    file_name = data.get("file_name", section_json_path.name)
    sections: Dict[str, str] = data.get("sections", {})

    full_text = "\n\n".join(sections.values())

    name = extract_name(sections, file_name)
    email = extract_email(full_text)
    phone = extract_phone(full_text)

    summary = get_section(sections, "summary")
    personal_details = get_section(sections, "personal_details")
    education = get_section(sections, "education")
    experience = get_section(sections, "experience")
    skills = get_section(sections, "skills")
    projects = get_section(sections, "projects")
    publications = get_section(sections, "publications")
    certifications = get_section(sections, "certifications")
    achievements = get_section(sections, "achievements")
    research_interests = get_section(sections, "research_interests")
    responsibilities = get_section(sections, "responsibilities")

    publication_count = count_publications(publications)

    profile = {
        "file_name": file_name,
        "name": name,
        "email": email,
        "phone": phone,

        "summary": one_line(summary, 800),
        "personal_details": one_line(personal_details, 1000),

        "education": one_line(education, 2000),
        "experience": one_line(experience, 2500),
        "skills": one_line(skills, 1500),
        "research_interests": one_line(research_interests, 1500),
        "projects": one_line(projects, 2000),
        "publications": one_line(publications, 2500),
        "publication_count_estimate": publication_count,
        "certifications": one_line(certifications, 2000),
        "achievements": one_line(achievements, 2000),
        "responsibilities": one_line(responsibilities, 2000),

        "detected_sections": "; ".join(sorted(sections.keys())),
        "section_json_file": str(section_json_path.relative_to(PROJECT_ROOT)),
    }

    evidence = {
        "file_name": file_name,
        "source_section_json": str(section_json_path.relative_to(PROJECT_ROOT)),
        "extracted_fields": profile,
        "source_sections": sections,
    }

    return {
        "profile": profile,
        "evidence": evidence,
    }


def write_csv(rows: List[Dict[str, Any]]) -> None:
    PROFILE_OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file_name",
        "name",
        "email",
        "phone",
        "summary",
        "personal_details",
        "education",
        "experience",
        "skills",
        "research_interests",
        "projects",
        "publications",
        "publication_count_estimate",
        "certifications",
        "achievements",
        "responsibilities",
        "detected_sections",
        "section_json_file",
    ]

    with PROFILE_OUTPUT_CSV.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(evidence_rows: List[Dict[str, Any]]) -> None:
    PROFILE_OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    PROFILE_OUTPUT_JSON.write_text(
        json.dumps(evidence_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    section_files = sorted(SECTION_INPUT_DIR.glob("*_sections.json"))

    if not section_files:
        print(f"No section JSON files found in: {SECTION_INPUT_DIR}")
        print("Run src/segment_resumes_into_sections.py first.")
        return

    print(f"Found {len(section_files)} section JSON file(s). Extracting candidate profiles...\n")

    profile_rows: List[Dict[str, Any]] = []
    evidence_rows: List[Dict[str, Any]] = []

    for index, section_path in enumerate(section_files, start=1):
        result = build_profile(section_path)

        profile = result["profile"]
        evidence = result["evidence"]

        profile_rows.append(profile)
        evidence_rows.append(evidence)

        print(
            f"[{index}/{len(section_files)}] {profile['file_name']} | "
            f"name={profile['name'] or 'MISSING'} | "
            f"email={profile['email'] or 'MISSING'} | "
            f"phone={profile['phone'] or 'MISSING'}"
        )

    write_csv(profile_rows)
    write_json(evidence_rows)

    print("\nCandidate profile extraction complete.")
    print(f"CSV saved to: {PROFILE_OUTPUT_CSV}")
    print(f"JSON evidence saved to: {PROFILE_OUTPUT_JSON}")


if __name__ == "__main__":
    main()