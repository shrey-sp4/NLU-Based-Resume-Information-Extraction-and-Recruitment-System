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

target_fields = ["education_cgpa", "education_degree", "education_graduation_year", "experience_title"]

print("======================================================================")
print("DIAGNOSTIC AUDIT OF THE 4 ASYMMETRIC FIELDS")
print("======================================================================")

for field in target_fields:
    print(f"\n======================================================================")
    print(f"AUDITING FIELD: {field}")
    print(f"======================================================================")
    fp_pairs = []
    
    for gtf in sorted(GT_DIR.glob("*.json")):
        doc_id_base = gtf.name.replace(".json", "")
        pred_file = PRED_DIR / gtf.name
        if not pred_file.exists():
            continue

        with open(gtf, "r", encoding="utf-8") as f:
            gt = json.load(f)
        with open(pred_file, "r", encoding="utf-8") as f:
            pred = json.load(f)

        # Ground Truth Values
        gt_vals = []
        if "education_" in field:
            sub = field.replace("education_", "")
            for e in gt.get("education", []):
                if isinstance(e, dict):
                    if sub == "degree" and e.get("degree"): gt_vals.append(str(e.get("degree")))
                    elif sub == "graduation_year" and (e.get("duration") or e.get("graduation_year")): gt_vals.append(str(e.get("duration") or e.get("graduation_year")))
                    elif sub == "cgpa" and (e.get("grade") or e.get("cgpa")): gt_vals.append(str(e.get("grade") or e.get("cgpa")))
                    elif sub == "institution" and e.get("institution"): gt_vals.append(str(e.get("institution")))
        elif "experience_" in field:
            sub = field.replace("experience_", "")
            gt_exp = gt.get("experience", []) + gt.get("academic_experience", [])
            for e in gt_exp:
                if isinstance(e, dict):
                    if sub == "title" and (e.get("title") or e.get("position") or e.get("job_title")):
                        gt_vals.append(str(e.get("title") or e.get("position") or e.get("job_title")))
                    elif sub == "institution" and (e.get("organization") or e.get("institution") or e.get("company")):
                        gt_vals.append(str(e.get("organization") or e.get("institution") or e.get("company")))
                    elif sub == "dates" and (e.get("duration") or e.get("dates")):
                        gt_vals.append(str(e.get("duration") or e.get("dates")))

        # Predicted Values
        pred_vals = []
        if "education_" in field:
            pred_vals = [str(x) for x in pred.get("education", [])]
        elif "experience_" in field:
            pred_vals = [str(x) for x in pred.get("experience", [])]

        # Check overlap
        for g_v in gt_vals:
            for p_v in pred_vals:
                if g_v.lower() in p_v.lower() or p_v.lower() in g_v.lower():
                    fp_pairs.append({
                        "doc": gtf.name,
                        "ground_truth": g_v,
                        "predicted_full_text": p_v[:140] + "..." if len(p_v) > 140 else p_v
                    })

    print(f"Total overlapping FP pairs identified: {len(fp_pairs)}")
    print("Dumping 15 raw (predicted, ground_truth) pairs:")
    for idx, item in enumerate(fp_pairs[:15]):
        print(f"  [{idx+1:2d}] Resume: {item['doc']}")
        print(f"       Ground Truth : \"{item['ground_truth']}\"")
        print(f"       Predicted Val: \"{item['predicted_full_text']}\"")
