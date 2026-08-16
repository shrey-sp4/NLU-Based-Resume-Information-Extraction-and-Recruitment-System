import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

from src.extract_structured_information import extract_personal_details

test_docs = [
    "Anibrata_Pal_Resume", "Dr_Akash_Thakkar_CV", "Doyel-Mukherjee-25_06_2024",
    "Dibakar_Resume_June_2024", "Dhwanil_G_CV_2024", "Priyanka_Sharma_CV",
    "Resume_final_Amit_CMA_IIM_A"
]

print("======================================================================")
print("TESTING NAME EXTRACTION & SECTIONS ACROSS 7 RESUMES")
print("======================================================================\n")

for doc in test_docs:
    sec_file = PROJECT_ROOT / "output" / "sections" / f"{doc}_sections.json"
    if not sec_file.exists():
        sec_file = PROJECT_ROOT / "output" / "sections" / f"{doc}.json"
    
    with open(sec_file, "r", encoding="utf-8") as f:
        data = json.load(f).get("sections", {})

    p_details = extract_personal_details(data)
    print(f"DOCUMENT: {doc}.json")
    print(f"  Sections Present: {list(data.keys())}")
    print(f"  Extracted Name  : \"{p_details.get('name')}\"")
    print(f"  Extracted Email : \"{p_details.get('email')}\"")
    print(f"  Extracted Phone : \"{p_details.get('phone')}\"")
    print("-" * 60)
