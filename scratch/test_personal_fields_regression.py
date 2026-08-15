import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

from src.extract_structured_information import (
    extract_personal_details,
    extract_all_phones,
    phone_matches,
    normalize_phone_for_compare
)

def run_personal_fields_regression():
    gt_files = sorted((PROJECT_ROOT / "ground_truth").glob("*.json"))
    
    total_name_pass = 0
    total_email_pass = 0
    total_phone_pass = 0

    print("==========================================================================================================")
    print("REGRESSION TEST: PERSONAL DETAILS EXTRACTION (10 GROUND TRUTH RESUMES)")
    print("==========================================================================================================")

    for gtf in gt_files:
        doc_name = gtf.name
        with open(gtf, "r", encoding="utf-8") as f:
            gt = json.load(f)
        gt_p = gt.get("personal_details", {})
        gt_name = (gt_p.get("name") or "").strip()
        gt_email = (gt_p.get("email") or "").strip()
        gt_phone = (gt_p.get("phone") or "").strip()
        gt_emails = [e.lower().strip() for e in re.split(r"[,\s]+", gt_email) if "@" in e]

        sec_file = PROJECT_ROOT / "output" / "sections" / f"{gtf.stem}_sections.json"
        if not sec_file.exists():
            sec_file = PROJECT_ROOT / "output" / "sections" / f"{gtf.stem}.json"
        
        with open(sec_file, "r", encoding="utf-8") as f:
            sec_data = json.load(f).get("sections", {})

        pred_p = extract_personal_details(sec_data)
        pred_name = (pred_p.get("name") or "").strip()
        pred_email = (pred_p.get("email") or "").strip()
        pred_phone = (pred_p.get("phone") or "").strip()

        # Name match check: containment or exact
        name_pass = False
        if gt_name and pred_name:
            n1 = re.sub(r"[^\w\s]", "", gt_name.lower())
            n2 = re.sub(r"[^\w\s]", "", pred_name.lower())
            if n1 in n2 or n2 in n1:
                name_pass = True
        elif not gt_name and not pred_name:
            name_pass = True

        # Email match check: pred_email in gt_emails or gt_email in pred_email
        email_pass = False
        if gt_email and pred_email:
            if pred_email.lower() in [e.lower() for e in gt_emails] or any(e.lower() in pred_email.lower() for e in gt_emails):
                email_pass = True
        elif not gt_email and not pred_email:
            email_pass = True

        # Phone match check
        phone_pass = False
        if gt_phone and pred_phone:
            if phone_matches(pred_phone, gt_phone) or (normalize_phone_for_compare(pred_phone) in [normalize_phone_for_compare(p) for p in gt_p.get("phones", [])]):
                phone_pass = True
        elif not gt_phone and not pred_phone:
            phone_pass = True

        if name_pass: total_name_pass += 1
        if email_pass: total_email_pass += 1
        if phone_pass: total_phone_pass += 1

        print(f"Document: {doc_name:<32}")
        print(f"  NAME : [{'PASS' if name_pass else 'FAIL'}] Pred=\"{pred_name}\" | GT=\"{gt_name}\"")
        print(f"  EMAIL: [{'PASS' if email_pass else 'FAIL'}] Pred=\"{pred_email}\" | GT=\"{gt_email}\"")
        print(f"  PHONE: [{'PASS' if phone_pass else 'FAIL'}] Pred=\"{pred_phone}\" | GT=\"{gt_phone}\"")

    print("==========================================================================================================")
    print(f"SUMMARY: NAME PASS: {total_name_pass}/10 | EMAIL PASS: {total_email_pass}/10 | PHONE PASS: {total_phone_pass}/10")
    print("==========================================================================================================")

if __name__ == "__main__":
    run_personal_fields_regression()
