"""Create blank ground_truth_v2/<name>.json files for every resume that has no label yet,
and split them randomly into DEV and TEST (fixed seed, so the split never changes).
Run from the project root:  python make_blank_gt_v2.py
"""
import json, random
from pathlib import Path

PRED, GT = Path("output/predictions"), Path("ground_truth_v2")
GT.mkdir(exist_ok=True)
SPLIT = GT / "_split.json"

done = {f.stem for f in GT.glob("*.json") if not f.name.startswith("_")}
todo = sorted(f.stem for f in PRED.glob("*.json") if f.stem not in done)

if SPLIT.exists():
    split = json.load(open(SPLIT, encoding="utf-8"))
else:
    unl = sorted(todo)
    random.Random(42).shuffle(unl)
    half = len(unl) // 2
    split = {"test_frozen": sorted(unl[:half]), "dev": sorted(unl[half:])}
    json.dump(split, open(SPLIT, "w", encoding="utf-8"), indent=2)

blank = lambda stem: {
    "resume_file": stem + ".pdf", "candidate_name": "",
    "education": [{"degree": "", "degree_level": "", "stream": "", "institution": ""}],
    "experience": [{"job_title": "", "institution": "", "dates": "", "experience_type": ""}],
    "publications": [{"title": "", "type": "", "year": "", "venue": ""}],
    "stated_totals": {"journal": None, "conference": None, "total": None}, "notes": ""}

for stem in todo:
    json.dump(blank(stem), open(GT / (stem + ".json"), "w", encoding="utf-8"), indent=2)
print(f"already labelled: {len(done)} | blank files created: {len(todo)}")
print(f"frozen TEST set: {len(split['test_frozen'])} | DEV set: {len(split['dev'])} (names are in ground_truth_v2/_split.json)")
