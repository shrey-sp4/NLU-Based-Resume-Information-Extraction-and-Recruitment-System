from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
EXT_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "external" / "external_dataturks_normalized.jsonl"
GOLD_FILE = PROJECT_ROOT / "data" / "entity_annotations" / "gold" / "gold_annotations_dev.jsonl"

print("======================================================================")
print("STAGE 4 LEARNED NER FAILURE ANALYSIS (DEV DATA ONLY)")
print("======================================================================")

# Ingest training stats for Category C classes
category_c_classes = ["NAME", "UNIV", "TITLE", "COMPANY", "PROJ", "PUB"]

class_stats = defaultdict(lambda: {
    "train_examples": 0,
    "unique_docs": set(),
    "lengths": [],
    "multi_token_count": 0,
})

# External DataTurks corpus
if EXT_FILE.exists():
    with open(EXT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            doc_id = rec["document_id"]
            for s in rec.get("entity_spans", []):
                lbl = s["label"]
                if lbl in category_c_classes:
                    txt = s["token_text"]
                    toks = txt.split()
                    class_stats[lbl]["train_examples"] += 1
                    class_stats[lbl]["unique_docs"].add(doc_id)
                    class_stats[lbl]["lengths"].append(len(toks))
                    if len(toks) > 1:
                        class_stats[lbl]["multi_token_count"] += 1

print(f"{'Class':<12} | {'Train Ex':<10} | {'Docs':<8} | {'Avg Tok Length':<15} | {'Multi-Token %'}")
print("-" * 65)

for cls in category_c_classes:
    st = class_stats[cls]
    ex = st["train_examples"]
    d_cnt = len(st["unique_docs"])
    avg_len = sum(st["lengths"]) / len(st["lengths"]) if st["lengths"] else 0.0
    mt_pct = (st["multi_token_count"] / ex) * 100.0 if ex > 0 else 0.0
    print(f"{cls:<12} | {ex:<10} | {d_cnt:<8} | {avg_len:<15.2f} | {mt_pct:.1f}%")

audit_c_out = {
    "category_c_stats": {
        cls: {
            "train_examples": class_stats[cls]["train_examples"],
            "unique_docs": len(class_stats[cls]["unique_docs"]),
            "avg_token_length": round(sum(class_stats[cls]["lengths"]) / len(class_stats[cls]["lengths"]), 2) if class_stats[cls]["lengths"] else 0.0,
            "multi_token_percentage": round((class_stats[cls]["multi_token_count"] / class_stats[cls]["train_examples"]) * 100.0, 1) if class_stats[cls]["train_examples"] > 0 else 0.0
        }
        for cls in category_c_classes
    }
}

with open(PROJECT_ROOT / "scratch" / "stage4_learned_ner_audit.json", "w", encoding="utf-8") as f:
    json.dump(audit_c_out, f, indent=2)

print("\nSaved learned NER audit summary to 'scratch/stage4_learned_ner_audit.json'.")
