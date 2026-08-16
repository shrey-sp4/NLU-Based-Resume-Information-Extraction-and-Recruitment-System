import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

# Case-insensitive full patterns and explicit short patterns requiring dots or uppercase
DEGREE_PATTERNS = [
    r"\bDoctor of Philosophy(?:\s*\(PhD\))?\b", r"\bPh\.?D\.?\b",
    r"\bMaster of Science(?:\s*\(M\.?\s?Sc\.?\))?\b", r"\bM\.?\s?Sc\.?\b",
    r"\bMaster of Technology(?:\s*\(M\.?\s?Tech\.?\))?\b", r"\bM\.?\s?Tech\.?\b",
    r"\bMaster of Engineering(?:\s*\(M\.?\s?E\.?\))?\b", r"\bM\.E\.\b", r"\bM\.E\b", r"\bM\.Eng\.?\b",
    r"\bMaster of Computer (?:Science|Application)s?\b", r"\bMCA\b", r"\bMSW\b",
    r"\bBachelor of Science(?:\s*\(B\.?\s?Sc\.?\))?\b", r"\bB\.?\s?Sc\.?\b",
    r"\bBachelor of Technology(?:\s*\(B\.?\s?Tech\.?\))?\b", r"\bB\.?\s?Tech\.?\b",
    r"\bBachelor of (?:Computer Application|Engineering)s?\b", r"\bBCA\b", r"\bB\.E\.\b", r"\bB\.E\b", r"\bB\.Eng\.?\b",
    r"\bHigher Secondary(?:\s*\(10\+2\))?\b", r"\b12th(?:\s*\(10\+2\))?\b",
    r"\bMetric(?:\s*\(10th\))?\b", r"\b10th\b",
]
DEGREE_REGEX = re.compile("|".join(f"(?:{p})" for p in DEGREE_PATTERNS))

sec_f = PROJECT_ROOT / "output" / "sections" / "CV-_Amit_Parikh_2_sections.json"
with open(sec_f, "r", encoding="utf-8") as f:
    sec = json.load(f).get("sections", {})

edu_text = sec.get("education", "")
print("=== EDUCATION SECTION TEXT FOR CV- Amit Parikh (2).pdf ===")
print(edu_text)
print("\n=== EXTRACTED DEGREES PER LINE ===")

lines = [l.strip() for l in edu_text.splitlines() if len(l.strip()) > 3]
for idx, l in enumerate(lines):
    m = DEGREE_REGEX.search(l)
    print(f"Line {idx+1}: \"{l[:80]}\" -> Degree Match: {m.group(0) if m else None}")
