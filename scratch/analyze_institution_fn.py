import json
import glob
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
GT_DIR = PROJECT_ROOT / "ground_truth"
PRED_DIR = PROJECT_ROOT / "output" / "predictions"
SECTIONS_DIR = PROJECT_ROOT / "output" / "sections"

KEYWORD_REGEX = re.compile(r"\b(University|Institute|College|School|IIT|NIT|IIIT|IIM|Vishwavidhyalay|Vidyalaya|Academy|Centre|Center)\b", re.IGNORECASE)

fn_cases = []

for gtf in sorted(GT_DIR.glob("*.json")):
    doc_base = gtf.name.replace(".json", "")
    sec_file = SECTIONS_DIR / f"{doc_base}_sections.json"
    pred_file = PRED_DIR / gtf.name
    
    if not sec_file.exists() or not pred_file.exists():
        continue
        
    with open(gtf, "r", encoding="utf-8") as f:
        gt = json.load(f)
    with open(sec_file, "r", encoding="utf-8") as f:
        sections = json.load(f).get("sections", {})
    with open(pred_file, "r", encoding="utf-8") as f:
        pred = json.load(f)

    # Analyze Education Institutions
    gt_edu = gt.get("education", [])
    edu_text = sections.get("education", "")
    pred_edu_insts = [e.get("institution") for e in pred.get("education", []) if isinstance(e, dict) and e.get("institution")]

    for e in gt_edu:
        if isinstance(e, dict) and e.get("institution"):
            gt_inst = str(e.get("institution"))
            # Check if gt_inst is matched by any predicted inst
            matched = False
            for p in pred_edu_insts:
                if gt_inst.lower() in p.lower() or p.lower() in gt_inst.lower():
                    matched = True
                    break
            if not matched:
                # Classify failure mechanism
                mechanism = ""
                lines = [l for l in edu_text.splitlines() if l.strip()]
                
                if not edu_text.strip():
                    mechanism = "(c) whole section mis-segmented (section text empty/missing)"
                else:
                    found_kw = False
                    found_line_break = False
                    for line in lines:
                        if gt_inst.lower() in line.lower() or any(w.lower() in line.lower() for w in gt_inst.split() if len(w) > 4):
                            if KEYWORD_REGEX.search(line):
                                found_kw = True
                            else:
                                found_kw = False
                    
                    # Check line break
                    gt_first_word = gt_inst.split()[0].lower()
                    gt_last_word = gt_inst.split()[-1].lower()
                    first_line_idx = -1
                    last_line_idx = -1
                    for idx, line in enumerate(lines):
                        if gt_first_word in line.lower(): first_line_idx = idx
                        if gt_last_word in line.lower(): last_line_idx = idx
                    
                    if first_line_idx != -1 and last_line_idx != -1 and first_line_idx != last_line_idx:
                        mechanism = f"(a) institution name spans line breaks (line {first_line_idx+1} to line {last_line_idx+1})"
                    elif not KEYWORD_REGEX.search(gt_inst):
                        mechanism = "(b) institution keyword missing entirely from institution name"
                    else:
                        mechanism = "(b) institution keyword missing/unmatched on single entry line"

                fn_cases.append({
                    "field": "education_institution",
                    "doc": gtf.name,
                    "gt_inst": gt_inst,
                    "sec_text_snippet": edu_text[:200].replace("\n", " "),
                    "mechanism": mechanism
                })

    # Analyze Experience Institutions
    gt_exp = gt.get("experience", []) + gt.get("academic_experience", [])
    exp_text = sections.get("experience", "") + sections.get("academic_experience", "")
    pred_exp_insts = [e.get("institution") for e in pred.get("experience", []) if isinstance(e, dict) and e.get("institution")]

    for e in gt_exp:
        if isinstance(e, dict) and (e.get("organization") or e.get("institution") or e.get("company")):
            gt_inst = str(e.get("organization") or e.get("institution") or e.get("company"))
            matched = False
            for p in pred_exp_insts:
                if gt_inst.lower() in p.lower() or p.lower() in gt_inst.lower():
                    matched = True
                    break
            if not matched:
                mechanism = ""
                lines = [l for l in exp_text.splitlines() if l.strip()]
                
                if not exp_text.strip():
                    mechanism = "(c) whole section mis-segmented (section text empty/missing)"
                else:
                    first_word = gt_inst.split()[0].lower()
                    last_word = gt_inst.split()[-1].lower()
                    first_idx, last_idx = -1, -1
                    for idx, line in enumerate(lines):
                        if first_word in line.lower(): first_idx = idx
                        if last_word in line.lower(): last_idx = idx
                    
                    if first_idx != -1 and last_idx != -1 and first_idx != last_idx:
                        mechanism = f"(a) institution name spans line breaks (line {first_idx+1} to line {last_idx+1})"
                    elif not KEYWORD_REGEX.search(gt_inst):
                        mechanism = "(b) institution keyword missing entirely from institution name (e.g. company/abbreviation name)"
                    else:
                        mechanism = "(b) institution keyword present but unmatched on entry line"

                fn_cases.append({
                    "field": "experience_institution",
                    "doc": gtf.name,
                    "gt_inst": gt_inst,
                    "sec_text_snippet": exp_text[:200].replace("\n", " "),
                    "mechanism": mechanism
                })

print(f"Total False Negative Cases Analyzed: {len(fn_cases)}")
print("\n--- DUMPING WORST 15 FALSE NEGATIVES WITH RAW SOURCE LINES & MECHANISM ---")
for idx, case in enumerate(fn_cases[:15]):
    print(f"\n[{idx+1:2d}] Field: {case['field']} | Document: {case['doc']}")
    print(f"     Ground Truth Institution: \"{case['gt_inst']}\"")
    print(f"     Failure Mechanism       : {case['mechanism']}")
    print(f"     Raw Section Text Snippet: {case['sec_text_snippet']}")
