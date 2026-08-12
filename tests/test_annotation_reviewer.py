import json
from pathlib import Path
import pytest

from src import annotation_reviewer as ar


def make_sample_machine_file(path: Path):
    records = [
        {"resume_id": "r1", "page_number": 1, "line_number": 1, "line_index": 1, "text": "Header", "machine_suggested_heading": "Header", "machine_suggested_section": "summary", "machine_confidence": 0.9, "machine_review_required": False},
        {"resume_id": "r1", "page_number": 1, "line_number": 2, "line_index": 2, "text": "body line", "machine_suggested_heading": None, "machine_suggested_section": "other", "machine_confidence": 0.0, "machine_review_required": True},
        {"resume_id": "r2", "page_number": 1, "line_number": 1, "line_index": 3, "text": "Skills", "machine_suggested_heading": "Skills", "machine_suggested_section": "skills", "machine_confidence": 0.8, "machine_review_required": False},
    ]
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return records


def test_make_key_and_validation():
    rec = {"resume_id": "x", "page_number": 1, "line_number": 2, "line_index": 5}
    k = ar.make_key(rec)
    assert "x|p1|l2|i5" in k
    with pytest.raises(ValueError):
        ar.make_key({"resume_id": "x"})


def test_load_and_save_human_annotations(tmp_path):
    human_path = tmp_path / "human.jsonl"
    ann = {"_key": "k1", "resume_id": "r1", "page_number": 1, "line_number": 1, "line_index": 1, "is_heading": True, "section_label": "summary", "annotator_notes": "ok", "review_state": "annotated"}
    anns = {ann["_key"]: ann}
    ar.save_human_annotations(human_path, anns)
    loaded = ar.load_human_annotations(human_path)
    assert loaded["k1"]["section_label"] == "summary"


def test_queue_and_ordering(tmp_path):
    machine_file = tmp_path / "machine.jsonl"
    records = make_sample_machine_file(machine_file)
    loaded = ar.load_machine_records(machine_file)
    # no human annotations yet
    q = ar.generate_queue(loaded, {})
    # only records with machine_suggested_heading are candidates
    assert len(q) == 2
    # ordering groups by resume_id then page then line_index
    assert q[0]["resume_id"] == "r1"


def test_context_generation(tmp_path):
    machine_file = tmp_path / "machine.jsonl"
    records = make_sample_machine_file(machine_file)
    loaded = ar.load_machine_records(machine_file)
    # find index of second record
    idx = 1
    ctx = ar.get_context(loaded, idx, before=2, after=2)
    # candidate present
    assert any(m == "candidate" for m, _ in ctx)


def test_create_annotation_validation():
    rec = {"resume_id": "r1", "page_number": 1, "line_number": 1, "line_index": 1}
    ann = ar.create_annotation_from_machine(rec, True, "education", "note", "annotated")
    assert ann["is_heading"] is True
    with pytest.raises(ValueError):
        bad = {"resume_id": "r1"}
        ar.create_annotation_from_machine(bad, True, "education", "", "annotated")
