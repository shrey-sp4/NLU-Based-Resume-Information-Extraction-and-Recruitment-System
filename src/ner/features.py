from __future__ import annotations

from typing import Any, Dict, List

from .gazetteers import (
    DEGREE_GAZETTEER,
    LANGUAGE_GAZETTEER,
    ROLE_TITLE_GAZETTEER,
    SKILL_GAZETTEER,
    UNIVERSITY_KEYWORDS,
)

NAME_PREFIXES = {"dr.", "prof.", "mr.", "mrs.", "ms."}
COMPANY_SUFFIXES = {"ltd", "inc", "corp", "technologies", "services", "pvt", "solutions", "labs", "systems"}


def extract_token_features(
    tokens: List[str],
    index: int,
    section_type: str = "other",
    window_size: int = 1,
    use_caps: bool = True,
    use_affixes: bool = True,
    use_section_ctx: bool = True,
) -> Dict[str, Any]:
    token = tokens[index]
    lower = token.lower()
    clean_tok = lower.strip(".,;:()[]{}")

    features: Dict[str, Any] = {
        "bias": 1.0,
        "word": token,
        "lower": lower,
    }

    if use_affixes:
        features.update({
            "prefix_2": lower[:2] if len(lower) >= 2 else lower,
            "prefix_3": lower[:3] if len(lower) >= 3 else lower,
            "suffix_2": lower[-2:] if len(lower) >= 2 else lower,
            "suffix_3": lower[-3:] if len(lower) >= 3 else lower,
        })

    if use_caps:
        features.update({
            "is_upper": 1.0 if token.isupper() and any(c.isalpha() for c in token) else 0.0,
            "is_title": 1.0 if token.istitle() else 0.0,
            "is_digit": 1.0 if token.isdigit() else 0.0,
            "has_hyphen": 1.0 if "-" in token else 0.0,
            "has_at": 1.0 if "@" in token else 0.0,
        })

    if use_section_ctx:
        features["section_type"] = section_type

    features.update({
        "in_skill_gazetteer": 1.0 if clean_tok in SKILL_GAZETTEER else 0.0,
        "in_degree_gazetteer": 1.0 if clean_tok in DEGREE_GAZETTEER else 0.0,
        "in_language_gazetteer": 1.0 if clean_tok in LANGUAGE_GAZETTEER else 0.0,
        "in_role_gazetteer": 1.0 if clean_tok in ROLE_TITLE_GAZETTEER else 0.0,
        "in_univ_gazetteer": 1.0 if clean_tok in UNIVERSITY_KEYWORDS else 0.0,
        "is_company_suffix": 1.0 if clean_tok in COMPANY_SUFFIXES else 0.0,
    })

    # Left Context Window (-1 to -window_size)
    for offset in range(1, window_size + 1):
        if index - offset >= 0:
            prev_tok = tokens[index - offset]
            prev_lower = prev_tok.lower()
            features[f"prev_{offset}_lower"] = prev_lower
            if use_caps:
                features[f"prev_{offset}_is_title"] = 1.0 if prev_tok.istitle() else 0.0
                features[f"prev_{offset}_is_upper"] = 1.0 if prev_tok.isupper() else 0.0
            if offset == 1:
                features["prev_is_name_prefix"] = 1.0 if prev_lower in NAME_PREFIXES else 0.0
        else:
            features[f"BOS_{offset}"] = 1.0

    # Right Context Window (+1 to +window_size)
    for offset in range(1, window_size + 1):
        if index + offset < len(tokens):
            next_tok = tokens[index + offset]
            next_lower = next_tok.lower()
            features[f"next_{offset}_lower"] = next_lower
            if use_caps:
                features[f"next_{offset}_is_title"] = 1.0 if next_tok.istitle() else 0.0
                features[f"next_{offset}_is_upper"] = 1.0 if next_tok.isupper() else 0.0
        else:
            features[f"EOS_{offset}"] = 1.0

    return features
