import json
import glob
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

def normalize_text_for_match(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def line_match_score(line1: str, line2: str) -> float:
    n1 = normalize_text_for_match(line1)
    n2 = normalize_text_for_match(line2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    if len(n1) > 8 and (n1 in n2 or n2 in n1):
        return 0.95
    tokens1 = set(t for t in n1.split() if len(t) >= 3)
    tokens2 = set(t for t in n2.split() if len(t) >= 3)
    if not tokens1 or not tokens2:
        return 0.0
    overlap = len(tokens1 & tokens2)
    if overlap == 0:
        return 0.0
    jaccard = overlap / len(tokens1 | tokens2)
    containment = max(overlap / len(tokens1), overlap / len(tokens2))
    return max(jaccard, containment * 0.85)

def flatten_object(sec_name: str, obj: Any) -> List[Tuple[str, str]]:
    results = []
    if isinstance(obj, str):
        s = obj.strip()
        if len(s) > 3:
            results.append((sec_name, s))
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, str):
                s = item.strip()
                if len(s) > 3:
                    results.append((sec_name, s))
            elif isinstance(item, dict):
                # Flatten dict entry
                vals = [str(v).strip() for k, v in item.items() if k not in ("raw_text",) and v]
                joined = " - ".join(vals)
                if len(joined) > 3:
                    results.append((sec_name, joined))
    elif isinstance(obj, dict):
        for subk, subv in obj.items():
            sub_sec = f"{sec_name}_{subk}" if sec_name == "publications" else subk
            results.extend(flatten_object(sub_sec, subv))
    return results

print("Flattening GT and Predictions across 10 Resumes...")
gt_files = sorted(PROJECT_ROOT.glob("ground_truth/*.json"))

for gtf in gt_files[:3]:
    with open(gtf, "r", encoding="utf-8") as f:
        gt = json.load(f)
    pred_f = PROJECT_ROOT / "output" / "predictions" / gtf.name
    with open(pred_f, "r", encoding="utf-8") as f:
        pred = json.load(f)
        
    gt_pairs = []
    for sec_k, sec_v in gt.items():
        gt_pairs.extend(flatten_object(sec_k, sec_v))
        
    pred_pairs = []
    for sec_k, sec_v in pred.items():
        pred_pairs.extend(flatten_object(sec_k, sec_v))
        
    print(f"=== {gtf.name} ===")
    print(f"  GT Total Lines  : {len(gt_pairs)}")
    print(f"  Pred Total Lines: {len(pred_pairs)}")
