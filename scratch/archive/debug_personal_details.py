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

gt_files = sorted((PROJECT_ROOT / "ground_truth").glob("*.json"))

print("==========================================================================================================")
print("PERSONAL DETAILS PREDICTION VS GROUND TRUTH SIDE-BY-SIDE (10 RESUMES)")
print("==========================================================================================================")

mismatches = []

for gtf in gt_files:
    doc_name = gtf.name
    with open(gtf, "r", encoding="utf-8") as f:
        gt = json.load(f)
    gt_p = gt.get("personal_details", {})
    gt_name = (gt_p.get("name") or "").strip()
    gt_email = (gt_p.get("email") or "").strip()
    gt_phone = (gt_p.get("phone") or "").strip()

    sec_file = PROJECT_ROOT / "output" / "sections" / f"{gtf.stem}_sections.json"
    with open(sec_file, "r", encoding="utf-8") as f:
        sec_data = json.load(f).get("sections", {})

    pred_p = extract_personal_details(sec_data)
    pred_name = (pred_p.get("name") or "").strip()
    pred_email = (pred_p.get("email") or "").strip()
    pred_phone = (pred_p.get("phone") or "").strip()

    # Match checks
    name_ok = (pred_name.lower() == gt_name.lower()) or (gt_name.lower() in pred_name.lower() or pred_name.lower() in gt_name.lower())
    email_ok = (pred_email.lower() == gt_email.lower())
    
    # Phone match using normalize_phone_for_compare
    phone_ok = phone_matches(pred_phone, gt_phone) or (normalize_phone_for_compare(pred_phone) in [normalize_phone_for_compare(p) for p in gt_p.get("phones", [])])

    print(f"\nDocument: {doc_name}")
    print(f"  NAME : Pred=\"{pred_name}\" | GT=\"{gt_name}\" -> [{'MATCH' if name_ok else 'MISMATCH'}]")
    print(f"  EMAIL: Pred=\"{pred_email}\" | GT=\"{gt_email}\" -> [{'MATCH' if email_ok else 'MISMATCH'}]")
    print(f"  PHONE: Pred=\"{pred_phone}\" | GT=\"{gt_phone}\" -> [{'MATCH' if phone_ok else 'MISMATCH'}]")

    if not name_ok or not email_ok or not phone_ok:
        mismatches.append({
            "doc": doc_name,
            "name_ok": name_ok, "gt_name": gt_name, "pred_name": pred_name,
            "email_ok": email_ok, "gt_email": gt_email, "pred_email": pred_email,
            "phone_ok": phone_ok, "gt_phone": gt_phone, "pred_phone": pred_phone,
            "preamble": sec_data.get("preamble", "")[:400]
        })

print("\n" + "="*100)
print(f"TOTAL MISMATCHES: {len(mismatches)} / 10 DOCUMENTS")
print("="*100)

for m in mismatches:
    print(f"\n--- MISMATCH DETAILS FOR: {m['doc']} ---")
    if not m["name_ok"]:
        print(f"  NAME  MISMATCH: Pred=\"{m['pred_name']}\" vs GT=\"{m['gt_name']}\"")
    if not m["email_ok"]:
        print(f"  EMAIL MISMATCH: Pred=\"{m['pred_email']}\" vs GT=\"{m['gt_email']}\"")
    if not m["phone_ok"]:
        print(f"  PHONE MISMATCH: Pred=\"{m['pred_phone']}\" vs GT=\"{m['gt_phone']}\"")
    print(f"  Raw Preamble Text:\n{m['preamble']}\n")
