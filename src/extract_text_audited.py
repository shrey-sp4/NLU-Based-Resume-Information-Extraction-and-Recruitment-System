"""
Audited Resume Text Extraction Pipeline

Purpose:
- Read resume PDFs from data/real_resumes/original/
- Extract page-wise text using pdfplumber
- Save full extracted text as .txt
- Save per-resume metadata as .json
- Save extraction summary as output/extraction/extraction_summary.csv

This is Stage 1 of the auditable resume extraction pipeline.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import pdfplumber


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = PROJECT_ROOT / "data" / "real_resumes" / "original"
TEXT_OUTPUT_DIR = PROJECT_ROOT / "data" / "real_resumes" / "extracted_text"
METADATA_OUTPUT_DIR = PROJECT_ROOT / "data" / "real_resumes" / "metadata"
SUMMARY_OUTPUT_PATH = PROJECT_ROOT / "output" / "extraction" / "extraction_summary.csv"


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

LOW_TEXT_CHAR_THRESHOLD = 50
LOW_TEXT_WORD_THRESHOLD = 10


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------

def clean_text(text: str) -> str:
    """
    Basic cleaning for extracted text.
    This does NOT remove content aggressively.
    It only normalizes whitespace lightly.
    """
    if not text:
        return ""

    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive spaces inside lines, but keep line structure.
    cleaned_lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        cleaned_lines.append(line)

    # Remove excessive blank lines.
    cleaned_text = "\n".join(cleaned_lines)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return cleaned_text.strip()


def count_words(text: str) -> int:
    """Count approximate words."""
    if not text:
        return 0
    return len(re.findall(r"\b\w+\b", text))


def safe_filename(file_path: Path) -> str:
    """
    Create safe stem for output files.
    Example: 'Aakash Choudhary CV.pdf' -> 'Aakash_Choudhary_CV'
    """
    stem = file_path.stem.strip()
    stem = re.sub(r"[^\w\-]+", "_", stem)
    stem = re.sub(r"_+", "_", stem)
    return stem.strip("_")


def extract_pdf_with_pdfplumber(pdf_path: Path) -> Dict[str, Any]:
    """
    Extract text page-wise using pdfplumber.

    Returns:
        Dictionary containing full_text, page metadata, and summary values.
    """
    pages_data: List[Dict[str, Any]] = []
    full_text_parts: List[str] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        page_count = len(pdf.pages)

        for page_index, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text() or ""
            cleaned_page_text = clean_text(raw_text)

            char_count = len(cleaned_page_text)
            word_count = count_words(cleaned_page_text)

            is_blank = char_count == 0
            is_low_text = (
                char_count < LOW_TEXT_CHAR_THRESHOLD
                or word_count < LOW_TEXT_WORD_THRESHOLD
            )

            page_record = {
                "page_number": page_index,
                "char_count": char_count,
                "word_count": word_count,
                "is_blank": is_blank,
                "is_low_text": is_low_text,
                "width": page.width,
                "height": page.height,
            }

            pages_data.append(page_record)

            page_header = f"\n\n--- PAGE {page_index} ---\n"
            full_text_parts.append(page_header + cleaned_page_text)

    full_text = "\n".join(full_text_parts).strip()

    total_chars = len(full_text)
    total_words = count_words(full_text)

    blank_pages = [
        page["page_number"] for page in pages_data if page["is_blank"]
    ]

    low_text_pages = [
        page["page_number"] for page in pages_data if page["is_low_text"]
    ]

    manual_review_required = len(low_text_pages) > 0 or total_chars == 0

    if total_chars == 0:
        status = "fail"
    elif manual_review_required:
        status = "review"
    else:
        status = "pass"

    return {
        "full_text": full_text,
        "page_count": page_count,
        "total_char_count": total_chars,
        "total_word_count": total_words,
        "blank_pages": blank_pages,
        "low_text_pages": low_text_pages,
        "manual_review_required": manual_review_required,
        "status": status,
        "pages": pages_data,
    }


def process_pdf(pdf_path: Path) -> Dict[str, Any]:
    """
    Process one PDF:
    - extract text
    - save .txt file
    - save metadata .json
    - return summary row
    """
    output_stem = safe_filename(pdf_path)

    text_output_path = TEXT_OUTPUT_DIR / f"{output_stem}.txt"
    metadata_output_path = METADATA_OUTPUT_DIR / f"{output_stem}_metadata.json"

    try:
        extraction_result = extract_pdf_with_pdfplumber(pdf_path)

        text_output_path.write_text(
            extraction_result["full_text"],
            encoding="utf-8"
        )

        metadata = {
            "file_name": pdf_path.name,
            "file_path": str(pdf_path),
            "extraction_method": "pdfplumber",
            "processed_at": datetime.now().isoformat(timespec="seconds"),
            "text_output_path": str(text_output_path),
            "page_count": extraction_result["page_count"],
            "total_char_count": extraction_result["total_char_count"],
            "total_word_count": extraction_result["total_word_count"],
            "blank_pages": extraction_result["blank_pages"],
            "low_text_pages": extraction_result["low_text_pages"],
            "manual_review_required": extraction_result["manual_review_required"],
            "status": extraction_result["status"],
            "pages": extraction_result["pages"],
            "notes": [
                "OCR fallback is not implemented in this first version.",
                "Low-text pages should be manually checked or handled with OCR later."
            ],
        }

        metadata_output_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return {
            "file_name": pdf_path.name,
            "file_type": "pdf",
            "page_count": extraction_result["page_count"],
            "total_char_count": extraction_result["total_char_count"],
            "total_word_count": extraction_result["total_word_count"],
            "blank_pages": json.dumps(extraction_result["blank_pages"]),
            "low_text_pages": json.dumps(extraction_result["low_text_pages"]),
            "extraction_method": "pdfplumber",
            "manual_review_required": extraction_result["manual_review_required"],
            "status": extraction_result["status"],
            "text_output_file": str(text_output_path.relative_to(PROJECT_ROOT)),
            "metadata_file": str(metadata_output_path.relative_to(PROJECT_ROOT)),
            "error": "",
        }

    except Exception as exc:
        error_metadata = {
            "file_name": pdf_path.name,
            "file_path": str(pdf_path),
            "extraction_method": "pdfplumber",
            "processed_at": datetime.now().isoformat(timespec="seconds"),
            "status": "error",
            "error": str(exc),
        }

        metadata_output_path.write_text(
            json.dumps(error_metadata, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return {
            "file_name": pdf_path.name,
            "file_type": "pdf",
            "page_count": 0,
            "total_char_count": 0,
            "total_word_count": 0,
            "blank_pages": "[]",
            "low_text_pages": "[]",
            "extraction_method": "pdfplumber",
            "manual_review_required": True,
            "status": "error",
            "text_output_file": "",
            "metadata_file": str(metadata_output_path.relative_to(PROJECT_ROOT)),
            "error": str(exc),
        }


def write_summary(rows: List[Dict[str, Any]]) -> None:
    """Write extraction summary CSV."""
    SUMMARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file_name",
        "file_type",
        "page_count",
        "total_char_count",
        "total_word_count",
        "blank_pages",
        "low_text_pages",
        "extraction_method",
        "manual_review_required",
        "status",
        "text_output_file",
        "metadata_file",
        "error",
    ]

    with SUMMARY_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Main entry point."""
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in: {INPUT_DIR}")
        print("Put your resume PDFs in data/real_resumes/original/ and run again.")
        return

    print(f"Found {len(pdf_files)} PDF file(s). Starting extraction...\n")

    summary_rows: List[Dict[str, Any]] = []

    for index, pdf_path in enumerate(pdf_files, start=1):
        print(f"[{index}/{len(pdf_files)}] Processing: {pdf_path.name}")
        row = process_pdf(pdf_path)
        summary_rows.append(row)
        print(f"    Status: {row['status']}")
        print(f"    Chars: {row['total_char_count']}, Words: {row['total_word_count']}")
        if row["manual_review_required"]:
            print("    Manual review required: YES")
        print()

    write_summary(summary_rows)

    print("Extraction complete.")
    print(f"Summary saved to: {SUMMARY_OUTPUT_PATH}")


if __name__ == "__main__":
    main()