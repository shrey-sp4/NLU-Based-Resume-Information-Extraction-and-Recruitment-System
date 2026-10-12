"""
Error report: shows exactly WHAT the extraction missed on the 10 labelled resumes.
Run from the project folder:   python scratch/error_report.py
Does not change any existing file. Writes output/evaluation/error_report.txt
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GT_DIR = ROOT / "ground_truth"
PRED_DIR = ROOT / "output" / "predictions"
OUT_FILE = ROOT / "output" / "evaluation" / "error_report.txt"

lines = []


def log(text=""):
    print(text)
    lines.append(text)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def found(gt_value, pred_values):
    """Same idea as the evaluator: a match if one text contains the other."""
    g = norm(gt_value)
    if not g:
        return True
    return any(p and (g in p or p in g) for p in pred_values)


def main():
    if not GT_DIR.exists() or not PRED_DIR.exists():
        sys.exit(f"Missing folder: {GT_DIR} or {PRED_DIR}")

    totals = {"degree": [0, 0], "edu_institution": [0, 0],
              "exp_title": [0, 0], "exp_org": [0, 0], "exp_dates": [0, 0], "pub_count": [0, 0]}

    for gt_file in sorted(GT_DIR.glob("*.json")):
        pred_file = PRED_DIR / gt_file.name
        if not pred_file.exists():
            continue
        gt = json.loads(gt_file.read_text(encoding="utf-8"))
        pred = json.loads(pred_file.read_text(encoding="utf-8"))
        log("=" * 70)
        log(gt_file.name)

        # ---- Education: degree and institution ----
        p_edu = [e for e in pred.get("education", []) if isinstance(e, dict)]
        p_degrees = [norm(e.get("degree")) for e in p_edu]
        p_insts = [norm(e.get("institution")) for e in p_edu]
        p_raw = norm(" ".join(str(e.get("raw_text", "")) for e in p_edu))
        for e in gt.get("education", []):
            if not isinstance(e, dict):
                continue
            d, i = e.get("degree"), e.get("institution")
            if d:
                totals["degree"][1] += 1
                if found(d, p_degrees):
                    totals["degree"][0] += 1
                else:
                    where = "text is in raw_text (parsing problem)" if norm(d)[:6] in p_raw \
                        else "NOT in education section (section problem)"
                    log(f"  MISSED DEGREE      : {d}   -> {where}")
            if i:
                totals["edu_institution"][1] += 1
                if found(i, p_insts):
                    totals["edu_institution"][0] += 1
                else:
                    log(f"  MISSED INSTITUTION : {i}")

        # ---- Experience: title and organisation ----
        p_exp = [e for e in pred.get("experience", []) if isinstance(e, dict)]
        p_blob = norm(json.dumps(p_exp))
        p_titles = [norm(e.get("job_title")) for e in p_exp]
        for e in gt.get("experience", []):
            if not isinstance(e, dict):
                continue
            title, org, dur = e.get("position"), e.get("organization"), e.get("duration")
            if title:
                totals["exp_title"][1] += 1
                if found(title, p_titles):
                    totals["exp_title"][0] += 1
                else:
                    log(f"  MISSED JOB TITLE   : {title} @ {org} ({dur})")
            if org:
                totals["exp_org"][1] += 1
                if norm(org)[:10] in p_blob:
                    totals["exp_org"][0] += 1
                else:
                    log(f"  MISSED ORGANISATION: {org} ({dur})")
            if dur:
                totals["exp_dates"][1] += 1
                if any(norm(dur) in norm(x.get("dates")) for x in p_exp):
                    totals["exp_dates"][0] += 1
                else:
                    log(f"  MISSED DATES       : {dur}  ({title} @ {org})")
        empty_dates = sum(1 for e in p_exp if not str(e.get("dates") or "").strip())
        if empty_dates:
            log(f"  Experience entries with EMPTY dates: {empty_dates} of {len(p_exp)}")

        # ---- Publications: count per resume ----
        gt_n = sum(len(v) for v in gt.get("publications", {}).values())
        pr_n = sum(len(v) for v in pred.get("publications", {}).values())
        totals["pub_count"][1] += gt_n
        totals["pub_count"][0] += min(gt_n, pr_n)
        if gt_n != pr_n:
            log(f"  PUBLICATION COUNT  : true={gt_n}  extracted={pr_n}")

    log("=" * 70)
    log("SUMMARY (found / total in ground truth)")
    for k, (ok, tot) in totals.items():
        pct = 100 * ok / tot if tot else 0
        log(f"  {k:16s}: {ok:3d} / {tot:3d}  = {pct:5.1f}%")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved to {OUT_FILE}")


if __name__ == "__main__":
    main()