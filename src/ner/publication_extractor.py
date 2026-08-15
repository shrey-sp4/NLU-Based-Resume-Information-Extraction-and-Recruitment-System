from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .models import ExtractedEntity

DOI_REGEX = re.compile(r"\b10\.\d{4,}/[-._;()/:A-Za-z0-9]+\b")
YEAR_REGEX = re.compile(r"\b(19|20)\d{2}\b")
PATENT_REGEX = re.compile(r"\b(?:US|EP|WO|IN)\s*\d{6,12}[A-Z0-9]*\b", re.IGNORECASE)

class PublicationExtractorSubsystem:
    """Specialized Publication Extraction Subsystem for Academic Resume Parsing."""

    def extract_publication_entities(
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

        # 1. DOI Extraction (100% Precision)
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
                extractor_name="publication_doi_regex",
            ))

        # 2. Patent Number Extraction
        for m in PATENT_REGEX.finditer(line_text):
            entities.append(ExtractedEntity(
                value=m.group(0),
                entity_type="patent",
                confidence=0.95,
                source_section_id=sec_id,
                source_section_type=sec_type,
                page_number=page_num,
                line_number=line_num,
                line_index=line_idx,
                start_char=m.start(),
                end_char=m.end(),
                raw_line_text=line_text,
                extractor_name="publication_patent_regex",
            ))

        # 3. Hierarchical Publication Subtype Parsing in Publication Sections
        if sec_type in ("publications", "journals", "conferences", "research"):
            lower_text = text.lower()
            if "journal" in sec_type or "journal" in lower_text:
                pub_type = "journal"
            elif "conf" in sec_type or "conference" in lower_text or "proceedings" in lower_text:
                pub_type = "conference"
            elif "workshop" in sec_type or "workshop" in lower_text:
                pub_type = "workshop"
            elif "book" in lower_text or "chapter" in lower_text:
                pub_type = "book_chapter"
            else:
                pub_type = "publication"

            if len(text) >= 20 and not text.startswith(("http", "www", "DOI")):
                entities.append(ExtractedEntity(
                    value=text,
                    entity_type=pub_type,
                    confidence=0.88,
                    source_section_id=sec_id,
                    source_section_type=sec_type,
                    page_number=page_num,
                    line_number=line_num,
                    line_index=line_idx,
                    start_char=0,
                    end_char=len(line_text),
                    raw_line_text=line_text,
                    extractor_name="publication_subtype_tagger",
                ))

        return entities
