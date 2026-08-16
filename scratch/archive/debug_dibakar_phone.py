import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

from src.extract_structured_information import PHONE_CANDIDATE_REGEX, extract_all_phones

sec_file = PROJECT_ROOT / "output" / "sections" / "Dibakar_Resume_June_2024_sections.json"
with open(sec_file, "r", encoding="utf-8") as f:
    data = json.load(f).get("sections", {})

full_doc_text = "\n".join(str(v) for v in data.values() if isinstance(v, str))

print("=== PHONE_CANDIDATE_REGEX MATCHES IN DIBAKAR RESUME ===")
for m in PHONE_CANDIDATE_REGEX.finditer(full_doc_text):
    raw_m = m.group(0)
    digits = re.sub(r"\D", "", raw_m)
    print(f"Raw Match: \"{raw_m}\" -> Clean Digits: \"{digits}\"")

print("\nExtracted Phones:", extract_all_phones(full_doc_text))
