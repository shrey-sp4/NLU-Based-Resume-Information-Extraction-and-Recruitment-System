import glob, json, os, subprocess

BUCKETS = ["journal_articles", "conference_papers", "conference_proceedings",
           "communications", "book_chapters", "books", "technical_reports", "preprints"]
changed = 0
for path in sorted(glob.glob("output/predictions/*.json")):
    rel = path.replace("\\", "/")
    res = subprocess.run(["git", "show", "HEAD:" + rel], capture_output=True, encoding="utf-8")
    if res.returncode != 0:
        continue
    old = json.loads(res.stdout).get("publications", {})
    with open(path, encoding="utf-8") as f:
        new = json.load(f).get("publications", {})
    diffs = []
    for b in BUCKETS:
        o, n = len(old.get(b, [])), len(new.get(b, []))
        if o != n:
            diffs.append(f"{b} {o}->{n}")
    if diffs:
        changed += 1
        tag = "[LABELLED]" if os.path.exists(os.path.join("ground_truth", os.path.basename(path))) else "[unlabelled]"
        print(f"{tag:<13} {os.path.basename(path)}: " + "; ".join(diffs))
print(f"\nResumes whose publication buckets changed: {changed}")