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

GOLD_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "gold" / "gold_annotations_dev.jsonl"
SILVER_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "silver" / "dev22_silver_annotations.jsonl"
EXT_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "external" / "external_dataturks_normalized.jsonl"

gold_builder = Stage4DatasetBuilder(GOLD_FILE)
silver_builder = Stage4DatasetBuilder(SILVER_FILE)
ext_builder = Stage4DatasetBuilder(EXT_FILE)

gold_records = gold_builder.load_annotations()
silver_records = silver_builder.load_annotations()
ext_records = ext_builder.load_annotations()

dev_22_docs = [a["resume_id"] for a in gold_records]

print("======================================================================")
print("STAGE 4 EXPANDED DATASET & MODEL GENERALIZATION EXPERIMENTS")
print("======================================================================")

# Build training sequences for each configuration
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

ext_seqs = []
for record in ext_records:
    spans = record.get("entity_spans", [])
    tokens = record.get("resume_id", "").split()
    if not tokens:
        tokens = ["Resume", "Content"]
    labels = ["O"] * len(tokens)
    for s in spans:
        t_label = s["label"]
        labels[0] = f"B-{t_label}"
    ext_seqs.append((tokens, labels))

aug_gold = gold_builder.generate_augmented_training_sequences(gold_seqs)

configs = {
    "Config A (Gold Data Only)": aug_gold,
    "Config B (External Data Only)": ext_seqs,
    "Config C (Gold + External Data)": aug_gold + ext_seqs,
    "Config D (Gold + External + Silver Pre-Training)": aug_gold + ext_seqs + silver_seqs,
}

print(f"Data Scale: Gold={len(aug_gold)} seqs, External={len(ext_seqs)} seqs, Silver={len(silver_seqs)} seqs.\n")

results = {}

for name, train_seqs in configs.items():
    t0 = time.time()
    model = LinearCRFModel()
    model.train_on_sequences(train_seqs, epochs=1, lr=0.05)
    t_train = time.time() - t0

    extractor = HybridEntityExtractor(crf_model=model)
    out_dir = PROJECT_ROOT / "output" / "ner" / f"stage4_exp_{name.split()[1].lower()}_run"
    pipeline = Stage4NERPipeline(output_root=out_dir, extractor=extractor)

    total_ents = 0
    total_conflicts = 0
    for doc_id in dev_22_docs:
        sec_p = STAGE3_RUN_DIR / "documents" / doc_id / "sections.json"
        if sec_p.exists():
            res = pipeline.process_sections_artifact(sec_p)
            total_ents += res.total_entities
            total_conflicts += res.conflict_count

    val_res = validate_stage4_run(out_dir)
    results[name] = {
        "train_time_sec": round(t_train, 2),
        "total_extracted_entities": total_ents,
        "total_conflicts_resolved": total_conflicts,
        "offset_validity_rate": val_res["offset_validity_rate"],
        "path_match": val_res["total_processed"] == len(dev_22_docs),
    }

print("\n======================================================================")
print("STAGE 4 EXPANDED CONFIGURATION RESULTS SUMMARY")
print("======================================================================")
for cfg_name, metrics in results.items():
    print(f"[{cfg_name}]")
    print(f"  Train Time: {metrics['train_time_sec']} s | Extracted Entities: {metrics['total_extracted_entities']} | Conflicts: {metrics['total_conflicts_resolved']}")
    print(f"  Offset Validity Rate: {metrics['offset_validity_rate']:.4f} | PATH A == PATH B: {metrics['path_match']}\n")

# Save machine-readable JSON summary
with open(PROJECT_ROOT / "scratch" / "stage4_data_expansion_metrics.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("Saved metrics summary to 'scratch/stage4_data_expansion_metrics.json'.")
