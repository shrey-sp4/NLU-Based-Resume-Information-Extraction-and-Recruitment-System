from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from .models import RawLineRecord


WORD_RE = re.compile(r"\b[\w&+/.-]+\b", flags=re.UNICODE)
NUMERIC_LINE_RE = re.compile(r"^\s*(?:\d+[\.\)]|\(\d+\)|[-•*])\s*")
PUNCT_CHARS = set("!?,.;:()[]{}<>-/\\|@#$%^&*_+=~`\"'")


@dataclass(slots=True)
class LineFeatureBundle:
    structural: Dict[str, float]
    lexical: Dict[str, float]

    def to_dict(self) -> Dict[str, float]:
        payload: Dict[str, float] = {}
        payload.update(self.structural)
        payload.update(self.lexical)
        return payload


def tokenize_words(text: str) -> List[str]:
    return [token.lower() for token in WORD_RE.findall(text or "")]


def char_ngrams(text: str, min_n: int = 3, max_n: int = 5) -> List[str]:
    cleaned = re.sub(r"\s+", " ", (text or "").lower()).strip()
    if not cleaned:
        return []

    ngrams: List[str] = []
    for n in range(min_n, max_n + 1):
        if len(cleaned) < n:
            continue
        for idx in range(len(cleaned) - n + 1):
            ngrams.append(cleaned[idx : idx + n])
    return ngrams


def count_punctuation(text: str) -> int:
    return sum(1 for ch in text if ch in PUNCT_CHARS)


def is_title_case_line(text: str) -> bool:
    words = WORD_RE.findall(text or "")
    if not words:
        return False
    title_like = 0
    alpha_words = 0
    for word in words:
        if any(ch.isalpha() for ch in word):
            alpha_words += 1
            if word[:1].isupper() and word[1:].islower():
                title_like += 1
    return alpha_words > 0 and title_like >= max(1, alpha_words - 1)


def lexical_density(text: str) -> float:
    words = tokenize_words(text)
    if not words:
        return 0.0
    unique = len(set(words))
    return unique / len(words)


def extract_line_features(
    text: str,
    preceded_by_blank: bool = False,
    followed_by_blank: bool = False,
) -> Dict[str, float]:
    raw = text or ""
    stripped = raw.strip()
    raw_words = WORD_RE.findall(stripped)
    words = [word.lower() for word in raw_words]
    char_count = len(stripped)
    word_count = len(words)
    alpha_count = sum(1 for ch in stripped if ch.isalpha())
    digit_count = sum(1 for ch in stripped if ch.isdigit())
    upper_count = sum(1 for ch in stripped if ch.isupper())
    lower_count = sum(1 for ch in stripped if ch.islower())
    punctuation_count = count_punctuation(stripped)
    non_space_count = sum(1 for ch in stripped if not ch.isspace())

    features: Dict[str, float] = {
        "bias": 1.0,
        "char_count": float(char_count),
        "word_count": float(word_count),
        "alpha_count": float(alpha_count),
        "digit_count": float(digit_count),
        "uppercase_ratio": (upper_count / alpha_count) if alpha_count else 0.0,
        "lowercase_ratio": (lower_count / alpha_count) if alpha_count else 0.0,
        "digit_ratio": (digit_count / non_space_count) if non_space_count else 0.0,
        "punctuation_ratio": (punctuation_count / non_space_count) if non_space_count else 0.0,
        "is_all_caps": 1.0 if stripped and stripped.isupper() else 0.0,
        "is_title_case": 1.0 if is_title_case_line(stripped) else 0.0,
        "starts_with_numbering": 1.0 if bool(NUMERIC_LINE_RE.match(stripped)) else 0.0,
        "ends_with_colon": 1.0 if stripped.endswith(":") else 0.0,
        "preceded_by_blank": 1.0 if preceded_by_blank else 0.0,
        "followed_by_blank": 1.0 if followed_by_blank else 0.0,
        "lexical_density": lexical_density(stripped),
        "bullet_like": 1.0 if stripped[:1] in {"-", "•", "*", "·", "▪", "▪"} else 0.0,
        "has_mixed_case": 1.0 if alpha_count and upper_count and lower_count else 0.0,
    }

    # More interpretable ratios for section headings.
    features["uppercase_word_ratio"] = (
        sum(1 for word in raw_words if word.isupper()) / word_count if word_count else 0.0
    )
    features["short_line"] = 1.0 if word_count <= 7 and char_count <= 85 else 0.0
    features["very_short_line"] = 1.0 if word_count <= 4 and char_count <= 50 else 0.0
    return features


class SparseTfidfVectorizer:
    def __init__(
        self,
        *,
        word_ngram_range: tuple[int, int] = (1, 2),
        char_ngram_range: tuple[int, int] = (3, 5),
        min_df: int = 1,
    ) -> None:
        self.word_ngram_range = word_ngram_range
        self.char_ngram_range = char_ngram_range
        self.min_df = min_df
        self.document_count = 0
        self.document_frequency: Dict[str, int] = {}
        self.idf_: Dict[str, float] = {}

    def _iter_ngrams(self, text: str) -> List[str]:
        tokens = tokenize_words(text)
        word_ngrams: List[str] = []
        min_w, max_w = self.word_ngram_range
        for n in range(min_w, max_w + 1):
            if len(tokens) < n:
                continue
            for index in range(len(tokens) - n + 1):
                word_ngrams.append("w:" + " ".join(tokens[index : index + n]))

        char_ngrams_list = ["c:" + gram for gram in char_ngrams(text, *self.char_ngram_range)]
        return word_ngrams + char_ngrams_list

    def fit(self, texts: Sequence[str]) -> "SparseTfidfVectorizer":
        self.document_count = len(texts)
        df: Dict[str, int] = defaultdict(int)
        for text in texts:
            seen = set(self._iter_ngrams(text))
            for feature in seen:
                df[feature] += 1
        self.document_frequency = dict(df)
        self.idf_ = {
            feature: math.log((1 + self.document_count) / (1 + freq)) + 1.0
            for feature, freq in self.document_frequency.items()
            if freq >= self.min_df
        }
        return self

    def transform_one(self, text: str) -> Dict[str, float]:
        ngrams = self._iter_ngrams(text)
        if not ngrams:
            return {}

        counts = Counter(ngrams)
        total = sum(counts.values()) or 1
        features: Dict[str, float] = {}
        for feature, count in counts.items():
            if feature not in self.idf_:
                continue
            tf = count / total
            features[feature] = tf * self.idf_[feature]
        return features

    def transform(self, texts: Sequence[str]) -> List[Dict[str, float]]:
        return [self.transform_one(text) for text in texts]


class SectionFeatureExtractor:
    def __init__(self) -> None:
        self.vectorizer = SparseTfidfVectorizer()

    def fit(self, texts: Sequence[str]) -> "SectionFeatureExtractor":
        self.vectorizer.fit(texts)
        return self

    def transform(self, text: str, preceded_by_blank: bool = False, followed_by_blank: bool = False) -> Dict[str, float]:
        return merge_feature_dicts(
            extract_line_features(text, preceded_by_blank=preceded_by_blank, followed_by_blank=followed_by_blank),
            self.vectorizer.transform_one(text),
        )

    def transform_many(self, texts: Sequence[str]) -> List[Dict[str, float]]:
        return [self.transform(text) for text in texts]


def merge_feature_dicts(*feature_sets: Mapping[str, float]) -> Dict[str, float]:
    merged: Dict[str, float] = {}
    for feature_map in feature_sets:
        for key, value in feature_map.items():
            merged[key] = merged.get(key, 0.0) + float(value)
    return merged
