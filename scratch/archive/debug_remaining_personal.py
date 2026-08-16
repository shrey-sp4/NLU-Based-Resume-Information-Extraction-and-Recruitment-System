import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

docs = ["CV-Anurag_Choudhary", "Dr_Akash_Thakkar_CV", "CV_Arghya_Maity", "Anibrata_Pal_Resume"]

for doc in docs:
    sec_file = PROJECT_ROOT / "output" / "sections" / f"{doc}_sections.json"
    with open(sec_file, "r", encoding="utf-8") as f:
        data = json.load(f).get("sections", {})
    print(f"=== {doc} ===")
    for k, v in data.items():
        if any(term in v.lower() for term in ["@", "contact", "mobile", "phone", "email"]) or k in ("preamble", "personal_details", "summary"):
            print(f"  [{k}] ({len(v)} chars): \"{v[:250]}\"")
