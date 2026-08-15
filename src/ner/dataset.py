from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


class Stage4DatasetBuilder:
    def __init__(self, annotations_file: Path) -> None:
        self.annotations_file = annotations_file

    def load_annotations(self) -> List[Dict[str, Any]]:
        records = []
        if not self.annotations_file.exists():
            return records
        with open(self.annotations_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records

    def build_bio_tokens_for_doc(
        self, doc_record: Dict[str, Any], sec_data: Dict[str, Any]
    ) -> List[Tuple[List[str], List[str]]]:
        """Convert line records and character entity spans into BIO token sequences."""
        spans = doc_record.get("entity_spans", [])
        span_map: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        for s in spans:
            key = (s["page_number"], s["line_number"])
            if key not in span_map:
                span_map[key] = []
            span_map[key].append(s)

        sequences = []

        for section in sec_data.get("sections", []):
            for l_rec in section.get("lines", []):
                text = l_rec.get("text", "").strip()
                if not text or l_rec.get("is_heading", False):
                    continue

                tokens = text.split()
                if not tokens:
                    continue

                bio_labels = ["O"] * len(tokens)
                p_num = l_rec["page_number"]
                l_num = l_rec["line_number"]
                line_spans = span_map.get((p_num, l_num), [])

                for s in line_spans:
                    t_target = s["token_text"].strip()
                    t_label = s["label"]

                    for idx, tok in enumerate(tokens):
                        clean_tok = tok.strip(".,;:()[]{}")
                        if clean_tok and clean_tok.lower() in t_target.lower():
                            if bio_labels[idx] == "O":
                                prev_label = bio_labels[idx - 1] if idx > 0 else "O"
                                if prev_label.endswith(t_label):
                                    bio_labels[idx] = f"I-{t_label}"
                                else:
                                    bio_labels[idx] = f"B-{t_label}"

                sequences.append((tokens, bio_labels))

        return sequences

    def generate_augmented_training_sequences(
        self, base_sequences: List[Tuple[List[str], List[str]]]
    ) -> List[Tuple[List[str], List[str]]]:
        """Data augmentation to improve generalization over unseen capitalization and spacing."""
        augmented = list(base_sequences)
        for tokens, labels in base_sequences:
            # Augmentation 1: Lowercase variant
            low_tokens = [t.lower() for t in tokens]
            augmented.append((low_tokens, labels))

            # Augmentation 2: Titlecase variant
            title_tokens = [t.title() for t in tokens]
            augmented.append((title_tokens, labels))

        return augmented
