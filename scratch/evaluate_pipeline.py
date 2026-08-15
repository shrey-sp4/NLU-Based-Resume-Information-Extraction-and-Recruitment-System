from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
GT_DIR = PROJECT_ROOT / "ground_truth"
SECTIONS_DIR = PROJECT_ROOT / "output" / "sections"
EVAL_DIR = PROJECT_ROOT / "output" / "evaluation"

GT_PDF_MAP = [
    ("A_Mitesh_CV.json", "A_Mitesh_CV_sections.json", "A_Mitesh_CV_88e32579"),
    ("Afzal_Beg_Resume.json", "Afzal_Beg_Resume_sections.json", "Afzal_Beg_Resume_fa289535"),
    ("Anibrata_Pal_Resume.json", "Anibrata_Pal_Resume_sections.json", "Anibrata_Pal_Resume_c35c7b6c"),
    ("CV-Anurag_Choudhary.json", "CV-Anurag_Choudhary_sections.json", "CV_Anurag_Choudhary_15b316ad"),
    ("CV_Arghya_Maity.json", "CV_Arghya_Maity_sections.json", "CV_Arghya_Maity_3f200851"),
    ("CV_Chandan.json", "CV_Chandan_sections.json", "CV_Chandan_f5f89208"),
    ("Dr_Akash_Thakkar_CV.json", "Dr_Akash_Thakkar_CV_sections.json", "Dr_Akash_Thakkar_CV_df681585"),
    ("Resume_Kritishnu_Sanyal.json", "Resume_Kritishnu_Sanyal_sections.json", "Resume_Kritishnu_Sanyal_856a9dfa"),
    ("Resume_final_Amit_CMA_IIM_A.json", "Resume_final_Amit_CMA_IIM_A_sections.json", "Resume_final_Amit_CMA_IIM_A_5b066fd0"),
]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extract_structured_information import process_resume, extract_all_phones, phone_matches, normalize_phone_for_compare

# Regex engines for parsing fine-grained subfields from extracted sections
DEGREE_REGEX = re.compile(r"\b(Ph\.?D\.?|Doctor of Philosophy|M\.?Tech\.?|B\.?Tech\.?|M\.?Sc\.?|B\.?Sc\.?|B\.?E\.?|M\.?E\.?|Bachelor|Master|Diploma)\b", re.IGNORECASE)
YEAR_REGEX = re.compile(r"\b(19|20)\d{2}\b")
GRADE_REGEX = re.compile(r"\b\d+\.\d+\s*%?\b|\b\d+%\b", re.IGNORECASE)
TITLE_REGEX = re.compile(r"\b(Assistant Professor|Associate Professor|Professor|Post-?doctoral Fellow|Visiting Assistant Professor|Senior Research Scholar|Project Associate|Senior Survey Scientist|Research Associate|Lecturer)\b", re.IGNORECASE)

def tokenize(text: str) -> Set[str]:
    return set(re.findall(r"\b\w+\b", str(text or "").lower()))

def calc_f1(gt_text: str, pred_text: str) -> Tuple[float, float, float]:
    gt_tokens = tokenize(gt_text)
    pred_tokens = tokenize(pred_text)
    if not gt_tokens and not pred_tokens: return 1.0, 1.0, 1.0
    if not gt_tokens or not pred_tokens: return 0.0, 0.0, 0.0
    tp = len(gt_tokens.intersection(pred_tokens))
    fp = len(pred_tokens - gt_tokens)
    fn = len(gt_tokens - pred_tokens)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

def score_entity_set_match(gt_vals: List[str], pred_vals: List[str]) -> Tuple[float, float, float]:
    if not gt_vals and not pred_vals: return 1.0, 1.0, 1.0
    if not gt_vals or not pred_vals: return 0.0, 0.0, 0.0

    tp = 0
    matched_preds = set()
    for g in gt_vals:
        g_norm = str(g).strip().lower()
        if not g_norm: continue
        for idx, p in enumerate(pred_vals):
            if idx in matched_preds: continue
            p_norm = str(p).strip().lower()
            if not p_norm: continue
            if g_norm == p_norm or g_norm in p_norm or p_norm in g_norm:
                tp += 1
                matched_preds.add(idx)
                break

    fp = len(pred_vals) - len(matched_preds)
    fn = len(gt_vals) - tp
    precision = tp / len(pred_vals) if len(pred_vals) > 0 else 0.0
    recall = tp / len(gt_vals) if len(gt_vals) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

def run_consolidated_evaluation():
    print("======================================================================")
    print("CONSOLIDATED END-TO-END PIPELINE EVALUATION ON 10 GROUND TRUTH RESUMES")
    print("======================================================================")

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    for _, sec_file, _ in GT_PDF_MAP:
        sec_path = SECTIONS_DIR / sec_file
        if sec_path.exists():
            process_resume(sec_path)

    all_field_scores = defaultdict(list)
    section_csv_rows = []

    for gt_fname, _, _ in GT_PDF_MAP:
        gt_path = GT_DIR / gt_fname
        pred_path = PROJECT_ROOT / "output" / "predictions" / gt_fname

        if not gt_path.exists() or not pred_path.exists():
            continue

        with open(gt_path, "r", encoding="utf-8") as f:
            gt = json.load(f)
        with open(pred_path, "r", encoding="utf-8") as f:
            pred = json.load(f)

        res_metrics = []

        # --- Personal Details ---
        for fld in ("name", "email", "phone"):
            if fld == "phone":
                gt_p_raw = str(gt.get("personal_details", {}).get("phone", "") or "")
                g_v = extract_all_phones(gt_p_raw)
                if not g_v and gt_p_raw:
                    d = re.sub(r"\D", "", gt_p_raw)
                    if d: g_v = [d]

                pr_p = pred.get("personal_details", {}).get("phone", "") or pred.get("personal_details", {}).get("phones", [])
                if isinstance(pr_p, list):
                    p_v = [str(x) for x in pr_p if x]
                else:
                    p_v = extract_all_phones(str(pr_p)) if pr_p else []

                res_metrics.append(("personal_phone", *score_entity_set_match(g_v, p_v)))
            else:
                g_v = [str(gt.get("personal_details", {}).get(fld, "") or "")] if gt.get("personal_details", {}).get(fld) else []
                p_v = [str(pred.get("personal_details", {}).get(fld, "") or "")] if pred.get("personal_details", {}).get(fld) else []
                res_metrics.append((f"personal_{fld}", *score_entity_set_match(g_v, p_v)))

        # --- Education Subfields ---
        gt_edu = gt.get("education", [])
        pred_edu = pred.get("education", [])

        g_deg = [str(e.get("degree")) for e in gt_edu if isinstance(e, dict) and e.get("degree")]
        p_deg = [str(e.get("degree")) for e in pred_edu if isinstance(e, dict) and e.get("degree")]
        res_metrics.append(("education_degree", *score_entity_set_match(g_deg, p_deg)))

        g_inst = [str(e.get("institution")) for e in gt_edu if isinstance(e, dict) and e.get("institution")]
        p_inst = [str(e.get("institution")) for e in pred_edu if isinstance(e, dict) and e.get("institution")]
        res_metrics.append(("education_institution", *score_entity_set_match(g_inst, p_inst)))

        g_yr = [str(e.get("duration") or e.get("graduation_year")) for e in gt_edu if isinstance(e, dict) and (e.get("duration") or e.get("graduation_year"))]
        p_yr = [str(e.get("graduation_year")) for e in pred_edu if isinstance(e, dict) and e.get("graduation_year")]
        res_metrics.append(("education_graduation_year", *score_entity_set_match(g_yr, p_yr)))

        g_cg = [str(e.get("grade") or e.get("cgpa")) for e in gt_edu if isinstance(e, dict) and (e.get("grade") or e.get("cgpa"))]
        p_cg = [str(e.get("cgpa")) for e in pred_edu if isinstance(e, dict) and e.get("cgpa")]
        res_metrics.append(("education_cgpa", *score_entity_set_match(g_cg, p_cg)))

        # --- Experience Subfields ---
        gt_exp = gt.get("experience", []) + gt.get("academic_experience", [])
        pred_exp = pred.get("experience", [])

        g_t = [str(e.get("title") or e.get("position") or e.get("job_title")) for e in gt_exp if isinstance(e, dict) and (e.get("title") or e.get("position") or e.get("job_title"))]
        p_t = [str(e.get("job_title") or e.get("title")) for e in pred_exp if isinstance(e, dict) and (e.get("job_title") or e.get("title"))]
        res_metrics.append(("experience_title", *score_entity_set_match(g_t, p_t)))

        g_org = [str(e.get("organization") or e.get("institution") or e.get("company")) for e in gt_exp if isinstance(e, dict) and (e.get("organization") or e.get("institution") or e.get("company"))]
        p_org = [str(e.get("institution")) for e in pred_exp if isinstance(e, dict) and e.get("institution")]
        res_metrics.append(("experience_institution", *score_entity_set_match(g_org, p_org)))

        g_d = [str(e.get("duration") or e.get("dates")) for e in gt_exp if isinstance(e, dict) and (e.get("duration") or e.get("dates"))]
        p_d = [str(e.get("dates")) for e in pred_exp if isinstance(e, dict) and e.get("dates")]
        res_metrics.append(("experience_dates", *score_entity_set_match(g_d, p_d)))

        # --- Text Sections ---
        for sec in ("summary", "projects", "certifications", "research_interests", "responsibilities", "references", "skills"):
            g_t = " ".join(str(x) for x in (gt.get(sec, []) if isinstance(gt.get(sec), list) else [gt.get(sec, "")]))
            p_t = " ".join(str(x) for x in (pred.get(sec, []) if isinstance(pred.get(sec), list) else [pred.get(sec, "")]))
            res_metrics.append((sec, *calc_f1(g_t, p_t)))

        # --- Publications by Subtype ---
        gt_pubs = gt.get("publications", {}) if isinstance(gt.get("publications"), dict) else {}
        pred_pubs = pred.get("publications", {}) if isinstance(pred.get("publications"), dict) else {}

        pub_subtypes = [
            "journal_articles", "conference_papers", "conference_proceedings",
            "communications", "book_chapters", "books", "technical_reports", "preprints"
        ]

        for st in pub_subtypes:
            g_st = " ".join(str(x) for x in gt_pubs.get(st, []))
            p_st = " ".join(str(x) for x in pred_pubs.get(st, []))
            res_metrics.append((f"publications_{st}", *calc_f1(g_st, p_st)))

        for fld, p, r, f1 in res_metrics:
            all_field_scores[fld].append((p, r, f1))
            section_csv_rows.append({
                "resume": gt_fname,
                "section": fld,
                "precision": round(p, 4),
                "recall": round(r, 4),
                "f1_score": round(f1, 4)
            })

    # Save section metrics CSV
    with open(EVAL_DIR / "section_metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["resume", "section", "precision", "recall", "f1_score"])
        writer.writeheader()
        writer.writerows(section_csv_rows)

    # Print Table
    print("\n--- FULL 25-FIELD STRICT ACCURACY METRICS TABLE ---")
    print(f"{'FIELD NAME':<38} | {'PRECISION':<10} | {'RECALL':<10} | {'F1 SCORE':<10}")
    print("-" * 76)

    macro_f1_sum = 0.0
    for fld in sorted(all_field_scores.keys()):
        scores = all_field_scores[fld]
        avg_p = sum(s[0] for s in scores) / len(scores) if scores else 0.0
        avg_r = sum(s[1] for s in scores) / len(scores) if scores else 0.0
        avg_f1 = sum(s[2] for s in scores) / len(scores) if scores else 0.0
        macro_f1_sum += avg_f1
        print(f"{fld:<38} | {avg_p*100:<9.2f}% | {avg_r*100:<9.2f}% | {avg_f1*100:<9.2f}%")

    macro_f1 = macro_f1_sum / len(all_field_scores) if all_field_scores else 0.0
    print("-" * 76)
    print(f"{'AVERAGE MACRO FIELD F1 (25 FIELDS)':<38} | {'':<10} | {'':<10} | {macro_f1*100:<9.2f}%")
    print("======================================================================\n")

    with open(EVAL_DIR / "overall_metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Score"])
        writer.writerow(["Macro Average Field F1 (25 Fields)", round(macro_f1, 4)])

if __name__ == "__main__":
    run_consolidated_evaluation()
