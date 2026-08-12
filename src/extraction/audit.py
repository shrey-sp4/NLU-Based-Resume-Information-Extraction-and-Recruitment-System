from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

from .models import DocumentExtractionResult, PageExtractionResult, RunManifest


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def write_text(path: Path, text: str) -> None:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(text)


def write_run_manifest(run_dir: Path, manifest: RunManifest) -> Path:
    path = run_dir / "manifest.json"
    write_json(path, manifest.to_dict())
    return path


def write_page_result(page_dir: Path, page: PageExtractionResult) -> None:
    ensure_directory(page_dir)
    write_json(page_dir / "page.json", page.to_dict())
    write_text(page_dir / "final.txt", page.final_text)

    attempts_dir = page_dir / "attempts"
    ensure_directory(attempts_dir)
    for index, attempt in enumerate(page.attempts, start=1):
        write_json(attempts_dir / f"{index:02d}_{attempt.method}.json", attempt.to_dict())
        if attempt.text:
            write_text(attempts_dir / f"{index:02d}_{attempt.method}.txt", attempt.text)


def write_document_result(document_dir: Path, result: DocumentExtractionResult) -> None:
    ensure_directory(document_dir)
    write_json(document_dir / "document.json", result.to_dict())
    write_text(document_dir / "full_text.txt", result.full_text())


def write_review_queue(run_dir: Path, rows: Iterable[Dict[str, Any]]) -> Path:
    review_dir = ensure_directory(run_dir / "review_queue")
    path = review_dir / "review_items.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")
    return path
