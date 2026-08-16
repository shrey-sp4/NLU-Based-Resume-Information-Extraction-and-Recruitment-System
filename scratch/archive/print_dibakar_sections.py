import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

sec_file = PROJECT_ROOT / "output" / "sections" / "Dibakar_Resume_June_2024_sections.json"
with open(sec_file, "r", encoding="utf-8") as f:
    data = json.load(f).get("sections", {})

for k, v in data.items():
    print(f"Section [{k}] ({len(v)} chars): \"{v[:150].replace('\n', ' ')}\"")
