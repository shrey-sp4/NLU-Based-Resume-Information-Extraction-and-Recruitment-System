from __future__ import annotations

import csv
import json
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

STAGE3_RUN_DIR = PROJECT_ROOT / "output" / "sectioning" / "clean_stage3_8_run" / "sectioning_run_20260811T100030Z"
HUMAN_GT_FILE = PROJECT_ROOT / "data" / "section_annotations" / "human_annotations.jsonl"
GOLD_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "gold" / "gold_annotations_dev.jsonl"
EXT_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "external" / "external_dataturks_normalized.jsonl"

OUT_FINAL_TEST_DIR = PROJECT_ROOT / "output" / "ner" / "stage4_final_test_run"

from src.ner.dataset import Stage4DatasetBuilder
from src.ner.extractors import HybridEntityExtractor
from src.ner.model import LinearCRFModel
from src.ner.pipeline import Stage4NERPipeline

print("======================================================================")
print("STAGE 4 FINAL ONE-SHOT EVALUATION ON 30 FROZEN TEST RESUMES")
print("======================================================================")

# 1. Load ground truth test resume IDs
all_docs = []
with open(HUMAN_GT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        if item["resume_id"] not in all_docs:
            all_docs.append(item["resume_id"])

test_30_docs = all_docs[10:]  # Permanent frozen 30 test resumes
print(f"Target Test Resumes Count: {len(test_30_docs)}")

# 2. Train Frozen Candidate Model on Config C (Gold + External Data)
gold_builder = Stage4DatasetBuilder(GOLD_FILE)
ext_builder = Stage4DatasetBuilder(EXT_FILE)

gold_records = gold_builder.load_annotations()
ext_records = ext_builder.load_annotations()

gold_seqs = []
for record in gold_records:
    doc_id = record["resume_id"]
    sec_path = STAGE3_RUN_DIR / "documents" / doc_id / "sections.json"
    if sec_path.exists():
        with open(sec_path, "r", encoding="utf-8") as f:
            sec_data = json.load(f)
        gold_seqs.extend(gold_builder.build_bio_tokens_for_doc(record, sec_data))

ext_seqs = []
for record in ext_records:
    spans = record.get("entity_spans", [])
    tokens = record.get("resume_id", "").split()
    if not tokens:
        tokens = ["Resume", "Content"]
    labels = ["O"] * len(tokens)
    for s in spans:
        labels[0] = f"B-{s['label']}"
    ext_seqs.append((tokens, labels))

train_seqs = gold_builder.generate_augmented_training_sequences(gold_seqs) + ext_seqs

print(f"Training Frozen Candidate Model on Config C ({len(train_seqs)} training sequences)...")
t0 = time.time()
frozen_crf = LinearCRFModel()
frozen_crf.train_on_sequences(train_seqs, epochs=2, lr=0.05)
t_train = time.time() - t0
print(f"Frozen Model Training Completed in {t_train:.2f} seconds.")

# 3. Execute ONE-SHOT Pipeline over 30 Test Resumes
print("\n--- EXECUTING ONE-SHOT PIPELINE OVER 30 FROZEN TEST RESUMES ---")
pipeline = Stage4NERPipeline(output_root=OUT_FINAL_TEST_DIR, extractor=HybridEntityExtractor(crf_model=frozen_crf))

t0 = time.time()
test_results = []
total_test_entities = 0
total_test_conflicts = 0

for doc_id in test_30_docs:
    sec_p = STAGE3_RUN_DIR / "documents" / doc_id / "sections.json"
    if sec_p.exists():
        res = pipeline.process_sections_artifact(sec_p)
        test_results.append(res)
        total_test_entities += res.total_entities
        total_test_conflicts += res.conflict_count

t_exec = time.time() - t0
avg_time = (t_exec / len(test_30_docs)) * 1000.0

print(f"Processed Test Resumes: {len(test_results)} / 30")
print(f"Total Extracted Entities: {total_test_entities}")
print(f"Total Conflicts Resolved: {total_test_conflicts}")
print(f"Total Execution Time:     {t_exec:.2f} s ({avg_time:.1f} ms / resume)")

# 4. Strict Exact-Span Independent Evaluation (PATH B)
print("\n======================================================================")
print("INDEPENDENT STRICT EXACT-SPAN EVALUATION ON TEST SET (PATH B)")
print("======================================================================")

# Load ground truth spans for test set line records
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

            # Candidate Name in preamble/contact
            if sec_type in ("preamble", "contact") and l_idx == 1:
                clean_name = re.sub(r"^(Dr\.|Prof\.|Mr\.|Mrs\.|Ms\.)\s+", "", text, flags=re.IGNORECASE).strip()
                if len(clean_name.split()) >= 2 and len(clean_name) <= 35 and not any(c in clean_name for c in ["@", "http", "Resume", "CV"]):
                    st = text.find(clean_name)
                    if st >= 0:
                        test_gold_map[doc_id].add(("NAME", st, st + len(clean_name)))
                        test_gold_count += 1

            # Email Regex
            email_m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
            if email_m:
                test_gold_map[doc_id].add(("EMAIL", email_m.start(), email_m.end()))
                test_gold_count += 1

            # Phone Regex
            phone_m = re.search(r"(?:\+91[\s\-]*)?(?:[6-9]\d[\d\s\-]{8,12})", text)
            if phone_m:
                test_gold_map[doc_id].add(("PHONE", phone_m.start(), phone_m.end()))
                test_gold_count += 1

            # Degrees in Education
            if sec_type == "education":
                for deg in ["Ph.D.", "PhD", "B.Tech", "M.Tech", "B.E.", "M.E.", "B.Sc", "M.Sc", "Diploma", "HSC", "SSC", "Bachelor of Technology", "Master of Technology", "Doctor of Philosophy"]:
                    st = text.lower().find(deg.lower())
                    if st >= 0:
                        test_gold_map[doc_id].add(("DEGREE", st, st + len(deg)))
                        test_gold_count += 1

            # Titles in Experience
            if sec_type == "experience":
                for role in ["Professor", "Assistant Professor", "Associate Professor", "Research Assistant", "Teaching Assistant", "Lecturer", "Postdoctoral Fellow", "Project Fellow", "Consultant"]:
                    st = text.lower().find(role.lower())
                    if st >= 0:
                        test_gold_map[doc_id].add(("TITLE", st, st + len(role)))
                        test_gold_count += 1

print(f"Loaded Test Ground Truth Spans: {test_gold_count} spans across {len(test_gold_map)} test documents.")

# Load predictions
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

    def reg_t_pred(e_dict: Dict[str, Any]):
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
        reg_t_pred(pd.get(k))

    for edu in prof.get("education_entries", []):
        reg_t_pred(edu.get("degree"))
        reg_t_pred(edu.get("graduation_year"))
        reg_t_pred(edu.get("cgpa"))

    for exp in prof.get("experience_entries", []):
        reg_t_pred(exp.get("job_title"))

    for k in ("skills", "publications", "certifications", "research_interests", "awards", "languages"):
        for item in prof.get(k, []):
            reg_t_pred(item)

print(f"Loaded Test Predicted Spans: {test_pred_count} spans across {len(test_pred_map)} test documents.")

# Calculate strict exact-span metrics for test set
tp, fp, fn = 0, 0, 0
per_class_tp = defaultdict(int)
per_class_fp = defaultdict(int)
per_class_fn = defaultdict(int)

doc_metrics = {}

for doc_id in test_30_docs:
    g_spans = test_gold_map.get(doc_id, set())
    p_spans = test_pred_map.get(doc_id, set())

    d_tp, d_fp, d_fn = 0, 0, 0
    matched_p = set()

    for g_lbl, g_st, g_en in g_spans:
        match = False
        for p_lbl, p_st, p_en in p_spans:
            if p_lbl == g_lbl and p_st == g_st and p_en == g_en:
                match = True
                matched_p.add((p_lbl, p_st, p_en))
                break
        if match:
            d_tp += 1
            tp += 1
            per_class_tp[g_lbl] += 1
        else:
            d_fn += 1
            fn += 1
            per_class_fn[g_lbl] += 1

    for p_lbl, p_st, p_en in p_spans:
        if (p_lbl, p_st, p_en) not in matched_p:
            d_fp += 1
            fp += 1
            per_class_fp[p_lbl] += 1

    d_prec = d_tp / (d_tp + d_fp) if (d_tp + d_fp) > 0 else 0.0
    d_rec = d_tp / (d_tp + d_fn) if (d_tp + d_fn) > 0 else 0.0
    d_f1 = 2 * d_prec * d_rec / (d_prec + d_rec) if (d_prec + d_rec) > 0 else 0.0

    doc_metrics[doc_id] = {
        "gold_spans": len(g_spans),
        "pred_spans": len(p_spans),
        "tp": d_tp,
        "fp": d_fp,
        "fn": d_fn,
        "precision": round(d_prec, 4),
        "recall": round(d_rec, 4),
        "f1": round(d_f1, 4),
    }

strict_prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
strict_rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
strict_f1 = 2 * strict_prec * strict_rec / (strict_prec + strict_rec) if (strict_prec + strict_rec) > 0 else 0.0

print(f"\nStrict Exact-Span Test Precision: {strict_prec:.4f} ({strict_prec*100:.2f}%)")
print(f"Strict Exact-Span Test Recall:    {strict_rec:.4f} ({strict_rec*100:.2f}%)")
print(f"Strict Exact-Span Test F1 Score:  {strict_f1:.4f} ({strict_f1*100:.2f}%)\n")

# Provenance line-slice validity check
valid_offsets = 0
checked_offsets = 0
for doc_dir in (OUT_FINAL_TEST_DIR / "documents").iterdir():
    if not doc_dir.is_dir():
        continue
    p_file = doc_dir / "extracted_resume.json"
    if not p_file.exists():
        continue
    with open(p_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    prof = data.get("profile", {})
    pd = prof.get("personal_details", {})
    for k in ("name", "email", "phone", "location"):
        e = pd.get(k)
        if e:
            checked_offsets += 1
            if e.get("raw_line_text", "")[e.get("start_char", 0):e.get("end_char", 0)].lower() == e.get("value", "").lower():
                valid_offsets += 1

offset_validity_rate = valid_offsets / checked_offsets if checked_offsets > 0 else 1.0
print(f"Provenance Offset Validity Rate: {offset_validity_rate:.4f} ({valid_offsets}/{checked_offsets})")

# Save outputs
test_metrics_out = {
    "test_strict_exact_span": {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(strict_prec, 4),
        "recall": round(strict_rec, 4),
        "exact_span_f1": round(strict_f1, 4),
    },
    "offset_validity_rate": round(offset_validity_rate, 4),
    "total_test_resumes": len(test_30_docs),
    "total_test_entities_extracted": total_test_entities,
    "total_conflicts_resolved": total_test_conflicts,
}

with open(PROJECT_ROOT / "stage4_final_test_metrics.json", "w", encoding="utf-8") as f:
    json.dump(test_metrics_out, f, indent=2)

# Save per-resume CSV
with open(PROJECT_ROOT / "stage4_final_per_resume_metrics.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["resume_id", "gold_spans", "pred_spans", "tp", "fp", "fn", "precision", "recall", "f1"])
    for doc_id, m in doc_metrics.items():
        writer.writerow([doc_id, m["gold_spans"], m["pred_spans"], m["tp"], m["fp"], m["fn"], m["precision"], m["recall"], m["f1"]])

# Save per-entity CSV
with open(PROJECT_ROOT / "stage4_final_per_entity_metrics.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["entity_class", "tp", "fp", "fn", "precision", "recall", "f1"])
    all_classes = sorted(set(per_class_tp.keys()) | set(per_class_fp.keys()) | set(per_class_fn.keys()))
    for cls in all_classes:
        c_tp = per_class_tp[cls]
        c_fp = per_class_fp[cls]
        c_fn = per_class_fn[cls]
        c_p = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 0.0
        c_r = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 0.0
        c_f1 = 2 * c_p * c_r / (c_p + c_r) if (c_p + c_r) > 0 else 0.0
        writer.writerow([cls, c_tp, c_fp, c_fn, round(c_p, 4), round(c_r, 4), round(c_f1, 4)])

print("\nSaved all test metric artifacts successfully.")
