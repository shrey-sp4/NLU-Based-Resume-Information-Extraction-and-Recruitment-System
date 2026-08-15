from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from .features import extract_token_features

# Pure Python Linear CRF / Token Sequence Classifier
BIO_LABELS: List[str] = [
    "O",
    "B-NAME", "I-NAME",
    "B-UNIV", "I-UNIV",
    "B-TITLE", "I-TITLE",
    "B-COMPANY", "I-COMPANY",
    "B-PROJ", "I-PROJ",
    "B-PUB", "I-PUB",
]


class LinearCRFModel:
    def __init__(
        self,
        window_size: int = 1,
        use_caps: bool = True,
        use_affixes: bool = True,
        use_section_ctx: bool = True,
    ) -> None:
        self.weights: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.label_to_id: Dict[str, int] = {lbl: i for i, lbl in enumerate(BIO_LABELS)}
        self.id_to_label: Dict[int, str] = {i: lbl for i, lbl in enumerate(BIO_LABELS)}
        self.window_size = window_size
        self.use_caps = use_caps
        self.use_affixes = use_affixes
        self.use_section_ctx = use_section_ctx

    def train_on_sequences(
        self,
        sequences: List[Tuple[List[str], List[str]]],
        epochs: int = 5,
        lr: float = 0.05,
    ) -> None:
        """Train weights using multi-class logistic regression over token feature vectors."""
        for epoch in range(epochs):
            for tokens, labels in sequences:
                for idx, (token, label) in enumerate(zip(tokens, labels)):
                    if label not in self.label_to_id:
                        continue
                    feats = extract_token_features(
                        tokens,
                        idx,
                        window_size=self.window_size,
                        use_caps=self.use_caps,
                        use_affixes=self.use_affixes,
                        use_section_ctx=self.use_section_ctx,
                    )
                    num_feats = [(k, v) for k, v in feats.items() if isinstance(v, (int, float)) and v != 0]
                    target_id = self.label_to_id[label]

                    # Compute score for each label
                    scores = [
                        sum(fv * self.weights[lbl][fk] for fk, fv in num_feats)
                        for lbl in BIO_LABELS
                    ]

                    # Softmax probabilities
                    max_s = max(scores)
                    exp_scores = [math.exp(s - max_s) for s in scores]
                    sum_exp = sum(exp_scores)
                    probs = [e / sum_exp for e in exp_scores]

                    # SGD Update
                    for i, lbl in enumerate(BIO_LABELS):
                        y_val = 1.0 if i == target_id else 0.0
                        err = probs[i] - y_val
                        if abs(err) > 1e-4:
                            for fk, fv in num_feats:
                                self.weights[lbl][fk] -= lr * err * fv

    def predict_sequence(
        self, tokens: List[str], section_type: str = "other"
    ) -> List[Tuple[str, float]]:
        predictions = []
        for idx in range(len(tokens)):
            feats = extract_token_features(
                tokens,
                idx,
                section_type=section_type,
                window_size=self.window_size,
                use_caps=self.use_caps,
                use_affixes=self.use_affixes,
                use_section_ctx=self.use_section_ctx,
            )
            num_feats = [(k, v) for k, v in feats.items() if isinstance(v, (int, float)) and v != 0]
            scores = [
                sum(fv * self.weights[lbl][fk] for fk, fv in num_feats)
                for lbl in BIO_LABELS
            ]

            max_s = max(scores)
            exp_scores = [math.exp(s - max_s) for s in scores]
            sum_exp = sum(exp_scores)
            probs = [e / sum_exp for e in exp_scores]

            best_idx = int(max(range(len(probs)), key=lambda i: probs[i]))
            predictions.append((BIO_LABELS[best_idx], round(probs[best_idx], 4)))

        return predictions
