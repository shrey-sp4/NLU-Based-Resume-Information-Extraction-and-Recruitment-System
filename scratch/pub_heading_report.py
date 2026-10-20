"""Read-only report: which headings and sub-headings sit inside the publications section.

Run from the project folder AFTER running Stage 2:
    python src/segment_resumes_into_sections.py
    python scratch/pub_heading_report.py > scratch/pub_headings.txt
Nothing is changed by this script.
"""
import glob
import json
import os
import re
from collections import Counter

TYPE_WORDS = re.compile(
    r"journal|conference|proceeding|communicat|submitted|under\s+review|in\s+review|preprint|arxiv|"
    r"book|chapter|report|patent|accepted|published|peer|international|national|symposi|workshop|poster|"
    r"presentation|manuscript|article|paper|letter|magazine|thesis",
    re.IGNORECASE,
)


def looks_like_subheading(line):
    t = line.strip().strip(":-–—|•●■□*➢+ ")
    if not t or len(t.split()) > 8 or len(t) > 70:
        return False
    if re.search(r"\b(?:19|20)\d{2}\b", t):          # references carry years
        return False
    if re.match(r"^\[?\d+[\.\)\]]", t):               # numbered list items
        return False
    if t.endswith(".") and len(t.split()) > 4:        # sentence-like
        return False
    return bool(TYPE_WORDS.search(t))


def gt_summary(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        pubs = json.load(f).get("publications", {})
    return {k: len(v) for k, v in pubs.items() if v}


group_headings = Counter()
inline_candidates = Counter()
labelled_rows = []
total_resumes = 0

for sec_path in sorted(glob.glob("output/sections/*_sections.json")):
    total_resumes += 1
    stem = os.path.basename(sec_path).replace("_sections.json", "")
    with open(sec_path, encoding="utf-8") as f:
        data = json.load(f)
    groups = data.get("publication_groups")
    if groups is None:
        raise SystemExit("No 'publication_groups' key - run Stage 2 again first: python src/segment_resumes_into_sections.py")
    heads, inline = [], []
    for g in groups:
        h = g["heading"].strip()
        group_headings[h.lower()] += 1
        heads.append(h)
        for line in g["text"].splitlines():
            if looks_like_subheading(line):
                key = line.strip().strip(":-–—|•●■□*➢+ ")
                inline_candidates[key.lower()] += 1
                inline.append(key)
    gt = gt_summary(os.path.join("ground_truth", stem + ".json"))
    if gt is not None:
        labelled_rows.append((stem, gt, heads, inline))

print(f"Resumes with sections: {total_resumes}")
print("\n=== A. LABELLED resumes: what the author's GT types look like next to the headings in the text ===")
for stem, gt, heads, inline in labelled_rows:
    print(f"\n{stem[:40]}")
    print("  GT types       :", gt)
    print("  group headings :", heads)
    print("  inline lines   :", inline[:12])

print("\n=== B. Publication GROUP headings across all resumes (count) ===")
for h, c in group_headings.most_common():
    print(f"  {c:3d}  {h}")

print("\n=== C. Inline sub-heading candidates inside publication text, all resumes (count) ===")
for h, c in inline_candidates.most_common(80):
    print(f"  {c:3d}  {h}")