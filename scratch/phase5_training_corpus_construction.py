from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

STAGE3_RUN_DIR = PROJECT_ROOT / "output" / "sectioning" / "clean_stage3_8_run" / "sectioning_run_20260811T100030Z"
HUMAN_GT_FILE = PROJECT_ROOT / "data" / "section_annotations" / "human_annotations.jsonl"
GOLD_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "gold" / "gold_annotations_dev.jsonl"
SILVER_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "silver" / "dev22_silver_annotations.jsonl"
EXT_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "external" / "external_combined_normalized.jsonl"

print("======================================================================")
print("STAGE 4.5 PHASE 5 — TRAINING CORPUS CONSTRUCTION & LEAKAGE AUDIT")
print("======================================================================")

# Load test resume hashes
all_docs = []
with open(HUMAN_GT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        if item["resume_id"] not in all_docs:
            all_docs.append(item["resume_id"])

test_30_docs = set(all_docs[10:])
test_hashes: Set[str] = set()

for doc_id in test_30_docs:
    sec_p = STAGE3_RUN_DIR / "documents" / doc_id / "sections.json"
    if sec_p.exists():
        with open(sec_p, "r", encoding="utf-8") as f:
            data = json.load(f)
        for span in data.get("sections", []):
            for l_rec in span.get("lines", []):
                t_str = (l_rec.get("text") or "").strip().lower()
                if len(t_str) > 15:
                    test_hashes.add(hashlib.md5(t_str.encode("utf-8")).hexdigest())

print(f"Test Set Protection Filter: {len(test_hashes)} line text hashes active.")

def audit_file_leakage(file_path: Path) -> Tuple[int, int]:
    if not file_path.exists():
        return 0, 0
    total_recs = 0
    leak_cnt = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            total_recs += 1
            h = hashlib.md5(line.lower().encode("utf-8")).hexdigest()
            if h in test_hashes:
                leak_cnt += 1
    return total_recs, leak_cnt

gold_tot, gold_leak = audit_file_leakage(GOLD_FILE)
silver_tot, silver_leak = audit_file_leakage(SILVER_FILE)
ext_tot, ext_leak = audit_file_leakage(EXT_FILE)

print(f"\n--- TRAINING TIER INVENTORY & LEAKAGE AUDIT ---")
print(f"Tier 1 Gold Development Corpus:  {gold_tot} docs | Leakage: {gold_leak}")
print(f"Tier 2 Silver Pre-Training:      {silver_tot} docs | Leakage: {silver_leak}")
print(f"Tier 3 External Gold Corpus:     {ext_tot} docs | Leakage: {ext_leak}")
print(f"TOTAL COMBINED TRAINING SCALE:   {gold_tot + silver_tot + ext_tot} documents")

corpus_audit_res = {
    "tier_1_gold_docs": gold_tot,
    "tier_2_silver_docs": silver_tot,
    "tier_3_external_docs": ext_tot,
    "total_training_documents": gold_tot + silver_tot + ext_tot,
    "gold_leakage": gold_leak,
    "silver_leakage": silver_leak,
    "external_leakage": ext_leak,
    "zero_leakage_status": (gold_leak == 0 and silver_leak == 0 and ext_leak == 0)
}

with open(PROJECT_ROOT / "stage4_training_contamination_audit.json", "w", encoding="utf-8") as f:
    json.dump(corpus_audit_res, f, indent=2)

print("\nSaved contamination audit summary to 'stage4_training_contamination_audit.json'.")
