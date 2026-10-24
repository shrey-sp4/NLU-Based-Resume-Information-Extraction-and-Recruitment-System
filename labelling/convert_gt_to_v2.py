"""Convert the 10 old-format ground_truth/*.json files into the new shortlister-based format.
Run from the project root:  python convert_gt_to_v2.py
Reads  ground_truth/*.json   Writes  ground_truth_v2/*.json  and  ground_truth_v2/_conversion_report.txt
"""
import json, re, sys
from pathlib import Path

SRC, DST = Path("ground_truth"), Path("ground_truth_v2")
DST.mkdir(exist_ok=True)

SECONDARY = re.compile(r"\b(10th|12th|10\+2|higher\s+secondary|secondary|matric|metric|intermediate|high\s+school|ssc|hsc|cbse|icse|madhyamik)\b", re.I)
LEVELS = [
    ("doctorate", r"ph\.?\s*d|doctor|d\.?\s*phil"),
    ("masters",   r"m\.?\s*tech|m\.?\s*e\b|m\.?\s*sc|m\.?\s*s\b|m\.?\s*a\b|m\.?\s*phil|mba|mca|master|msw|m\.?\s*com"),
    ("bachelors", r"b\.?\s*tech|b\.?\s*e\b|b\.?\s*sc|b\.?\s*s\b|b\.?\s*a\b|bca|bba|bachelor|b\.?\s*com"),
]
ACAD_T = re.compile(r"professor|lecturer|faculty|teaching|research (scholar|associate|fellow)|post-?doc|fellow|\b(srf|jrf)\b|dean|hod|scientist", re.I)
ACAD_I = re.compile(r"universit|institute|college|school|academy|\biit|\bnit\b|\biiit|\biim\b|iisc|vidyapeeth|campus", re.I)
IND_I  = re.compile(r"\b(pvt|ltd|inc|corp|llc|technologies|solutions|services|bank|consultancy|group)\b", re.I)

def level(deg):
    for name, pat in LEVELS:
        if re.search(pat, deg, re.I): return name
    return "other"

def etype(title, inst):
    a_t, a_i, i_i = bool(ACAD_T.search(title)), bool(ACAD_I.search(inst)), bool(IND_I.search(inst))
    if a_t and not i_i: return "academic"
    if a_i and not i_i: return "academic"
    if i_i and not a_i: return "industry"
    return ""   # ambiguous: you fill it in by hand

TYPE_MAP = {"journal_articles": "journal", "conference_papers": "conference",
            "conference_proceedings": "conference"}   # everything else -> other

report = []
for f in sorted(SRC.glob("*.json")):
    d = json.load(open(f, encoding="utf-8"))
    out = {"resume_file": f.stem + ".pdf",
           "candidate_name": (d.get("personal_details") or {}).get("name", ""),
           "education": [], "experience": [], "publications": [],
           "stated_totals": {"journal": None, "conference": None, "total": None},
           "notes": ""}
    dropped = 0
    for e in d.get("education", []):
        deg = e.get("degree", "") or ""
        if SECONDARY.search(deg) and level(deg) == "other":
            dropped += 1; continue
        out["education"].append({"degree": deg, "degree_level": level(deg),
                                 "stream": e.get("field", ""), "institution": e.get("institution", "")})
    blank_type = 0
    for e in d.get("experience", []):
        t, i = e.get("position", ""), e.get("organization", "")
        et = etype(t, i); blank_type += (et == "")
        out["experience"].append({"job_title": t, "institution": i,
                                  "dates": e.get("duration", ""), "experience_type": et})
    npub = 0
    for cat, items in (d.get("publications") or {}).items():
        flat = []
        for p in items:                      # one old file stores a nested list of papers: flatten it
            flat.extend(p if isinstance(p, list) else [p])
        for p in flat:
            if isinstance(p, str): p = {"title": p}
            venue = p.get("journal") or p.get("conference") or p.get("publisher") or ""
            out["publications"].append({"title": p.get("title", ""), "type": TYPE_MAP.get(cat, "other"),
                                        "year": p.get("year", "") or "", "venue": venue})
            npub += 1
    json.dump(out, open(DST / f.name, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    report.append(f"{f.name}: education {len(out['education'])} (dropped {dropped} school-level), "
                  f"experience {len(out['experience'])} ({blank_type} need experience_type by hand), publications {npub}")
txt = "\n".join(report)
(DST / "_conversion_report.txt").write_text(txt, encoding="utf-8")
print(txt.encode("ascii", "replace").decode())
