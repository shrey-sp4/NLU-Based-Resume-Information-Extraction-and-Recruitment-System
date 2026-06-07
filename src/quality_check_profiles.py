"""
Candidate Profile Quality Check

Input:
- output/profiles/candidate_profiles.csv

Output:
- output/quality_checks/profile_quality_report.csv

Purpose:
Flag suspicious candidate profile fields before ground-truth evaluation.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import List, Dict, Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROFILE_CSV = PROJECT_ROOT / "output" / "profiles" / "candidate_profiles.csv"
OUTPUT_CSV = PROJECT_ROOT / "output" / "quality_checks" / "profile_quality_report.csv"


BAD_NAME_TERMS = [
    "curriculum vitae",
    "curiculam vitae",
    "resume",
    "cv",
    "email",
    "e-mail",
    "mobile",
    "phone",
    "contact",
    "address",
    "permanent address",
    "department",
    "university",
    "college",
    "school",
    "regular",
    "mobileno",
    "mobile no",
]


def read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as csvfile:
        return list(csv.DictReader(csvfile))


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file_name",
        "name",
        "email",
        "phone",
        "flags",
        "status",
        "suggested_manual_check",
    ]

    with path.open("w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def is_suspicious_name(name: str) -> bool:
    if not name or name.strip().upper() == "MISSING":
        return True

    lower = name.lower().strip()

    if any(term in lower for term in BAD_NAME_TERMS):
        return True

    if "@" in name:
        return True

    if re.search(r"\d{4,}", name):
        return True

    words = name.split()

    if len(words) < 2:
        return True

    if len(words) > 6:
        return True

    return False


def is_suspicious_email(email: str) -> bool:
    if not email or email.strip().upper() == "MISSING":
        return True

    if "@" not in email:
        return True

    return False


def is_suspicious_phone(phone: str) -> bool:
    if not phone or phone.strip().upper() == "MISSING":
        return True

    digits = re.sub(r"\D", "", phone)

    if len(digits) != 10:
        return True

    # Indian mobile numbers usually start with 6,7,8,9.
    # Some landlines exist, but for resume contact this is suspicious.
    if not digits.startswith(("6", "7", "8", "9")):
        return True

    # Reject obvious repeated/invalid patterns.
    if len(set(digits)) <= 2:
        return True

    return False


def check_profile(row: Dict[str, Any]) -> Dict[str, Any]:
    flags = []

    name = row.get("name", "").strip()
    email = row.get("email", "").strip()
    phone = row.get("phone", "").strip()

    if is_suspicious_name(name):
        flags.append("suspicious_name")

    if is_suspicious_email(email):
        flags.append("suspicious_or_missing_email")

    if is_suspicious_phone(phone):
        flags.append("suspicious_or_missing_phone")

    if not row.get("education", "").strip():
        flags.append("missing_education")

    if not row.get("experience", "").strip() and not row.get("publications", "").strip():
        flags.append("missing_experience_and_publications")

    if flags:
        status = "review"
    else:
        status = "pass"

    return {
        "file_name": row.get("file_name", ""),
        "name": name,
        "email": email,
        "phone": phone,
        "flags": "; ".join(flags),
        "status": status,
        "suggested_manual_check": "yes" if flags else "no",
    }


def main() -> None:
    if not PROFILE_CSV.exists():
        print(f"Missing profile CSV: {PROFILE_CSV}")
        print("Run src/extract_candidate_profiles.py first.")
        return

    rows = read_csv(PROFILE_CSV)

    report_rows = [check_profile(row) for row in rows]

    write_csv(OUTPUT_CSV, report_rows)

    pass_count = sum(1 for row in report_rows if row["status"] == "pass")
    review_count = sum(1 for row in report_rows if row["status"] == "review")

    print("Profile quality check complete.")
    print(f"Total profiles: {len(report_rows)}")
    print(f"Pass: {pass_count}")
    print(f"Review: {review_count}")
    print(f"Saved to: {OUTPUT_CSV}")

    print("\nProfiles needing review:")
    for row in report_rows:
        if row["status"] == "review":
            print(f"- {row['file_name']} | {row['flags']}")


if __name__ == "__main__":
    main()