"""Audit how publication headings, sub-headings and activity lines were handled (read-only).

Run from the project folder:
    python scratch/pub_audit.py                      (default list of resumes)
    python scratch/pub_audit.py CV-_Amit_Parikh_2    (any resume name, without .json)
Writes scratch/pub_audit.txt
"""
import json
import os
import sys

sys.path.insert(0, "src")
sys.stdout = open("scratch/pub_audit.txt", "w", encoding="utf-8")   # avoid Windows console encoding errors
import extract_structured_information as esi

DEFAULT = ["Dibakar_Resume_June_2024", "CV-Anurag_Choudhary", "CV-_Amit_Parikh_2", "Resume_SPK_final"]
names = sys.argv[1:] or DEFAULT

for stem in names:
    path = os.path.join("output", "sections", stem + "_sections.json")
    if not os.path.exists(path):
        print(f"\n### {stem}: no sections file at {path}")
        continue
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    groups = data.get("publication_groups") or []
    print(f"\n################ {stem}")
    print("A. group headings -> type given:")
    for g in groups:
        print(f"   {g['heading'][:60]!r:<64} -> {esi._heading_type(g['heading'])}")
    print("B. lines treated as sub-headings (these lines are REMOVED from the entries):")
    found = False
    for g in groups:
        for line in g["text"].splitlines():
            r = esi._inline_subheading(line)
            if r is not None:
                found = True
                print(f"   {str(r):<28} | {line.strip()[:95]}")
    if not found:
        print("   (none)")
    print("C. entries dropped as activity lines (not publications):")
    dropped = 0
    for hint, chunk in esi._typed_segments("", groups):
        for e in [q for x in esi.split_publication_entries(chunk) for q in esi.split_glued_references(x)]:
            if esi._is_activity_entry(e):
                dropped += 1
                if dropped <= 6:
                    print(f"   - {e[:110]}")
    print(f"   total dropped: {dropped}")
    kept = {}
    for hint, chunk in esi._typed_segments("", groups):
        for e in [q for x in esi.split_publication_entries(chunk) for q in esi.split_glued_references(x)]:
            if not esi._is_activity_entry(e):
                b = hint or esi.classify_publication(e)
                kept[b] = kept.get(b, 0) + 1
    print("D. entries kept per type:", kept)