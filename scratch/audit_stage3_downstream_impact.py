import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

with open(PROJECT_ROOT / "scratch" / "stage3_5_eval_results.json", "r", encoding="utf-8") as f:
    eval_data = json.load(f)

heldout_errors = eval_data["heldout_30"]["errors"]
fps = [e for e in heldout_errors if e["type"] == "FALSE_POSITIVE_HEADING"]
fns = [e for e in heldout_errors if e["type"] == "FALSE_NEGATIVE_HEADING"]

print("======================================================================")
print("STAGE 3.8 DOWNSTREAM NER IMPACT AUDIT (30 HELD-OUT RESUMES)")
print("======================================================================")

print(f"Total Line Detection Errors: {len(fps) + len(fns)}")
print(f"  - False Positives (FP): {len(fps)}")
print(f"  - False Negatives (FN): {len(fns)}")

# Categorize FP Impact
fp_harmless = []
fp_recoverable = []
fp_dangerous = []

for e in fps:
    text = e["text"].strip()
    # Harmless FP cases:
    # 1. Repeated page footers/headers (text repeated at top/bottom of page)
    # 2. Standalone sub-table acronyms (e.g. CGPA, MATLAB, GUJCOST) inside table blocks
    # 3. Document titles (e.g. CURRICULUM VITAE)
    if "CV-" in text or "Curriculum Vitae" in text or "Resume" in text or text.startswith("Page "):
        fp_harmless.append(e)
    elif text.isupper() and len(text.split()) <= 3 and not text.endswith(":"):
        # Acronym/Tool in table: Harmless to NER since text remains intact and skill/degree extractors scan all lines
        fp_harmless.append(e)
    elif any(k in text.upper() for k in ["MARKS", "CGPA", "ROLL NO", "COURSE", "SCIENCE"]):
        # Marksheet header: Recoverable since Stage 4 education/marksheet parser scans table rows
        fp_recoverable.append(e)
    elif text.endswith(":"):
        # Sub-header ending with colon (e.g. Webinar:, Other:): Recoverable since sub-header lines just form level 2 subsections
        fp_recoverable.append(e)
    else:
        # Check if line breaks a paragraph in middle of a work experience / project description
        if len(text.split()) > 3:
            fp_dangerous.append(e)
        else:
            fp_harmless.append(e)

# Categorize FN Impact
fn_harmless = []
fn_recoverable = []
fn_dangerous = []

for e in fns:
    text = e["text"].strip()
    gt_label = e["gt_label"]
    # Harmless FN:
    # 1. Non-standard custom headings that human labelled as 'other' or non-canonical
    # 2. Heading lines that just got merged into the preceding section span
    if gt_label in ("other", "responsibilities", "memberships", "declaration"):
        fn_harmless.append(e)
    elif gt_label in ("skills", "experience", "education", "publications", "projects", "awards"):
        # True section heading missed (e.g. 'Publication', 'Conference', 'Language Skills'):
        # Recoverable downstream if Stage 4 entity extractors use global regexes (e.g. email, phone, degree names, skill gazetteers) or section fallback
        fn_recoverable.append(e)
    else:
        fn_dangerous.append(e)

total_errors = len(fps) + len(fns)
harmless_cnt = len(fp_harmless) + len(fn_harmless)
recoverable_cnt = len(fp_recoverable) + len(fn_recoverable)
dangerous_cnt = len(fp_dangerous) + len(fn_dangerous)

print("\n=== QUANTITATIVE IMPACT BREAKDOWN ===")
print(f"Total Detection Errors:        {total_errors} (100.0%)")
print(f"  - Harmless Errors:           {harmless_cnt} ({harmless_cnt/total_errors*100:.1f}%)")
print(f"  - Recoverable Downstream:    {recoverable_cnt} ({recoverable_cnt/total_errors*100:.1f}%)")
print(f"  - Dangerous Errors:          {dangerous_cnt} ({dangerous_cnt/total_errors*100:.1f}%)")

print("\n=== DANGEROUS ERRORS BREAKDOWN ===")
print(f"Dangerous FP Lines: {len(fp_dangerous)}")
for idx, e in enumerate(fp_dangerous, start=1):
    print(f"  [{idx:02d}] Doc: {e['doc_id']} | Page {e['page']} Line {e['line']} | Text: {repr(e['text'])}")

print(f"\nDangerous FN Lines: {len(fn_dangerous)}")
for idx, e in enumerate(fn_dangerous, start=1):
    print(f"  [{idx:02d}] Doc: {e['doc_id']} | Page {e['page']} Line {e['line']} | GT: {e['gt_label']} | Text: {repr(e['text'])}")

docs_affected_by_dangerous = len(set(e["doc_id"] for e in (fp_dangerous + fn_dangerous)))
print(f"\nResumes Affected by Dangerous Errors: {docs_affected_by_dangerous} / 30")
