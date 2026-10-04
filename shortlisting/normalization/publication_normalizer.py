from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from shortlisting.llm.publication_service import PublicationService
from shortlisting.models.candidate import PublicationEntry

REJECT_PUB_PATTERNS = [
    r"^(?:citation:\s*)?first/corresponding",
    r"^(?:citation:\s*)?(?:co-corresponding|author\s+publications|publications\s*:|papers?\s+presented\s*:|list\s+of\s+publications?)",
    r"\b(?:delivered\s+(?:an?\s+)?(?:expert|scholarly|invited|keynote|guest)?\s*(?:talk|address|lecture|speech))\b",
    r"\b(?:invited\s+talks?|invited\s+presentations?|presentations?\s+at|talks?\s+at)\b",
    r"\b(?:participated\s+in(?:\s+the)?\s+(?:national|international|two\s+days?|one\s+week)?\s*(?:workshop|sttp|training))\b",
    r"\b(?:participated\s+in|attended\s+(?:an?\s+)?(?:online\s+)?(?:workshop|seminar|conference|training))\b",
    r"\b(?:organized\s+(?:international|national)?\s*(?:conference|workshop))\b",
    r"\b(?:total\s+paper\s+published|total\s+publications?)\b",
    r"\b(?:international\s+workshop\s+on\b)",
    r"\b(?:training\s+program\s+in|hands-on\s+workshop)\b",
    r"page\s+\d+\s+of\s+\d+",
    r"^\s*\d+\s*\|\s*p\s*age",
    r"^\s*\d{4,}/[a-z0-9\.\-_/]+\)?\s*page\s+\d+",
    r"^\s*\d{4,}/[a-z0-9\.\-_/]+$",
    r"^\s*(?:rganized\s+by|f\s+recent\s+trends|ccurring\s+during|during\s+\d+\s*[-–]\s*\d+|f\s+limited\s+capability|n\s+biodiversity)\b",
]
REJECT_PUB_REGEX = re.compile("|".join(REJECT_PUB_PATTERNS), re.IGNORECASE)


class PublicationNormalizer:
    """
    Normalizes extracted publication records into the strict candidate publication schema:
    title, type, year, tier.
    Filters out section headings, invited talks, workshop attendances, and broken fragments.
    Deduplicates publications conservatively within each candidate profile.
    Guarantees that raw citations, venues, and DOIs never appear in the normalized candidate model.
    """

    def __init__(self, pub_service: Optional[PublicationService] = None):
        self.pub_service = pub_service or PublicationService()

    @staticmethod
    def _is_invalid_citation(raw_citation: str) -> bool:
        """Checks if citation string represents obvious non-publication junk."""
        text = raw_citation.strip()
        words = text.split()
        if len(words) < 6:
            return True
        if REJECT_PUB_REGEX.search(text):
            return True
        return False

    @staticmethod
    def _normalize_title_for_dedup(title: str) -> str:
        """Conservative normalization of title for duplicate detection."""
        clean = (title or "").lower()
        clean = re.sub(r"[^a-z0-9\s]", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def normalize(self, raw_publications: Dict[str, Any]) -> List[PublicationEntry]:
        if not isinstance(raw_publications, dict):
            return []

        categories = [
            "journal_articles",
            "conference_papers",
            "conference_proceedings",
            "communications",
            "book_chapters",
            "books",
            "technical_reports",
            "preprints",
        ]

        valid_entries: List[PublicationEntry] = []

        for cat in categories:
            citation_list = raw_publications.get(cat, [])
            if not isinstance(citation_list, list):
                continue

            for raw_citation in citation_list:
                if not isinstance(raw_citation, str) or not raw_citation.strip():
                    continue

                # 1. Pre-filter obvious non-publication records
                if self._is_invalid_citation(raw_citation):
                    continue

                # 2. Parse citation and determine tier via LLM service
                parsed = self.pub_service.parse_and_classify_citation(
                    raw_citation=raw_citation, category_hint=cat
                )

                title = (parsed.get("title") or "").strip()

                # 3. Reject record if title cannot be reliably determined (do not create empty titles)
                if not title or len(title.split()) < 3:
                    continue
                if REJECT_PUB_REGEX.search(title):
                    continue

                pub_type = parsed.get("type", "other")
                if pub_type not in ("journal", "conference", "other"):
                    pub_type = "other"

                tier = parsed.get("tier", "Unranked")

                valid_entries.append(
                    PublicationEntry(
                        title=title,
                        type=pub_type,
                        year=parsed.get("year"),
                        tier=tier,
                    )
                )

        # 4. Conservative Deduplication within candidate
        deduped_entries: List[PublicationEntry] = []
        seen_keys: Dict[str, PublicationEntry] = {}

        for entry in valid_entries:
            key = self._normalize_title_for_dedup(entry.title)
            if len(key) < 12:
                # If title is very short, do not deduplicate aggressively
                deduped_entries.append(entry)
                continue

            if key not in seen_keys:
                seen_keys[key] = entry
                deduped_entries.append(entry)
            else:
                existing = seen_keys[key]
                # Merge / prefer entry with known year or higher tier
                if existing.year is None and entry.year is not None:
                    existing.year = entry.year
                if existing.type == "other" and entry.type in ("journal", "conference"):
                    existing.type = entry.type
                if existing.tier in ("Unranked", "Tier-3") and entry.tier in ("Tier-1", "Tier-2"):
                    existing.tier = entry.tier

        return deduped_entries
