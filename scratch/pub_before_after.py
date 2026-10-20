"""Read-only: publication entries for resumes whose buckets changed, HEAD vs working copy.
Writes scratch/pub_before_after.txt (UTF-8)."""
import json, subprocess
from pathlib import Path

names = ["Snehamoy_P_CV", "Updated_CV-_Dr_Soumen_Mukherjee", "Curriculum_Vitae_Rakesh",
         "Sourabh_Pal_1", "CV_DAIICT", "MKS_CV"]
out = []

def show(tag, pubs):
    for bucket, items in pubs.items():
        if not items:
            continue
        out.append(f"  [{tag}] {bucket}: {len(items)}")
        for it in items[:4]:
            out.append("      - " + str(it).replace("\n", " ")[:160])

for n in names:
    rel = f"output/predictions/{n}.json"
    head = subprocess.run(["git", "show", f"HEAD:{rel}"], capture_output=True, encoding="utf-8").stdout
    before = json.loads(head)["publications"]
    after = json.loads(Path(rel).read_text(encoding="utf-8"))["publications"]
    out.append(f"=== {n}")
    show("BEFORE", before)
    show("AFTER ", after)
    sec = Path(f"output/sections/{n}_sections.json")
    if sec.exists():
        d = json.loads(sec.read_text(encoding="utf-8"))
        out.append("  Stage 2 publications heading(s): " + str([g["heading"] for g in d.get("publication_groups", [])]))
        out.append("  Stage 2 section names: " + str(list(d["sections"].keys())))
Path("scratch/pub_before_after.txt").write_text("\n".join(out), encoding="utf-8")
print("written scratch/pub_before_after.txt")