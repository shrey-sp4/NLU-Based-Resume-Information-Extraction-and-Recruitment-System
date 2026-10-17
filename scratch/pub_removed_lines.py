"""List every line Stage 3 REMOVES from the publications section, for all resumes (read-only).

Run from the project folder AFTER Stage 2:
    python scratch/pub_removed_lines.py
Writes scratch/pub_removed.txt. Read it for real publication text that should not be there.
"""
import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, "src")
sys.stdout = open("scratch/pub_removed.txt", "w", encoding="utf-8")   # avoid Windows console encoding errors
import extract_structured_information as esi

kinds = Counter()
rows = []
for path in sorted(glob.glob("output/sections/*_sections.json")):
    stem = os.path.basename(path).replace("_sections.json", "")
    with open(path, encoding="utf-8") as f:
        groups = json.load(f).get("publication_groups") or []
    for g in groups:
        for line in g["text"].splitlines():
            r = esi._inline_subheading(line)
            if r is not None and line.strip():
                kinds["line:" + r[0]] += 1
                rows.append((stem, "line-" + r[0], line.strip()))
    for hint, chunk in esi._typed_segments("", groups):
        for e in [q for x in esi.split_publication_entries(chunk) for q in esi.split_glued_references(x)]:
            if esi._is_activity_entry(e):
                kinds["entry:activity"] += 1
                rows.append((stem, "entry-activity", e))
            elif esi._is_non_citation_entry(e):
                kinds["entry:non-citation"] += 1
                rows.append((stem, "entry-noncite", e))

print("Removed items by kind:", dict(kinds))
print("\n(type = heading switches the type; reset = caption removed; skip = list after it ignored)")
for stem, kind, text in rows:
    print(f"{stem[:22]:<22} {kind:<15} | {text[:120]}")