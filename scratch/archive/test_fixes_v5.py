import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

# Fixed phone regex with horizontal whitespace [ \t]
PHONE_CANDIDATE_REGEX_FIXED = re.compile(
    r"(?:\(?\+?91\)?|0091|0)?[ \t\-\(\)]*(?:[6-9][ \t\-\(\)\.]*){1}(?:\d[ \t\-\(\)\.]*){9,11}"
)

def extract_all_phones_fixed(text):
    results = []
    for m in PHONE_CANDIDATE_REGEX_FIXED.finditer(text or ""):
        digits = re.sub(r"\D", "", m.group(0))
        if digits.startswith("0091"):
            digits = digits[4:]
        elif digits.startswith("91") and len(digits) >= 12:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]
        if len(digits) == 10 and digits[0] in "6789" and digits not in results:
            results.append(digits)
    return results

GERUND_PATTERNS = re.compile(
    r"^\s*(?:Conducting|Designing|Preparing|Crafting|Executing|Managing|Developing|Leading|Coordinating|Creating|Implementing|Formulating|Providing|Handling|Organizing)\b",
    re.IGNORECASE
)

NARRATIVE_PHRASES = [
    "years of exposure", "skills and ethics", "critical thinking skills to",
    "strong ability to", "skilled in coordinating", "experience with analytical",
    "ability to identify", "good communication ability", "possess organizing"
]

def is_narrative_skill_item(item: str) -> bool:
    words = item.split()
    if len(words) > 13:
        return True
    if GERUND_PATTERNS.search(item):
        return True
    item_lower = item.lower()
    if any(phrase in item_lower for phrase in NARRATIVE_PHRASES):
        return True
    return False

test_docs = [
    "Anibrata_Pal_Resume", "Dr_Akash_Thakkar_CV", "Doyel-Mukherjee-25_06_2024",
    "Dibakar_Resume_June_2024", "Dhwanil_G_CV_2024", "Priyanka_Sharma_CV",
    "Resume_final_Amit_CMA_IIM_A"
]

print("======================================================================")
print("TESTING FIXED PHONE & NARRATIVE SKILLS FLAG ACROSS 7 RESUMES")
print("======================================================================\n")

for doc in test_docs:
    sec_file = PROJECT_ROOT / "output" / "sections" / f"{doc}_sections.json"
    if not sec_file.exists():
        sec_file = PROJECT_ROOT / "output" / "sections" / f"{doc}.json"
    
    with open(sec_file, "r", encoding="utf-8") as f:
        data = json.load(f).get("sections", {})

    full_doc_text = "\n".join(str(v) for v in data.values() if isinstance(v, str))
    extracted_phones = extract_all_phones_fixed(full_doc_text)
    
    skills_text = data.get("skills", "")
    skills_items = [re.sub(r'\s+', ' ', item).strip() for item in re.split(r'\n\s*(?:[-•*➢|o\+]|\d+[\.\)])\s*|\n{2,}', skills_text) if len(item.strip()) > 5]
    
    has_narrative_flag = any(is_narrative_skill_item(item) for item in skills_items)

    print(f"DOCUMENT: {doc}.json")
    print(f"  Extracted Phone(s): {extracted_phones}")
    print(f"  Skills Item Count : {len(skills_items)}")
    print(f"  Narrative Flag    : {'⚠️ possible_narrative_skills_not_itemized' if has_narrative_flag else '✅ CLEAN ITEMIZED SKILLS'}")
    if skills_items:
        print(f"  First Skill Item  : \"{skills_items[0][:90]}...\"")
    print("-" * 65)
