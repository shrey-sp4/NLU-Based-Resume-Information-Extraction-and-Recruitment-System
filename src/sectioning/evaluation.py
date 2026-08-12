from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def precision_recall_f1(tp: int, fp: int, fn: int) -> Dict[str, float]:
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def boundary_metrics(gold: Sequence[Mapping[str, object]], pred: Sequence[Mapping[str, object]]) -> Dict[str, float]:
    gold_set = {
        (
            str(row.get("resume_id", "")),
            int(row.get("page_number", 0)),
            int(row.get("line_number", 0)),
        )
        for row in gold
        if row.get("is_heading") is True
    }
    pred_set = {
        (
            str(row.get("resume_id", "")),
            int(row.get("page_number", 0)),
            int(row.get("line_number", 0)),
        )
        for row in pred
        if row.get("is_heading") is True
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
        ): str(row.get("section_label") or "other")
        for row in gold
        if row.get("is_heading") is True
    }
    pred_by_key = {
        (
            str(row.get("resume_id", "")),
            int(row.get("page_number", 0)),
            int(row.get("line_number", 0)),
        ): str(row.get("section_label") or "other")
        for row in pred
        if row.get("is_heading") is True
    }

    labels = sorted(set(gold_by_key.values()) | set(pred_by_key.values()))
    label_scores: Dict[str, Dict[str, float]] = {}
    macro_f1_total = 0.0

    for label in labels:
        tp = sum(1 for key, gold_label in gold_by_key.items() if gold_label == label and pred_by_key.get(key) == label)
        fp = sum(1 for key, pred_label in pred_by_key.items() if pred_label == label and gold_by_key.get(key) != label)
        fn = sum(1 for key, gold_label in gold_by_key.items() if gold_label == label and pred_by_key.get(key) != label)
        scores = precision_recall_f1(tp, fp, fn)
        label_scores[label] = scores
        macro_f1_total += scores["f1"]

    accuracy = _safe_div(
        sum(1 for key in gold_by_key if gold_by_key.get(key) == pred_by_key.get(key)),
        len(gold_by_key),
    )
    macro_f1 = _safe_div(macro_f1_total, len(labels))

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_section": label_scores,
    }

