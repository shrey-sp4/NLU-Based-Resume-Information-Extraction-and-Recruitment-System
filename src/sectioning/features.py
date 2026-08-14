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

PROSE_VERBS_PRONOUNS = {
    "i", "my", "me", "we", "our", "he", "she", "his", "her", "they", "their",
    "have", "has", "had", "was", "were", "am", "is", "are", "been", "being",
    "worked", "managed", "developed", "created", "built", "implemented", "designed",
    "responsible", "assisted", "led", "handled", "conducted", "supported", "maintained",
    "using", "includes", "including", "involving", "proficient", "experienced",
}

EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
URL_RE = re.compile(r"(?:https?://|www\.)\S+")
DATE_RANGE_RE = re.compile(r"\b(?:19|20)\d{2}\b")
MONTH_NAME_RE = re.compile(
    r"\b(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|september|oct|october|nov|november|dec|december|present|current)\b",
    re.I,
)
LOCATION_RE = re.compile(
    r"\b[A-Z][a-zA-Z\s]+,\s*(?:[A-Z]{2}|[A-Z][a-zA-Z\s]+)\b"
)
DEGREE_KEYWORDS = {
    "bachelor", "master", "phd", "ph.d", "b.tech", "m.tech", "b.e.", "m.e.",
    "b.sc", "m.sc", "bba", "mba", "diploma", "degree", "bs", "ms", "ba", "ma",
    "b.a", "m.a",
}
INSTITUTION_KEYWORDS = {
    "university", "college", "institute", "school", "academy", "polytechnic",
}
JOB_TITLE_KEYWORDS = {
    "developer", "engineer", "manager", "analyst", "consultant", "intern",
    "assistant", "specialist", "designer", "lead", "architect", "director",
    "officer", "administrator", "executive", "associate", "head", "supervisor",
    "programmer", "administrator",
}




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
    feature_flags: Optional[Dict[str, bool]] = None,
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
        "ends_with_period": 1.0 if stripped.endswith(".") else 0.0,
        "has_prose_indicators": 1.0 if any(w in PROSE_VERBS_PRONOUNS for w in words) else 0.0,
        "has_contact_info": 1.0 if bool(EMAIL_RE.search(stripped) or URL_RE.search(stripped)) else 0.0,
        "has_date_range": 1.0 if bool(DATE_RANGE_RE.search(stripped)) else 0.0,
    }

    # More interpretable ratios for section headings.
    features["uppercase_word_ratio"] = (
        sum(1 for word in raw_words if word.isupper()) / word_count if word_count else 0.0
    )
    features["short_line"] = 1.0 if word_count <= 7 and char_count <= 85 else 0.0
    features["very_short_line"] = 1.0 if word_count <= 4 and char_count <= 50 else 0.0

    if feature_flags:
        if feature_flags.get("date_location"):
            has_month = 1.0 if bool(MONTH_NAME_RE.search(stripped)) else 0.0
            has_loc = 1.0 if bool(LOCATION_RE.search(stripped)) else 0.0
            features["cand_has_month"] = has_month
            features["cand_has_location"] = has_loc
            features["cand_date_loc_combo"] = 1.0 if (has_month or has_loc or features["has_date_range"]) else 0.0

        if feature_flags.get("education"):
            has_deg = 1.0 if any(w in DEGREE_KEYWORDS for w in words) else 0.0
            has_inst = 1.0 if any(w in INSTITUTION_KEYWORDS for w in words) else 0.0
            features["cand_has_degree"] = has_deg
            features["cand_has_institution"] = has_inst
            features["cand_edu_combo"] = 1.0 if (has_deg or has_inst) else 0.0

        if feature_flags.get("separator"):
            has_pipe = 1.0 if "|" in stripped else 0.0
            has_mid_bullet = 1.0 if any(c in stripped[1:] for c in ["•", "–", "—", "@"]) else 0.0
            sep_cnt = float(sum(stripped.count(c) for c in ["|", "•", "–", "—", "@"]))
            features["cand_has_pipe"] = has_pipe
            features["cand_has_mid_bullet"] = has_mid_bullet
            features["cand_separator_count"] = sep_cnt

        if feature_flags.get("job_subtitle"):
            has_job_kw = 1.0 if any(w in JOB_TITLE_KEYWORDS for w in words) else 0.0
            has_job_combo = 1.0 if (has_job_kw and ("|" in stripped or bool(DATE_RANGE_RE.search(stripped)) or word_count >= 4)) else 0.0
            features["cand_has_job_kw"] = has_job_kw
            features["cand_job_subtitle_combo"] = has_job_combo

        if feature_flags.get("short_phrase"):
            has_short_colon_non_head = 1.0 if (word_count <= 4 and stripped.endswith(":") and not any(w in words for w in ["summary", "skills", "experience", "education", "projects", "certifications"])) else 0.0
            has_short_mixed = 1.0 if (word_count <= 3 and not stripped.isupper() and not is_title_case_line(stripped)) else 0.0
            features["cand_short_colon_non_head"] = has_short_colon_non_head
            features["cand_short_mixed_case"] = has_short_mixed

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


class DenseSentenceEmbedder:
    """Generates a dense semantic embedding vector for a line of text using n-gram feature hashing."""
    def __init__(self, dim: int = 128) -> None:
        self.dim = dim

    def embed_text(self, text: str) -> Dict[str, float]:
        cleaned = (text or "").strip().lower()
        if not cleaned:
            return {f"emb_{i}": 0.0 for i in range(self.dim)}

        tokens = tokenize_words(cleaned) + char_ngrams(cleaned, 3, 4)
        vector = [0.0] * self.dim

        for token in tokens:
            # Deterministic hash to dimension index
            idx = int(abs(hash(token)) % self.dim)
            sign = 1.0 if (hash(token) & 1) else -1.0
            vector[idx] += sign

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return {f"emb_{i}": round(vector[i] / norm, 6) for i in range(self.dim)}


def extract_context_window_features(
    page_lines: List[Dict[str, Any]],
    current_idx: int,
    base_features_func,
) -> Dict[str, float]:
    """Extract features for current line concatenated with preceding (i-1) and succeeding (i+1) line context."""
    n = len(page_lines)
    curr = page_lines[current_idx]
    curr_text = curr.get("text", "")
    curr_prev_blank = bool(curr.get("preceded_by_blank"))
    curr_next_blank = bool(curr.get("followed_by_blank"))

    curr_features = base_features_func(curr_text, preceded_by_blank=curr_prev_blank, followed_by_blank=curr_next_blank)

    # Preceding line features (i-1)
    if current_idx > 0:
        prev_line = page_lines[current_idx - 1]
        prev_text = prev_line.get("text", "")
        prev_feats = base_features_func(prev_text, preceded_by_blank=bool(prev_line.get("preceded_by_blank")), followed_by_blank=bool(prev_line.get("followed_by_blank")))
        prev_context = {f"prev_{k}": v for k, v in prev_feats.items() if not k.startswith("emb_")}
    else:
        prev_context = {"prev_is_page_start": 1.0}

    # Succeeding line features (i+1)
    if current_idx + 1 < n:
        next_line = page_lines[current_idx + 1]
        next_text = next_line.get("text", "")
        next_feats = base_features_func(next_text, preceded_by_blank=bool(next_line.get("preceded_by_blank")), followed_by_blank=bool(next_line.get("followed_by_blank")))
        next_context = {f"next_{k}": v for k, v in next_feats.items() if not k.startswith("emb_")}
    else:
        next_context = {"next_is_page_end": 1.0}

    return merge_feature_dicts(curr_features, prev_context, next_context)

