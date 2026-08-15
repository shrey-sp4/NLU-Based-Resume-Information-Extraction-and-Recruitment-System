from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

print("======================================================================")
print("STAGE 4.5 PHASE 1 — REPOSITORY & DATA AUDIT")
print("======================================================================")

# 1. Audit Source Code Files in src/ner/
src_ner_dir = PROJECT_ROOT / "src" / "ner"
src_files = {}

for fpath in sorted(src_ner_dir.glob("*.py")):
    size = fpath.stat().st_size
    with open(fpath, "r", encoding="utf-8") as f:
        line_cnt = len(f.readlines())
    src_files[fpath.name] = {"lines": line_cnt, "size_bytes": size}

print("--- SOURCE CODE INVENTORY (src/ner/) ---")
for fname, meta in src_files.items():
    print(f"  {fname:<25}: {meta['lines']:<5} lines | {meta['size_bytes']:<8} bytes")

# 2. Audit Data Annotations in data/
data_dir = PROJECT_ROOT / "data"
data_files = {}

for root, _, files in os.walk(data_dir):
    for fn in files:
        if fn.endswith((".json", ".jsonl")):
            fp = Path(root) / fn
            rel_p = fp.relative_to(PROJECT_ROOT).as_posix()
            size = fp.stat().st_size
            line_cnt = 0
            if fn.endswith(".jsonl"):
                with open(fp, "r", encoding="utf-8") as f:
                    line_cnt = len(f.readlines())
            data_files[rel_p] = {"lines_or_records": line_cnt, "size_bytes": size}

print("\n--- DATASET INVENTORY (data/) ---")
for rel_p, meta in data_files.items():
    print(f"  {rel_p:<65}: {meta['lines_or_records']:<5} records | {meta['size_bytes']:<8} bytes")

# 3. Unit Tests Check
test_dir = PROJECT_ROOT / "tests"
test_files = [f.name for f in test_dir.glob("*.py")]
print(f"\n--- UNIT TESTS INVENTORY (tests/) ---")
print(f"  Total Test Files: {len(test_files)} -> {', '.join(test_files)}")

phase1_summary = {
    "src_files": src_files,
    "data_files": data_files,
    "test_files": test_files,
    "phase_status": "PHASE_1_COMPLETED"
}

with open(PROJECT_ROOT / "scratch" / "phase1_repository_audit.json", "w", encoding="utf-8") as f:
    json.dump(phase1_summary, f, indent=2)

print("\nSaved Phase 1 Audit Summary to 'scratch/phase1_repository_audit.json'.")
