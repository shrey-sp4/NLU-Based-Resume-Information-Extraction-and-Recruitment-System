from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .models import ExtractedEntity

ACADEMIC_ROLES = [
    "assistant professor", "associate professor", "professor",
    "postdoctoral fellow", "postdoctoral researcher", "postdoc",
    "research fellow", "research assistant", "teaching assistant",
    "visiting faculty", "visiting researcher", "lecturer",
    "senior scientist", "research scientist", "project fellow"
]

class AcademicExperienceExtractorSubsystem:
    """Specialized Academic Experience & Research Extraction Subsystem for Academic Resume Parsing."""

    def extract_academic_experience(
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

        lower = text.lower()

        # 1. Academic Position / Rank Title Extraction
        if sec_type in ("experience", "research", "teaching", "preamble"):
            for role in ACADEMIC_ROLES:
                m = re.search(r"\b" + re.escape(role) + r"\b", lower)
                if m:
                    st, en = m.start(), m.end()
                    val = text[st:en]
                    entities.append(ExtractedEntity(
                        value=val,
                        entity_type="job_title",
                        confidence=0.95,
                        source_section_id=sec_id,
                        source_section_type=sec_type,
                        page_number=page_num,
                        line_number=line_num,
                        line_index=line_idx,
                        start_char=st,
                        end_char=en,
                        raw_line_text=line_text,
                        extractor_name="academic_role_tagger",
                    ))

        # 2. Research Organization / Institution Extraction
        if sec_type in ("experience", "research", "education"):
            for univ in ["Indian Institute of Technology", "IIT", "NIT", "Jadavpur University", "Delhi University", "DAIICT", "DRDO", "ISRO", "IBM Research"]:
                m = re.search(r"\b" + re.escape(univ) + r"\b", text)
                if m:
                    entities.append(ExtractedEntity(
                        value=m.group(0),
                        entity_type="university",
                        confidence=0.92,
                        source_section_id=sec_id,
                        source_section_type=sec_type,
                        page_number=page_num,
                        line_number=line_num,
                        line_index=line_idx,
                        start_char=m.start(),
                        end_char=m.end(),
                        raw_line_text=line_text,
                        extractor_name="academic_institution_tagger",
                    ))

        # 3. Research Interest Keywords Extraction
        if sec_type in ("interests", "research", "skills", "summary"):
            for area in ["Computer Vision", "Machine Learning", "Natural Language Processing", "Deep Learning", "Signal Processing", "Data Structures"]:
                m = re.search(r"\b" + re.escape(area) + r"\b", text, re.IGNORECASE)
                if m:
                    entities.append(ExtractedEntity(
                        value=text[m.start():m.end()],
                        entity_type="research_interest",
                        confidence=0.90,
                        source_section_id=sec_id,
                        source_section_type=sec_type,
                        page_number=page_num,
                        line_number=line_num,
                        line_index=line_idx,
                        start_char=m.start(),
                        end_char=m.end(),
                        raw_line_text=line_text,
                        extractor_name="research_interest_tagger",
                    ))

        return entities
