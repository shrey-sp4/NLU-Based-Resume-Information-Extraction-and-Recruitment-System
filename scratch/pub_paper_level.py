"""Paper-level publication score on the labelled resumes (matches papers by title, not by word overlap).

Run from the project folder AFTER Stage 3:
    python scratch/pub_paper_level.py
The official evaluator treats each publication type as a bag of words, so it cannot see lost,
truncated or extra papers. This script can.
"""
import glob
import json
import os
import re
import sys

sys.stdout = open("scratch/pub_paper_level.txt", "w", encoding="utf-8")   # avoid Windows console encoding errors


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def title_of(item):
    if isinstance(item, dict):
        return item.get("title", "")
    if isinstance(item, list):
        return " ".join(map(str, item))
    return str(item)


THREE = {"journal_articles": "journal", "conference_papers": "conference", "conference_proceedings": "conference"}
t3 = lambda b: THREE.get(b, "other")

G = P = found = ok8 = ok3 = matched_pred = 0
print(f"{'resume':<24}{'labelled':>9}{'predicted':>10}{'found':>7}{'type ok':>8}{'pred w/o label':>16}")
for gt_path in sorted(glob.glob("ground_truth/*.json")):
    name = os.path.basename(gt_path)
    pred_path = os.path.join("output", "predictions", name)
    if not os.path.exists(pred_path):
        continue
    with open(gt_path, encoding="utf-8") as f:
        gt = json.load(f).get("publications", {})
    with open(pred_path, encoding="utf-8") as f:
        pr = json.load(f).get("publications", {})
    preds = [(b, norm(e)) for b, v in pr.items() for e in v]
    keys = [(gb, norm(title_of(it))[:60]) for gb, v in gt.items() for it in v]
    f_n = t_ok = 0
    for gb, k in keys:
        if len(k) < 20:
            continue
        hit = next((pb for pb, pe in preds if k in pe), None)
        if hit is not None:
            f_n += 1
            t_ok += (t3(hit) == t3(gb))
            ok8 += (hit == gb)
    mp = sum(1 for _, pe in preds if any(len(k) >= 20 and k in pe for _, k in keys))
    G += len(keys); P += len(preds); found += f_n; ok3 += t_ok; matched_pred += mp
    print(f"{name[:23]:<24}{len(keys):>9}{len(preds):>10}{f_n:>7}{t_ok:>8}{len(preds) - mp:>16}")
print(f"\nLabelled papers: {G} | predicted entries: {P}")
print(f"Found (recall)        : {found}/{G} = {100.0 * found / G:.1f}%")
print(f"Type correct (3-way)  : {ok3}/{found} = {100.0 * ok3 / max(found, 1):.1f}% of found")
print(f"Type correct (8-way)  : {ok8}/{found} = {100.0 * ok8 / max(found, 1):.1f}% of found")
print(f"Predicted entries that contain a labelled title: {matched_pred}/{P} = {100.0 * matched_pred / P:.1f}%")
print("'pred w/o label' can be real papers the labeller did not list, or junk - read them before judging.")