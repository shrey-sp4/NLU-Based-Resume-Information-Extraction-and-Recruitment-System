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
cls_mismatches = [e for e in heldout_errors if e["type"] == "CLASSIFICATION_MISMATCH"]

print("======================================================================")
print("STAGE 3.6 DETAILED FAILURE MODE & QUANTITIES AUDIT")
print("======================================================================")

print(f"\n1. QUANTITY UNITS DISAMBIGUATION (HELD-OUT 30 RESUMES):")
print(f"  - Total Resumes in Test Set: 30")
print(f"  - Total Evaluated Lines in Test Set: {eval_data.get('heldout_30', {}).get('tn', 0) + len(fps) + len(fns) + eval_data['heldout_30']['tp']}")
print(f"  - False Positive Line Predictions: {len(fps)}")
print(f"  - False Negative Line Predictions: {len(fns)}")
print(f"  - Total Heading Detection Line Errors (FP + FN): {len(fps) + len(fns)}")
print(f"  - Classification Mismatch Line Predictions (on TP): {len(cls_mismatches)}")
print(f"  - Total Categorized Line Errors: {len(heldout_errors)}")

# Group False Positives by Pattern
fp_by_doc = defaultdict(list)
fp_patterns = Counter()

for e in fps:
    doc_id = e["doc_id"]
    text = e["text"].strip()
    fp_by_doc[doc_id].append(e)

    # Classify pattern category
    if "CV-" in text or "Curriculum Vitae" in text or "Resume" in text or text.startswith("Page ") or "CV page" in text:
        cat = "A_REPEATED_PAGE_HEADER_FOOTER"
    elif text.startswith("ISBN") or "DOI:" in text or "ISSN" in text or "10." in text or "PMC" in text or "http" in text:
        cat = "B_PUBLICATION_METADATA"
    elif "MARKS" in text or "CGPA" in text or "Aggregate" in text or "COURSE" in text or "SCIENCE" in text or "Education" in text:
        cat = "C_MARKSHEET_TABLE_HEADER"
    elif text.isupper() and len(text.split()) <= 3:
        cat = "D_SHORT_ALL_CAPS_BODY_TEXT"
    elif text.endswith(":"):
        cat = "E_SUB_HEADER_COLON_LINE"
    else:
        cat = "F_OTHER_FORMATTING_ARTIFACT"

    fp_patterns[cat] += 1

print("\n2. FALSE POSITIVE PATTERN CATEGORIES & IMPACT:")
for cat, cnt in fp_patterns.most_common():
    docs_affected = len(set(e["doc_id"] for e in fps if (
        ("CV-" in e["text"] or "Curriculum Vitae" in e["text"] or "Resume" in e["text"] or e["text"].startswith("Page ") or "CV page" in e["text"]) if cat == "A_REPEATED_PAGE_HEADER_FOOTER" else
        ("ISBN" in e["text"] or "DOI:" in e["text"] or "ISSN" in e["text"] or "10." in e["text"] or "PMC" in e["text"] or "http" in e["text"]) if cat == "B_PUBLICATION_METADATA" else
        ("MARKS" in e["text"] or "CGPA" in e["text"] or "Aggregate" in e["text"] or "COURSE" in e["text"] or "SCIENCE" in e["text"] or "Education" in e["text"]) if cat == "C_MARKSHEET_TABLE_HEADER" else
        (e["text"].isupper() and len(e["text"].split()) <= 3) if cat == "D_SHORT_ALL_CAPS_BODY_TEXT" else
        (e["text"].endswith(":")) if cat == "E_SUB_HEADER_COLON_LINE" else
        True
    )))
    print(f"  - [{cat:<30}] FP Lines: {cnt:<4} | Affected Resumes: {docs_affected}")

print("\n3. REPEATED PAGE HEADER / FOOTER DEEP DIVE:")
repeated_header_fps = [e for e in fps if "CV-" in e["text"] or "Curriculum Vitae" in e["text"] or "Resume" in e["text"] or "CV page" in e["text"]]
docs_with_repeated_headers = set(e["doc_id"] for e in repeated_header_fps)
print(f"  - Resumes Affected by Repeated Headers/Footers: {len(docs_with_repeated_headers)}")
print(f"  - Total FP Lines from Repeated Headers/Footers: {len(repeated_header_fps)}")

print("\nSample Repeated Header Lines across pages:")
for e in repeated_header_fps[:10]:
    print(f"    Doc: {e['doc_id']} | Page {e['page']} Line {e['line']} | Text: {repr(e['text'])}")
