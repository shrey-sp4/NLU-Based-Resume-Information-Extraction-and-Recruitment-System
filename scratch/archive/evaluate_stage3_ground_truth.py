from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

# Ground truth files
HUMAN_GT_FILE = PROJECT_ROOT / "data" / "section_annotations" / "human_annotations.jsonl"
LINE_DATA_FILE = PROJECT_ROOT / "data" / "section_annotations" / "section_line_annotations.jsonl"
STAGE3_RUN_DIR = PROJECT_ROOT / "output" / "sectioning" / "clean_stage3_2_run" / "sectioning_run_20260811T100030Z"


def load_ground_truth() -> Tuple[Dict[str, Dict[Tuple[int, int], Dict[str, Any]]], List[str]]:
    human_records = []
    with open(HUMAN_GT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            human_records.append(json.loads(line))

    line_info_map = {}
    with open(LINE_DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            key = (item["resume_id"], item["page_number"], item["line_number"])
            line_info_map[key] = item

    doc_gt: Dict[str, Dict[Tuple[int, int], Dict[str, Any]]] = defaultdict(dict)
    all_doc_ids = set()

    for h in human_records:
        doc_id = h["resume_id"]
        all_doc_ids.add(doc_id)
        page_num = h["page_number"]
        line_num = h["line_number"]

        key = (doc_id, page_num, line_num)
        text = line_info_map.get((doc_id, page_num, line_num), {}).get("text", "")
        line_idx = line_info_map.get((doc_id, page_num, line_num), {}).get("line_index", 0)

        doc_gt[doc_id][(page_num, line_num)] = {
            "page_number": page_num,
            "line_number": line_num,
            "line_index": line_idx,
            "text": text,
            "is_heading": h.get("is_heading", False),
            "section_label": h.get("section_label"),
            "review_state": h.get("review_state"),
        }

    sorted_docs = sorted(list(all_doc_ids))
    return doc_gt, sorted_docs


def load_stage3_predictions(doc_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    predictions = {}
    for doc_id in doc_ids:
        sec_file = STAGE3_RUN_DIR / "documents" / doc_id / "sections.json"
        if not sec_file.exists():
            continue
        with open(sec_file, "r", encoding="utf-8") as f:
            sec_data = json.load(f)

        pred_lines: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for span in sec_data.get("sections", []):
            orig_heading = span.get("original_heading", "")
            norm_heading = span.get("normalized_heading", "other")
            stype = span.get("section_type", "canonical")
            level = span.get("level", 1)
            parent_id = span.get("parent_section_id")

            for l_rec in span.get("lines", []):
                p_num = l_rec["page_number"]
                l_num = l_rec["line_number"]
                pred_lines[(p_num, l_num)] = {
                    "is_heading": l_rec.get("is_heading", False),
                    "original_heading": orig_heading,
                    "normalized_heading": norm_heading,
                    "section_type": stype,
                    "level": level,
                    "parent_section_id": parent_id,
                    "span_id": span["section_id"],
                    "start_line": span["start_line"],
                    "end_line": span["end_line"],
                    "text": l_rec.get("text", ""),
                }
        predictions[doc_id] = {
            "spans": sec_data.get("sections", []),
            "lines": pred_lines,
        }
    return predictions


def evaluate() -> Dict[str, Any]:
    doc_gt, all_docs = load_ground_truth()
    predictions = load_stage3_predictions(all_docs)

    # Select 10 resumes for Evaluation Subset
    eval_10_docs = all_docs[:10]
    unannotated_30_docs = all_docs[10:]

    print(f"Total Resumes with Annotations: {len(all_docs)}")
    print(f"Evaluation Subset (10 Resumes): {eval_10_docs}")
    print(f"Unannotated Validation Corpus (30 Resumes): {len(unannotated_30_docs)} documents")

    # Evaluate 10-Resume Evaluation Subset
    tp = 0
    fp = 0
    fn = 0
    tn = 0

    classification_correct = 0
    classification_total = 0

    error_analysis_list = []

    for doc_id in eval_10_docs:
        gt_lines = doc_gt[doc_id]
        pred_info = predictions.get(doc_id, {})
        pred_lines = pred_info.get("lines", {})

        for (p_num, l_num), gt_rec in gt_lines.items():
            gt_is_head = gt_rec["is_heading"]
            gt_label = gt_rec["section_label"]
            text = gt_rec["text"]

            pred_rec = pred_lines.get((p_num, l_num), {})
            pred_is_head = pred_rec.get("is_heading", False)
            pred_norm = pred_rec.get("normalized_heading")

            if gt_is_head and pred_is_head:
                tp += 1
                classification_total += 1

                # Normalize gt_label for fair comparison (e.g. personal_details -> contact)
                norm_gt = gt_label
                if norm_gt == "personal_details":
                    norm_gt = "contact"
                elif norm_gt in ("responsibilities", "memberships", "declaration"):
                    norm_gt = "other"

                if pred_norm == norm_gt:
                    classification_correct += 1
                else:
                    error_analysis_list.append({
                        "doc_id": doc_id,
                        "type": "CLASSIFICATION_MISMATCH",
                        "text": text,
                        "gt_label": gt_label,
                        "pred_label": pred_norm,
                        "page": p_num,
                        "line": l_num,
                    })

            elif not gt_is_head and pred_is_head:
                fp += 1
                error_analysis_list.append({
                    "doc_id": doc_id,
                    "type": "FALSE_POSITIVE_HEADING",
                    "text": text,
                    "gt_label": "non_heading",
                    "pred_label": pred_norm,
                    "page": p_num,
                    "line": l_num,
                })
            elif gt_is_head and not pred_is_head:
                fn += 1
                error_analysis_list.append({
                    "doc_id": doc_id,
                    "type": "FALSE_NEGATIVE_HEADING",
                    "text": text,
                    "gt_label": gt_label,
                    "pred_label": "non_heading",
                    "page": p_num,
                    "line": l_num,
                })
            else:
                tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    cls_acc = classification_correct / classification_total if classification_total > 0 else 0.0

    results = {
        "evaluation_subset_size": len(eval_10_docs),
        "unannotated_corpus_size": len(unannotated_30_docs),
        "metrics": {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "heading_precision": round(precision, 4),
            "heading_recall": round(recall, 4),
            "heading_f1": round(f1, 4),
            "classification_accuracy": round(cls_acc, 4),
            "classification_correct": classification_correct,
            "classification_total": classification_total,
        },
        "errors": error_analysis_list,
    }

    print("\n=== STAGE 3.3 GROUND TRUTH EVALUATION METRICS (10-RESUME EVAL SET) ===")
    print(f"True Positives (TP):  {tp}")
    print(f"False Positives (FP): {fp}")
    print(f"False Negatives (FN): {fn}")
    print(f"True Negatives (TN):  {tn}")
    print(f"Heading Precision:    {precision:.4f} ({precision*100:.2f}%)")
    print(f"Heading Recall:       {recall:.4f} ({recall*100:.2f}%)")
    print(f"Heading F1 Score:     {f1:.4f} ({f1*100:.2f}%)")
    print(f"Classification Acc:   {cls_acc:.4f} ({cls_acc*100:.2f}%) [{classification_correct}/{classification_total}]")

    print("\n=== TOP ERROR CATEGORIES ===")
    err_counts = Counter(e["type"] for e in error_analysis_list)
    for err_type, cnt in err_counts.items():
        print(f"  {err_type:<25}: {cnt}")

    return results


if __name__ == "__main__":
    evaluate()
