"""Publication TYPE accuracy on the labelled resumes (matched by title), 8-way and 3-way.

3-way = what the shortlisting system sees:  journal / conference / other.
Run from the project folder:  python scratch/pub_type_report.py
"""
import glob
import json
import os
import re
from collections import Counter


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


THREE = {"journal_articles": "journal", "conference_papers": "conference", "conference_proceedings": "conference"}


def t3(bucket):
    return THREE.get(bucket, "other")


def title_of(item):
    if isinstance(item, dict):
        return item.get("title", "")
    if isinstance(item, list):
        return " ".join(map(str, item))
    return str(item)


conf8, conf3 = Counter(), Counter()
gt_total = found = 0
for gt_path in sorted(glob.glob("ground_truth/*.json")):
    name = os.path.basename(gt_path)
    pred_path = os.path.join("output", "predictions", name)
    if not os.path.exists(pred_path):
        continue
    with open(gt_path, encoding="utf-8") as f:
        gt = json.load(f).get("publications", {})
    with open(pred_path, encoding="utf-8") as f:
        pr = json.load(f).get("publications", {})
    pool = [(b, norm(e)) for b, v in pr.items() for e in v]
    for gt_bucket, items in gt.items():
        for item in items:
            gt_total += 1
            key = norm(title_of(item))[:60]
            hit = None
            if len(key) >= 20:
                for b, text in pool:
                    if key in text:
                        hit = b
                        break
            if hit is None:
                conf8[(gt_bucket, "NOT FOUND")] += 1
                conf3[(t3(gt_bucket), "NOT FOUND")] += 1
                continue
            found += 1
            conf8[(gt_bucket, hit)] += 1
            conf3[(t3(gt_bucket), t3(hit))] += 1

ok8 = sum(v for (a, b), v in conf8.items() if a == b)
ok3 = sum(v for (a, b), v in conf3.items() if a == b)
print(f"Labelled papers: {gt_total} | found in predictions by title: {found}")
print("\n8-way confusion (labelled type -> predicted type):")
for (a, b), v in sorted(conf8.items(), key=lambda x: -x[1]):
    print(f"  {a:<24}-> {b:<24}{v:4d}{'   <-- wrong' if a != b and b != 'NOT FOUND' else ''}")
print("\n3-way confusion (what shortlisting sees):")
for (a, b), v in sorted(conf3.items(), key=lambda x: -x[1]):
    print(f"  {a:<11}-> {b:<11}{v:4d}")
print(f"\n8-way type accuracy among found papers: {ok8}/{found} = {100.0 * ok8 / max(found, 1):.1f}%")
print(f"3-way type accuracy among found papers: {ok3}/{found} = {100.0 * ok3 / max(found, 1):.1f}%")