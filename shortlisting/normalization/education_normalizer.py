from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from shortlisting.llm.university_tier_service import UniversityTierService
from shortlisting.models.candidate import EducationEntry

TABLE_HEADER_REGEX = re.compile(
    r"\b(?:degree\s+university|board/university|university/board|college/school|"
    r"percentage\s+passing|year\s+of\s+percentage|division\s+completion|"
    r"year\s+of\s+passing|in\s+which\s+year|academic\s+college|level\s+board|"
    r"passing\s+year)\b",
    re.IGNORECASE,
)

SECONDARY_EDUCATION_REGEX = re.compile(
    r"\b(?:10th|12th|higher\s+secondary|secondary\s+school|secondary\s+education|"
    r"madhyamik|matric(?:ulation)?|intermediate|high\s+school|ssc|hsc|cbse|icse|gsheb|"
    r"wbbse|wbchse|up\s+board|jk\s+board|bsemp|board\s+of\s+secondary|"
    r"council\s+of\s+higher\s+secondary|council\s+of\s+secondary|"
    r"school\s+examination|patna\s+central\s+school|public\s+school)\b",
    re.IGNORECASE,
)

NON_EDU_JUNK_REGEX = re.compile(
    r"\b(?:tentative\s+thesis|outline\s+of\s+the\s+work|completed\s+coursework|"
    r"tools/languages|teaching\s+assistantship|publication\s+details|"
    r"international\s+journals?|national\s+journals?|book\s+chapters?|"
    r"book\s+reviews?|seminars?|conferences?|workshop\s+attended|"
    r"net/set|ugc\s+net|wbset|diagnostic\s+strategies|"
    r"induction\s+motor|thermal\s+imaging|7\.4\s+cgpa|cgpa\s+of|"
    r"forest\s+dependence|forest\s+management|himalayan\s+region|"
    r"food\s+security\s+act)\b",
    re.IGNORECASE,
)

DEGREE_LOOKUP_REGEX = re.compile(
    r"\b(Ph\.?D\.?|Doctor of Philosophy|D\.?Phil\.?|"
    r"M\.?Tech\.?|M\.?E\.?|Master of Technology|Master of Engineering|"
    r"M\.?Sc\.?|Master of Science|M\.?S\.?|"
    r"M\.?A\.?|Master in Arts|Master of Arts|M\.?Phil\.?|"
    r"B\.?Tech\.?|B\.?E\.?|Bachelor of Technology|Bachelor of Engineering|"
    r"B\.?Sc\.?|Bachelor of Science|B\.?A\.?(?:\([A-Z]\))?|Bachelor of Arts|"
    r"MCA|BCA|MBA|Postdoctoral|Post Doctoral)\b",
    re.IGNORECASE,
)


ADVISOR_SUPERVISOR_REGEX = re.compile(
    r"(?:^\s*[•\-\*\s]*\s*(?:ph\.?d\.?\s*(?:advisor|supervisor|guide)|advisor|supervisor|co-advisor|co-supervisor|guide)\s*[:\-])|"
    r"\b(?:co-advisor,\s*dr|phd\.\s*advisor:)\b",
    re.IGNORECASE,
)

THESIS_PURE_REGEX = re.compile(
    r"^\s*[•\-\*\s]*\s*(?:ph\.?d\.?\s*(?:thesis|dissertation)\s*:|m\.?sc\.?\s*(?:project|thesis)\s*:|m\.?tech\s*thesis\s*:|b\.?tech\s*project\s*:)",
    re.IGNORECASE,
)

PUB_DUMP_REGEX = re.compile(r"\b(?:list\s+of\s+publications?|peer-reviewed\s+journals)\b", re.IGNORECASE)


class EducationNormalizer:
    """
    Normalizes education records from raw extraction JSON into the strict candidate education schema:
    degree, stream, institution, university_tier.
    Filters out table headers, secondary school boards, thesis topics, advisor lines, and non-education text.
    Strictly avoids inferring missing universities.
    Explicitly omits graduation_year, cgpa, and raw_text.
    """

    def __init__(self, tier_service: Optional[UniversityTierService] = None):
        self.tier_service = tier_service or UniversityTierService()

    def normalize(self, raw_education_entries: List[Dict[str, Any]]) -> List[EducationEntry]:
        candidates_raw: List[Dict[str, str]] = []

        for raw_entry in raw_education_entries:
            if not isinstance(raw_entry, dict):
                continue

            raw_t = str(raw_entry.get("raw_text", "") or "").strip()
            degree = str(raw_entry.get("degree", "") or "").strip()
            institution = str(raw_entry.get("institution", "") or "").strip()

            # 1. Reject table column headers (when institution itself is a header, or degree is empty and raw_t is a header)
            if TABLE_HEADER_REGEX.search(institution) or (not degree and TABLE_HEADER_REGEX.search(raw_t)):
                continue

            # 2. Reject advisor/supervisor lines
            if ADVISOR_SUPERVISOR_REGEX.search(raw_t) or institution.lower() in (
                "advisor",
                "co-advisor",
                "supervisor",
                "co-supervisor",
                "guide",
            ):
                continue

            # 3. Reject standalone thesis title entries and publication dumps in education
            if (not institution and THESIS_PURE_REGEX.search(raw_t)) or PUB_DUMP_REGEX.search(raw_t):
                continue

            # Detect whether degree or raw_text explicitly contains a recognized higher degree
            has_higher_deg = bool(DEGREE_LOOKUP_REGEX.search(degree) or DEGREE_LOOKUP_REGEX.search(raw_t))
            is_secondary_degree = bool(degree and SECONDARY_EDUCATION_REGEX.search(degree) and not DEGREE_LOOKUP_REGEX.search(degree))

            # 4. Reject genuine secondary-school-only records:
            # - If degree is explicitly secondary (e.g. 10th, 12th, Higher Secondary), OR
            # - If there is no higher degree, and (institution or raw_t matches secondary regex)
            if is_secondary_degree:
                continue
            if not has_higher_deg and (SECONDARY_EDUCATION_REGEX.search(institution) or SECONDARY_EDUCATION_REGEX.search(raw_t)):
                continue

            # 5. Reject pure non-education junk records (only when no higher degree is present)
            if not has_higher_deg and (NON_EDU_JUNK_REGEX.search(raw_t) or NON_EDU_JUNK_REGEX.search(institution)):
                continue

            # 6. Recover degree if empty but clearly stated in raw text
            if not degree:
                dm = DEGREE_LOOKUP_REGEX.search(raw_t)
                if dm:
                    degree = dm.group(0).strip()

            # 7. Clean existing institution (do NOT infer missing universities)
            if institution:
                institution = re.sub(r"^(?:from\s+|at\s+)", "", institution, flags=re.IGNORECASE).strip()
                # If institution is just department/school/generic fragment without a university, clear it
                if institution.lower() in (
                    "department",
                    "school",
                    "institute",
                    "analytics",
                    "department of mathematics",
                    "department of physics",
                    "school of humanities and social sciences",
                ):
                    institution = ""
                elif DEGREE_LOOKUP_REGEX.fullmatch(institution.strip()):
                    if not degree:
                        degree = institution.strip()
                    institution = ""
                else:
                    # Strip leading degree acronym if attached to institution (e.g. 'M.Tech Galgotias University' -> 'Galgotias University')
                    institution = re.sub(
                        r"^(?:Ph\.?D\.?|Doctor of Philosophy|D\.?Phil\.?|"
                        r"M\.?Tech\.?|M\.?E\.?|Master of Technology|Master of Engineering|"
                        r"M\.?Sc\.?|Master of Science|M\.?S\.?|"
                        r"M\.?A\.?|Master in Arts|Master of Arts|M\.?Phil\.?|"
                        r"B\.?Tech\.?|B\.?E\.?|Bachelor of Technology|Bachelor of Engineering|"
                        r"B\.?Sc\.?|Bachelor of Science|B\.?A\.?(?:\([A-Z]\))?|Bachelor of Arts|"
                        r"MCA|BCA|MBA|Postdoctoral|Post Doctoral)\s+",
                        "",
                        institution,
                        flags=re.IGNORECASE,
                    ).strip()
                    # If remaining string starts with a preposition like 'in ' or 'of ', it's a major/discipline, not an institution
                    if institution.lower().startswith(("in ", "of ", "with ")):
                        institution = ""
                    # Clean trailing 'Present' if attached to institution name
                    institution = re.sub(r"\s+present$", "", institution, flags=re.IGNORECASE).strip()

            # 8. Reject if both degree and institution remain empty
            if not degree and not institution:
                continue

            candidates_raw.append({"degree": degree, "institution": institution})

        # Conservative deduplication / merging of fragmented entries for the same degree
        merged_entries: Dict[str, Dict[str, str]] = {}
        for item in candidates_raw:
            deg_key = item["degree"].lower().replace(".", "").replace(" ", "").strip()
            if not deg_key:
                # Keep institution-only entry if unique
                inst_key = item["institution"].lower().strip()
                if inst_key not in merged_entries:
                    merged_entries[inst_key] = item
            elif deg_key not in merged_entries:
                merged_entries[deg_key] = item
            else:
                # Merge if new record has institution and existing one does not
                if not merged_entries[deg_key]["institution"] and item["institution"]:
                    merged_entries[deg_key]["institution"] = item["institution"]

        normalized_entries: List[EducationEntry] = []
        for item in merged_entries.values():
            degree = item["degree"]
            institution = item["institution"]
            stream = ""  # Extraction pipeline does not isolate stream; keep empty without hallucinating

            tier_info = self.tier_service.categorize_institution(institution, degree=degree)
            tier = tier_info.get("tier", "Unknown")

            normalized_entries.append(
                EducationEntry(
                    degree=degree,
                    stream=stream,
                    institution=institution,
                    university_tier=tier,
                )
            )

        return normalized_entries
