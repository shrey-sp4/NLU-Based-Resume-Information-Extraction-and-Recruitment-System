from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FINAL_DATASET_PATH = PROJECT_ROOT / "data" / "section_annotations" / "final_section_annotations.jsonl"
DEFAULT_MACHINE_PATH = PROJECT_ROOT / "data" / "section_annotations" / "section_line_annotations.jsonl"
DEFAULT_HUMAN_PATH = PROJECT_ROOT / "data" / "section_annotations" / "human_annotations.jsonl"
DEFAULT_QC_PATH = PROJECT_ROOT / "data" / "section_annotations" / "qc_decisions.jsonl"


def make_line_key(record: Dict) -> str:
    return record.get("_key") or f"{record.get('resume_id')}|p{record.get('page_number')}|l{record.get('line_number')}|i{record.get('line_index')}"


@dataclass(slots=True)
class SectionDatasetItem:
    key: str
    resume_id: str
    page_number: int
    line_number: int
    line_index: int
    text: str
    is_heading: bool
    section_label: str
    custom_section_label: Optional[str]
    is_custom_section: bool
    preceded_by_blank: bool
    followed_by_blank: bool
    decision_source: str
    annotator_notes: str = ""
    is_multiline_component: bool = False
    multiline_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_key": self.key,
            "resume_id": self.resume_id,
            "page_number": self.page_number,
            "line_number": self.line_number,
            "line_index": self.line_index,
            "text": self.text,
            "is_heading": self.is_heading,
            "section_label": self.section_label,
            "custom_section_label": self.custom_section_label,
            "is_custom_section": self.is_custom_section,
            "preceded_by_blank": self.preceded_by_blank,
            "followed_by_blank": self.followed_by_blank,
            "decision_source": self.decision_source,
            "annotator_notes": self.annotator_notes,
            "is_multiline_component": self.is_multiline_component,
            "multiline_text": self.multiline_text,
        }


@dataclass(slots=True)
class FoldSplit:
    fold_index: int
    train_items: List[SectionDatasetItem]
    test_items: List[SectionDatasetItem]
    train_resumes: Set[str]
    test_resumes: Set[str]

    def summary(self) -> Dict[str, Any]:
        def split_stats(items: List[SectionDatasetItem], resume_set: Set[str]):
            headings = sum(1 for item in items if item.is_heading)
            section_dist = Counter(item.section_label for item in items if item.is_heading)
            return {
                "total_resumes": len(resume_set),
                "total_lines": len(items),
                "heading_lines": headings,
                "non_heading_lines": len(items) - headings,
                "section_label_distribution": dict(section_dist.most_common()),
            }

        return {
            "fold_index": self.fold_index,
            "train": split_stats(self.train_items, self.train_resumes),
            "test": split_stats(self.test_items, self.test_resumes),
        }


class SectionDatasetLoader:
    def __init__(self, dataset_path: Path = FINAL_DATASET_PATH):
        self.dataset_path = Path(dataset_path)

    def load_final_dataset(self) -> List[SectionDatasetItem]:
        items: List[SectionDatasetItem] = []
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Final dataset not found at {self.dataset_path}. Run build_final_section_dataset.py first.")

        with self.dataset_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                key = make_line_key(rec)

                is_heading = bool(rec.get("final_is_heading", False))
                section_label = str(rec.get("final_section_label") or "other") if is_heading else "other"

                item = SectionDatasetItem(
                    key=key,
                    resume_id=rec["resume_id"],
                    page_number=int(rec.get("page_number", 1)),
                    line_number=int(rec.get("line_number", 0)),
                    line_index=int(rec.get("line_index", 0)),
                    text=rec.get("text", ""),
                    is_heading=is_heading,
                    section_label=section_label,
                    custom_section_label=rec.get("custom_section_label"),
                    is_custom_section=bool(rec.get("is_custom_section", False)),
                    preceded_by_blank=bool(rec.get("preceded_by_blank", False)),
                    followed_by_blank=bool(rec.get("followed_by_blank", False)),
                    decision_source=rec.get("final_decision_source", "accepted_initial_human"),
                    annotator_notes=rec.get("annotator_notes", ""),
                    is_multiline_component=bool(rec.get("is_multiline_heading_component", False)),
                    multiline_text=rec.get("multiline_heading_text"),
                )
                items.append(item)

        return items

    def create_grouped_5fold_splits(self, seed: int = 42) -> List[FoldSplit]:
        """Create 5-fold cross validation splits grouped strictly by resume_id."""
        items = self.load_final_dataset()

        # Group items by resume_id
        resume_items: Dict[str, List[SectionDatasetItem]] = defaultdict(list)
        for item in items:
            resume_items[item.resume_id].append(item)

        resumes = sorted(resume_items.keys())
        rng = random.Random(seed)
        rng.shuffle(resumes)

        # Distribute 40 resumes evenly across 5 folds (8 resumes per fold)
        n_folds = 5
        folds: List[FoldSplit] = []

        for fold_idx in range(n_folds):
            test_resumes = set(resumes[fold_idx::n_folds])
            train_resumes = set(resumes) - test_resumes

            train_items: List[SectionDatasetItem] = []
            test_items: List[SectionDatasetItem] = []

            for res_id in sorted(resume_items.keys()):
                res_lines = list(resume_items[res_id])
                res_lines.sort(key=lambda r: (r.page_number, r.line_index))

                if res_id in train_resumes:
                    train_items.extend(res_lines)
                else:
                    test_items.extend(res_lines)

            folds.append(
                FoldSplit(
                    fold_index=fold_idx + 1,
                    train_items=train_items,
                    test_items=test_items,
                    train_resumes=train_resumes,
                    test_resumes=test_resumes,
                )
            )

        return folds


# Backwards compatibility alias
SectionDatasetBuilder = SectionDatasetLoader
SectionDatasetSplit = FoldSplit


if __name__ == "__main__":
    loader = SectionDatasetLoader()
    folds = loader.create_grouped_5fold_splits()
    print(f"Loaded {len(folds)} Grouped Folds from final dataset.")
    for f in folds:
        s = f.summary()
        print(f"Fold {f.fold_index}: Train lines={s['train']['total_lines']} (resumes={s['train']['total_resumes']}), Test lines={s['test']['total_lines']} (resumes={s['test']['total_resumes']})")

