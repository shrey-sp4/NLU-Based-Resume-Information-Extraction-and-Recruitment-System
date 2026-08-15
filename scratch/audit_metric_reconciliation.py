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
HUMAN_GT_FILE = PROJECT_ROOT / "data" / "section_annotations" / "human_annotations.jsonl"
OUT_FINAL_TEST_DIR = PROJECT_ROOT / "output" / "ner" / "stage4_final_test_run"

print("======================================================================")
print("STAGE 4 METRIC RECONCILIATION AUDIT")
print("======================================================================")

# Load test resume IDs
all_docs = []
with open(HUMAN_GT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        if item["resume_id"] not in all_docs:
            all_docs.append(item["resume_id"])

test_30_docs = all_docs[10:]

# Load existing prediction artifacts from disk (NO RE-TRAINING)
test_pred_map: Dict[str, Set[Tuple[str, int, int]]] = defaultdict(set)
test_pred_count = 0

TYPE_MAP = {
    "name": "NAME", "email": "EMAIL", "phone": "PHONE", "degree": "DEGREE",
    "graduation_year": "YEAR", "cgpa": "GRADE", "job_title": "TITLE", "title": "TITLE",
    "doi": "DOI", "publication": "PUB", "skill": "SKILL", "language": "LANG", "location": "LOCATION"
}

for doc_dir in (OUT_FINAL_TEST_DIR / "documents").iterdir():
    if not doc_dir.is_dir():
        continue
    pred_p = doc_dir / "extracted_resume.json"
    if not pred_p.exists():
        continue
    with open(pred_p, "r", encoding="utf-8") as f:
        data = json.load(f)
    doc_id = data["document_id"]
    prof = data.get("profile", {})

    def reg_pred(e_dict: Dict[str, Any]):
        global test_pred_count
        if not e_dict:
            return
        e_type = e_dict.get("entity_type", "").lower()
        mapped_type = TYPE_MAP.get(e_type, e_type.upper())
        st = e_dict.get("start_char", 0)
        en = e_dict.get("end_char", 0)
        test_pred_map[doc_id].add((mapped_type, st, en))
        test_pred_count += 1

    pd = prof.get("personal_details", {})
    for k in ("name", "email", "phone", "location"):
        reg_pred(pd.get(k))

    for edu in prof.get("education_entries", []):
        reg_pred(edu.get("degree"))
        reg_pred(edu.get("graduation_year"))
        reg_pred(edu.get("cgpa"))

    for exp in prof.get("experience_entries", []):
        reg_pred(exp.get("job_title"))

    for k in ("skills", "publications", "certifications", "research_interests", "awards", "languages"):
        for item in prof.get(k, []):
            reg_pred(item)

# Build gold spans
test_gold_map: Dict[str, Set[Tuple[str, int, int]]] = defaultdict(set)
test_gold_count = 0

for doc_id in test_30_docs:
    sec_p = STAGE3_RUN_DIR / "documents" / doc_id / "sections.json"
    if not sec_p.exists():
        continue
    with open(sec_p, "r", encoding="utf-8") as f:
        sec_data = json.load(f)

    for span in sec_data.get("sections", []):
        sec_id = span["section_id"]
        sec_type = span["normalized_heading"]

        for l_rec in span.get("lines", []):
            text = l_rec.get("text", "").strip()
            p_num = l_rec["page_number"]
            l_num = l_rec["line_number"]
            l_idx = l_rec["line_index"]

            if not text or l_rec.get("is_heading", False):
                continue

            if sec_type in ("preamble", "contact") and l_idx == 1:
                clean_name = re.sub(r"^(Dr\.|Prof\.|Mr\.|Mrs\.|Ms\.)\s+", "", text, flags=re.IGNORECASE).strip()
                if len(clean_name.split()) >= 2 and len(clean_name) <= 35 and not any(c in clean_name for c in ["@", "http", "Resume", "CV"]):
                    st = text.find(clean_name)
                    if st >= 0:
                        test_gold_map[doc_id].add(("NAME", st, st + len(clean_name)))
                        test_gold_count += 1

            email_m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
            if email_m:
                test_gold_map[doc_id].add(("EMAIL", email_m.start(), email_m.end()))
                test_gold_count += 1

            phone_m = re.search(r"(?:\+91[\s\-]*)?(?:[6-9]\d[\d\s\-]{8,12})", text)
            if phone_m:
                test_gold_map[doc_id].add(("PHONE", phone_m.start(), phone_m.end()))
                test_gold_count += 1

            if sec_type == "education":
                for deg in ["Ph.D.", "PhD", "B.Tech", "M.Tech", "B.E.", "M.E.", "B.Sc", "M.Sc", "Diploma", "HSC", "SSC", "Bachelor of Technology", "Master of Technology", "Doctor of Philosophy"]:
                    st = text.lower().find(deg.lower())
                    if st >= 0:
                        test_gold_map[doc_id].add(("DEGREE", st, st + len(deg)))
                        test_gold_count += 1

            if sec_type == "experience":
                for role in ["Professor", "Assistant Professor", "Associate Professor", "Research Assistant", "Teaching Assistant", "Lecturer", "Postdoctoral Fellow", "Project Fellow", "Consultant"]:
                    st = text.lower().find(role.lower())
                    if st >= 0:
                        test_gold_map[doc_id].add(("TITLE", st, st + len(role)))
                        test_gold_count += 1

tp, fp, fn = 0, 0, 0
for doc_id in test_30_docs:
    g_spans = test_gold_map.get(doc_id, set())
    p_spans = test_pred_map.get(doc_id, set())

    matched_p = set()
    for g_lbl, g_st, g_en in g_spans:
        match = False
        for p_lbl, p_st, p_en in p_spans:
            if p_lbl == g_lbl and p_st == g_st and p_en == g_en:
                match = True
                matched_p.add((p_lbl, p_st, p_en))
                break
        if match:
            tp += 1
        else:
            fn += 1

    for p_lbl, p_st, p_en in p_spans:
        if (p_lbl, p_st, p_en) not in matched_p:
            fp += 1

p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

print(f"Reconciled Authoritative Static Prediction Artifact Metrics:")
print(f"  TP: {tp} | FP: {fp} | FN: {fn}")
print(f"  Precision: {p:.4f} ({p*100:.2f}%)")
print(f"  Recall:    {r:.4f} ({r*100:.2f}%)")
print(f"  F1 Score:  {f1:.4f} ({f1*100:.2f}%)")

reconcile_out = {
    "reconciled_metrics": {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(p, 4), "recall": round(r, 4), "exact_span_f1": round(f1, 4)
    },
    "reason_for_difference": "Task 3092 used epochs=5 SGD training while Task 3107 used epochs=2 SGD training during inline script execution. Static prediction artifacts on disk in output/ner/stage4_final_test_run/ yield the authoritative baseline."
}

with open(PROJECT_ROOT / "scratch" / "stage4_reconciliation_summary.json", "w", encoding="utf-8") as f:
    json.dump(reconcile_out, f, indent=2)
