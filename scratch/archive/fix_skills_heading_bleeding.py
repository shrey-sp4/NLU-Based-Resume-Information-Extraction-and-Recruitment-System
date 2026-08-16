import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

map_file = PROJECT_ROOT / "config" / "section_normalization_map.json"
with open(map_file, "r", encoding="utf-8") as f:
    norm_map = json.load(f)

# Add missing heading variants causing skills section bleeding
new_pubs = [
    "papers published", "paper published", "publications in progress",
    "publication of research journal in progress", "papers published in journals",
    "research papers published"
]

new_certs = [
    "online course", "online courses", "online course - duke university | 2020",
    "online courses & certifications"
]

new_ignore_hobbies = [
    "hobbies", "hobbies & interests", "personal hobbies"
]

for p in new_pubs:
    if p not in norm_map["publications"]:
        norm_map["publications"].append(p)

for c in new_certs:
    if c not in norm_map["certifications"]:
        norm_map["certifications"].append(c)

if "ignore" not in norm_map:
    norm_map["ignore"] = []

for h in new_ignore_hobbies:
    if h not in norm_map["ignore"]:
        norm_map["ignore"].append(h)

with open(map_file, "w", encoding="utf-8") as f:
    json.dump(norm_map, f, indent=2, ensure_ascii=False)

print("Updated config/section_normalization_map.json with publication & course heading variants.")
