from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from shortlisting.llm.client import ConfigurableLLMClient, LLMClient
from shortlisting.models.candidate import ExperienceEntry

MONTHS_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

ACADEMIC_TITLE_KEYWORDS = re.compile(
    r"\b(?:Professor|Assistant Professor|Associate Professor|Visiting Faculty|Lecturer|"
    r"Post-?doctoral|Research Scholar|Research Associate|Project Associate|Teaching Assistant|"
    r"Senior Research Fellow|Junior Research Fellow|SRF|JRF|Fellow|Scientist|Dean|HOD)\b",
    re.IGNORECASE,
)

ACADEMIC_INSTITUTION_KEYWORDS = re.compile(
    r"\b(?:University|Institute|College|School of|Academy|IIT|NIT|IIIT|IIM|IISc|Vishwavidyalay|Vidyalaya|Campus)\b",
    re.IGNORECASE,
)

INDUSTRY_TITLE_KEYWORDS = re.compile(
    r"\b(?:Software Engineer|Developer|Product Manager|Data Scientist|Data Analyst|Consultant|"
    r"Architect|DevOps|System Administrator|Sales|Marketing|Business Analyst|Lead Engineer)\b",
    re.IGNORECASE,
)

INDUSTRY_INSTITUTION_KEYWORDS = re.compile(
    r"\b(?:Pvt|Ltd|Inc|Corp|Corporation|LLC|Technologies|Solutions|Services|Holdings|Bank|Consultancy|Group)\b",
    re.IGNORECASE,
)

MONTH_REGEX_STR = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)

ENDPOINT_PATTERNS = [
    # DD/MM/YYYY or D/M/YYYY
    r"\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}\b",
    # MM/YYYY
    r"\b\d{1,2}[/.-](?:19|20)\d{2}\b",
    # MM/YY
    r"\b\d{1,2}/\d{2}\b",
    # Day Month Year, e.g. 22nd November, 2010 or 5th July 2022
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTH_REGEX_STR}[,\s]+(?:19|20)\d{{2}}\b",
    # Month Day Year, e.g. March 02, 2019
    rf"\b{MONTH_REGEX_STR}\s+\d{{1,2}}(?:st|nd|rd|th)?[,\s]+(?:19|20)\d{{2}}\b",
    # Month Year, e.g. July 2016, May, 2017, Aug-2011, Sep'24, Sep’24
    rf"\b{MONTH_REGEX_STR}[,\s\-_'’]*(?:(?:19|20)\d{{2}}|['’]?\d{{2}})\b",
    # Year Month, e.g. 2022 Dec
    rf"\b(?:19|20)\d{{2}}\s+{MONTH_REGEX_STR}\b",
    # 4-digit Year
    r"\b(?:19|20)\d{2}\b",
]

SEP_PATTERN = r"(?:\s*[-–—−]\s*(?:till\s+)?|\s+to\s+|\s+till\s+|\s+until\s+)"
END_PATTERN = r"(?:present|current|till\s+date|till\s+now|now|" + "|".join(ENDPOINT_PATTERNS) + r")"
START_PATTERN = "(?:" + "|".join(ENDPOINT_PATTERNS) + r")"

RANGE_REGEX = re.compile(
    rf"({START_PATTERN}){SEP_PATTERN}({END_PATTERN})",
    re.IGNORECASE,
)

SINCE_REGEX = re.compile(
    rf"\b(?:since)\s+({START_PATTERN})",
    re.IGNORECASE,
)

ONWARD_REGEX = re.compile(
    rf"({START_PATTERN})\s+(?:onward|onwards)\b",
    re.IGNORECASE,
)


class ExperienceNormalizer:
    """
    Normalizes extracted experience records into the strict candidate experience schema:
    job_title, institution, dates, experience_type, duration_years.
    Performs hybrid classification and strict duration calculation.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or ConfigurableLLMClient()

    def classify_experience_type(self, job_title: str, institution: str) -> str:
        """
        Classifies experience into: academic | industry | other/unknown.
        Uses deterministic high-confidence rules first, with LLM fallback for ambiguous cases.
        """
        t = job_title.strip()
        i = institution.strip()

        is_academic_title = bool(ACADEMIC_TITLE_KEYWORDS.search(t))
        is_academic_inst = bool(ACADEMIC_INSTITUTION_KEYWORDS.search(i))
        is_industry_title = bool(INDUSTRY_TITLE_KEYWORDS.search(t))
        is_industry_inst = bool(INDUSTRY_INSTITUTION_KEYWORDS.search(i))

        # High-confidence deterministic rules
        if is_academic_title and is_academic_inst:
            return "academic"
        if is_industry_title and is_industry_inst:
            return "industry"
        if is_academic_title and not is_industry_inst:
            return "academic"
        if is_industry_title and not is_academic_inst:
            return "industry"

        # Ambiguous case: Fallback to lightweight LLM query
        if t or i:
            try:
                system_prompt = (
                    "Classify whether the given job role and organization represent 'academic', "
                    "'industry', or 'other/unknown' experience. "
                    "Return ONLY a JSON with key 'experience_type' with value strictly one of: "
                    "'academic', 'industry', 'other/unknown'."
                )
                user_prompt = f"Job Title: {t}\nOrganization: {i}"
                res = self.llm_client.generate_json(system_prompt, user_prompt)
                exp_type = str(res.get("experience_type", "other/unknown")).lower().strip()
                if exp_type in ("academic", "industry", "other/unknown"):
                    return exp_type
            except Exception:
                pass

        if is_academic_inst:
            return "academic"
        if is_industry_inst:
            return "industry"

        return "other/unknown"

    def _parse_endpoint(self, endpoint_str: str, is_end: bool) -> Optional[Tuple[int, int]]:
        if not endpoint_str or not endpoint_str.strip():
            return None
        lower = endpoint_str.lower().strip()

        # 1. Handle Present / Current / till date / now / onward
        if is_end and any(w in lower for w in ["present", "current", "till date", "till now", "now", "onward", "onwards", "date"]):
            now = datetime.now()
            return now.year, now.month

        # 2. Extract year:
        # A. Check MM/YY or D/M/YY (e.g. 08/12 or 1/8/06)
        mmyy_m = re.search(r"\b(\d{1,2})/(\d{2})\b", endpoint_str)
        if mmyy_m and not re.search(r"\b(19|20)\d{2}\b", endpoint_str):
            mo = int(mmyy_m.group(1))
            yy = int(mmyy_m.group(2))
            yr = 2000 + yy if yy < 70 else 1900 + yy
            if 1 <= mo <= 12:
                return yr, mo

        # B. Check 4-digit year (19xx or 20xx)
        year_match = re.search(r"\b(19|20)\d{2}\b", endpoint_str)
        year = None
        if year_match:
            year = int(year_match.group(0))
        else:
            # Check for 2-digit year with apostrophe e.g. '24 or ’24
            apostrophe_m = re.search(r"['’](\d{2})\b", endpoint_str)
            if apostrophe_m:
                yy = int(apostrophe_m.group(1))
                year = 2000 + yy if yy < 70 else 1900 + yy

        if year is None:
            return None

        # 3. Extract month:
        month = None
        # A. Named month in MONTHS_MAP
        for m_name, m_num in MONTHS_MAP.items():
            if re.search(rf"\b{m_name}\b", lower):
                month = m_num
                break

        # B. Numeric month
        if month is None:
            # Check DD/MM/YYYY or D/M/YYYY
            dmy_m = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](?:19|20)\d{2}\b", endpoint_str)
            if dmy_m:
                m_val = int(dmy_m.group(2))
                if 1 <= m_val <= 12:
                    month = m_val
            else:
                # Check MM/YYYY
                my_m = re.search(r"\b(\d{1,2})[/.-](?:19|20)\d{2}\b", endpoint_str)
                if my_m:
                    m_val = int(my_m.group(1))
                    if 1 <= m_val <= 12:
                        month = m_val

        # Default month if not found:
        if month is None:
            month = 1 if not is_end else 12

        return year, month

    def calculate_duration_years(self, dates_str: str) -> Optional[float]:
        """
        Calculates duration in fractional years from a dates string.
        - First attempts to parse explicit date range from dates_str.
        - Supports separators: '-', '–', '—', '−', ' to ', ' till ', ' until '.
        - Supports 'since <date>', '<date> onward', '<date> to Present'.
        - Uses runtime datetime.now() for 'Present' / 'Current'.
        - Rejects standalone single years (e.g. '2019') without end date -> returns None.
        - Rejects standalone approximate durations (e.g. '14+ years') -> returns None.
        - Returns None if dates cannot be reliably parsed.
        """
        if not dates_str or not dates_str.strip():
            return None

        s = dates_str.strip()

        # If string contains approximate duration like "14+ years", "4 years", "10.8 YEAR"
        # without an explicit range (no separator / no start and end year), return None
        if re.search(r"\b\d+(?:\.\d+)?\+?\s*(?:years?|yrs?|months?|mo)\b", s, re.IGNORECASE):
            if not re.search(r"\b(?:19|20)\d{2}\b", s) and not re.search(r"\bpresent\b", s, re.IGNORECASE):
                return None

        clean_str = s.replace("–", "-").replace("—", "-").replace("−", "-")

        # Case 1: "since <date>"
        m_since = re.search(r"^\s*since\s+(.+)$", clean_str, re.IGNORECASE)
        if m_since:
            start_date = self._parse_endpoint(m_since.group(1), is_end=False)
            end_date = self._parse_endpoint("present", is_end=True)
        # Case 2: "<date> onward(s)"
        elif re.search(r"\b(?:onward|onwards)\b", clean_str, re.IGNORECASE):
            cleaned_start = re.sub(r"\s+(?:onward|onwards)\b", "", clean_str, flags=re.IGNORECASE)
            start_date = self._parse_endpoint(cleaned_start, is_end=False)
            end_date = self._parse_endpoint("present", is_end=True)
        else:
            # Case 3: Range with separator: '-', ' to ', ' till ', ' until '
            sep_m = re.search(r"(?:\s*[-–—−]\s*(?:till\s+)?|\s+to\s+|\s+till\s+|\s+until\s+)", clean_str, re.IGNORECASE)
            if not sep_m:
                return None
            start_str = clean_str[:sep_m.start()].strip()
            end_str = clean_str[sep_m.end():].strip()

            # Clean leading "from"
            start_str = re.sub(r"^\s*from\s+", "", start_str, flags=re.IGNORECASE).strip()

            start_date = self._parse_endpoint(start_str, is_end=False)
            end_date = self._parse_endpoint(end_str, is_end=True)

        if start_date is None or end_date is None:
            return None

        y1, m1 = start_date
        y2, m2 = end_date

        total_months = (y2 - y1) * 12 + (m2 - m1)
        if total_months < 0:
            return None

        return round(total_months / 12.0, 1)

    def extract_date_range_from_text(self, raw_text: str) -> Optional[str]:
        """
        Extracts an explicit date range from raw_text as a fallback when dates
        field is incomplete, missing, or only a single year.
        """
        if not raw_text or not raw_text.strip():
            return None

        clean = raw_text.replace("–", "-").replace("—", "-").replace("−", "-")

        # 1. Range match: start - end
        m = RANGE_REGEX.search(clean)
        if m:
            s = m.group(1).strip()
            e = m.group(2).strip()
            s = re.sub(r"^\s*from\s+", "", s, flags=re.IGNORECASE).strip()
            return f"{s} - {e}"

        # 2. Since match: since start
        m_since = SINCE_REGEX.search(clean)
        if m_since:
            s = m_since.group(1).strip()
            s = re.sub(r"^\s*from\s+", "", s, flags=re.IGNORECASE).strip()
            return f"{s} - Present"

        # 3. Onward match: start onward(s)
        m_onward = ONWARD_REGEX.search(clean)
        if m_onward:
            s = m_onward.group(1).strip()
            s = re.sub(r"^\s*from\s+", "", s, flags=re.IGNORECASE).strip()
            return f"{s} - Present"

        return None

    def normalize(self, raw_experience_entries: List[Dict[str, Any]]) -> List[ExperienceEntry]:
        normalized_entries: List[ExperienceEntry] = []

        for raw_entry in raw_experience_entries:
            if not isinstance(raw_entry, dict):
                continue

            job_title = str(raw_entry.get("job_title", "") or "").strip()
            institution = str(raw_entry.get("institution", "") or "").strip()
            dates = str(raw_entry.get("dates", "") or "").strip()
            raw_text = str(raw_entry.get("raw_text", "") or "").strip()

            exp_type = self.classify_experience_type(job_title, institution)

            # 1. Try to calculate duration from the structured dates field
            duration = self.calculate_duration_years(dates)
            norm_dates = dates

            # 2. Fallback to raw_text if dates is missing, only a single year, or unparseable
            if duration is None and raw_text:
                extracted_range = self.extract_date_range_from_text(raw_text)
                if extracted_range:
                    fallback_duration = self.calculate_duration_years(extracted_range)
                    if fallback_duration is not None:
                        duration = fallback_duration
                        norm_dates = extracted_range

            normalized_entries.append(
                ExperienceEntry(
                    job_title=job_title,
                    institution=institution,
                    dates=norm_dates,
                    experience_type=exp_type,
                    duration_years=duration,
                )
            )

        return normalized_entries
