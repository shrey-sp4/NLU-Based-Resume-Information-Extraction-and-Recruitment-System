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
    r"\b(Ph\.?\s*D\.?|PhDin[A-Za-z]+|MastersofScience|BachelorofScience|"
    r"Doctor of Philosophy|D\.?Phil\.?|"
    r"M\.?Tech\.?|M\.?E\.?|Master of Technology|Master of Engineering|"
    r"M\.?Sc\.?|Master of Science|M\.?S\.?|"
    r"M\.?A\.?|Master in Arts|Master of Arts|M\.?Phil\.?|"
    r"B\.?Tech\.?|B\.?E\.?|Bachelor of Technology|Bachelor of Engineering|"
    r"B\.?Sc\.?(?:\s*\(Honours\))?|Bachelor of Science(?:\s*\(Honours\))?|"
    r"B\.?A\.?(?:\([A-Z]\))?|Bachelor of Arts|"
    r"MCA|BCA|MBA)\b",
    re.IGNORECASE,
)

POSTDOC_JOB_REGEX = re.compile(
    r"\b(?:post-?doctoral\s+(?:research\s+associate|researcher|fellow|scholar|scientist|intern)|"
    r"post-?doc\.?\s+research\s+associate|post-?doctoral)\b",
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

INSTITUTION_EXTRACT_REGEX = re.compile(
    r"\b((?:[A-Z][A-Za-z0-9&.\-']*(?:\s+[A-Za-z0-9&.\-']+){0,6}\s+)?"
    r"(?:University(?:\s*of)?|Universityof|Institute(?:\s*of)?|College(?:\s*of)?|Academy|Vidyapeeth|Vishwavidyalaya|"
    r"IIT|NIT|IIIT|IIM|IISc|BITS|VNIT|SVNIT|MANIT|MNIT|RGTU|DAVV|"
    r"IndianInstituteofTechnology[A-Za-z]*|DelhiUniversity|MirandaHouse)"
    r"(?:\s+[A-Za-z0-9&.\-']+(?:\s+[A-Za-z0-9&.\-']+){0,4})?)\b",
    re.IGNORECASE,
)

DATE_RANGE_REGEX = re.compile(
    r"(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+)?\d{4}"
    r"(?:\s*(?:-|–|to)\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+)?(?:Present|\d{4}))?",
    re.IGNORECASE,
)


def get_canonical_degree_key(deg: str) -> str:
    """Returns canonical key for deduplication (e.g. phd, mtech, msc, ma, btech, bsc, ba)."""
    d = deg.lower().replace(".", "").replace(" ", "").strip()
    if d in ("phd", "doctorofphilosophy", "dphil", "doctorate") or d.startswith("phdin"):
        return "phd"
    if d in ("mtech", "me", "masteroftechnology", "masterofengineering"):
        return "mtech"
    if d in ("msc", "ms", "masterofscience", "mastersofscience"):
        return "msc"
    if d in ("ma", "masterinarts", "masterofarts"):
        return "ma"
    if d in ("btech", "be", "bacheloroftechnology", "bachelorofengineering"):
        return "btech"
    if d in ("bsc", "bs", "bachelorofscience", "bachelorofsciencehonours"):
        return "bsc"
    if d in ("ba", "bachelorofarts"):
        return "ba"
    if d in ("mphil", "masterofphilosophy"):
        return "mphil"
    if d in ("mba", "masterofbusinessadministration"):
        return "mba"
    if d in ("mca", "masterofcomputerapplications"):
        return "mca"
    if d in ("bca", "bachelorofcomputerapplications"):
        return "bca"
    return d


def normalize_degree_name(deg: str) -> str:
    """Normalizes raw or un-spaced degree names to standard representations."""
    d_clean = deg.strip()
    d_lower = d_clean.lower()
    if d_lower.startswith("phdin"):
        return "PhD"
    if d_lower == "mastersofscience":
        return "Master of Science"
    if d_lower == "bachelorofscience":
        return "Bachelor of Science"
    if d_lower in ("ph. d", "ph.d", "ph.d.", "phd"):
        return "Ph.D."
    return d_clean


def clean_institution(inst: str) -> str:
    """Cleans raw institution string, stripping prefixes, dates, supervisor names, and un-spacing run-together tokens."""
    if not inst:
        return ""
    # Strip leading from/at/in
    inst = re.sub(r"^(?:from\s+|at\s+|in\s+)", "", inst, flags=re.IGNORECASE).strip()
    # Strip leading month words like 'May University...'
    inst = re.sub(
        r"^(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+",
        "",
        inst,
        flags=re.IGNORECASE,
    ).strip()
    # Fix Universityof
    inst = re.sub(r"\bUniversityof\b", "University of", inst, flags=re.IGNORECASE).strip()
    # Un-concatenate camelCase / run-together tokens
    if "IndianInstituteofTechnology" in inst:
        inst = re.sub(r"IndianInstituteofTechnology([A-Za-z]*)", r"Indian Institute of Technology \1", inst).strip()
    if "DelhiUniversity" in inst:
        inst = inst.replace("DelhiUniversity", "Delhi University")
    if "MirandaHouse" in inst:
        inst = inst.replace("MirandaHouse", "Miranda House")

    # Strip specialization and department prefixes (e.g. inCommunicationandSignalProcessing. ElectronicsEngineeringDepartment Indian Institute of Technology)
    inst = re.sub(
        r"^(?:in[A-Za-z]+[.,]?\s+)?(?:[A-Za-z]+Department|[A-Za-z]+Dept)\s+",
        "",
        inst,
    ).strip()

    # Strip leading supervisor words or titles
    inst = re.sub(
        r"^(?:Prof\.?|Dr\.?)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\s+(?=(?:National|Indian|Institute|University))",
        "",
        inst,
    ).strip()
    # Strip leading degree acronym or level (e.g. 'PhD Visvesvaraya', 'Masters Institute of Engineering', 'Graduation Medicaps')
    inst = re.sub(
        r"^(?:Ph\.?D\.?|PhD|Doctor of Philosophy|D\.?Phil\.?|"
        r"M\.?Tech\.?|M\.?E\.?|Master of Technology|Master of Engineering|Masters|"
        r"M\.?Sc\.?|Master of Science|M\.?S\.?|"
        r"M\.?A\.?|Master in Arts|Master of Arts|M\.?Phil\.?|"
        r"B\.?Tech\.?|B\.?E\.?|Bachelor of Technology|Bachelor of Engineering|Graduation|"
        r"B\.?Sc\.?|Bachelor of Science|B\.?A\.?(?:\([A-Z]\))?|Bachelor of Arts|"
        r"MCA|BCA|MBA)\s+",
        "",
        inst,
        flags=re.IGNORECASE,
    ).strip()
    # Strip trailing year or date info like "in 2017", "2005", "1998", "2016-2018"
    inst = re.sub(r"\s+(?:in\s+)?(?:\d{4}\s*(?:-\s*\d{4})?|\d{4})$", "", inst, flags=re.IGNORECASE).strip()
    # Strip trailing "present"
    inst = re.sub(r"\s+present$", "", inst, flags=re.IGNORECASE).strip()

    # Reject generic fragments without institutional identity
    if inst.lower() in (
        "department",
        "school",
        "institute",
        "analytics",
        "science",
        "department of mathematics",
        "department of physics",
        "school of letters",
        "school of humanities and social sciences",
    ):
        return ""
    if inst.lower().startswith(("in ", "of ", "with ")):
        return ""
    return inst


def find_degrees_in_text(text: str) -> List[tuple[int, int, str]]:
    """Finds genuine degree matches in text, excluding false positives like Medford, MA, MS Office, and Postdoc job titles."""
    matches = []
    for m in DEGREE_LOOKUP_REGEX.finditer(text):
        val = m.group(0).strip()
        start = m.start()
        end = m.end()
        # Filter MA in location (Medford, MA, USA)
        if val.upper() == "MA":
            prefix = text[max(0, start - 15) : start]
            suffix = text[end : min(len(text), end + 15)]
            if re.search(r"[A-Za-z]+,\s*$", prefix) or re.search(r"^\s*,\s*(?:USA|US|\d{5})", suffix):
                continue
        # Filter MS in MS Excel / MS Word
        if val.upper() == "MS":
            suffix = text[end : min(len(text), end + 20)]
            if re.search(r"^\s*(?:Office|Excel|Word|Powerpoint|Windows|Access)", suffix, re.IGNORECASE):
                continue
        # Filter Postdoctoral job title
        if POSTDOC_JOB_REGEX.search(text[max(0, start - 10) : min(len(text), end + 30)]):
            continue
        matches.append((start, end, val))
    return matches


class EducationNormalizer:
    """
    Normalizes education records from raw extraction JSON into the strict candidate education schema:
    degree, stream, institution, university_tier.
    Filters out table headers, secondary school boards, thesis topics, advisor lines, postdoctoral job titles,
    and non-education text.
    Safely handles multi-degree composite blocks and preserves explicit degree-institution associations.
    Rejects orphaned institution-only records where degree cannot be verified.
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

            # 4. Reject postdoctoral employment appointments / job titles
            if POSTDOC_JOB_REGEX.search(degree) or (not degree and POSTDOC_JOB_REGEX.search(raw_t)):
                continue

            # 5. Check higher degree presence
            valid_degs = find_degrees_in_text(raw_t)
            has_higher_deg = bool(
                degree and not SECONDARY_EDUCATION_REGEX.search(degree) and DEGREE_LOOKUP_REGEX.search(degree)
            ) or bool(valid_degs)
            is_secondary_degree = bool(
                degree and SECONDARY_EDUCATION_REGEX.search(degree) and not DEGREE_LOOKUP_REGEX.search(degree)
            )

            # Reject secondary-school-only records
            if is_secondary_degree:
                continue
            if not has_higher_deg and (
                SECONDARY_EDUCATION_REGEX.search(institution) or SECONDARY_EDUCATION_REGEX.search(raw_t)
            ):
                continue

            # 6. Reject pure non-education junk records (only when no higher degree is present)
            if not has_higher_deg and (NON_EDU_JUNK_REGEX.search(raw_t) or NON_EDU_JUNK_REGEX.search(institution)):
                continue

            # 7. Safe multi-degree composite block recovery
            distinct_canon_degs = list(dict.fromkeys([get_canonical_degree_key(d[2]) for d in valid_degs]))
            if len(distinct_canon_degs) >= 2:
                # First check if text is partitioned by bullet characters or newlines
                bullet_parts = re.split(r"[•\*\u25cf\u25cb\u2022\u25e6\u27a2\uf0d8\uf0b7\uf0f3]+|\n+", raw_t)
                bullet_parts = [p.strip() for p in bullet_parts if p.strip()]

                if len(bullet_parts) > 1:
                    for bp in bullet_parts:
                        b_degs = find_degrees_in_text(bp)
                        if not b_degs or (
                            SECONDARY_EDUCATION_REGEX.search(bp)
                            and not any(d in bp for d in [x[2] for x in b_degs])
                        ):
                            continue
                        deg_name = normalize_degree_name(b_degs[0][2])
                        im = INSTITUTION_EXTRACT_REGEX.search(bp)
                        inst_name = ""
                        if im:
                            ci = clean_institution(im.group(0))
                            if not SECONDARY_EDUCATION_REGEX.search(ci):
                                inst_name = ci
                        if not inst_name and institution and institution.lower() in bp.lower():
                            inst_name = clean_institution(institution)
                        candidates_raw.append({"degree": deg_name, "institution": inst_name})
                    continue
                else:
                    # Date-aware boundary splitting for run-on narrative blocks
                    for i, (start, end, deg_name) in enumerate(valid_degs):
                        next_start = valid_degs[i + 1][0] if i + 1 < len(valid_degs) else len(raw_t)
                        between = raw_t[end:next_start]
                        date_m = DATE_RANGE_REGEX.search(between)
                        inst_name = ""
                        if date_m:
                            before_date = between[: date_m.end()]
                            im = INSTITUTION_EXTRACT_REGEX.search(before_date)
                            if im:
                                ci = clean_institution(im.group(0))
                                if not SECONDARY_EDUCATION_REGEX.search(ci):
                                    inst_name = ci
                        else:
                            im = INSTITUTION_EXTRACT_REGEX.search(between)
                            if im:
                                ci = clean_institution(im.group(0))
                                if not SECONDARY_EDUCATION_REGEX.search(ci):
                                    inst_name = ci
                        if not inst_name and i > 0:
                            prev_end = valid_degs[i - 1][1]
                            prev_between = raw_t[prev_end:start]
                            p_date_m = DATE_RANGE_REGEX.search(prev_between)
                            if p_date_m:
                                after_p_date = prev_between[p_date_m.end() :]
                                im_a = INSTITUTION_EXTRACT_REGEX.search(after_p_date)
                                if im_a:
                                    ci = clean_institution(im_a.group(0))
                                    if not SECONDARY_EDUCATION_REGEX.search(ci):
                                        inst_name = ci
                        candidates_raw.append({"degree": normalize_degree_name(deg_name), "institution": inst_name})
                    continue

            # 8. Single-degree entry recovery
            if not degree:
                if len(valid_degs) == 1:
                    degree = valid_degs[0][2]
                elif DEGREE_LOOKUP_REGEX.search(institution):
                    degree = institution.strip()
                    institution = ""

            degree = normalize_degree_name(degree)
            institution = clean_institution(institution)
            if SECONDARY_EDUCATION_REGEX.search(institution):
                institution = ""

            # If institution is empty but clearly present in single-degree raw_t
            if not institution and len(valid_degs) == 1:
                im = INSTITUTION_EXTRACT_REGEX.search(raw_t)
                if im:
                    ci = clean_institution(im.group(0))
                    if not SECONDARY_EDUCATION_REGEX.search(ci):
                        institution = ci

            # Reject orphaned records with no degree
            if not degree:
                continue

            candidates_raw.append({"degree": degree, "institution": institution})

        # Deduplication using canonical degree keys
        merged_entries: Dict[str, Dict[str, str]] = {}
        for item in candidates_raw:
            canon_key = get_canonical_degree_key(item["degree"])
            if not canon_key:
                continue
            if canon_key not in merged_entries:
                merged_entries[canon_key] = item
            else:
                existing = merged_entries[canon_key]
                # If new entry has institution and existing does not, adopt it
                if not existing["institution"] and item["institution"]:
                    existing["institution"] = item["institution"]
                elif existing["institution"] and item["institution"]:
                    # Prefer Tier-1 / Tier-2 over Tier-3 / Unknown
                    ex_tier = self.tier_service.categorize_institution(existing["institution"]).get("tier", "Unknown")
                    new_tier = self.tier_service.categorize_institution(item["institution"]).get("tier", "Unknown")
                    if ex_tier in ("Unknown", "Tier-3") and new_tier in ("Tier-1", "Tier-2"):
                        existing["institution"] = item["institution"]

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
