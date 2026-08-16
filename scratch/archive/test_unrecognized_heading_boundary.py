import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

def is_structural_heading(line: str) -> bool:
    cleaned = line.strip()
    if not cleaned:
        return False
    if cleaned.endswith((".", ",", ";")):
        return False
    if re.match(r"^\s*(?:[-•*➢]|\d+[\.\)])", cleaned):
        return False
    if "@" in cleaned or "http" in cleaned or "www." in cleaned:
        return False
    if re.match(r"^\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}", cleaned, re.IGNORECASE):
        return False
    if re.match(r"^\s*(?:19|20)\d{2}\s*[-–—]", cleaned):
        return False
    
    words = cleaned.split()
    if len(words) > 6:
        return False
    
    # Must be ALL CAPS, Title Case, or end with colon
    is_caps = cleaned.isupper()
    is_title = cleaned.istitle() or all(w[0].isupper() for w in words if len(w) > 2 and w.isalpha())
    ends_colon = cleaned.endswith(":")

    return is_caps or is_title or ends_colon

print("Testing structural heading decision...")
test_lines = [
    "Assessments & Evaluation:",
    "Publication of Research Journal in Progress",
    "HOBBIES",
    "Programming Languages: Efficient in C, C++ and Python",
    "This is a normal body sentence describing skills."
]

for t in test_lines:
    print(f"Line: \"{t}\" -> Is Structural Heading: {is_structural_heading(t)}")
