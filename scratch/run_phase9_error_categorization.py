from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

STAGE3_RUN_DIR = PROJECT_ROOT / "output" / "sectioning" / "clean_stage3_8_run" / "sectioning_run_20260811T100030Z"
GOLD_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "gold" / "gold_annotations_dev.jsonl"
OUT_PHASE8_DIR = PROJECT_ROOT / "output" / "ner" / "stage45_p8_config_g"

print("======================================================================")
print("STAGE 4.5 PHASE 9 — BASELINE REPRODUCTION & ERROR CATEGORIZATION")
print("======================================================================")

# Load gold development records
gold_records = []
with open(GOLD_FILE, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            gold_records.append(json.loads(line))

dev_22_docs = [a["resume_id"] for a in gold_records]

# Build gold map
gold_map: Dict[str, Set[Tuple[str, int, int]]] = defaultdict(set)
gold_span_counts = defaultdict(int)

for rec in gold_records:
    doc_id = rec["resume_id"]
    for s in rec.get("entity_spans", []):
        lbl = s["label"]
        st = s["start_char"]
        en = s["end_char"]
        gold_map[doc_id].add((lbl, st, en))
        gold_span_counts[lbl] += 1

# Load prediction map from OUT_PHASE8_DIR
pred_map: Dict[str, Set[Tuple[str, int, int]]] = defaultdict(set)
pred_span_counts = defaultdict(int)

TYPE_MAP = {
    "name": "NAME", "email": "EMAIL", "phone": "PHONE", "degree": "DEGREE",
    "graduation_year": "YEAR", "cgpa": "GRADE", "job_title": "TITLE", "title": "TITLE",
    "doi": "DOI", "publication": "PUB", "skill": "SKILL", "language": "LANG", "location": "LOCATION",
    "university": "UNIV", "company": "COMPANY"
}

for doc_dir in (OUT_PHASE8_DIR / "documents").iterdir():
    if not doc_dir.is_dir():
        continue
    pred_p = doc_dir / "extracted_resume.json"
    if not pred_p.exists():
        continue
    with open(pred_p, "r", encoding="utf-8") as f:
        data = json.load(f)
    doc_id = data["document_id"]
    prof = data.get("profile", {})

    def reg_p(e_dict: Dict[str, Any]):
        if not e_dict:
            return
        e_type = e_dict.get("entity_type", "").lower()
        mapped_type = TYPE_MAP.get(e_type, e_type.upper())
        st = e_dict.get("start_char", 0)
        en = e_dict.get("end_char", 0)
        pred_map[doc_id].add((mapped_type, st, en))
        pred_span_counts[mapped_type] += 1

    pd = prof.get("personal_details", {})
    for k in ("name", "email", "phone", "location"):
        reg_p(pd.get(k))

    for edu in prof.get("education_entries", []):
        reg_p(edu.get("degree"))
        reg_p(edu.get("graduation_year"))
        reg_p(edu.get("cgpa"))

    for exp in prof.get("experience_entries", []):
        reg_p(exp.get("job_title"))

    for k in ("skills", "publications", "certifications", "research_interests", "awards", "languages"):
        for item in prof.get(k, []):
            reg_p(item)

# Calculate exact-span metrics and categorize errors
tp, fp, fn = 0, 0, 0
error_categories = {
    "incorrect_entity_type": 0,
    "incorrect_start_boundary": 0,
    "incorrect_end_boundary": 0,
    "partial_span_match": 0,
    "missed_entity": 0,
    "duplicate_entity": 0,
    "section_context_error": 0,
    "unannotated_gold_skill": 0,
    "unannotated_gold_doi": 0,
}

for doc_id in dev_22_docs:
    g_spans = gold_map.get(doc_id, set())
    p_spans = pred_map.get(doc_id, set())

    matched_p = set()
    for g_lbl, g_st, g_en in g_spans:
        match = False
        for p_lbl, p_st, p_en in p_spans:
            if p_lbl == g_lbl and p_st == g_st and p_en == g_en:
                match = True
                matched_p.add((p_lbl, p_st, p_en))
                break
            elif p_lbl == g_lbl and not (p_en <= g_st or p_st >= g_en):
                error_categories["partial_span_match"] += 1
            elif p_lbl != g_lbl and (p_st == g_st or p_en == g_en):
                error_categories["incorrect_entity_type"] += 1

        if match:
            tp += 1
        else:
            fn += 1
            error_categories["missed_entity"] += 1

    for p_lbl, p_st, p_en in p_spans:
        if (p_lbl, p_st, p_en) not in matched_p:
            fp += 1
            if p_lbl == "SKILL":
                error_categories["unannotated_gold_skill"] += 1
            elif p_lbl == "DOI":
                error_categories["unannotated_gold_doi"] += 1

prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

print(f"Reproduced Authoritative Baseline Metrics:")
print(f"  TP: {tp} | FP: {fp} | FN: {fn}")
print(f"  Strict Precision: {prec:.4f} ({prec*100:.2f}%)")
print(f"  Strict Recall:    {rec:.4f} ({rec*100:.2f}%)")
print(f"  Strict F1 Score:  {f1:.4f} ({f1*100:.2f}%)\n")

print("--- ERROR CATEGORIZATION BREAKDOWN ---")
for cat, cnt in sorted(error_categories.items(), key=lambda x: -x[1]):
    print(f"  {cat:<30}: {cnt} error occurrences")

cat_out = {
    "authoritative_baseline": {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(prec, 4), "recall": round(rec, 4), "exact_span_f1": round(f1, 4)
    },
    "error_categorization": error_categories
}

with open(PROJECT_ROOT / "scratch" / "stage4_phase9_error_categorization.json", "w", encoding="utf-8") as f:
    json.dump(cat_out, f, indent=2)

print("\nSaved error categorization summary to 'scratch/stage4_phase9_error_categorization.json'.")
