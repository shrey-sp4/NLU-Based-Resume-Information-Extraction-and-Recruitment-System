from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
GT_DIR = PROJECT_ROOT / "ground_truth"
PRED_DIR = PROJECT_ROOT / "output" / "predictions"

def normalize_text_for_match(text: str) -> str:
    """Cleans punctuation, lowercases, and compresses whitespace."""
    t = (text or "").lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def line_match_score(line1: str, line2: str) -> float:
    """Computes similarity / substring containment score between two lines."""
    n1 = normalize_text_for_match(line1)
    n2 = normalize_text_for_match(line2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    if len(n1) > 8 and (n1 in n2 or n2 in n1):
        return 0.95
    tokens1 = set(t for t in n1.split() if len(t) >= 3)
    tokens2 = set(t for t in n2.split() if len(t) >= 3)
    if not tokens1 or not tokens2:
        return 0.0
    overlap = len(tokens1 & tokens2)
    if overlap == 0:
        return 0.0
    jaccard = overlap / len(tokens1 | tokens2)
    containment = max(overlap / len(tokens1), overlap / len(tokens2))
    return max(jaccard, containment * 0.85)

def flatten_section_object(sec_name: str, obj: Any) -> List[Tuple[str, str]]:
    """Recursively flattens section content into (section_key, line_text) pairs."""
    results = []
    if isinstance(obj, str):
        s = obj.strip()
        if len(s) > 3:
            results.append((sec_name, s))
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, str):
                s = item.strip()
                if len(s) > 3:
                    results.append((sec_name, s))
            elif isinstance(item, dict):
                # Flatten structured dict entry
                vals = [str(v).strip() for k, v in item.items() if k not in ("raw_text",) and v]
                joined = " - ".join(vals)
                if len(joined) > 3:
                    results.append((sec_name, joined))
    elif isinstance(obj, dict):
        for subk, subv in obj.items():
            sub_sec = f"{sec_name}_{subk}" if sec_name == "publications" else subk
            results.extend(flatten_section_object(sub_sec, subv))
    return results

def evaluate_coverage_and_routing():
    gt_files = sorted(GT_DIR.glob("*.json"))
    
    # Aggregators per section
    gt_section_totals = defaultdict(int)
    gt_section_matched = defaultdict(int)
    
    pred_section_totals = defaultdict(int)
    pred_same_section = defaultdict(int)
    pred_any_section = defaultdict(int)
    pred_different_section = defaultdict(int)
    
    content_lost_samples = []
    misrouted_samples = []

    # Map section alias synonyms if GT section naming differs slightly
    SECTION_SYNONYMS = {
        "academic_experience": "experience",
        "job_title": "experience",
        "memberships": "certifications", # Check if members map to certifications or societies
    }

    for gtf in gt_files:
        doc_name = gtf.name
        with open(gtf, "r", encoding="utf-8") as f:
            gt_raw = json.load(f)
        pred_f = PRED_DIR / doc_name
        if not pred_f.exists():
            continue
        with open(pred_f, "r", encoding="utf-8") as f:
            pred_raw = json.load(f)

        gt_lines = []
        for sec_k, sec_v in gt_raw.items():
            gt_lines.extend(flatten_section_object(sec_k, sec_v))

        pred_lines = []
        for sec_k, sec_v in pred_raw.items():
            pred_lines.extend(flatten_section_object(sec_k, sec_v))

        # Track which GT lines were matched by ANY prediction
        gt_line_matched = [False] * len(gt_lines)
        
        # Count total GT lines per section
        for g_sec, g_text in gt_lines:
            gt_section_totals[g_sec] += 1

        # Match each predicted line against all GT lines
        for p_sec, p_text in pred_lines:
            pred_section_totals[p_sec] += 1

            best_overall_score = 0.0
            best_overall_idx = -1
            best_same_score = 0.0

            for idx, (g_sec, g_text) in enumerate(gt_lines):
                score = line_match_score(p_text, g_text)
                if score > best_overall_score:
                    best_overall_score = score
                    best_overall_idx = idx

                # Check same section match (or canonical synonym)
                is_same_sec = (g_sec == p_sec) or (SECTION_SYNONYMS.get(p_sec) == g_sec) or (SECTION_SYNONYMS.get(g_sec) == p_sec)
                if is_same_sec and score > best_same_score:
                    best_same_score = score

            MATCH_THRESHOLD = 0.45

            if best_overall_score >= MATCH_THRESHOLD:
                pred_any_section[p_sec] += 1
                matched_gt_sec, matched_gt_text = gt_lines[best_overall_idx]
                gt_line_matched[best_overall_idx] = True

                is_same = (matched_gt_sec == p_sec) or (SECTION_SYNONYMS.get(p_sec) == matched_gt_sec) or (SECTION_SYNONYMS.get(matched_gt_sec) == p_sec)

                if is_same or (best_same_score >= MATCH_THRESHOLD and abs(best_overall_score - best_same_score) < 0.15):
                    pred_same_section[p_sec] += 1
                else:
                    pred_different_section[p_sec] += 1
                    misrouted_samples.append({
                        "document": doc_name,
                        "pred_section": p_sec,
                        "actual_gt_section": matched_gt_sec,
                        "pred_text": p_text[:120],
                        "matched_gt_text": matched_gt_text[:120],
                        "score": round(best_overall_score, 2)
                    })

        # Identify GT lines that were lost (never matched anywhere)
        for idx, (g_sec, g_text) in enumerate(gt_lines):
            if gt_line_matched[idx]:
                gt_section_matched[g_sec] += 1
            else:
                content_lost_samples.append({
                    "document": doc_name,
                    "gt_section": g_sec,
                    "lost_text": g_text
                })

    # All section names encountered across GT or Predictions
    all_sections = sorted(list(set(list(gt_section_totals.keys()) + list(pred_section_totals.keys()) + ["societies"])))

    print("==========================================================================================================")
    print("COVERAGE AND ROUTING-ACCURACY EVALUATION TABLE (10 GROUND TRUTH RESUMES)")
    print("==========================================================================================================")
    print(f"{'SECTION NAME':<34} | {'GT LINES':<8} | {'COVERAGE RATE':<36} | {'PRED LINES':<10} | {'ROUTING ACCURACY':<16}")
    print("-" * 115)

    for sec in all_sections:
        gt_tot = gt_section_totals[sec]
        gt_m = gt_section_matched[sec]
        
        if gt_tot == 0:
            cov_str = "NOT_EVALUABLE (No GT Data)"
        else:
            cov_pct = (gt_m / gt_tot) * 100.0
            cov_str = f"{cov_pct:6.2f}% ({gt_m}/{gt_tot} GT matched)"

        pr_tot = pred_section_totals[sec]
        pr_same = pred_same_section[sec]
        pr_any = pred_any_section[sec]

        if pr_any == 0:
            rout_str = "N/A (0 matched)"
        else:
            rout_pct = (pr_same / pr_any) * 100.0
            rout_str = f"{rout_pct:6.2f}% ({pr_same}/{pr_any})"

        print(f"{sec:<34} | {gt_tot:<8} | {cov_str:<36} | {pr_tot:<10} | {rout_str:<16}")

    print("==========================================================================================================")

    # Dump 10 Samples of Content Lost
    print("\n--- SAMPLE OF 10 CONTENT_LOST LINES (REAL DROPPED CONTENT FROM GT) ---")
    for idx, item in enumerate(content_lost_samples[:10]):
        print(f"[{idx+1:2d}] Doc: {item['document']:<28} | GT Sec: {item['gt_section']:<22} | Dropped Text: \"{item['lost_text']}\"")

    # Dump 5 Samples of Matched Different Section (Misrouting)
    print("\n--- SAMPLE OF 5 MATCHED_DIFFERENT_SECTION EXAMPLES (MISROUTED PREDICTED LINES) ---")
    for idx, item in enumerate(misrouted_samples[:5]):
        print(f"[{idx+1:2d}] Doc: {item['document']:<28}")
        print(f"     Predicted Section : '{item['pred_section']}'")
        print(f"     Actual GT Section : '{item['actual_gt_section']}'")
        print(f"     Predicted Text    : \"{item['pred_text']}\"")
        print(f"     Matched GT Text   : \"{item['matched_gt_text']}\" (Score: {item['score']})\n")

if __name__ == "__main__":
    evaluate_coverage_and_routing()
