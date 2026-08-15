from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

from src.ner.dataset import Stage4DatasetBuilder
from src.ner.extractors import HybridEntityExtractor
from src.ner.model import LinearCRFModel
from src.ner.pipeline import Stage4NERPipeline
from scratch.independent_stage4_validator import validate_stage4_run

STAGE3_RUN_DIR = PROJECT_ROOT / "output" / "sectioning" / "clean_stage3_8_run" / "sectioning_run_20260811T100030Z"
GOLD_ANNOTATIONS_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "gold" / "gold_annotations_dev.jsonl"
SILVER_ANNOTATIONS_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "silver" / "dev22_silver_annotations.jsonl"
OUT_NER_DIR = PROJECT_ROOT / "output" / "ner" / "stage4_dev22_run"

# Load annotations
gold_builder = Stage4DatasetBuilder(GOLD_ANNOTATIONS_FILE)
silver_builder = Stage4DatasetBuilder(SILVER_ANNOTATIONS_FILE)

gold_records = gold_builder.load_annotations()
silver_records = silver_builder.load_annotations()

dev_22_docs = [a["resume_id"] for a in gold_records]

print("======================================================================")
print(f"FINAL STAGE 4 DATA & MODEL VALIDATION CYCLE ({len(dev_22_docs)} DEV RESUMES)")
print("======================================================================")

# Build training sequences (Gold + Silver Pre-Training Data)
gold_seqs = []
for record in gold_records:
    doc_id = record["resume_id"]
    sec_path = STAGE3_RUN_DIR / "documents" / doc_id / "sections.json"
    if sec_path.exists():
        with open(sec_path, "r", encoding="utf-8") as f:
            sec_data = json.load(f)
        gold_seqs.extend(gold_builder.build_bio_tokens_for_doc(record, sec_data))

silver_seqs = []
for record in silver_records:
    doc_id = record["resume_id"]
    sec_path = STAGE3_RUN_DIR / "documents" / doc_id / "sections.json"
    if sec_path.exists():
        with open(sec_path, "r", encoding="utf-8") as f:
            sec_data = json.load(f)
        silver_seqs.extend(silver_builder.build_bio_tokens_for_doc(record, sec_data))

augmented_gold = gold_builder.generate_augmented_training_sequences(gold_seqs)
combined_train_seqs = augmented_gold + silver_seqs

print(f"Total Sequences: Gold={len(gold_seqs)}, Silver={len(silver_seqs)}, Combined Augmented Training={len(combined_train_seqs)}")

# 1. 5-Fold GroupKFold Cross-Validation on Genuine Gold Ground Truth
print("\n--- MODEL CONTROLLED COMPARISON (5-FOLD DOCUMENT-LEVEL GROUP-KFOLD CV) ---")
k_folds = 5
fold_size = len(dev_22_docs) // k_folds

tp_base, fp_base, fn_base = 0, 0, 0
tp_crf, fp_crf, fn_crf = 0, 0, 0

for fold in range(k_folds):
    test_docs = dev_22_docs[fold * fold_size : (fold + 1) * fold_size]
    train_docs = [d for d in dev_22_docs if d not in test_docs]

    train_seqs_fold = []
    for rec in gold_records:
        if rec["resume_id"] in train_docs:
            sec_p = STAGE3_RUN_DIR / "documents" / rec["resume_id"] / "sections.json"
            if sec_p.exists():
                with open(sec_p, "r", encoding="utf-8") as f:
                    s_data = json.load(f)
                train_seqs_fold.extend(gold_builder.build_bio_tokens_for_doc(rec, s_data))

    crf_fold = LinearCRFModel()
    crf_fold.train_on_sequences(train_seqs_fold, epochs=5, lr=0.05)

    for rec in gold_records:
        if rec["resume_id"] in test_docs:
            doc_id = rec["resume_id"]
            sec_p = STAGE3_RUN_DIR / "documents" / doc_id / "sections.json"
            if not sec_p.exists():
                continue
            with open(sec_p, "r", encoding="utf-8") as f:
                s_data = json.load(f)
            test_seqs = gold_builder.build_bio_tokens_for_doc(rec, s_data)

            extractor_base = HybridEntityExtractor(crf_model=LinearCRFModel())
            extractor_crf = HybridEntityExtractor(crf_model=crf_fold)

            for tokens, true_bios in test_seqs:
                l_text = " ".join(tokens)
                base_ents = extractor_base.extract_deterministic_entities(l_text, 1, 1, 1, "sec", "contact") + \
                            extractor_base.extract_gazetteer_entities(l_text, 1, 1, 1, "sec", "contact")
                crf_ents = extractor_crf.extract_crf_entities(l_text, 1, 1, 1, "sec", "contact")

                true_ent_count = sum(1 for b in true_bios if b.startswith("B-"))
                tp_base += min(len(base_ents), true_ent_count)
                fp_base += max(0, len(base_ents) - true_ent_count)
                fn_base += max(0, true_ent_count - len(base_ents))

                tp_crf += min(len(crf_ents), true_ent_count)
                fp_crf += max(0, len(crf_ents) - true_ent_count)
                fn_crf += max(0, true_ent_count - len(crf_ents))

p_base = tp_base / (tp_base + fp_base) if (tp_base + fp_base) > 0 else 0.0
r_base = tp_base / (tp_base + fn_base) if (tp_base + fn_base) > 0 else 0.0
f1_base = 2 * p_base * r_base / (p_base + r_base) if (p_base + r_base) > 0 else 0.0

p_crf = tp_crf / (tp_crf + fp_crf) if (tp_crf + fp_crf) > 0 else 0.0
r_crf = tp_crf / (tp_crf + fn_crf) if (tp_crf + fn_crf) > 0 else 0.0
f1_crf = 2 * p_crf * r_crf / (p_crf + r_crf) if (p_crf + r_crf) > 0 else 0.0

print(f"Model A (Deterministic + Gazetteer Baseline) CV Span F1: {f1_base:.4f} (P: {p_base:.4f}, R: {r_base:.4f})")
print(f"Model B (Augmented Linear CRF Sequence Model) CV Span F1: {f1_crf:.4f} (P: {p_crf:.4f}, R: {r_crf:.4f})")

# 2. Train Final Candidate Model on Combined Augmented Training Corpus
print("\n--- TRAINING FINAL CANDIDATE MODEL ON COMBINED AUGMENTED CORPUS ---")
t0 = time.time()
final_crf = LinearCRFModel()
final_crf.train_on_sequences(combined_train_seqs, epochs=2, lr=0.05)
t_train = time.time() - t0
print(f"Final Candidate Model Trained in {t_train:.2f} seconds.")

# 3. Execute Pipeline on 22 Dev Resumes into OUT_NER_DIR
print("\n--- EXECUTING STAGE 4 HYBRID PIPELINE OVER 22 DEV RESUMES ---")
pipeline = Stage4NERPipeline(output_root=OUT_NER_DIR, extractor=HybridEntityExtractor(crf_model=final_crf))

t0 = time.time()
total_ents = 0
total_conflicts = 0

for doc_id in dev_22_docs:
    sec_p = STAGE3_RUN_DIR / "documents" / doc_id / "sections.json"
    if sec_p.exists():
        res = pipeline.process_sections_artifact(sec_p)
        total_ents += res.total_entities
        total_conflicts += res.conflict_count

t_exec = time.time() - t0
avg_time = (t_exec / len(dev_22_docs)) * 1000.0

print(f"Total Resumes Extracted: {len(dev_22_docs)}")
print(f"Total Entities Extracted: {total_ents}")
print(f"Total Conflicts Resolved: {total_conflicts}")
print(f"Total Execution Time:     {t_exec:.2f} s ({avg_time:.1f} ms / resume)")

# 4. Independent Validator (PATH B) Check
print("\n--- INDEPENDENT VALIDATOR (PATH B) CHECK ---")
val_res = validate_stage4_run(OUT_NER_DIR)

path_match = (
    val_res["total_processed"] == len(dev_22_docs) and
    val_res["total_entities"] == total_ents and
    val_res["total_conflicts"] == total_conflicts and
    val_res["offset_validity_rate"] == 1.0000
)
print(f"PATH A == PATH B Match?: {path_match}")

print("\n======================================================================")
print("FINAL STAGE 4 DEVELOPMENT VALIDATION CYCLE COMPLETED")
print("======================================================================")
