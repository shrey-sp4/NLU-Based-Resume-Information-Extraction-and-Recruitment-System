import json
import glob
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

PHONE_CANDIDATE_REGEX = re.compile(
    r"(?:\+?91|0091|0)?[\s\-\(\)]*[6-9](?:[\s\-]?\d){9}"
)

def extract_all_phones(text):
    results = []
    for m in PHONE_CANDIDATE_REGEX.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if digits.startswith("0091"):
            digits = digits[4:]
        elif digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]
        if len(digits) == 10 and digits[0] in "6789" and digits not in results:
            results.append(digits)
    return results

def score_entity_set_match(gt_vals, pred_vals):
    if not gt_vals and not pred_vals: return 1.0, 1.0, 1.0
    if not gt_vals or not pred_vals: return 0.0, 0.0, 0.0
    tp = 0
    matched_preds = set()
    for g in gt_vals:
        g_norm = str(g).strip().lower()
        if not g_norm: continue
        for idx, p in enumerate(pred_vals):
            if idx in matched_preds: continue
            p_norm = str(p).strip().lower()
            if not p_norm: continue
            if g_norm == p_norm or g_norm in p_norm or p_norm in g_norm:
                tp += 1
                matched_preds.add(idx)
                break
    fp = len(pred_vals) - len(matched_preds)
    fn = len(gt_vals) - tp
    precision = tp / len(pred_vals) if len(pred_vals) > 0 else 0.0
    recall = tp / len(gt_vals) if len(gt_vals) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

gt_files = sorted(PROJECT_ROOT.glob("ground_truth/*.json"))
p_list, r_list, f1_list = [], [], []

for gtf in gt_files:
    with open(gtf, "r", encoding="utf-8") as f:
        gt = json.load(f)
    sec_f = PROJECT_ROOT / "output" / "sections" / (gtf.name.replace(".json", "_sections.json"))
    if not sec_f.exists(): continue
    with open(sec_f, "r", encoding="utf-8") as f:
        sec_data = json.load(f).get("sections", {})
    text = (sec_data.get("preamble", "") + "\n" + sec_data.get("personal_details", "")).strip()
    
    gt_phone_raw = str(gt.get("personal_details", {}).get("phone", "") or "")
    g_phones = extract_all_phones(gt_phone_raw)
    if not g_phones and gt_phone_raw:
        d = re.sub(r"\D", "", gt_phone_raw)
        if d: g_phones = [d]
        
    p_phones = extract_all_phones(text)
    
    p, r, f1 = score_entity_set_match(g_phones, p_phones)
    p_list.append(p)
    r_list.append(r)
    f1_list.append(f1)
    print(f"{gtf.name:<32} | GT Raw: \"{gt_phone_raw}\" -> GT Parsed: {g_phones} | Pred: {p_phones} | F1: {f1*100:.1f}%")

avg_p = sum(p_list) / len(p_list)
avg_r = sum(r_list) / len(r_list)
avg_f1 = sum(f1_list) / len(f1_list)
print("-" * 80)
print(f"PERSONAL PHONE SUMMARY METRICS: Precision={avg_p*100:.2f}%, Recall={avg_r*100:.2f}%, F1={avg_f1*100:.2f}%")
