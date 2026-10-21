"""Read-only: what changed in names and experience entries between the last commit (HEAD) and the working predictions?
Writes scratch/unlabelled_delta.txt (ASCII-safe)."""
import json, subprocess
from pathlib import Path

gt = {p.name for p in Path("ground_truth").glob("*.json")}
out, name_changes, exp_changes = [], 0, 0
for p in sorted(Path("output/predictions").glob("*.json")):
    head = subprocess.run(["git", "show", "HEAD:output/predictions/" + p.name], capture_output=True, encoding="utf-8").stdout
    if not head.strip():
        continue
    old = json.loads(head); new = json.loads(p.read_text(encoding="utf-8"))
    tag = "[LABELLED]  " if p.name in gt else "[unlabelled]"
    on, nn = old["personal_details"].get("name", ""), new["personal_details"].get("name", "")
    if on != nn:
        name_changes += 1
        out.append("%s %s: name '%s' -> '%s'" % (tag, p.name, on, nn))
    oe, ne = old["experience"], new["experience"]
    if len(oe) != len(ne):
        exp_changes += 1
        out.append("%s %s: experience entries %d -> %d" % (tag, p.name, len(oe), len(ne)))
out.append("")
out.append("Names changed: %d | resumes with a different number of experience entries: %d" % (name_changes, exp_changes))
out.append("Empty names now: %d of %d" % (sum(1 for p in Path("output/predictions").glob("*.json")
           if not json.loads(p.read_text(encoding="utf-8"))["personal_details"].get("name")), len(list(Path("output/predictions").glob("*.json")))))
Path("scratch/unlabelled_delta.txt").write_text("\n".join(out).encode("ascii", "replace").decode("ascii"), encoding="ascii")
print("written scratch/unlabelled_delta.txt")
