import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

CANONICAL_SECTIONS = [
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
]


def make_key(record: Dict[str, Any]) -> str:
    """Create a stable key from identifiers.

    Key fields: resume_id, page_number, line_number, line_index
    """
    for f in ("resume_id", "page_number", "line_number", "line_index"):
        if f not in record:
            raise ValueError(f"missing identifier field: {f}")
    return f"{record['resume_id']}|p{record['page_number']}|l{record['line_number']}|i{record['line_index']}"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    items = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def load_machine_records(path: Path) -> List[Dict[str, Any]]:
    return load_jsonl(path)


def load_human_annotations(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    annotations = {}
    for rec in load_jsonl(path):
        if "_key" not in rec:
            continue
        annotations[rec["_key"]] = rec
    return annotations


def save_human_annotations(path: Path, annotations: Dict[str, Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in annotations.values():
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def generate_queue(machine_records: List[Dict[str, Any]], human_annotations: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate queue of candidates to review.

    Only include records where `machine_suggested_heading` is not null.
    """
    queue = []
    for rec in machine_records:
        key = make_key(rec)
        if key in human_annotations:
            continue
        # include only machine-suggested headings
        if rec.get("machine_suggested_heading") is not None:
            queue.append(rec)
    # order by resume_id, page_number, line_index to support resume-by-resume review
    queue.sort(key=lambda r: (r.get("resume_id"), r.get("page_number", 0), r.get("line_index", 0)))
    return queue


def get_context(machine_records: List[Dict[str, Any]], idx: int, before: int = 4, after: int = 4) -> List[Tuple[str, Dict[str, Any]]]:
    # returns list of (marker, record) where marker is 'prev','candidate','next'
    if idx < 0 or idx >= len(machine_records):
        return []
    rec = machine_records[idx]
    resume = rec.get("resume_id")
    page = rec.get("page_number")
    # collect surrounding lines but preserve page boundaries and resume boundaries
    out = []
    # go backwards
    i = idx - 1
    b = 0
    while i >= 0 and b < before:
        r = machine_records[i]
        if r.get("resume_id") != resume or r.get("page_number") != page:
            break
        out.insert(0, ("prev", r))
        i -= 1
        b += 1
    out.append(("candidate", rec))
    i = idx + 1
    a = 0
    while i < len(machine_records) and a < after:
        r = machine_records[i]
        if r.get("resume_id") != resume or r.get("page_number") != page:
            break
        out.append(("next", r))
        i += 1
        a += 1
    return out


def validate_annotation_entry(entry: Dict[str, Any]) -> None:
    # required identifiers
    for f in ("resume_id", "page_number", "line_number", "line_index"):
        if f not in entry:
            raise ValueError(f"annotation missing required field {f}")
    if "is_heading" not in entry or not isinstance(entry["is_heading"], bool):
        raise ValueError("is_heading must be boolean")
    if entry.get("section_label") not in CANONICAL_SECTIONS:
        raise ValueError("section_label must be one of canonical sections")


def create_annotation_from_machine(rec: Dict[str, Any], is_heading: bool, section_label: Optional[str], annotator_notes: str, review_state: str) -> Dict[str, Any]:
    ann = {
        "_key": make_key(rec),
        "resume_id": rec.get("resume_id"),
        "page_number": rec.get("page_number"),
        "line_number": rec.get("line_number"),
        "line_index": rec.get("line_index"),
        "is_heading": bool(is_heading),
        "section_label": section_label if section_label in CANONICAL_SECTIONS else "other",
        "annotator_notes": annotator_notes or "",
        "review_state": review_state,
    }
    validate_annotation_entry(ann)
    return ann


def summarize(queue: List[Dict[str, Any]], annotations: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    total = len(queue) + len(annotations)
    annotated = len(annotations)
    remaining = len(queue)
    headings = sum(1 for v in annotations.values() if v.get("is_heading"))
    non_headings = annotated - headings
    section_counts = {}
    for v in annotations.values():
        lbl = v.get("section_label") or "other"
        section_counts[lbl] = section_counts.get(lbl, 0) + 1
    pct_annotated = (annotated / total * 100) if total else 0.0
    return {
        "total_candidates": total,
        "annotated": annotated,
        "remaining": remaining,
        "headings_confirmed": headings,
        "non_headings_confirmed": non_headings,
        "section_counts": section_counts,
        "percentage_annotated": pct_annotated,
    }


if __name__ == "__main__":
    print("This module provides functions for the annotation reviewer. Use review_annotations.py to run the CLI.")
