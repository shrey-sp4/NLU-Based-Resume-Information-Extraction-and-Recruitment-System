import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

JOB_TITLE_WORDS = re.compile(
    r"\b(?:Professor|Scientist|Scholar|Engineer|Manager|Director|Postdoctoral|Lecturer|Researcher|Fellow|Experienced|Graduate|Student|Assistant|Associate|Executive|Consultant|Developer|Analyst|Lead|Head|Officer|Member)\b",
    re.IGNORECASE
)

ADDRESS_WORDS = re.compile(
    r"\b(?:Road|Street|Avenue|Boulevard|Lane|Drive|Kolkata|Hyderabad|Delhi|Mumbai|Chennai|Bangalore|Gujarat|India|Campus|Building|Floor|Suite|Block|Sector|Apartment|Society|Pincode|School)\b",
    re.IGNORECASE
)

def is_structural_heading_fixed(line: str, line_number: int = 10) -> bool:
    if line_number <= 6:
        return False

    cleaned = line.strip()
    if not cleaned:
        return False
    if cleaned.endswith((".", ",", ";")):
        return False
    if re.match(r"^\s*(?:[-•*➢|o\+]|\d+[\.\)])", line):
        return False
    if "@" in cleaned or "http" in cleaned or "www." in cleaned:
        return False
    if JOB_TITLE_WORDS.search(cleaned):
        return False
    if ADDRESS_WORDS.search(cleaned):
        return False
    if re.search(r"\b\d{5,}\b", cleaned):
        return False
    if re.match(r"^\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}", cleaned, re.IGNORECASE):
        return False
    if re.match(r"^\s*(?:19|20)\d{2}\s*[-–—]", cleaned):
        return False
    
    words = cleaned.split()
    if len(words) > 6:
        return False
    
    is_caps = cleaned.isupper()
    is_title = cleaned.istitle() or all(w[0].isupper() for w in words if len(w) > 2 and w.isalpha())
    ends_colon = cleaned.endswith(":")

    return is_caps or is_title or ends_colon

dibakar_txt = PROJECT_ROOT / "data" / "real_resumes" / "extracted_text" / "Dibakar_Resume_June_2024.txt"
lines = dibakar_txt.read_text(encoding="utf-8", errors="ignore").splitlines()[:10]

print("=== TESTING DIBAKAR TOP 10 LINES ===")
for i, l in enumerate(lines, start=1):
    is_h = is_structural_heading_fixed(l, i)
    print(f"Line {i}: \"{l[:70]}\" -> Heading: {is_h}")
