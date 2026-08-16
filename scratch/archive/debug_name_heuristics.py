import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

# Job title and address noise words to reject
JOB_TITLE_WORDS = re.compile(
    r"\b(?:Professor|Scientist|Scholar|Engineer|Manager|Director|Postdoctoral|Lecturer|Researcher|Fellow|Experienced|Graduate|Student|Assistant|Associate|Executive|Consultant|Developer|Analyst|Lead|Head|Officer|Member)\b",
    re.IGNORECASE
)

ADDRESS_WORDS = re.compile(
    r"\b(?:Road|Street|Avenue|Boulevard|Lane|Drive|Kolkata|Hyderabad|Delhi|Mumbai|Chennai|Bangalore|Gujarat|India|Campus|Building|Floor|Suite|Block|Sector|Apartment|Society|Pincode)\b",
    re.IGNORECASE
)

PREAMBLE_HEADER_NOISE = re.compile(
    r"\b(?:curricu?lam|curriculum|vitae|resume|biodata|profile|page\s+\d+|page|recognized|top\s+\d+%|stanford|elsevier|webpage|google scholar|looking for|achievements|opportunities|qualified|gold medalist)\b",
    re.IGNORECASE
)

def robust_extract_candidate_name(text: str) -> str:
    if not text:
        return ""
    
    raw_lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not raw_lines:
        return ""

    # Check for 2 single-word lines at top (e.g. "Doyel" \n "Mukherjee")
    if len(raw_lines) >= 2:
        l1, l2 = raw_lines[0], raw_lines[1]
        if (len(l1.split()) == 1 and len(l2.split()) == 1 and 
            re.match(r"^[A-Z][a-z]+$", l1) and re.match(r"^[A-Z][a-z]+$", l2)):
            return f"{l1} {l2}"

    # Search top 6 lines of preamble/text
    candidate_lines = raw_lines[:8]
    
    for line in candidate_lines:
        if "@" in line:
            continue
        if PREAMBLE_HEADER_NOISE.search(line):
            continue
        if JOB_TITLE_WORDS.search(line):
            continue
        if ADDRESS_WORDS.search(line):
            continue

        clean_line = re.sub(r"^(?:name|full name|candidate name)\s*[:\-]\s*", "", line, flags=re.IGNORECASE).strip()
        clean_line = clean_line.strip(":-–—|•●■□*➢ ")
        clean_line = re.split(r"\b(?:Address|Email|E-mail|Phone|Mobile|Contact|Location|Webpage|CV page|Page)\b", clean_line, flags=re.IGNORECASE)[0].strip()
        clean_line = re.split(r"\d", clean_line)[0].strip()
        clean_line = re.sub(r"[^\w\s\.\-']", "", clean_line).strip()
        
        words = clean_line.split()
        if 2 <= len(words) <= 5 and re.match(r"^[A-Za-z\.\s\-']+$", clean_line):
            return clean_line

    return ""

doyel_text = """Doyel
Mukherjee
doyel.mukherjee90@gmail.com
+919831700331
Swastik-II 56 Panchanantala Road , Kolkata-700041
PROFILE
Experienced Research Scholar and..."""

dibakar_text = """Dibakar Roy Chowdhury
Ecole Centrale School of Engineering,
FInstP (UK) Mahindra University,
Professor of Physics, Jeedimetla, Hyderabad, 500043
Email: dibakarrc@gmail.com"""

print("=== TESTING REDESIGNED NAME DETECTION HEURISTIC ===")
print("Doyel Name Result  :", robust_extract_candidate_name(doyel_text))
print("Dibakar Name Result:", robust_extract_candidate_name(dibakar_text))
