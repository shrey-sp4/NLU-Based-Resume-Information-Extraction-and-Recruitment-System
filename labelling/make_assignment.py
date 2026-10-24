"""Split the 30 unlabelled resumes between you and your friend (15 each) and build the friend's package.
Run from the project root AFTER make_blank_gt_v2.py:   python labelling\\make_assignment.py
"""
import json, shutil
from pathlib import Path

GT, PKG = Path("ground_truth_v2"), Path("friend_package")
split = json.load(open(GT / "_split.json", encoding="utf-8"))
mine, friend = [], []
for i, s in enumerate(sorted(split["dev"])):
    (mine if i % 2 == 0 else friend).append((s, "DEV"))
for i, s in enumerate(sorted(split["test_frozen"])):
    (friend if i % 2 == 0 else mine).append((s, "TEST"))
json.dump({"me": mine, "friend": friend}, open(GT / "_assignment.json", "w", encoding="utf-8"), indent=1)

(PKG / "ground_truth_v2").mkdir(parents=True, exist_ok=True)
(PKG / "pdfs").mkdir(exist_ok=True)
pdfs = {p.stem.lower(): p for p in Path("data/real_resumes/original").rglob("*.pdf")}
missing = []
for stem, _ in friend:
    shutil.copy(GT / f"{stem}.json", PKG / "ground_truth_v2" / f"{stem}.json")
    if stem.lower() in pdfs: shutil.copy(pdfs[stem.lower()], PKG / "pdfs" / f"{stem}.pdf")
    else: missing.append(stem)
for name in ("validate_gt_v2.py", "TEMPLATE.json", "LABELLING_GUIDE.md"):
    for src in (Path("labelling") / name, Path(name)):
        if src.exists(): shutil.copy(src, PKG / name); break
(PKG / "YOUR_RESUMES.txt").write_text("\n".join(f"{s}  [{k}]" for s, k in friend), encoding="utf-8")

print(f"YOU: {len(mine)} resumes ({sum(k=='DEV' for _,k in mine)} DEV, {sum(k=='TEST' for _,k in mine)} TEST)")
print(f"FRIEND: {len(friend)} resumes ({sum(k=='DEV' for _,k in friend)} DEV, {sum(k=='TEST' for _,k in friend)} TEST)")
print("PDFs not found for friend's resumes (copy by hand):", missing if missing else "none")
