from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from .config import ExtractionConfig
from .models import DocumentSource, RunManifest


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return cleaned or "document"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_pdf_files(input_root: Path) -> List[Path]:
    if not input_root.exists():
        return []
    return sorted(
        [
            path
            for path in input_root.rglob("*")
            if path.is_file() and path.suffix.lower() == ".pdf"
        ],
        key=lambda path: path.name.lower(),
    )


def build_document_id(path: Path, file_hash: str) -> str:
    base = slugify(path.stem)
    return f"{base}_{file_hash[:8]}"


def build_document_sources(paths: Iterable[Path]) -> List[DocumentSource]:
    sources: List[DocumentSource] = []
    for path in paths:
        file_hash = sha256_file(path)
        sources.append(
            DocumentSource(
                document_id=build_document_id(path, file_hash),
                source_path=path,
                file_hash=file_hash,
                file_size=path.stat().st_size,
            )
        )
    return sources


def build_run_manifest(config: ExtractionConfig, documents: List[DocumentSource]) -> RunManifest:
    run_id = config.run_id()
    return RunManifest(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_root=config.input_root,
        output_root=config.output_root / run_id,
        document_count=len(documents),
        documents=documents,
        config=config.as_dict(),
    )

