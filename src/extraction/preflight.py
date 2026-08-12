from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from .discovery import sha256_file
from .models import PreflightResult


def _try_pymupdf(path: Path) -> Tuple[Optional[int], bool, bool, List[str], List[str]]:
    warnings: List[str] = []
    errors: List[str] = []
    try:
        import fitz  # type: ignore
    except Exception as exc:
        errors.append(f"PyMuPDF unavailable: {exc}")
        return None, False, False, warnings, errors

    try:
        doc = fitz.open(str(path))
        page_count = len(doc)
        encrypted = bool(getattr(doc, "is_encrypted", False))
        readable = not encrypted
        return page_count, encrypted, readable, warnings, errors
    except Exception as exc:
        errors.append(f"PyMuPDF open failed: {exc}")
        return None, False, False, warnings, errors


def _try_pypdf(path: Path) -> Tuple[Optional[int], bool, bool, List[str], List[str]]:
    warnings: List[str] = []
    errors: List[str] = []
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:
        errors.append(f"pypdf unavailable: {exc}")
        return None, False, False, warnings, errors

    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        encrypted = bool(getattr(reader, "is_encrypted", False))
        readable = not encrypted
        return page_count, encrypted, readable, warnings, errors
    except Exception as exc:
        errors.append(f"pypdf open failed: {exc}")
        return None, False, False, warnings, errors


def preflight_pdf(path: Path) -> PreflightResult:
    file_hash = sha256_file(path)
    file_size = path.stat().st_size
    warnings: List[str] = []
    errors: List[str] = []
    is_pdf = path.suffix.lower() == ".pdf"
    page_count: Optional[int] = None
    encrypted = False
    readable = False
    backend: Optional[str] = None

    if not is_pdf:
        warnings.append("Source file does not use a .pdf extension")

    page_count, encrypted, readable, pymupdf_warnings, pymupdf_errors = _try_pymupdf(path)
    warnings.extend(pymupdf_warnings)
    errors.extend(pymupdf_errors)
    if page_count is not None:
        backend = "pymupdf"
    else:
        alt_page_count, alt_encrypted, alt_readable, pypdf_warnings, pypdf_errors = _try_pypdf(path)
        warnings.extend(pypdf_warnings)
        errors.extend(pypdf_errors)
        if alt_page_count is not None:
            page_count = alt_page_count
            encrypted = alt_encrypted
            readable = alt_readable
            backend = "pypdf"

    if page_count is None:
        errors.append("Unable to determine page count from available PDF backends")

    if encrypted:
        warnings.append("PDF appears to be encrypted")

    return PreflightResult(
        source_path=path,
        file_hash=file_hash,
        file_size=file_size,
        is_pdf=is_pdf,
        readable=readable,
        page_count=page_count,
        encrypted=encrypted,
        warnings=warnings,
        errors=errors,
        backend=backend,
    )

