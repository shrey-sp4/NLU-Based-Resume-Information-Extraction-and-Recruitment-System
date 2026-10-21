"""Read-only: how close are the fields the shortlisting system consumes to the hand labels?
Writes scratch/shortlist_inputs.txt (ASCII-safe)."""
import json, re, statistics
from datetime import date
from pathlib import Path

REF = date(2026, 10, 20)
REF_Y = REF.year + REF.month / 12.0
MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
YEAR = re.compile(r"(?:19|20)\d{2}")
OPEN_END = re.compile(r"present|current|till\s+date|till\s+now|\bnow\b|onward|\bdate\b", re.I)

def endpoint(text, pos):
    y = float(YEAR.match(text[pos:pos + 4]).group(0))
    before = text[max(0, pos - 12):pos].lower()
    m = re.findall(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", before)
    return y + ((MONTHS[m[-1]] - 0.5) / 12.0 if m else 0.5)

def interval(dates):
    s = dates or ""
    years = [m.start() for m in YEAR.finditer(s)]
    if not years:
        return None
    start = endpoint(s, years[0])
    if OPEN_END.search(s):
        end = REF_Y
    elif len(years) >= 2:
        end = endpoint(s, years[1])
    else:
        return None
    return (start, end) if end >= start else None

def total_years(date_strings):
    iv = sorted(i for i in (interval(d) for d in date_strings) if i)
    total, cur_s, cur_e = 0.0, None, None
    for a, b in iv:
        if cur_e is None or a > cur_e:
            if cur_e is not None:
                total += cur_e - cur_s
            cur_s, cur_e = a, b
        else:
            cur_e = max(cur_e, b)
    if cur_e is not None:
        total += cur_e - cur_s
    return total

LEVELS = [("phd", r"ph\.?\s?d|doctor\s+of\s+philosophy|d\.?\s?phil"),
          ("masters", r"m\.?\s?tech|m\.?\s?sc|\bm\.?e\b|master|\bmca\b|\bmba\b|m\.?\s?phil|\bm\.?a\b|\bm\.?s\b"),
          ("bachelors", r"b\.?\s?tech|b\.?\s?sc|\bb\.?e\b|bachelor|\bbca\b|\bb\.?a\b")]
ADVISOR = re.compile(r"advisor|supervisor|\bguide\b", re.I)

def highest(strings):
    found = set()
    for s in strings:
        for name, pat in LEVELS:
            if re.search(pat, s or "", re.I):
                found.add(name)
    for name, _ in LEVELS:
        if name in found:
            return name
    return "none"

def pub_counts(pubs):
    c = lambda k: len(pubs.get(k, []) or [])
    return (c("journal_articles"), c("conference_papers") + c("conference_proceedings"),
            sum(c(k) for k in pubs if k not in ("journal_articles", "conference_papers", "conference_proceedings")))

rows, out = [], []
for gt_path in sorted(Path("ground_truth").glob("*.json")):
    pred_path = Path("output/predictions") / gt_path.name
    if not pred_path.exists():
        continue
    g = json.loads(gt_path.read_text(encoding="utf-8")); p = json.loads(pred_path.read_text(encoding="utf-8"))
    g_name = (g.get("personal_details", {}).get("name") or "").strip().lower()
    p_name = (p.get("personal_details", {}).get("name") or "").strip().lower()
    g_deg = highest([e.get("degree", "") for e in g.get("education", [])])
    p_deg = highest([e.get("degree", "") for e in p.get("education", [])
                     if not ADVISOR.search(e.get("raw_text", "") or "") and (e.get("institution", "") or "").lower() not in ("advisor", "co-advisor", "supervisor")])
    g_exp = total_years([e.get("duration", "") for e in g.get("experience", [])])
    p_exp = total_years([e.get("dates", "") for e in p.get("experience", [])])
    g_pub, p_pub = pub_counts(g.get("publications", {})), pub_counts(p.get("publications", {}))
    rows.append(dict(name=gt_path.stem, name_ok=(g_name == p_name), g_name=g_name, p_name=p_name,
                     g_deg=g_deg, p_deg=p_deg, g_exp=g_exp, p_exp=p_exp, g_pub=g_pub, p_pub=p_pub))

out.append("%-24s %-5s %-9s %-9s %6s %6s  %-14s %-14s" % ("resume", "name", "GT deg", "pred deg", "GTexp", "predE", "GT pubs J/C/O", "pred J/C/O"))
for r in rows:
    out.append("%-24s %-5s %-9s %-9s %6.1f %6.1f  %-14s %-14s" % (r["name"][:24], "ok" if r["name_ok"] else "DIFF", r["g_deg"], r["p_deg"],
               r["g_exp"], r["p_exp"], "/".join(map(str, r["g_pub"])), "/".join(map(str, r["p_pub"]))))
errs = [abs(r["g_exp"] - r["p_exp"]) for r in rows]
out.append("")
out.append("Names exactly right           : %d/%d" % (sum(r["name_ok"] for r in rows), len(rows)))
out.append("Highest degree level correct  : %d/%d" % (sum(r["g_deg"] == r["p_deg"] for r in rows), len(rows)))
out.append("PhD gate (has PhD) correct    : %d/%d" % (sum((r["g_deg"] == "phd") == (r["p_deg"] == "phd") for r in rows), len(rows)))
out.append("Experience years abs error    : median %.1f y, within 0.5y: %d/%d, within 1y: %d/%d" % (
    statistics.median(errs), sum(e <= 0.5 for e in errs), len(rows), sum(e <= 1.0 for e in errs), len(rows)))
out.append("Total pubs (all types) exact  : %d/%d" % (sum(sum(r["g_pub"]) == sum(r["p_pub"]) for r in rows), len(rows)))
out.append("Total pubs within +-10%%       : %d/%d" % (sum(abs(sum(r["g_pub"]) - sum(r["p_pub"])) <= 0.1 * max(1, sum(r["g_pub"])) for r in rows), len(rows)))
text = "\n".join(out)
Path("scratch/shortlist_inputs.txt").write_text(text.encode("ascii", "replace").decode("ascii"), encoding="ascii")
print("written scratch/shortlist_inputs.txt")
