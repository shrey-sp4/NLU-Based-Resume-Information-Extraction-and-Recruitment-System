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
    r"\b(?:participated\s+in(?:\s+the)?\s+(?:national|international|two\s+days?|one\s+week)?\s*(?:workshop|sttp|training|fdp|faculty\s+development\s+program))\b",
    r"\b(?:participated\s+in|attended\s+(?:an?\s+)?(?:online\s+)?(?:workshop|seminar|conference|training|symposium))\b",
    r"\b(?:attended\s+the\s+(?:international|national|springer|ieee)\s+conference)\b",
    r"\b(?:organized\s+(?:international|national)?\s*(?:conference|workshop)|convenor|coordinator)\b",
    r"^\s*(?:total\s+(?:paper\s+published|publications?|citations?)|total\s+of\s+\d+\s+publications)\b",
    r"^\s*(?:h-index|i10-index|cum\.\s*if|average\s*if|max\s*if)\b",
    r"\b(?:training\s+program\s+in|hands-on\s+workshop)\b",
    r"^\s*page\s+\d+\s+of\s+\d+\s*$",
    r"^\s*\d+\s*\|\s*p\s*age\s*$",
    r"^\s*\d{4,}/[a-z0-9\.\-_/]+\)?\s*page\s+\d+\s*$",
    r"^\s*\d{4,}/[a-z0-9\.\-_/]+$",
    r"^\s*(?:rganized\s+by|f\s+recent\s+trends|ccurring\s+during|during\s+\d+\s*[-–]\s*\d+|f\s+limited\s+capability|n\s+biodiversity)\b",
    r"^\s*(?:\(impact\s+factor:\s*[\d\.]+\)|\(?highlighted\s+as\s+the\s+cover\s+page|\(citations?:\s*\d+\)|\(cid:\d+\))\s*$",
    r"^\s*https?://\S+$",
    r"^\s*doi:\s*\S+$",
    r"^\s*Springer,\s*Singapore\.\s*https?://\S+",
    r"(?:email\s*:|mobile\s*:|\+\d{2,}\b|\bcurriculum\s+vitae\b)",
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
    def _clean_preamble(text: str) -> str:
        """Removes summary preambles and footer artifacts from raw text."""
        t = text.strip()
        if re.match(r"^A\s+total\s+of\s+\d+\s+publications\b", t, re.I):
            m = re.search(
                r"\]\s*(?:AuthoredBook|Books?|Papers?|Articles?)?[^\w]*?(?:CV-[^\s]+\s+egaP\s+\d+\s*)?[\uf076\u2022\*\-➢\s]*",
                t,
                re.I,
            )
            if m:
                t = t[m.end() :].strip()
            else:
                m2 = re.search(r"[\uf076\u2022\*\-➢]\s*([A-Z])", t)
                if m2:
                    t = t[m2.start() + 1 :].strip()

        # Strip embedded page numbers
        t = re.sub(r"\bpage\s+\d+\s+of\s+\d+\b", "", t, flags=re.I).strip()
        t = re.sub(r"^(?:CV-[A-Za-z0-9_-]+\s*)?(?:egaP|Page)\s*\d+\s*", "", t, flags=re.I).strip()
        t = re.sub(r"^[\uf076\u2022\*\-➢\s]+", "", t).strip()

        # Strip trailing citation count blocks
        t = re.sub(r"\bCITATIONS\s+Number\s+of\s+citations:.*$", "", t, flags=re.I).strip()
        t = re.sub(r"\b(?:h-index:\s*\d+|i10-index:\s*\d+).*$", "", t, flags=re.I).strip()
        return t

    @classmethod
    def _split_embedded_citations(cls, raw_citation: str) -> List[str]:
        """Splits single text blocks containing multiple distinct publications."""
        text = cls._clean_preamble(raw_citation)

        # Strip trailing non-pub blocks before splitting
        text = re.split(
            r"\b(?:Invited\s+Talks|Conferences\s+and\s+Workshops\s+attended)\b",
            text,
            flags=re.I,
        )[0].strip()

        # 1. Numbered entries like "1 N.Pradhan... 2 S.Saha..." or "2 S.Saha... 3 S.Gupta..."
        if re.search(r"(?:^|\s)\b\d{1,2}\s+[A-Z].*?\b\d{1,2}\s+[A-Z]", text):
            parts = re.split(r"(?<=[,\.\d\s])\s*\b\d{1,2}\s+(?=[A-Z][a-zA-Z\.\,])", text)
            cleaned = [p.strip() for p in parts if len(p.strip().split()) >= 3 or len(p.strip()) >= 25]
            if len(cleaned) > 1:
                return cleaned

        # 2. Sub-items like "(i) “Title 1”... (ii) “Title 2”..."
        if re.search(r"\([ivx0-9]+\)\s*[\"“]", text, re.I):
            parts = re.split(r"(?<=[;\.\)])\s*(?=\([ivx0-9]+\)\s*[\"“])", text, flags=re.I)
            cleaned = [p.strip() for p in parts if len(p.strip().split()) >= 3]
            if len(cleaned) > 1:
                return cleaned

        # 3. Concatenated publications ending in year period: "(2018). Author, Title..."
        if re.search(r"\((?:19|20)\d{2}\)\.\s+[A-Z][a-zA-Z\.\s]+(?:Collaboration|\bet\s+al)", text):
            parts = re.split(
                r"(?<=\(\d{4}\)\.)\s+(?=[A-Z])|(?<=\d{4}\.)\s+(?=[A-Z][a-zA-Z\.\s]+(?:Collaboration|\bet\s+al))",
                text,
            )
            cleaned = [p.strip() for p in parts if len(p.strip().split()) >= 4]
            if len(cleaned) > 1:
                return cleaned

        return [text]

    @staticmethod
    def _is_invalid_citation(text: str) -> bool:
        """Checks if citation string represents obvious non-publication junk."""
        t = text.strip()
        words = t.split()
        if len(words) < 3 and len(t) < 25:
            return True
        t_clean = re.sub(r"^[➢\-\*•\d\.\s\(\)]+\s*", "", t).strip()

        # Pure attendance / participation records
        if re.match(r"^(?:❖\s*)?(?:Attended|Participated\s+in)\b", t_clean, re.I):
            if not re.search(r"\b(?:paper\s+presented|presented\s+a\s+paper)\b", t_clean, re.I):
                return True

        if REJECT_PUB_REGEX.search(t):
            return True

        # Standalone table headers
        if re.search(r"\b(?:board/university|university/board|percentage|passing\s+year|examination\s+passed)\b", t, re.I):
            return True

        # Fragments with no actual paper title
        if re.fullmatch(
            r"(?:Presented\s+Paper\s+in\s+(?:International|National)?|Paper\s+Published\s+in|Page\s+\d+|[0-9\s\|\-_/]+)",
            t_clean,
            re.I,
        ):
            return True

        return False

    @staticmethod
    def _clean_title(title: str) -> str:
        """Cleans bullet characters, numbering, reverse page footers, and punctuation from title."""
        if not title:
            return ""
        t = title.strip(' \t\n\r"\'“”-–—•*➢,;:')
        t = re.sub(r"^(?:\(?\d+\)?\.?|\(?[ivx]+\)\.?)\s*", "", t, flags=re.IGNORECASE).strip()
        t = re.sub(r"\bpage\s+\d+\s+of\s+\d+\b", "", t, flags=re.I).strip()
        t = re.sub(r"^(?:CV-[A-Za-z0-9_-]+\s*)?(?:egaP|Page)\s*\d+\s*", "", t, flags=re.I).strip()
        t = re.sub(r"^[\uf076\u2022\*\-➢\s]+", "", t).strip()
        # Strip trailing book metadata like ", Foreword by...", ", Publisher..."
        t = re.split(r",\s*(?:Foreword|Edited by|Publisher|Raj Publications)\b", t, flags=re.I)[0].strip()
        t = t.strip(' \t\n\r"\'“”-–—•*➢,;:')
        t = re.sub(r"\s+", " ", t)
        return t

    @classmethod
    def _looks_like_person_name(cls, s: str) -> bool:
        """Checks if a comma-separated clause looks like author names rather than a publication title."""
        clean = s.strip()
        clean = re.sub(r"^(?:and|&)\s+", "", clean, flags=re.I).strip()
        clean = re.sub(r"#", "", clean).strip()
        words = clean.split()
        if 1 <= len(words) <= 4:
            if all(
                w[0].isupper()
                or w.lower() in ("van", "der", "von", "de", "da")
                or re.match(r"^[A-Z]\.", w)
                for w in words
                if w.isalpha()
            ):
                if not re.search(
                    r"\b(?:Method|Model|Analysis|Study|Effect|Investigation|Synthesis|Structure|System|Review|Introduction|Properties|Design|Conference|Journal|Proceedings|Evaluation|Optimization|Algorithm|Application|Modulation|Resonance|Metamaterial|Detection|Fabrication|Dynamics|Characterization|Transmission)\b",
                    clean,
                    re.I,
                ):
                    return True
        if " and " in clean:
            parts = clean.split(" and ", 1)
            return cls._looks_like_person_name(parts[0]) and cls._looks_like_person_name(parts[1])
        return False

    @classmethod
    def _extract_title(cls, text: str) -> str:
        """Deterministic, multi-pattern title extraction from citation string."""
        clean_text = cls._clean_preamble(text)
        clean_text = re.sub(r"^[➢\-\*•\d\.\s\(\)]+\s*", "", clean_text).strip()

        # Pattern A: Quoted title: "Title" or “Title”
        qm = re.search(r'[\"“]([^\”\"\r\n]{8,300})[\"”]', clean_text)
        if qm:
            cand = cls._clean_title(qm.group(1))
            words = cand.split()
            if (len(words) >= 3 or len(cand) >= 20) and not re.search(
                r"\b(?:proceedings|conference on|symposium on|international journal)\b", cand, re.I
            ):
                return cand

        # Pattern B: Semicolon after title: Title; Authors... (physics CV style)
        if ";" in clean_text:
            before_semi = clean_text.split(";", 1)[0].strip()
            words = before_semi.split()
            if (3 <= len(words) <= 30 or len(before_semi) >= 20) and not re.search(
                r"^(?:pp|vol|doi|page|issn|isbn)\b", before_semi, re.I
            ):
                if not re.search(r"\b(?:et\s+al\.?)\b", before_semi):
                    return cls._clean_title(before_semi)

        # Pattern C: Authors: Title, Venue (Year) (math CV style)
        if ":" in clean_text:
            parts = clean_text.split(":", 1)
            prefix = parts[0].strip()
            if len(prefix.split()) <= 8 and (re.search(r"\band\b", prefix, re.I) or re.search(r"\b[A-Z]\.", prefix)):
                after_colon = parts[1].strip()
                tm = re.search(r"^([^,\n]+?)(?:,\s*[A-Z]|\.|\()", after_colon)
                if tm and len(tm.group(1).split()) >= 3:
                    return cls._clean_title(tm.group(1))
                tm2 = re.search(r"^([^\.\n]{8,250})", after_colon)
                if tm2 and len(tm2.group(1).split()) >= 3:
                    return cls._clean_title(tm2.group(1))

        # Pattern D: "Paper Published at / in <Venue> <Title> ISSN..." or "Presented Paper in <Venue> <Title> ISBN..."
        if re.match(r"^(?:Paper\s+Published\s+(?:at|in)|Presented\s+Paper\s+(?:at|in))\b", clean_text, re.I):
            m_end = re.search(r"\b(?:ISSN|ISBN|Vol\.?|Issue)\b", clean_text, re.I)
            core = clean_text[: m_end.start()].strip() if m_end else clean_text
            core = re.sub(r"^(?:Paper\s+Published\s+(?:at|in)|Presented\s+Paper\s+(?:at|in))\s+", "", core, flags=re.I).strip()
            m_loc = re.search(r",\s*(?:[A-Za-z\s]+(?:Pradesh|Noida\s*\(UP\)|Delhi|India))\s+", core)
            if m_loc:
                cand = core[m_loc.end() :].strip()
                if len(cand.split()) >= 3:
                    return cls._clean_title(cand)
            m_disc = re.search(r"\b(?:in\s+Engineering and Science|Parishodh Journal|Design Engineering)\s+", core, re.I)
            if m_disc:
                cand = core[m_disc.end() :].strip()
                if len(cand.split()) >= 3:
                    return cls._clean_title(cand)

        # Pattern E: Title before ISSN / Design Engineering
        j_m = re.search(r"^([A-Z][^\n]{10,200}?)\s+(?:Design Engineering|ISSN|ISBN)\b", clean_text, re.I)
        if j_m and len(j_m.group(1).split()) >= 3:
            return cls._clean_title(j_m.group(1))

        # Pattern F: APA style: Authors (YYYY). Title. Venue
        ym = re.search(
            r"\((?:19|20)\d{2}[a-z]?(?:,\s*[A-Za-z]+)?\)\s*[\.:,-]?\s*([A-Z][^\.\n]{8,250}?)(?:\.|\bISSN|\bVol|\bpp|\bin\b|\bdoi\b|\,)",
            clean_text,
            re.IGNORECASE,
        )
        if ym:
            cand = cls._clean_title(ym.group(1))
            if len(cand.split()) >= 3 and not re.search(r"^\s*under\s+review\b", cand, re.I):
                return cand

        # Pattern G: Comma-delimited clauses (distinguishes Title-first vs Authors-first)
        clauses = [c.strip() for c in clean_text.split(",") if c.strip()]
        if len(clauses) >= 2:
            # Case G1: Title first (e.g. Dibakar)
            if not cls._looks_like_person_name(clauses[0]) and len(clauses[0].split()) >= 4:
                return cls._clean_title(clauses[0])
            # Case G2: Authors first (e.g. Swapnil)
            for c in clauses:
                if not cls._looks_like_person_name(c) and len(c.split()) >= 4:
                    if not re.search(r"^(?:pp\.|vol\.|no\.|issue|page|doi|isbn|issn)\b", c, re.I):
                        return cls._clean_title(c)

        # Pattern H: IEEE / Science Style: Author initials list, Title, Journal
        author_prefix_m = re.match(r"^(?:(?:[A-Z]\.\s*){1,3}[A-Za-z\-']+(?:,\s*|\s+and\s+))+\s*", clean_text)
        if author_prefix_m:
            remaining = clean_text[author_prefix_m.end() :].strip()
            tm = re.search(
                r"^([A-Z][^\,\.\n]{8,250}?)(?:[\,\.]\s*(?:Int\.|J\.|Appl\.|Phys\.|IEEE|ACM|Mater\.|Results|New|Optics|Proc\.|Adv\.|Scientific|\d|\())",
                remaining,
            )
            if tm and len(tm.group(1).split()) >= 3:
                return cls._clean_title(tm.group(1))
            first_clause = remaining.split(",", 1)[0].strip()
            if len(first_clause.split()) >= 3:
                return cls._clean_title(first_clause)

        # Pattern I: "Paper presented on <Title> in <Conference>"
        pon = re.search(r"Paper presented on\s+[\"“]?([^\”\"\n]{8,250}?)[\"”]?\s+(?:in|at)\s+", clean_text, re.I)
        if pon and len(pon.group(1).split()) >= 3:
            return cls._clean_title(pon.group(1))

        # Fallback to split parts
        parts = re.split(r"[\.\,\;]\s+", clean_text)
        for p in parts:
            clean_p = cls._clean_title(p)
            words = clean_p.split()
            if 4 <= len(words) <= 25:
                if not re.search(
                    r"\b(?:pp|vol|isbn|issn|page|pages|editions?|proceedings|university|department|et\s+al\.?)\b",
                    clean_p,
                    re.I,
                ):
                    return clean_p

        return ""

    @staticmethod
    def _extract_year(text: str) -> Optional[str]:
        """Robust extraction of 4-digit publication year strictly supported by source text."""
        # 1. Year in parentheses: (YYYY) or (YYYY, Month) or (Month YYYY)
        m = re.search(r"\(((?:19|20)\d{2})(?:[a-z]|,\s*[A-Za-z]+)?\)", text)
        if m:
            return m.group(1)

        m1b = re.search(r"\((?:[A-Za-z]+[\s,-]+)?((?:19|20)\d{2})\)", text)
        if m1b:
            return m1b.group(1)

        # 2. Month-Year or Month Year: July-2023, July 2023, March/2020, 20th-22ndSep., 2007
        m2 = re.search(
            r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[-,\s\./]*(\d{1,2}[a-z]{0,2})?[-,\s\./]+((?:19|20)\d{2})\b",
            text,
            re.IGNORECASE,
        )
        if m2:
            return m2.group(2)

        # 3. Trailing year: , YYYY. or , YYYY
        m3 = re.search(r"[,\s]((?:19|20)\d{2})\s*[\.]?$", text.strip())
        if m3:
            return m3.group(1)

        # 4. Year preceded by "Year-" or "Year:" or "Pub."
        m4 = re.search(r"\b(?:Year|Pub|Published)[-:\s]+((?:19|20)\d{2})\b", text, re.IGNORECASE)
        if m4:
            return m4.group(1)

        # 5. Fallback: 4-digit year not preceded by pp./pages/vol/issue/no and not part of ISSN/ISBN range
        for ym in re.finditer(r"\b((?:19|20)\d{2})\b", text):
            start = ym.start()
            prefix = text[max(0, start - 12) : start].lower()
            if not re.search(r"(?:pp\.?|pages?|vol\.?|issue|no\.?|-|–)\s*$", prefix):
                after = text[ym.end() : min(len(text), ym.end() + 10)]
                if not re.search(r"^\s*-\s*\d+", after):
                    return ym.group(1)

        return None

    @staticmethod
    def _determine_type(category_hint: str, raw_citation: str) -> str:
        """Determines publication type strictly: 'journal', 'conference', or 'other'."""
        text_lower = raw_citation.lower()

        if any(k in text_lower for k in ["journal", "transactions", "letters", "annals of", "bulletin of"]):
            if not re.search(r"\b(?:proceedings|conference|symposium)\b", text_lower):
                return "journal"
        if any(k in text_lower for k in ["conference", "proceedings", "symposium", "proc.", "ieee trans", "acm", "workshop"]):
            if not re.search(r"\b(?:journal|letters)\b", text_lower):
                return "conference"

        if category_hint == "journal_articles":
            return "journal"
        elif category_hint in ("conference_papers", "conference_proceedings"):
            return "conference"
        else:
            return "other"

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

                # 1. Split embedded publications if present in a single text block
                sub_citations = self._split_embedded_citations(raw_citation)

                for sub_cit in sub_citations:
                    # 2. Pre-filter obvious non-publication records (talks, workshops, attendance, fragments)
                    if self._is_invalid_citation(sub_cit):
                        continue

                    # 3. Extract exact title, year, and type from citation evidence
                    title = self._extract_title(sub_cit)
                    if not title or (len(title.split()) < 3 and len(title) < 20) or self._is_invalid_citation(title):
                        continue

                    year = self._extract_year(sub_cit)
                    pub_type = self._determine_type(cat, sub_cit)

                    # 4. Classify tier via service (LLM layer or fallback)
                    parsed = self.pub_service.parse_and_classify_citation(
                        raw_citation=sub_cit, category_hint=cat
                    )
                    tier = parsed.get("tier", "Unranked")
                    if tier not in ("Tier-1", "Tier-2", "Tier-3", "Unranked"):
                        tier = "Unranked"

                    valid_entries.append(
                        PublicationEntry(
                            title=title,
                            type=pub_type,
                            year=year,
                            tier=tier,
                        )
                    )

        # 5. Conservative Deduplication within candidate
        deduped_entries: List[PublicationEntry] = []
        seen_keys: Dict[str, PublicationEntry] = {}

        for entry in valid_entries:
            key = self._normalize_title_for_dedup(entry.title)
            if len(key) < 12:
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
