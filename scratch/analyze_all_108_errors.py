import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from scratch.evaluate_stage3_ground_truth import evaluate

results = evaluate()
errors = results["errors"]

print("\n======================================================================")
print(f"DETAILED FORENSIC AUDIT OF ALL {len(errors)} ERRORS")
print("======================================================================")

fp_list = [e for e in errors if e["type"] == "FALSE_POSITIVE_HEADING"]
fn_list = [e for e in errors if e["type"] == "FALSE_NEGATIVE_HEADING"]
cls_list = [e for e in errors if e["type"] == "CLASSIFICATION_MISMATCH"]

print(f"\n--- FALSE POSITIVE HEADINGS ({len(fp_list)} cases) ---")
for idx, e in enumerate(fp_list, start=1):
    print(f"  [{idx:02d}] Doc: {e['doc_id']} | Line {e['page']}:{e['line']} | Text: {repr(e['text'])}")

print(f"\n--- FALSE NEGATIVE HEADINGS ({len(fn_list)} cases) ---")
for idx, e in enumerate(fn_list, start=1):
    print(f"  [{idx:02d}] Doc: {e['doc_id']} | Line {e['page']}:{e['line']} | GT Label: {e['gt_label']} | Text: {repr(e['text'])}")

print(f"\n--- CLASSIFICATION MISMATCHES ({len(cls_list)} cases) ---")
for idx, e in enumerate(cls_list, start=1):
    print(f"  [{idx:02d}] Doc: {e['doc_id']} | Line {e['page']}:{e['line']} | GT: {e['gt_label']} vs Pred: {e['pred_label']} | Text: {repr(e['text'])}")
