"""Check ground_truth_v2/*.json against the schema.  Run from the project root:  python validate_gt_v2.py"""
import json, sys
from pathlib import Path
KEYS = {"resume_file","candidate_name","education","experience","publications","stated_totals","notes"}
EDU = {"degree","degree_level","stream","institution"}
EXP = {"job_title","institution","dates","experience_type"}
PUB = {"title","type","year","venue"}
LVL = {"doctorate","masters","bachelors","other"}
ET = {"academic","industry","other"}
PT = {"journal","conference","other"}
bad = 0
files = sorted(Path("ground_truth_v2").glob("*.json"))
for f in files:
    d = json.load(open(f, encoding="utf-8")); errs = []
    if set(d) != KEYS: errs.append(f"top-level keys differ: missing {KEYS-set(d)} extra {set(d)-KEYS}")
    if not str(d.get("candidate_name","")).strip(): errs.append("candidate_name empty")
    for i,e in enumerate(d.get("education",[])):
        if set(e)!=EDU: errs.append(f"education[{i}] keys wrong")
        elif e["degree_level"] not in LVL: errs.append(f"education[{i}] degree_level '{e['degree_level']}'")
        elif not e["degree"].strip(): errs.append(f"education[{i}] degree empty")
    for i,e in enumerate(d.get("experience",[])):
        if set(e)!=EXP: errs.append(f"experience[{i}] keys wrong")
        elif e["experience_type"] not in ET: errs.append(f"experience[{i}] experience_type empty/invalid")
        elif not e["dates"].strip(): print(f"   (warning) {f.name} experience[{i}] has no dates - fine if the CV prints none")
    for i,e in enumerate(d.get("publications",[])):
        if set(e)!=PUB: errs.append(f"publications[{i}] keys wrong")
        elif e["type"] not in PT: errs.append(f"publications[{i}] type '{e['type']}'")
        elif not e["title"].strip(): errs.append(f"publications[{i}] title empty")
    if set(d.get("stated_totals",{}))!={"journal","conference","total"}: errs.append("stated_totals keys wrong")
    if errs:
        bad += 1; print(f.name); [print("   -", x.encode('ascii','replace').decode()) for x in errs]
print(f"\n{len(files)} files checked, {bad} with problems")
