import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

DATE_LINE_START_REGEX = re.compile(
    r"^\s*(?:"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|July|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}"
    r"|\b(?:19|20)\d{2}\s*[-–—]"
    r"|[-•*➢|o\+]|\d+[\.\)]"
    r")",
    re.IGNORECASE
)

DEGREE_LINE_START_REGEX = re.compile(
    r"^\s*(?:"
    r"Doctor of Philosophy|Ph\.?D\.?|Master of Science|M\.?Sc\.?|Master of Technology|M\.?Tech\.?|"
    r"Master of Engineering|M\.E\.|B\.?Tech\.?|B\.?Sc\.?|Higher Secondary|12th|10th"
    r")",
    re.IGNORECASE
)

def split_section_into_entries(text: str, is_education: bool = False) -> List[str]:
    if not text:
        return []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    entries = []
    current_entry = []

    for line in lines:
        if re.match(r"^(?:page\s+\d+|\d+)$", line, re.IGNORECASE):
            continue

        is_new_entry_start = bool(DATE_LINE_START_REGEX.search(line))
        if is_education and DEGREE_LINE_START_REGEX.search(line):
            is_new_entry_start = True

        if current_entry and is_new_entry_start:
            entries.append(" ".join(current_entry))
            current_entry = [line]
        else:
            current_entry.append(line)

    if current_entry:
        entries.append(" ".join(current_entry))

    # Fallback to double-newline or bullet split if line grouping produced only 1 item
    if len(entries) <= 1:
        items = re.split(r'\n\s*(?:[-•*➢|o\+]|\d+[\.\)])\s*|\n{2,}', text)
        entries = [re.sub(r'\s+', ' ', item).strip() for item in items if len(item.strip()) > 5]

    return [e for e in entries if len(e) > 5]

sec_file = PROJECT_ROOT / "output" / "sections" / "A_Mitesh_CV_sections.json"
with open(sec_file, "r", encoding="utf-8") as f:
    sec_data = json.load(f).get("sections", {})

exp_text = sec_data.get("experience", "")
split_entries = split_section_into_entries(exp_text)

print(f"=== SPLIT EXPERIENCE TEXT INTO {len(split_entries)} DISCRETE ENTRIES (Expected: 8) ===")
for idx, e in enumerate(split_entries):
    print(f"  [{idx+1}] \"{e}\"")
