from __future__ import annotations

from pathlib import Path

from .audit import ensure_directory


def build_run_directory(output_root: Path, run_id: str) -> Path:
    return ensure_directory(output_root / run_id)


def build_document_directory(run_dir: Path, document_id: str) -> Path:
    return ensure_directory(run_dir / "documents" / document_id)


def build_page_directory(document_dir: Path, page_number: int) -> Path:
    return ensure_directory(document_dir / "pages" / f"page_{page_number:04d}")


def build_render_directory(page_dir: Path) -> Path:
    return ensure_directory(page_dir / "render")

