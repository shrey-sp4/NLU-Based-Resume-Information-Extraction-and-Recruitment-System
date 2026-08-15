from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

ANNOTATIONS_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "gold" / "gold_annotations_dev.jsonl"
PREDICTIONS_DIR = PROJECT_ROOT / "output" / "ner" / "stage4_dev22_run" / "documents"

print("======================================================================")
print("INDEPENDENT STAGE 4 METRIC & EXACT-SPAN EVALUATOR")
print("======================================================================")

# 1. Load Gold Ground Truth Spans
gold_map: Dict[str, Set[Tuple[str, int, int]]] = defaultdict(set)
gold_type_map: Dict[str, Set[Tuple[str, str, int, int]]] = defaultdict(set)
gold_count = 0

with open(ANNOTATIONS_FILE, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        record = json.loads(line)
        doc_id = record["resume_id"]
        for s in record.get("entity_spans", []):
            label = s["label"].upper()
            st = s["start_char"]
            en = s["end_char"]
            p_num = s["page_number"]
            l_num = s["line_number"]

            gold_map[doc_id].add((label, st, en))
            gold_type_map[doc_id].add((label, p_num, l_num, st, en))
            gold_count += 1

print(f"Loaded Gold Ground Truth Spans: {gold_count} spans across {len(gold_map)} documents.")

# 2. Load Pipeline Extracted Entity Predictions
pred_map: Dict[str, Set[Tuple[str, int, int]]] = defaultdict(set)
pred_type_map: Dict[str, Set[Tuple[str, str, int, int]]] = defaultdict(set)
pred_count = 0

# Mapping pipeline entity types to gold annotation label types
TYPE_MAP = {
    "name": "NAME",
    "email": "EMAIL",
    "phone": "PHONE",
    "degree": "DEGREE",
    "graduation_year": "YEAR",
    "cgpa": "GRADE",
    "job_title": "TITLE",
    "title": "TITLE",
    "doi": "DOI",
    "publication": "PUB",
    "skill": "SKILL",
    "language": "LANG",
    "location": "LOCATION",
}

for doc_dir in PREDICTIONS_DIR.iterdir():
    if not doc_dir.is_dir():
        continue
    pred_path = doc_dir / "extracted_resume.json"
    if not pred_path.exists():
        continue

    with open(pred_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc_id = data["document_id"]
    prof = data.get("profile", {})

    # Helper to register prediction
    def reg_pred(e_dict: Dict[str, Any]):
        global pred_count
        if not e_dict:
            return
        e_type = e_dict.get("entity_type", "").lower()
        mapped_type = TYPE_MAP.get(e_type, e_type.upper())
        st = e_dict.get("start_char", 0)
        en = e_dict.get("end_char", 0)
        p_num = e_dict.get("page_number", 1)
        l_num = e_dict.get("line_number", 1)

        pred_map[doc_id].add((mapped_type, st, en))
        pred_type_map[doc_id].add((mapped_type, p_num, l_num, st, en))
        pred_count += 1

    # Personal details
    pd = prof.get("personal_details", {})
    for k in ("name", "email", "phone", "location"):
        reg_pred(pd.get(k))

    # Education degrees/cgpa
    for edu in prof.get("education_entries", []):
        reg_pred(edu.get("degree"))
        reg_pred(edu.get("graduation_year"))
        reg_pred(edu.get("cgpa"))

    # Experience titles
    for exp in prof.get("experience_entries", []):
        reg_pred(exp.get("job_title"))

    # Skills, Publications, etc.
    for k in ("skills", "publications", "certifications", "research_interests", "awards", "languages"):
        for item in prof.get(k, []):
            reg_pred(item)

print(f"Loaded Predicted Extracted Spans: {pred_count} spans across {len(pred_map)} documents.")

# 3. Calculate Strict Exact-Span Metrics
tp, fp, fn = 0, 0, 0
per_class_tp = defaultdict(int)
per_class_fp = defaultdict(int)
per_class_fn = defaultdict(int)

for doc_id, g_spans in gold_map.items():
    p_spans = pred_map.get(doc_id, set())

    matched_p = set()
    for g_lbl, g_st, g_en in g_spans:
        match_found = False
        for p_lbl, p_st, p_en in p_spans:
            if p_lbl == g_lbl and p_st == g_st and p_en == g_en:
                match_found = True
                matched_p.add((p_lbl, p_st, p_en))
                break

        if match_found:
            tp += 1
            per_class_tp[g_lbl] += 1
        else:
            fn += 1
            per_class_fn[g_lbl] += 1

    for p_lbl, p_st, p_en in p_spans:
        if (p_lbl, p_st, p_en) not in matched_p:
            fp += 1
            per_class_fp[p_lbl] += 1

strict_prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
strict_rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
strict_f1 = 2 * strict_prec * strict_rec / (strict_prec + strict_rec) if (strict_prec + strict_rec) > 0 else 0.0

print("\n======================================================================")
print("INDEPENDENT STRICT EXACT-SPAN EVALUATION RESULTS")
print("======================================================================")
print(f"True Positives (TP):  {tp}")
print(f"False Positives (FP): {fp}")
print(f"False Negatives (FN): {fn}")
print(f"Strict Precision:    {strict_prec:.4f} ({strict_prec*100:.2f}%)")
print(f"Strict Recall:       {strict_rec:.4f} ({strict_rec*100:.2f}%)")
print(f"Strict Exact-Span F1:{strict_f1:.4f} ({strict_f1*100:.2f}%)")

print("\n--- PER-ENTITY CLASS METRICS ---")
all_classes = sorted(set(per_class_tp.keys()) | set(per_class_fp.keys()) | set(per_class_fn.keys()))
for cls in all_classes:
    c_tp = per_class_tp[cls]
    c_fp = per_class_fp[cls]
    c_fn = per_class_fn[cls]
    c_p = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 0.0
    c_r = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 0.0
    c_f1 = 2 * c_p * c_r / (c_p + c_r) if (c_p + c_r) > 0 else 0.0
    print(f"  {cls:<12}: TP={c_tp:<3} | FP={c_fp:<3} | FN={c_fn:<3} | P={c_p:.4f} | R={c_r:.4f} | F1={c_f1:.4f}")

# Save raw evaluation json artifact
eval_out = {
    "strict_exact_span": {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(strict_prec, 4),
        "recall": round(strict_rec, 4),
        "exact_span_f1": round(strict_f1, 4),
    },
    "per_class": {
        cls: {
            "tp": per_class_tp[cls],
            "fp": per_class_fp[cls],
            "fn": per_class_fn[cls],
            "precision": round(per_class_tp[cls] / (per_class_tp[cls] + per_class_fp[cls]), 4) if (per_class_tp[cls] + per_class_fp[cls]) > 0 else 0.0,
            "recall": round(per_class_tp[cls] / (per_class_tp[cls] + per_class_fn[cls]), 4) if (per_class_tp[cls] + per_class_fn[cls]) > 0 else 0.0,
        }
        for cls in all_classes
    }
}

with open(PROJECT_ROOT / "scratch" / "independent_stage4_metrics_out.json", "w", encoding="utf-8") as f:
    json.dump(eval_out, f, indent=2)

print("\nSaved independent metrics to 'scratch/independent_stage4_metrics_out.json'.")
