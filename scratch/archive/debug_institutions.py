import json
import glob
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
GT_DIR = PROJECT_ROOT / "ground_truth"
PRED_DIR = PROJECT_ROOT / "output" / "predictions"

def normalize_entity_str(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()

print("======================================================================")
print("INSTITUTION EXTRACTION FAILURE PATTERN AUDIT")
print("======================================================================")

for field_type in ["education", "experience"]:
    print(f"\n--- AUDITING FIELD: {field_type}_institution ---")
    fp_list = []
    fn_list = []
    
    for gtf in sorted(GT_DIR.glob("*.json")):
        pred_file = PRED_DIR / gtf.name
        if not pred_file.exists():
            continue

        with open(gtf, "r", encoding="utf-8") as f:
            gt = json.load(f)
        with open(pred_file, "r", encoding="utf-8") as f:
            pred = json.load(f)

        # Ground truth institutions
        gt_insts = []
        if field_type == "education":
            for e in gt.get("education", []):
                if isinstance(e, dict) and e.get("institution"):
                    gt_insts.append(str(e.get("institution")))
        else:
            gt_exp = gt.get("experience", []) + gt.get("academic_experience", [])
            for e in gt_exp:
                if isinstance(e, dict) and (e.get("organization") or e.get("institution") or e.get("company")):
                    gt_insts.append(str(e.get("organization") or e.get("institution") or e.get("company")))

        # Predicted institutions
        pred_insts = []
        pred_list = pred.get(field_type, [])
        for e in pred_list:
            if isinstance(e, dict) and e.get("institution"):
                pred_insts.append(str(e.get("institution")))

        matched_preds = set()
        matched_gts = set()

        for g_idx, g in enumerate(gt_insts):
            g_norm = normalize_entity_str(g)
            if not g_norm: continue
            for p_idx, p in enumerate(pred_insts):
                if p_idx in matched_preds: continue
                p_norm = normalize_entity_str(p)
                if not p_norm: continue
                if g_norm == p_norm or g_norm in p_norm or p_norm in g_norm:
                    matched_preds.add(p_idx)
                    matched_gts.add(g_idx)
                    break

        for p_idx, p in enumerate(pred_insts):
            if p_idx not in matched_preds:
                fp_list.append({"doc": gtf.name, "pred": p, "gt_all": gt_insts})

        for g_idx, g in enumerate(gt_insts):
            if g_idx not in matched_gts:
                fn_list.append({"doc": gtf.name, "gt": g, "pred_all": pred_insts})

    print(f"\n[FALSE POSITIVES - Predicted but incorrect/truncated (Total: {len(fp_list)})]")
    for idx, item in enumerate(fp_list[:10]):
        print(f"  [{idx+1:2d}] {item['doc']:<32} PRED: \"{item['pred']}\" | GT GTs: {item['gt_all']}")

    print(f"\n[FALSE NEGATIVES - Ground truth missed (Total: {len(fn_list)})]")
    for idx, item in enumerate(fn_list[:10]):
        print(f"  [{idx+1:2d}] {item['doc']:<32} GT: \"{item['gt']}\" | PREDs: {item['pred_all']}")
