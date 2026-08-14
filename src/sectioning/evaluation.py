from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def precision_recall_f1(tp: int, fp: int, fn: int) -> Dict[str, float]:
    precision = _safe_div(float(tp), float(tp + fp))
    recall = _safe_div(float(tp), float(tp + fn))
    f1 = _safe_div(2.0 * precision * recall, precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def compute_paired_ttest_pvalue(diffs: List[float]) -> float:
    """Compute 2-tailed paired t-test p-value across fold differences."""
    n = len(diffs)
    if n < 2:
        return 1.0
    mean_diff = sum(diffs) / n
    var = sum((d - mean_diff) ** 2 for d in diffs) / (n - 1)
    std_err = math.sqrt(var / n) if var > 0 else 0.0
    if std_err == 0.0:
        return 0.0 if mean_diff != 0.0 else 1.0
    t_stat = mean_diff / std_err

    # Simple t-distribution 2-tailed p-value approximation for df=4
    abs_t = abs(t_stat)
    if abs_t > 3.74:
        return 0.005
    elif abs_t > 2.78:
        return 0.02
    elif abs_t > 2.13:
        return 0.05
    elif abs_t > 1.53:
        return 0.15
    else:
        return 0.35


def boundary_metrics(gold: Sequence[Mapping[str, object]], pred: Sequence[Mapping[str, object]]) -> Dict[str, float]:
    gold_set = {
        (
            str(row.get("resume_id", "")),
            int(row.get("page_number", 0)),
            int(row.get("line_number", 0)),
        )
        for row in gold
        if row.get("is_heading") is True or row.get("final_is_heading") is True
    }
    pred_set = {
        (
            str(row.get("resume_id", "")),
            int(row.get("page_number", 0)),
            int(row.get("line_number", 0)),
        )
        for row in pred
        if row.get("is_heading") is True or row.get("final_is_heading") is True
    }
    tp = len(gold_set & pred_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)
    return precision_recall_f1(tp, fp, fn)


def classification_metrics(gold: Sequence[Mapping[str, object]], pred: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    gold_by_key = {
        (
            str(row.get("resume_id", "")),
            int(row.get("page_number", 0)),
            int(row.get("line_number", 0)),
        ): str(row.get("section_label") or row.get("final_section_label") or "other")
        for row in gold
        if row.get("is_heading") is True or row.get("final_is_heading") is True
    }
    pred_by_key = {
        (
            str(row.get("resume_id", "")),
            int(row.get("page_number", 0)),
            int(row.get("line_number", 0)),
        ): str(row.get("section_label") or row.get("final_section_label") or "other")
        for row in pred
        if row.get("is_heading") is True or row.get("final_is_heading") is True
    }

    labels = sorted(set(gold_by_key.values()) | set(pred_by_key.values()))
    label_scores: Dict[str, Dict[str, float]] = {}
    macro_f1_total = 0.0
    total_samples = 0
    weighted_f1_total = 0.0

    for label in labels:
        tp = sum(1 for key, gold_label in gold_by_key.items() if gold_label == label and pred_by_key.get(key) == label)
        fp = sum(1 for key, pred_label in pred_by_key.items() if pred_label == label and gold_by_key.get(key) != label)
        fn = sum(1 for key, gold_label in gold_by_key.items() if gold_label == label and pred_by_key.get(key) != label)
        scores = precision_recall_f1(tp, fp, fn)
        support = sum(1 for gold_label in gold_by_key.values() if gold_label == label)
        scores["support"] = support
        if support < 10:
            scores["note"] = "Low Sample Support (N < 10)"

        label_scores[label] = scores
        macro_f1_total += scores["f1"]
        weighted_f1_total += scores["f1"] * support
        total_samples += support

    accuracy = _safe_div(
        sum(1 for key in gold_by_key if gold_by_key.get(key) == pred_by_key.get(key)),
        len(gold_by_key),
    )
    macro_f1 = _safe_div(macro_f1_total, len(labels))
    weighted_f1 = _safe_div(weighted_f1_total, total_samples)

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "per_section": label_scores,
    }


def evaluate_decision_criteria(
    baseline_summary: Dict[str, float],
    model_summary: Dict[str, float],
    fold_baseline_f1s: List[float],
    fold_model_f1s: List[float],
) -> Dict[str, Any]:
    """Evaluate explicit criteria for deciding if a learned model beats the mandatory baseline."""
    heading_f1_diff = model_summary["heading_f1"] - baseline_summary["heading_f1"]
    macro_f1_diff = model_summary["macro_f1"] - baseline_summary["macro_f1"]

    fold_diffs = [m - b for m, b in zip(fold_model_f1s, fold_baseline_f1s)]
    p_value = compute_paired_ttest_pvalue(fold_diffs)

    criterion1_pass = heading_f1_diff >= 0.03 and p_value < 0.05
    criterion2_pass = macro_f1_diff >= 0.03 and p_value < 0.05

    # Core sections check (education, experience, skills, publications)
    core_degraded = False
    core_sections = ["education", "experience", "skills", "publications"]
    for core in core_sections:
        b_f1 = baseline_summary.get("per_section", {}).get(core, {}).get("f1", 0.0)
        m_f1 = model_summary.get("per_section", {}).get(core, {}).get("f1", 0.0)
        if (b_f1 - m_f1) > 0.015:
            core_degraded = True
            break

    criterion3_pass = not core_degraded

    beats_baseline = criterion1_pass and criterion2_pass and criterion3_pass

    return {
        "beats_baseline": beats_baseline,
        "heading_f1_diff": round(heading_f1_diff, 4),
        "macro_f1_diff": round(macro_f1_diff, 4),
        "p_value": p_value,
        "criterion1_heading_f1_plus_3pct": criterion1_pass,
        "criterion2_macro_f1_plus_3pct": criterion2_pass,
        "criterion3_no_core_degradation": criterion3_pass,
        "explanation": (
            "Model successfully beats baseline with statistically significant improvement (+3.0% F1 & Macro F1, no core section degradation)."
            if beats_baseline
            else f"Model failed criteria check. Heading F1 diff={heading_f1_diff:+.4f}, Macro F1 diff={macro_f1_diff:+.4f}, p-value={p_value:.3f}, Core degraded={core_degraded}."
        )
    }
