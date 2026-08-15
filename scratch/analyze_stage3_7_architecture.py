import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

with open(PROJECT_ROOT / "scratch" / "stage3_5_eval_results.json", "r", encoding="utf-8") as f:
    eval_data = json.load(f)

dev_errors = eval_data["dev_10"]["errors"]
heldout_errors = eval_data["heldout_30"]["errors"]

print("======================================================================")
print("STAGE 3.7 ARCHITECTURAL EVIDENCE & FAILURE TAXONOMY AUDIT")
print("======================================================================")

print(f"\n1. ERROR COUNTS BY PARTITION:")
print(f"  Dev Set (10 Resumes):")
print(f"    - TP: {eval_data['dev_10']['tp']} | FP: {eval_data['dev_10']['fp']} | FN: {eval_data['dev_10']['fn']} | TN: {eval_data['dev_10']['tn']}")
print(f"    - Heading Precision: {eval_data['dev_10']['precision']:.4f} | Recall: {eval_data['dev_10']['recall']:.4f} | F1: {eval_data['dev_10']['f1']:.4f}")
print(f"    - Classification Acc: {eval_data['dev_10']['classification_accuracy']:.4f}")
print(f"    - Categorized Errors: {len(dev_errors)} (FP: {len([e for e in dev_errors if e['type'] == 'FALSE_POSITIVE_HEADING'])}, FN: {len([e for e in dev_errors if e['type'] == 'FALSE_NEGATIVE_HEADING'])}, Cls: {len([e for e in dev_errors if e['type'] == 'CLASSIFICATION_MISMATCH'])})")

print(f"\n  Held-Out Test Set (30 Resumes):")
print(f"    - TP: {eval_data['heldout_30']['tp']} | FP: {eval_data['heldout_30']['fp']} | FN: {eval_data['heldout_30']['fn']} | TN: {eval_data['heldout_30']['tn']}")
print(f"    - Heading Precision: {eval_data['heldout_30']['precision']:.4f} | Recall: {eval_data['heldout_30']['recall']:.4f} | F1: {eval_data['heldout_30']['f1']:.4f}")
print(f"    - Classification Acc: {eval_data['heldout_30']['classification_accuracy']:.4f}")
print(f"    - Categorized Errors: {len(heldout_errors)} (FP: {len([e for e in heldout_errors if e['type'] == 'FALSE_POSITIVE_HEADING'])}, FN: {len([e for e in heldout_errors if e['type'] == 'FALSE_NEGATIVE_HEADING'])}, Cls: {len([e for e in heldout_errors if e['type'] == 'CLASSIFICATION_MISMATCH'])})")

print("\n2. FORENSIC CLASSIFICATION OF DEV-SET ERRORS (10 RESUMES):")
dev_fps = [e for e in dev_errors if e['type'] == 'FALSE_POSITIVE_HEADING']
dev_fns = [e for e in dev_errors if e['type'] == 'FALSE_NEGATIVE_HEADING']

print(f"\n  Dev False Positives ({len(dev_fps)} lines):")
for idx, e in enumerate(dev_fps, start=1):
    print(f"    [{idx:02d}] Doc: {e['doc_id']} | Page {e['page']} Line {e['line']} | Text: {repr(e['text'])}")

print(f"\n  Dev False Negatives ({len(dev_fns)} lines):")
for idx, e in enumerate(dev_fns, start=1):
    print(f"    [{idx:02d}] Doc: {e['doc_id']} | Page {e['page']} Line {e['line']} | GT: {e['gt_label']} | Text: {repr(e['text'])}")
