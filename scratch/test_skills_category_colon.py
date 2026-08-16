import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

sec_dir = PROJECT_ROOT / "output" / "sections"
json_files = sorted(sec_dir.glob("*.json"))

CATEGORY_COLON_REGEX = re.compile(
    r"^\s*([A-Za-z0-9\s/&\.-]{2,45})\s*:\s*(.+)$"
)

def clean_skill_line(line: str) -> str:
    cleaned = line.strip()
    cleaned = re.sub(r"^\s*(?:[-•*➢|o\+]|\d+[\.\)])\s*", "", cleaned)
    return cleaned.strip()

def is_category_colon_item(item: str) -> bool:
    cleaned = clean_skill_line(item)
    m = CATEGORY_COLON_REGEX.match(cleaned)
    if m:
        cat = m.group(1).strip()
        words = cat.split()
        if 1 <= len(words) <= 6 and not any(w.lower() in ["note", "warning", "objective"] for w in words):
            return True
    return False

print("==========================================================================================================")
print("REAL EXAMPLES OF CATEGORY-COLON SKILLS EXTRACTION ACROSS RESUMES")
print("==========================================================================================================")

example_count = 0
for sec_file in json_files:
    with open(sec_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    skills_text = data.get("sections", {}).get("skills", "")
    if not skills_text:
        continue
    
    lines = [l.strip() for l in skills_text.splitlines() if l.strip()]
    
    for l in lines:
        cleaned = clean_skill_line(l)
        if is_category_colon_item(cleaned):
            example_count += 1
            m = CATEGORY_COLON_REGEX.match(cleaned)
            cat = m.group(1).strip()
            desc = m.group(2).strip()
            print(f"EXAMPLE [{example_count}]: ({sec_file.name})")
            print(f"  Raw Line    : \"{l}\"")
            print(f"  Category    : \"{cat}\"")
            print(f"  Description : \"{desc[:80]}...\"")
            print("-" * 75)
            if example_count >= 8:
                break
    if example_count >= 8:
        break
print("==========================================================================================================")
