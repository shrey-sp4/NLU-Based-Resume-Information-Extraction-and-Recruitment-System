from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .gazetteers import (
    AWARD_KEYWORDS,
    DEGREE_GAZETTEER,
    LANGUAGE_GAZETTEER,
    ROLE_TITLE_GAZETTEER,
    SKILL_GAZETTEER,
    UNIVERSITY_KEYWORDS,
)
from .models import ExtractedEntity
from .model import LinearCRFModel

# Deterministic Regex Engines
EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+", re.IGNORECASE)
PHONE_REGEX = re.compile(r"(?:\+91[\s\-]*)?(?:[6-9]\d[\d\s\-]{8,12})")
DOI_REGEX = re.compile(r"\b10\.\d{4,}/[-._;()/:A-Za-z0-9]+\b")
YEAR_REGEX = re.compile(r"\b(19|20)\d{2}\b")
GRADE_REGEX = re.compile(r"\b\d+\.\d+\s*(?:CGPA|CPI|GPA|%)\b|\b\d+%\b", re.IGNORECASE)


class HybridEntityExtractor:
    def __init__(self, crf_model: Optional[LinearCRFModel] = None) -> None:
        self.crf_model = crf_model or LinearCRFModel()

    def extract_deterministic_entities(
        self, line_text: str, page_num: int, line_num: int, line_idx: int, sec_id: str, sec_type: str
    ) -> List[ExtractedEntity]:
        entities = []
        if not line_text.strip():
            return entities

        # Email
        for m in EMAIL_REGEX.finditer(line_text):
            entities.append(ExtractedEntity(
                value=m.group(0),
                entity_type="email",
                confidence=1.0,
                source_section_id=sec_id,
                source_section_type=sec_type,
                page_number=page_num,
                line_number=line_num,
                line_index=line_idx,
                start_char=m.start(),
                end_char=m.end(),
                raw_line_text=line_text,
                extractor_name="deterministic_regex",
            ))

        # Phone
        for m in PHONE_REGEX.finditer(line_text):
            entities.append(ExtractedEntity(
                value=m.group(0),
                entity_type="phone",
                confidence=1.0,
                source_section_id=sec_id,
                source_section_type=sec_type,
                page_number=page_num,
                line_number=line_num,
                line_index=line_idx,
                start_char=m.start(),
                end_char=m.end(),
                raw_line_text=line_text,
                extractor_name="deterministic_regex",
            ))

        # DOI
        for m in DOI_REGEX.finditer(line_text):
            entities.append(ExtractedEntity(
                value=m.group(0),
                entity_type="doi",
                confidence=1.0,
                source_section_id=sec_id,
                source_section_type=sec_type,
                page_number=page_num,
                line_number=line_num,
                line_index=line_idx,
                start_char=m.start(),
                end_char=m.end(),
                raw_line_text=line_text,
                extractor_name="deterministic_regex",
            ))

        # Graduation Year in Education
        if sec_type == "education":
            for m in YEAR_REGEX.finditer(line_text):
                entities.append(ExtractedEntity(
                    value=m.group(0),
                    entity_type="graduation_year",
                    confidence=1.0,
                    source_section_id=sec_id,
                    source_section_type=sec_type,
                    page_number=page_num,
                    line_number=line_num,
                    line_index=line_idx,
                    start_char=m.start(),
                    end_char=m.end(),
                    raw_line_text=line_text,
                    extractor_name="deterministic_regex",
                ))

            for m in GRADE_REGEX.finditer(line_text):
                entities.append(ExtractedEntity(
                    value=m.group(0),
                    entity_type="cgpa",
                    confidence=1.0,
                    source_section_id=sec_id,
                    source_section_type=sec_type,
                    page_number=page_num,
                    line_number=line_num,
                    line_index=line_idx,
                    start_char=m.start(),
                    end_char=m.end(),
                    raw_line_text=line_text,
                    extractor_name="deterministic_regex",
                ))

        return entities

    def extract_gazetteer_entities(
        self, line_text: str, page_num: int, line_num: int, line_idx: int, sec_id: str, sec_type: str
    ) -> List[ExtractedEntity]:
        entities = []
        if not line_text.strip():
            return entities

        lower_text = line_text.lower()

        # Skills
        for skill in SKILL_GAZETTEER:
            pattern = r"\b" + re.escape(skill) + r"\b"
            for m in re.finditer(pattern, lower_text):
                st, en = m.start(), m.end()
                entities.append(ExtractedEntity(
                    value=line_text[st:en],
                    entity_type="skill",
                    confidence=0.95,
                    source_section_id=sec_id,
                    source_section_type=sec_type,
                    page_number=page_num,
                    line_number=line_num,
                    line_index=line_idx,
                    start_char=st,
                    end_char=en,
                    raw_line_text=line_text,
                    extractor_name="gazetteer_matcher",
                ))

        # Degrees in Education
        if sec_type == "education":
            for deg in DEGREE_GAZETTEER:
                pattern = r"\b" + re.escape(deg) + r"\b"
                for m in re.finditer(pattern, lower_text):
                    st, en = m.start(), m.end()
                    entities.append(ExtractedEntity(
                        value=line_text[st:en],
                        entity_type="degree",
                        confidence=0.95,
                        source_section_id=sec_id,
                        source_section_type=sec_type,
                        page_number=page_num,
                        line_number=line_num,
                        line_index=line_idx,
                        start_char=st,
                        end_char=en,
                        raw_line_text=line_text,
                        extractor_name="gazetteer_matcher",
                    ))

        # Languages
        for lang in LANGUAGE_GAZETTEER:
            pattern = r"\b" + re.escape(lang) + r"\b"
            for m in re.finditer(pattern, lower_text):
                st, en = m.start(), m.end()
                entities.append(ExtractedEntity(
                    value=line_text[st:en],
                    entity_type="language",
                    confidence=0.90,
                    source_section_id=sec_id,
                    source_section_type=sec_type,
                    page_number=page_num,
                    line_number=line_num,
                    line_index=line_idx,
                    start_char=st,
                    end_char=en,
                    raw_line_text=line_text,
                    extractor_name="gazetteer_matcher",
                ))

        return entities

    def extract_crf_entities(
        self, line_text: str, page_num: int, line_num: int, line_idx: int, sec_id: str, sec_type: str
    ) -> List[ExtractedEntity]:
        entities = []
        tokens = line_text.split()
        if not tokens:
            return entities

        preds = self.crf_model.predict_sequence(tokens, section_type=sec_type)

        curr_span_tokens = []
        curr_label = None
        curr_conf = []

        for idx, (token, (bio_label, prob)) in enumerate(zip(tokens, preds)):
            if bio_label.startswith("B-"):
                if curr_span_tokens and curr_label:
                    span_val = " ".join(curr_span_tokens)
                    st = line_text.find(span_val)
                    if st >= 0:
                        entities.append(ExtractedEntity(
                            value=span_val,
                            entity_type=curr_label.lower(),
                            confidence=round(sum(curr_conf) / len(curr_conf), 4),
                            source_section_id=sec_id,
                            source_section_type=sec_type,
                            page_number=page_num,
                            line_number=line_num,
                            line_index=line_idx,
                            start_char=st,
                            end_char=st + len(span_val),
                            raw_line_text=line_text,
                            extractor_name="learned_crf_ner",
                        ))
                curr_span_tokens = [token]
                curr_label = bio_label[2:]
                curr_conf = [prob]
            elif bio_label.startswith("I-") and curr_label == bio_label[2:]:
                curr_span_tokens.append(token)
                curr_conf.append(prob)
            else:
                if curr_span_tokens and curr_label:
                    span_val = " ".join(curr_span_tokens)
                    st = line_text.find(span_val)
                    if st >= 0:
                        entities.append(ExtractedEntity(
                            value=span_val,
                            entity_type=curr_label.lower(),
                            confidence=round(sum(curr_conf) / len(curr_conf), 4),
                            source_section_id=sec_id,
                            source_section_type=sec_type,
                            page_number=page_num,
                            line_number=line_num,
                            line_index=line_idx,
                            start_char=st,
                            end_char=st + len(span_val),
                            raw_line_text=line_text,
                            extractor_name="learned_crf_ner",
                        ))
                curr_span_tokens = []
                curr_label = None
                curr_conf = []

        if curr_span_tokens and curr_label:
            span_val = " ".join(curr_span_tokens)
            st = line_text.find(span_val)
            if st >= 0:
                entities.append(ExtractedEntity(
                    value=span_val,
                    entity_type=curr_label.lower(),
                    confidence=round(sum(curr_conf) / len(curr_conf), 4),
                    source_section_id=sec_id,
                    source_section_type=sec_type,
                    page_number=page_num,
                    line_number=line_num,
                    line_index=line_idx,
                    start_char=st,
                    end_char=st + len(span_val),
                    raw_line_text=line_text,
                    extractor_name="learned_crf_ner",
                ))

        return entities

    def resolve_conflicts(self, all_entities: List[ExtractedEntity]) -> Tuple[List[ExtractedEntity], int]:
        """Deterministic precedence resolution: Regex > Gazetteer > CRF."""
        conflicts = 0
        resolved: List[ExtractedEntity] = []

        for entity in all_entities:
            overlap = False
            for prev in resolved:
                if entity.page_number == prev.page_number and entity.line_number == prev.line_number:
                    # Check character overlap
                    if not (entity.end_char <= prev.start_char or entity.start_char >= prev.end_char):
                        overlap = True
                        conflicts += 1
                        # Deterministic precedence: regex > gazetteer > crf
                        if entity.extractor_name == "deterministic_regex" and prev.extractor_name != "deterministic_regex":
                            resolved.remove(prev)
                            resolved.append(entity)
                        break
            if not overlap:
                resolved.append(entity)

        return resolved, conflicts

    def recover_entity_span_boundaries(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Narrowly scoped boundary recovery for priority fields (university, job_title, title, degree).
        
        Only adjusts start_char / end_char of existing entities on the raw line text.
        Does NOT change entity type or introduce new entities.
        """
        for entity in entities:
            etype = entity.entity_type.lower()
            if etype not in ("university", "institution", "job_title", "title", "degree"):
                continue

            raw = entity.raw_line_text
            st = entity.start_char
            en = entity.end_char

            if not raw or st < 0 or en > len(raw):
                continue

            # Prefix expansion for titles and institutions
            if st > 0:
                prefix = raw[:st]
                if etype in ("job_title", "title"):
                    if prefix.rstrip().endswith(("Visiting", "Assistant", "Associate", "Postdoctoral", "Adjunct", "Honorary")):
                        m_st = max(prefix.rfind("Visiting"), prefix.rfind("Assistant"), prefix.rfind("Associate"), prefix.rfind("Postdoctoral"), prefix.rfind("Adjunct"), prefix.rfind("Honorary"))
                        if m_st >= 0:
                            st = m_st
                elif etype in ("university", "institution"):
                    if prefix.rstrip().endswith(("Indian Institute of", "National Institute of", "Pandit Deendayal", "Sardar Vallabhbhai", "Harish-Chandra", "College of", "Bengal College of", "Bharti College of", "GD Rungta College of", "Siliguri Institute of")):
                        m_st = max(0, min([prefix.rfind(kw) for kw in ("Indian Institute of", "National Institute of", "Pandit Deendayal", "Sardar Vallabhbhai", "Harish-Chandra", "College of", "Bengal College of", "Bharti College of", "GD Rungta College of", "Siliguri Institute of") if prefix.rfind(kw) >= 0]))
                        st = m_st

            # Suffix expansion for university campus cities
            if en < len(raw):
                suffix = raw[en:]
                if etype in ("university", "institution"):
                    m_suf = re.match(r"^\s*(?:Delhi|Gandhinagar|Bombay|Kanpur|Kharagpur|Ahmedabad|Chandigarh|Rajkot|Surat|Pune|Bhopal)", suffix, re.IGNORECASE)
                    if m_suf:
                        en = en + m_suf.end()

            # Update span values safely
            entity.start_char = st
            entity.end_char = en
            entity.value = raw[st:en]

        return entities
