from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Sequence

from .candidates import generate_heading_candidates
from .models import (
    RawLineRecord,
    SectionAnnotationRecord,
    validate_annotation_record,
)


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Dict[str, object]) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def iter_run_page_json_files(run_dir: Path) -> Iterator[Path]:
    documents_dir = run_dir / "documents"
    for path in sorted(documents_dir.rglob("page.json")):
        yield path


def load_page_artifact(page_json_path: Path) -> Dict[str, object]:
    return json.loads(page_json_path.read_text(encoding="utf-8"))


def extract_lines_from_text(text: str) -> List[tuple[int, str, bool]]:
    raw_lines = text.splitlines()
    lines: List[tuple[int, str, bool]] = []
    for line_number, raw in enumerate(raw_lines, start=1):
        lines.append((line_number, raw.rstrip(), not bool(raw.strip())))
    return lines


def build_raw_line_records_from_run(run_dir: Path) -> List[RawLineRecord]:
    page_files = list(iter_run_page_json_files(run_dir))
    records: List[RawLineRecord] = []
    for page_json_path in page_files:
        page_data = load_page_artifact(page_json_path)
        page_number = int(page_data.get("page_number", 0))
        final_text = str(page_data.get("final_text", ""))
        document_dir = page_json_path.parent.parent.parent
        document_id = document_dir.name
        document_json_path = document_dir / "document.json"
        source_document = ""
        if document_json_path.exists():
            document_data = json.loads(document_json_path.read_text(encoding="utf-8"))
            source_document = str(document_data.get("source_path", ""))
        source_file = str(page_data.get("source_file", document_id))
        source_run_id = run_dir.name

        line_records = extract_lines_from_text(final_text)
        for index, (line_number, text, is_blank) in enumerate(line_records):
            prev_text = ""
            next_text = ""
            prev_blank = index == 0 or line_records[index - 1][2]
            next_blank = index == len(line_records) - 1 or line_records[index + 1][2]
            if index > 0:
                prev_text = line_records[index - 1][1]
            if index < len(line_records) - 1:
                next_text = line_records[index + 1][1]
            records.append(
                RawLineRecord(
                    resume_id=document_id,
                    document_id=document_id,
                    source_file=source_file,
                    source_run_id=source_run_id,
                    page_number=page_number,
                    line_number=line_number,
                    line_index=len(records) + 1,
                    text=text.strip(),
                    previous_text=prev_text,
                    next_text=next_text,
                    preceded_by_blank=prev_blank,
                    followed_by_blank=next_blank,
                    page_status=str(page_data.get("status", "")),
                    page_type_guess=str(page_data.get("page_type_guess", "")),
                    final_method=str(page_data.get("final_method", "")),
                )
            )
    return records


def build_annotation_records_from_run(run_dir: Path) -> List[SectionAnnotationRecord]:
    raw_lines = build_raw_line_records_from_run(run_dir)
    records: List[SectionAnnotationRecord] = []
    candidates = generate_heading_candidates(raw_lines)
    candidate_map = {
        (
            candidate.line.document_id,
            candidate.line.page_number,
            candidate.line.line_number,
        ): candidate
        for candidate in candidates
    }
    for line in raw_lines:
        candidate = candidate_map.get((line.document_id, line.page_number, line.line_number))
        if candidate is None:
            candidate = generate_heading_candidates([line])[0]
        record = SectionAnnotationRecord(
            resume_id=line.resume_id,
            document_id=line.document_id,
            source_document=line.source_file,
            source_run_id=line.source_run_id,
            page_number=line.page_number,
            line_number=line.line_number,
            line_index=line.line_index,
            text=line.text,
            is_blank=not bool(line.text.strip()),
            preceded_by_blank=line.preceded_by_blank,
            followed_by_blank=line.followed_by_blank,
            machine_suggested_heading=line.text if candidate.is_candidate and line.text.strip() else None,
            machine_suggested_section=candidate.suggested_label if line.text.strip() else "other",
            machine_confidence=round(candidate.heading_score if line.text.strip() else 0.0, 4),
            machine_suggestion_method="heuristic_candidate_generation",
            machine_review_required=not candidate.is_candidate or candidate.confidence < 0.6 or not line.text.strip(),
            is_heading=None,
            section_label=None,
            annotator_notes="",
            review_state="pending",
        )
        validate_annotation_record(record.to_dict())
        records.append(record)
    return records


def write_annotation_dataset(run_dir: Path, output_path: Path, schema_path: Path) -> Dict[str, object]:
    records = build_annotation_records_from_run(run_dir)
    write_jsonl(output_path, [record.to_dict() for record in records])
    schema = {
        "dataset": "section_line_annotations",
        "source_run": str(run_dir),
        "record_count": len(records),
        "fields": [
            "resume_id",
            "document_id",
            "source_document",
            "source_run_id",
            "page_number",
            "line_number",
            "line_index",
            "text",
            "is_blank",
            "preceded_by_blank",
            "followed_by_blank",
            "machine_suggested_heading",
            "machine_suggested_section",
            "machine_confidence",
            "machine_suggestion_method",
            "machine_review_required",
            "is_heading",
            "section_label",
            "annotator_notes",
            "review_state",
        ],
        "canonical_labels": [
            "education",
            "experience",
            "skills",
            "projects",
            "publications",
            "certifications",
            "research_interests",
            "achievements",
            "personal_details",
            "summary",
            "references",
            "responsibilities",
            "memberships",
            "patents",
            "declaration",
            "other",
        ],
        "annotation_rules": {
            "machine_suggestion_is_ground_truth": False,
            "human_annotation_required": True,
            "section_label_optional_before_review": True,
        },
    }
    write_json(schema_path, schema)
    return schema
