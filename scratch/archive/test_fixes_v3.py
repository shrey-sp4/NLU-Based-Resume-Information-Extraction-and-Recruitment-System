import json
import glob
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

PHONE_CANDIDATE_REGEX = re.compile(
    r"(?:\+?91|0091|0)?[\s\-\(\)]*(?:[6-9][\s\-\(\)\.]*){1}(?:\d[\s\-\(\)\.]*){9,11}"
)

def extract_all_phones(text):
    """Returns ALL phone numbers found (list), normalized to bare 10-digit strings."""
    results = []
    candidates = PHONE_CANDIDATE_REGEX.finditer(text or "")
    for m in candidates:
        raw = m.group(0)
        digits = re.sub(r"\D", "", raw)
        if digits.startswith("0091"):
            digits = digits[4:]
        elif digits.startswith("91") and len(digits) >= 12:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]
        if len(digits) == 10 and digits[0] in "6789" and digits not in results:
            results.append(digits)
    return results

def extract_personal_name(text):
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 3]
    for line in lines:
        if "@" in line:
            continue
        if re.search(r"\b(curricu?lam|curriculum|vitae|resume|biodata|profile)\b", line, re.IGNORECASE):
            continue
        clean_line = re.sub(r"^(name|full name|candidate name)\s*[:\-]\s*", "", line, flags=re.IGNORECASE).strip()
        clean_line = clean_line.strip(":-–—|•●■□*➢ ")
        
        # Stop condition 1: Cut at 'Address', 'Email', 'Phone', 'Mobile', 'Contact', 'Location'
        clean_line = re.split(r"\b(?:Address|Email|E-mail|Phone|Mobile|Contact|Location)\b", clean_line, flags=re.IGNORECASE)[0].strip()
        
        # Stop condition 2: Cut at first digit
        clean_line = re.split(r"\d", clean_line)[0].strip()
        
        # Stop condition 3: Cut at line-internal capital-after-lowercase word boundary (e.g. KumarCurriculum)
        boundary_match = re.search(r"([a-z])([A-Z])", clean_line)
        if boundary_match:
            clean_line = clean_line[:boundary_match.start(1)+1].strip()

        clean_line = clean_line.strip(":-–—|•●■□*➢ ")
        if len(clean_line.split()) >= 2:
            return clean_line
    return ""

test_resumes = ["A_Mitesh_CV.json", "AH_CV.json", "CV_CSE_ASHISH_SONI.json"]

print("======================================================================")
print("TESTING NAME & PHONE FIXES ON 3 RESUMES")
print("======================================================================\n")

for r_name in test_resumes:
    sec_f = PROJECT_ROOT / "output" / "sections" / f"{r_name.replace('.json', '')}_sections.json"
    with open(sec_f, "r", encoding="utf-8") as f:
        sec = json.load(f).get("sections", {})
    text = (sec.get("preamble", "") + "\n" + sec.get("personal_details", "")).strip()
    
    name = extract_personal_name(text)
    phones = extract_all_phones(text)
    
    print(f"=== {r_name} ===")
    print(f"  Extracted Name  : \"{name}\"")
    print(f"  Extracted Phones: {phones}")
    print()
