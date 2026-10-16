"""Read-only audit: publication entries that do not look like citations.

Run from the project folder AFTER Stage 3:
    python scratch/pub_noncitation_audit.py
Writes scratch/pub_noncitation.txt. Changes nothing.

An entry is SUSPECT when it has no page/volume/DOI/ISSN marker AND
  (A) reads like an event or activity (workshop, FDP, organized by, course ...), or
  (B) has no year and no publication-venue word at all (fragments, name lists).
"""
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout = open("scratch/pub_noncitation.txt", "w", encoding="utf-8")   # avoid Windows console encoding errors

YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
LOCATOR = re.compile(r"\bpp?\.?\s*\d|\bvol(?:ume)?\.?\s*\d|\bdoi\b|\bissn\b|\bisbn\b|\d+\s*\(\d+\)\s*,?\s*\d+\s*[-–]\s*\d+|\b\d+\s*[-–]\s*\d+\b", re.IGNORECASE)
VENUE = re.compile(r"journal|proceedings|transactions|letters|review|press|springer|elsevier|ieee|acm|wiley|taylor|arxiv|"
                   r"conference|symposium|congress|bulletin|annals|magazine|chapter|publisher|university|report", re.IGNORECASE)
EVENT = re.compile(r"organi[sz]ed\s+by|sponsored\s+by|\bworkshop\b|\bseminar\b|\bwebinar\b|\bfdp\b|\bsttp\b|faculty\s+development|"
                   r"short[- ]term\s+course|refresher|orientation|\btraining\b|\bcertificate\b|resource\s+person|keynote|"
                   r"invited|guest\s+lecture|organizing\s+committee|\bcourse\b|\bsession\b|\bparticipat|\battend", re.IGNORECASE)

counts = Counter()
suspects = defaultdict(list)
per_resume = Counter()
for path in sorted(glob.glob("output/predictions/*.json")):
    name = os.path.basename(path).replace(".json", "")
    with open(path, encoding="utf-8") as f:
        pubs = json.load(f).get("publications", {})
    for bucket, entries in pubs.items():
        for e in entries:
            counts[bucket] += 1
            if LOCATOR.search(e):
                continue
            kind = None
            if EVENT.search(e):
                kind = "A_event_like"
            elif not YEAR.search(e) and not VENUE.search(e):
                kind = "B_no_signal"
            if kind:
                suspects[(bucket, kind)].append((name, e))
                per_resume[name] += 1

print("ALL entries per bucket:", dict(counts))
print("\nSUSPECT entries per bucket and kind:")
for (bucket, kind), items in sorted(suspects.items(), key=lambda x: -len(x[1])):
    print(f"  {bucket:<24} {kind:<13} {len(items):4d}   (of {counts[bucket]} in that bucket)")
print("\nResumes with most suspects:")
for name, c in per_resume.most_common(12):
    print(f"  {c:3d}  {name}")
print("\nEXAMPLES (up to 6 per bucket/kind):")
for (bucket, kind), items in sorted(suspects.items(), key=lambda x: -len(x[1])):
    print(f"\n[{bucket} / {kind}]")
    for name, e in items[:6]:
        print(f"   {name[:24]:<24} | {e[:105]}")