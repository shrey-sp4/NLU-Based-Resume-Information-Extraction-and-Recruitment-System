import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

DEFAULT_MACHINE_PATH = Path("data/section_annotations/section_line_annotations.jsonl")
DEFAULT_HUMAN_PATH = Path("data/section_annotations/human_annotations.jsonl")


def make_line_key(record: Dict) -> str:
    return f"{record['resume_id']}|p{record['page_number']}|l{record['line_number']}|i{record['line_index']}"


@dataclass
class SectionDatasetItem:
    key: str
    resume_id: str
    page_number: int
    line_number: int
    line_index: int
    text: str
    is_heading: bool
    section_label: str
    preceded_by_blank: bool
    followed_by_blank: bool
    is_candidate: bool
    human_reviewed: bool
    machine_suggested_heading: Optional[str] = None
    machine_suggested_section: Optional[str] = None
    machine_confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "_key": self.key,
            "resume_id": self.resume_id,
            "page_number": self.page_number,
            "line_number": self.line_number,
            "line_index": self.line_index,
            "text": self.text,
            "is_heading": self.is_heading,
            "section_label": self.section_label,
            "preceded_by_blank": self.preceded_by_blank,
            "followed_by_blank": self.followed_by_blank,
            "is_candidate": self.is_candidate,
            "human_reviewed": self.human_reviewed,
            "machine_suggested_heading": self.machine_suggested_heading,
            "machine_suggested_section": self.machine_suggested_section,
            "machine_confidence": self.machine_confidence,
        }


@dataclass
class SectionDatasetSplit:
    train: List[SectionDatasetItem] = field(default_factory=list)
    val: List[SectionDatasetItem] = field(default_factory=list)
    test: List[SectionDatasetItem] = field(default_factory=list)
    train_resumes: Set[str] = field(default_factory=set)
    val_resumes: Set[str] = field(default_factory=set)
    test_resumes: Set[str] = field(default_factory=set)

    def summary(self) -> Dict:
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
            "train": split_stats(self.train, self.train_resumes),
            "val": split_stats(self.val, self.val_resumes),
            "test": split_stats(self.test, self.test_resumes),
        }


class SectionDatasetBuilder:
    def __init__(
        self,
        machine_path: Path = DEFAULT_MACHINE_PATH,
        human_path: Path = DEFAULT_HUMAN_PATH,
    ):
        self.machine_path = Path(machine_path)
        self.human_path = Path(human_path)

    def load_merged_dataset(self) -> List[SectionDatasetItem]:
        # Load human annotations mapping
        human_map = {}
        if self.human_path.exists():
            with self.human_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if "_key" in rec:
                        human_map[rec["_key"]] = rec

        # Load machine records and merge
        items = []
        with self.machine_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                key = make_line_key(rec)
                
                is_cand = rec.get("machine_suggested_heading") is not None
                human_rec = human_map.get(key)
                human_reviewed = human_rec is not None

                if human_reviewed:
                    is_heading = bool(human_rec.get("is_heading", False))
                    section_label = str(human_rec.get("section_label") or "other") if is_heading else "other"
                else:
                    # Non-reviewed background content lines default to non-headings
                    is_heading = False
                    section_label = "other"

                item = SectionDatasetItem(
                    key=key,
                    resume_id=rec["resume_id"],
                    page_number=int(rec.get("page_number", 1)),
                    line_number=int(rec.get("line_number", 0)),
                    line_index=int(rec.get("line_index", 0)),
                    text=rec.get("text", ""),
                    is_heading=is_heading,
                    section_label=section_label,
                    preceded_by_blank=bool(rec.get("preceded_by_blank", False)),
                    followed_by_blank=bool(rec.get("followed_by_blank", False)),
                    is_candidate=is_cand,
                    human_reviewed=human_reviewed,
                    machine_suggested_heading=rec.get("machine_suggested_heading"),
                    machine_suggested_section=rec.get("machine_suggested_section"),
                    machine_confidence=float(rec.get("machine_confidence", 0.0)),
                )
                items.append(item)

        return items

    def create_grouped_splits(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> SectionDatasetSplit:
        """Create train/val/test splits strictly grouped by resume_id."""
        items = self.load_merged_dataset()
        
        # Group items by resume_id
        resume_items = defaultdict(list)
        for item in items:
            resume_items[item.resume_id].append(item)

        resumes = sorted(resume_items.keys())
        rng = random.Random(seed)
        rng.shuffle(resumes)

        num_resumes = len(resumes)
        num_train = max(1, int(num_resumes * train_ratio))
        num_val = max(1, int(num_resumes * val_ratio))

        train_resumes = set(resumes[:num_train])
        val_resumes = set(resumes[num_train:num_train + num_val])
        test_resumes = set(resumes[num_train + num_val:])

        split = SectionDatasetSplit(
            train_resumes=train_resumes,
            val_resumes=val_resumes,
            test_resumes=test_resumes,
        )

        for res_id, res_lines in resume_items.items():
            # Sort lines in order within resume
            res_lines.sort(key=lambda r: (r.page_number, r.line_index))
            if res_id in train_resumes:
                split.train.extend(res_lines)
            elif res_id in val_resumes:
                split.val.extend(res_lines)
            else:
                split.test.extend(res_lines)

        return split


if __name__ == "__main__":
    builder = SectionDatasetBuilder()
    split = builder.create_grouped_splits()
    print("=" * 60)
    print("  SECTION DETECTION DATASET SPLIT SUMMARY (GROUPED BY RESUME)")
    print("=" * 60)
    print(json.dumps(split.summary(), indent=2))
