"""Rewrites the stale parts of README.md: stage descriptions, the metrics table (generated from
output/evaluation/section_metrics.csv) and the limitations list. Asserts each anchor matches exactly once."""
import csv, re
from collections import defaultdict
from pathlib import Path

readme = Path("README.md")
text = readme.read_text(encoding="utf-8")
first_run = "**Publication typing**" not in text   # the append-style edits below run only once

# ---- metrics table, generated from the evaluator's own CSV ----
agg = defaultdict(lambda: ([], [], []))
for r in csv.DictReader(open("output/evaluation/section_metrics.csv", encoding="utf-8")):
    a = agg[r["section"]]
    a[0].append(float(r["precision"])); a[1].append(float(r["recall"])); a[2].append(float(r["f1_score"]))
n_resumes = len(next(iter(agg.values()))[0])
lines = ["| FIELD NAME | PRECISION | RECALL | F1 SCORE |", "| :--- | :---: | :---: | :---: |"]
f1s = []
for k in sorted(agg):
    p, r, f = [100 * sum(x) / len(x) for x in agg[k]]
    f1s.append(f)
    lines.append("| `%s` | %.2f%% | %.2f%% | **%.2f%%** |" % (k, p, r, f))
lines.append("| **AVERAGE MACRO FIELD F1 (%d FIELDS)** | | | **%.2f%%** |" % (len(f1s), sum(f1s) / len(f1s)))
table = "\n".join(lines)

metrics_section = (
f"The pipeline is scored against the {n_resumes} hand-labelled academic resumes in `ground_truth/` over {len(f1s)} fields, using "
"`scratch/evaluate_pipeline.py` (numbers below are regenerated from `output/evaluation/section_metrics.csv` by "
"`scratch/update_readme.py`). The remaining resumes have no labels and are only checked with label-free audits.\n\n"
"**How to read these numbers**\n\n"
"- They are **development-set numbers**: the rules were tuned while looking at these same resumes, so they are "
"optimistic for unseen CVs.\n"
"- Experience dates are compared **ignoring whitespace and dash style** (`2015 - Present` equals `2015-Present`). "
"This is a measurement choice made in the evaluator, not an extraction improvement.\n"
"- The publication fields are scored as a **bag of words per publication type**, not paper by paper, so they cannot "
"see missing, truncated or extra papers. `scratch/pub_paper_level.py` gives a title-matched paper-level view.\n\n"
+ table + "\n\n---\n\n")

m1 = re.search(r"^## .*Final 25-Field Pipeline Accuracy Metrics.*\n", text, re.M)
m2 = re.search(r"^## .*Known Pipeline Limitations", text, re.M)
assert m1 and m2 and m1.end() < m2.start(), "section anchors not found"
text = text[:m1.end()] + "\n" + metrics_section + text[m2.start():]

# ---- stage descriptions ----
def sub_line(prefix, new_line):
    global text
    pat = re.compile(r"^" + re.escape(prefix) + r".*$", re.M)
    assert len(pat.findall(text)) == 1, "stage line count for: " + prefix
    text = pat.sub(lambda m: new_line, text)

sub_line("1. **Stage 1: Text Extraction**",
  "1. **Stage 1: Text Extraction**: Extracts page-wise text from PDFs with `pdfplumber`, stripping page markers. If a page "
  "comes out with glued words (missing spaces, common in tightly kerned PDFs) it is re-extracted with a tighter "
  "`x_tolerance`; clean pages are left untouched.")
sub_line("2. **Stage 2: Section Detection**",
  "2. **Stage 2: Section Detection**: Normalizes raw heading variants into canonical section keys (`education`, `experience`, "
  "`skills`, `publications`, etc.) using a JSON lookup map. Sub-headings inside a publications list (\"Journal Articles\") and "
  "repeated running page headers do not end the section. For every publications heading it also records the heading and its "
  "text (`publication_groups`) so Stage 3 can use the author's own headings.")
m3 = re.search(r"^3\. \*\*Stage 3: Entity Extraction\*\*.*$", text, re.M)
assert m3 and len(re.findall(r"^3\. \*\*Stage 3: Entity Extraction\*\*", text, re.M)) == 1
if first_run:
  text = text[:m3.end()] + (
  " **Publication typing** uses, in order: the author's own heading (\"Communicated\", \"Working paper\", \"Book chapters\"...), "
  "an explicit per-entry marker such as \"(Communicated)\", and finally text rules, defaulting to journal article. Activity "
  "lines (talks, workshops attended), count lines (\"Total papers: 65\") and metric lines are filtered out.") + text[m3.end():]

# ---- limitations ----
m4 = re.search(r"^## .*Known Pipeline Limitations.*\n", text, re.M)
extra = (
"4. **Small labelled set**: only 10 resumes are hand-labelled, so every accuracy figure is a development-set figure with wide "
"uncertainty; it is not a held-out estimate.\n"
"5. **Wrapped citations**: a citation whose line wraps in the PDF can still be split into two entries, which inflates "
"publication counts on some long lists.\n"
"6. **Publication categories follow the author's headings**: where an author uses one generic \"Publications\" heading, "
"journal versus conference is decided by text rules and is less reliable.\n")
m5 = re.search(r"\n---\n\n## .*How to Run", text)
assert m5 and m4.end() < m5.start(), "run-section anchor not found"
if first_run:
    text = text[:m5.start()].rstrip("\n") + "\n" + extra + text[m5.start():]

readme.write_text(text, encoding="utf-8")
print("README updated:", n_resumes, "resumes,", len(f1s), "fields, macro %.2f" % (sum(f1s) / len(f1s)))
