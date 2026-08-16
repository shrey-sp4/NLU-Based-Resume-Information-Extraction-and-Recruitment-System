import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

map_file = PROJECT_ROOT / "config" / "section_normalization_map.json"
with open(map_file, "r", encoding="utf-8") as f:
    norm_map = json.load(f)

# Add missing variants
new_achievements = [
    "awards & honors", "awards and honors", "honours & awards", "honours and awards",
    "accolades", "key achievements", "awards & achievements", "awards and recognitions",
    "awards, fellowships & honors"
]
new_memberships = [
    "societies", "professional societies", "society memberships", "memberships & societies",
    "professional memberships & societies", "scholarly societies", "honor societies",
    "associations and memberships", "memberships and associations", "society"
]

for item in new_achievements:
    if item not in norm_map["achievements"]:
        norm_map["achievements"].append(item)

for item in new_memberships:
    if item not in norm_map["memberships"]:
        norm_map["memberships"].append(item)

with open(map_file, "w", encoding="utf-8") as f:
    json.dump(norm_map, f, indent=2, ensure_ascii=False)

print("Updated config/section_normalization_map.json with new heading variants.")
