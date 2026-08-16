import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

from scratch.test_fixes_v5 import extract_all_phones_fixed

sec_file = PROJECT_ROOT / "output" / "sections" / "Dibakar_Resume_June_2024_sections.json"
with open(sec_file, "r", encoding="utf-8") as f:
    data = json.load(f).get("sections", {})

preamble_text = data.get("preamble", "")
print("=== DIBAKAR PREAMBLE TEXT ===")
print(preamble_text)
print("=============================")
print("Extracted Phones from Preamble:", extract_all_phones_fixed(preamble_text))
