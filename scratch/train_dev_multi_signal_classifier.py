from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

from src.sectioning.normalization import SectionNormalizer
from src.sectioning.output import build_raw_line_records_from_run
import scratch.evaluate_held_out_and_full_corpus as eval_cor

doc_gt, all_docs = eval_cor.load_ground_truth()
dev_10_docs = all_docs[:10]

extraction_run = PROJECT_ROOT / "output" / "extraction" / "run_20260811T100030Z"
all_raw_lines = build_raw_line_records_from_run(extraction_run)

# Filter lines for Dev 10
dev_lines = [r for r in all_raw_lines if r.document_id in dev_10_docs]

normalizer = SectionNormalizer()

FEATURE_NAMES = [
    "word_count_le_3",
    "word_count_le_5",
    "word_count_le_8",
    "word_count_gt_8",
    "is_all_caps",
    "is_title_case",
    "ends_with_colon",
    "ends_with_period_or_comma",
    "has_bullet_marker",
    "has_digits_or_email",
    "has_metadata_keyword",
    "has_table_entry_keyword",
    "has_contact_prefix",
    "exact_alias_match",
    "substring_alias_match",
    "alias_confidence",
    "previous_blank",
    "next_blank",
    "is_top_of_page",
    "is_repeated_page_header",
]

def extract_features(line: Any, prev_is_heading: bool = False) -> List[float]:
    text = (line.text or "").strip()
    words = text.split()
    w_count = len(words)

    norm = normalizer.normalize(text)
    is_all_caps = 1.0 if (text.isupper() and any(c.isalpha() for c in text)) else 0.0
    is_title_case = 1.0 if ((text.istitle() or all(w[0].isupper() for w in words if w and w[0].isalpha())) and w_count <= 8) else 0.0
    ends_with_colon = 1.0 if text.endswith(":") else 0.0
    ends_with_period = 1.0 if text.endswith((".", ",", ";")) else 0.0
    has_bullet = 1.0 if text.startswith(("-", "•", "*", "➢")) else 0.0
    has_digits_email = 1.0 if ("@" in text or any(c.isdigit() for c in text)) else 0.0
    has_metadata = 1.0 if any(k in text.upper() for k in ["ISBN", "DOI", "ISSN", "HTTP", "WWW."]) else 0.0
    has_table = 1.0 if any(text.upper().startswith(k) for k in ["CGPA", "PERCENTAGE", "ROLL NO", "MARKS OBTAINED"]) else 0.0
    has_contact = 1.0 if any(text.upper().startswith(k) for k in ["CONTACT", "ADDRESS", "EMAIL", "MOBILE", "TEL", "DOB"]) else 0.0

    exact_alias = 1.0 if norm.method == "exact_alias_match" else 0.0
    sub_alias = 1.0 if (norm.method == "substring_alias_match" and norm.confidence >= 0.75) else 0.0
    alias_conf = norm.confidence

    prev_blank = 1.0 if (line.preceded_by_blank or prev_is_heading) else 0.0
    next_blank = 1.0 if line.followed_by_blank else 0.0
    is_top = 1.0 if line.line_number <= 2 else 0.0
    is_rep_hdr = 1.0 if getattr(line, "is_repeated_page_header", False) else 0.0

    return [
        1.0 if w_count <= 3 else 0.0,
        1.0 if 3 < w_count <= 5 else 0.0,
        1.0 if 5 < w_count <= 8 else 0.0,
        1.0 if w_count > 8 else 0.0,
        is_all_caps,
        is_title_case,
        ends_with_colon,
        ends_with_period,
        has_bullet,
        has_digits_email,
        has_metadata,
        has_table,
        has_contact,
        exact_alias,
        sub_alias,
        alias_conf,
        prev_blank,
        next_blank,
        is_top,
        is_rep_hdr,
    ]

# Build training set from Dev 10
X = []
y = []
doc_ids = []

for doc_id in dev_10_docs:
    gt_lines = doc_gt[doc_id]
    doc_records = [r for r in dev_lines if r.document_id == doc_id]
    doc_records.sort(key=lambda r: (r.page_number, r.line_number))

    prev_is_head = False
    for r in doc_records:
        key = (r.page_number, r.line_number)
        gt_rec = gt_lines.get(key)
        if not gt_rec:
            continue
        is_head = 1.0 if gt_rec["is_heading"] else 0.0
        feats = extract_features(r, prev_is_heading=prev_is_head)

        X.append(feats)
        y.append(is_head)
        doc_ids.append(doc_id)
        prev_is_head = gt_rec["is_heading"]

print(f"Total Training Samples Extracted from Dev 10: {len(X)} (Positives: {sum(y)}, Negatives: {len(y) - sum(y)})")

# Train Pure Python Logistic Regression model using SGD with L2 regularization
def train_logistic_regression(X_train: List[List[float]], y_train: List[float], epochs: int = 200, lr: float = 0.05, l2: float = 0.01) -> Tuple[List[float], float]:
    n_feats = len(X_train[0])
    weights = [0.0] * n_feats
    bias = 0.0

    for epoch in range(epochs):
        for feats, label in zip(X_train, y_train):
            # Compute logit
            z = sum(w * f for w, f in zip(weights, feats)) + bias
            # Sigmoid
            prob = 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))
            err = prob - label

            # Gradient update
            for i in range(n_feats):
                grad = err * feats[i] + l2 * weights[i]
                weights[i] -= lr * grad
            bias -= lr * err

    return weights, bias

weights, bias = train_logistic_regression(X, y)

print("\n=== TRAINED FEATURE WEIGHTS & BIAS ===")
print(f"Bias: {bias:.4f}")
for name, w in zip(FEATURE_NAMES, weights):
    print(f"  {name:<30}: {w:+.4f}")

# GroupKFold Cross-Validation on Dev 10
print("\n=== GROUP-KFOLD CROSS-VALIDATION (10 DEV RESUMES) ===")
correct = 0
total = 0
tp, fp, fn, tn = 0, 0, 0, 0

for test_doc in dev_10_docs:
    X_tr = [x for x, d in zip(X, doc_ids) if d != test_doc]
    y_tr = [label for label, d in zip(y, doc_ids) if d != test_doc]
    X_te = [x for x, d in zip(X, doc_ids) if d == test_doc]
    y_te = [label for label, d in zip(y, doc_ids) if d == test_doc]

    w_fold, b_fold = train_logistic_regression(X_tr, y_tr, epochs=150, lr=0.05)

    for feats, label in zip(X_te, y_te):
        z = sum(w * f for w, f in zip(w_fold, feats)) + b_fold
        prob = 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))
        pred = 1.0 if prob >= 0.55 else 0.0

        if pred == 1.0 and label == 1.0:
            tp += 1
        elif pred == 1.0 and label == 0.0:
            fp += 1
        elif pred == 0.0 and label == 1.0:
            fn += 1
        else:
            tn += 1

cv_prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
cv_rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
cv_f1 = 2 * cv_prec * cv_rec / (cv_prec + cv_rec) if (cv_prec + cv_rec) > 0 else 0.0

print(f"Cross-Validation TP: {tp} | FP: {fp} | FN: {fn} | TN: {tn}")
print(f"CV Precision: {cv_prec:.4f} ({cv_prec*100:.2f}%)")
print(f"CV Recall:    {cv_rec:.4f} ({cv_rec*100:.2f}%)")
print(f"CV F1 Score:  {cv_f1:.4f} ({cv_f1*100:.2f}%)")
