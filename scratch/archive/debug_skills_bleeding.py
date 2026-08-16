import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

sample_docs = [
    "Anibrata_Pal_Resume", "CV_Arghya_Maity", "CV_Chandan",
    "Dr_Akash_Thakkar_CV", "cv_aakash_daiict"
]

print("==========================================================================================================")
print("RAW SECTIONS.GET('SKILLS') TEXT DUMP BEFORE LIST-SPLITTING (5 RESUMES)")
print("==========================================================================================================")

for doc in sample_docs:
    sec_file = PROJECT_ROOT / "output" / "sections" / f"{doc}_sections.json"
    if not sec_file.exists():
        sec_file = PROJECT_ROOT / "output" / "sections" / f"{doc}.json"
    
    with open(sec_file, "r", encoding="utf-8") as f:
        data = json.load(f).get("sections", {})

    skills_raw = data.get("skills", "NOT FOUND")
    print(f"\nDOCUMENT: {doc}.json")
    print(f"Total Sections Present: {list(data.keys())}")
    print(f"Raw Skills Text Length: {len(skills_raw)} chars")
    print(f"--- RAW SKILLS CONTENT ---\n{skills_raw}\n" + "-"*70)
