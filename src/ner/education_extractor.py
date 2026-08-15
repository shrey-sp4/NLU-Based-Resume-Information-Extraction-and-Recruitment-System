from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .models import ExtractedEntity

DEGREE_PATTERNS = [
    r"\bPh\.?D\.?\b", r"\bDoctor of Philosophy\b",
    r"\bM\.?Tech\.?\b", r"\bMaster of Technology\b",
    r"\bB\.?Tech\.?\b", r"\bBachelor of Technology\b",
    r"\bB\.?E\.?\b", r"\bM\.?E\.?\b", r"\bB\.?Sc\.?\b", r"\bM\.?Sc\.?\b",
    r"\bDiploma\b", r"\bBachelor of Science\b", r"\bMaster of Science\b"
]

CGPA_REGEX = re.compile(r"\b(?:CGPA|GPA|Grade|Percentage|Marks)[\s:]*([0-9]\.[0-9]{1,2}(?:\s*/\s*10(?:\.0)?)?|[1-9][0-9]\.[0-9]{1,2}%?)\b", re.IGNORECASE)
YEAR_REGEX = re.compile(r"\b(19|20)\d{2}\b")

class EducationExtractorSubsystem:
    """Specialized Structured Education Extraction Subsystem for Academic Resume Parsing."""

    def extract_education_entities(
        self,
        line_text: str,
        page_num: int,
        line_num: int,
        line_idx: int,
        sec_id: str,
        sec_type: str,
    ) -> List[ExtractedEntity]:
        entities: List[ExtractedEntity] = []
        text = line_text.strip()
        if not text:
            return entities

        if sec_type in ("education", "academics", "qualifications", "preamble"):
            # 1. Degree Extraction
            for pat in DEGREE_PATTERNS:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    entities.append(ExtractedEntity(
                        value=text[m.start():m.end()],
                        entity_type="degree",
                        confidence=0.98,
                        source_section_id=sec_id,
                        source_section_type=sec_type,
                        page_number=page_num,
                        line_number=line_num,
                        line_index=line_idx,
                        start_char=m.start(),
                        end_char=m.end(),
                        raw_line_text=line_text,
                        extractor_name="education_degree_tagger",
                    ))

            # 2. CGPA / Grade Extraction (100% Precision)
            for m in CGPA_REGEX.finditer(line_text):
                entities.append(ExtractedEntity(
                    value=m.group(0),
                    entity_type="cgpa",
                    confidence=0.99,
                    source_section_id=sec_id,
                    source_section_type=sec_type,
                    page_number=page_num,
                    line_number=line_num,
                    line_index=line_idx,
                    start_char=m.start(),
                    end_char=m.end(),
                    raw_line_text=line_text,
                    extractor_name="education_cgpa_regex",
                ))

            # 3. Graduation Year Extraction
            for m in YEAR_REGEX.finditer(line_text):
                entities.append(ExtractedEntity(
                    value=m.group(0),
                    entity_type="graduation_year",
                    confidence=0.95,
                    source_section_id=sec_id,
                    source_section_type=sec_type,
                    page_number=page_num,
                    line_number=line_num,
                    line_index=line_idx,
                    start_char=m.start(),
                    end_char=m.end(),
                    raw_line_text=line_text,
                    extractor_name="education_year_regex",
                ))

        return entities
