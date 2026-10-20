"""Label-free quality gates over ALL predictions (no ground truth needed).

Run from the project folder:  python scratch/quality_report.py
Splits results into the 10 labelled resumes and the 30 unlabelled ones, so you can see
whether gains seen on the labelled set also show up on resumes the rules were never tuned on.
"""
import glob
import json
import os
import re

YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
LABELLED = {os.path.basename(p) for p in glob.glob("ground_truth/*.json")}


def pct(a, b):
    return f"{(100.0 * a / b):5.1f}%" if b else "  n/a"


def analyse(paths):
    s = dict(resumes=0, no_name=0, exp_total=0, exp_real=0, exp_partial=0, exp_junk=0,
             exp_no_inst=0, edu_total=0, edu_degree=0, edu_inst=0, edu_inst_odd=0,
             pub_total=0, pub_year=0, pub_giant=0)
    for path in paths:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        s["resumes"] += 1
        if not (d.get("personal_details", {}).get("name") or "").strip():
            s["no_name"] += 1
        for e in d.get("experience", []):
            s["exp_total"] += 1
            has_t, has_d = bool(e.get("job_title")), bool(e.get("dates"))
            if has_t and has_d:
                s["exp_real"] += 1
            elif has_t or has_d:
                s["exp_partial"] += 1
            else:
                s["exp_junk"] += 1
            if not e.get("institution"):
                s["exp_no_inst"] += 1
        for e in d.get("education", []):
            s["edu_total"] += 1
            if e.get("degree"):
                s["edu_degree"] += 1
            inst = (e.get("institution") or "").strip()
            if inst:
                s["edu_inst"] += 1
                # heuristic: an institution name that is very long or holds grades/percent is probably junk
                if len(inst) > 100 or re.search(r"cgpa|percentage|%|\bgpa\b", inst, re.IGNORECASE):
                    s["edu_inst_odd"] += 1
        for entries in (d.get("publications") or {}).values():
            for p in entries:
                s["pub_total"] += 1
                if YEAR.search(p):
                    s["pub_year"] += 1
                if len(p) > 1200:
                    s["pub_giant"] += 1
    return s


def show(title, s):
    print(f"\n=== {title}  ({s['resumes']} resumes) ===")
    print(f"Resumes with EMPTY name         : {s['no_name']} of {s['resumes']}")
    print(f"Experience entries              : {s['exp_total']}")
    print(f"  real jobs (title AND date)    : {s['exp_real']:4d}  {pct(s['exp_real'], s['exp_total'])}")
    print(f"  partial (title OR date)       : {s['exp_partial']:4d}  {pct(s['exp_partial'], s['exp_total'])}")
    print(f"  junk (neither)                : {s['exp_junk']:4d}  {pct(s['exp_junk'], s['exp_total'])}   <- target < 20%")
    print(f"  no institution                : {s['exp_no_inst']:4d}  {pct(s['exp_no_inst'], s['exp_total'])}")
    print(f"Education entries               : {s['edu_total']}")
    print(f"  with a degree                 : {s['edu_degree']:4d}  {pct(s['edu_degree'], s['edu_total'])}")
    print(f"  with an institution           : {s['edu_inst']:4d}  {pct(s['edu_inst'], s['edu_total'])}")
    print(f"  odd institution (long/grades) : {s['edu_inst_odd']:4d}  {pct(s['edu_inst_odd'], s['edu_inst'])}")
    print(f"Publication entries             : {s['pub_total']}")
    print(f"  containing a year             : {s['pub_year']:4d}  {pct(s['pub_year'], s['pub_total'])}")
    print(f"  giant (>1200 chars, unsplit?) : {s['pub_giant']:4d}")


all_paths = sorted(glob.glob("output/predictions/*.json"))
lab = [p for p in all_paths if os.path.basename(p) in LABELLED]
unl = [p for p in all_paths if os.path.basename(p) not in LABELLED]
show("LABELLED (tuned on)", analyse(lab))
show("UNLABELLED (not tuned on)", analyse(unl))
show("ALL", analyse(all_paths))