import json
import re
from pathlib import Path
import spacy

# Load spaCy model for statistical NER fallback
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None

# Paths
SECTIONS_DIR = Path("output/sections")
PREDICTIONS_DIR = Path("output/predictions")

def get_empty_gt_schema():
    return {
        "personal_details": {"name": "", "email": "", "phone": "", "phones": [], "address": ""},
        "summary": [""],
        "education": [],
        "experience": [],
        "research_interests": [],
        "skills": [],
        "projects": [],
        "publications": {
            "journal_articles": [],
            "conference_papers": [],
            "conference_proceedings": [],
            "communications": [],
            "book_chapters": [],
            "books": [],
            "technical_reports": [],
            "preprints": []
        },
        "certifications": [],
        "awards": [],
        "achievements": [],
        "memberships": [],
        "societies": [],
        "responsibilities": [],
        "references": []
    }

def get_section_text(sections, section_name):
    if section_name not in sections:
        return ""
    section = sections[section_name]
    if isinstance(section, dict):
        return section.get("content", "").strip()
    return section.strip()


# ---------- 1. PHONE EXTRACTION ----------
PHONE_CANDIDATE_REGEX = re.compile(
    r"(?:\(?\+?91\)?|0091|0)?[ \t\-\(\)]*(?:[6-9][ \t\-\(\)\.]*){1}(?:\d[ \t\-\(\)\.]*){9,11}"
)

def extract_all_phones(text):
    """Returns ALL phone numbers found (list), normalized to bare 10-digit strings."""
    results = []
    for m in PHONE_CANDIDATE_REGEX.finditer(text or ""):
        digits = re.sub(r"\D", "", m.group(0))
        if digits.startswith("0091"):
            digits = digits[4:]
        elif digits.startswith("91") and len(digits) >= 12:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]
        if len(digits) == 10 and digits[0] in "6789" and digits not in results:
            results.append(digits)
    return results

def extract_phone(text):
    phones = extract_all_phones(text)
    return phones[0] if phones else ""

def phone_matches(pred, gt_raw):
    pred_digits = re.sub(r"\D", "", pred or "")
    gt_digits_all = extract_all_phones(gt_raw or "")
    return pred_digits in gt_digits_all if pred_digits and gt_digits_all else (pred == gt_raw)

def normalize_phone_for_compare(p):
    digits = re.sub(r"\D", "", p or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits


# ---------- 2. PERSONAL DETAILS EXTRACTION ----------
JOB_TITLE_WORDS = re.compile(
    r"\b(?:Professor|Scientist|Scholar|Engineer|Manager|Director|Postdoctoral|Lecturer|Researcher|Fellow|Experienced|Graduate|Student|Assistant|Associate|Executive|Consultant|Developer|Analyst|Lead|Head|Officer|Member)\b",
    re.IGNORECASE
)

ADDRESS_WORDS = re.compile(
    r"\b(?:Road|Street|Avenue|Boulevard|Lane|Drive|Kolkata|Hyderabad|Delhi|Mumbai|Chennai|Bangalore|Gujarat|India|Campus|Building|Floor|Suite|Block|Sector|Apartment|Society|Pincode|School)\b",
    re.IGNORECASE
)

PREAMBLE_HEADER_NOISE = re.compile(
    r"\b(?:curricu?lam|curriculum|vitae|resume|biodata|profile|page\s+\d+|page|recognized|top\s+\d+%|stanford|elsevier|webpage|google scholar|looking for|achievements|opportunities|qualified|gold medalist)\b",
    re.IGNORECASE
)

def extract_personal_details(sections):
    preamble = get_section_text(sections, "preamble")
    details = get_section_text(sections, "personal_details")
    summary = get_section_text(sections, "summary")
    other = get_section_text(sections, "other_sections")
    
    primary_text = "\n".join([b for b in [preamble, details, summary] if b]).strip()
    full_doc_text = "\n".join(str(v) for v in sections.values() if isinstance(v, str))

    search_text = primary_text if (primary_text and len(primary_text) > 10) else (other or full_doc_text)

    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", search_text)
    if not emails:
        emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", full_doc_text)
    email = emails[0].strip() if emails else ""

    phones = extract_all_phones(search_text)
    if not phones:
        phones = extract_all_phones(full_doc_text)
    phone = phones[0] if phones else ""

    raw_lines = [l.strip() for l in search_text.splitlines() if len(l.strip()) > 1]
    name = ""

    if len(raw_lines) >= 2:
        l1, l2 = raw_lines[0], raw_lines[1]
        if (len(l1.split()) == 1 and len(l2.split()) == 1 and 
            re.match(r"^[A-Z][a-z]+$", l1) and re.match(r"^[A-Z][a-z]+$", l2)):
            name = f"{l1} {l2}"

    if not name:
        for raw_l in raw_lines[:12]:
            if "@" in raw_l or "http" in raw_l or "www." in raw_l:
                continue
            if PREAMBLE_HEADER_NOISE.search(raw_l):
                continue
            
            sub_lines = re.split(r"\s{3,}", raw_l)
            for line in sub_lines:
                line = line.strip()
                if not line or "@" in line or "http" in line:
                    continue
                if PREAMBLE_HEADER_NOISE.search(line):
                    continue
                if JOB_TITLE_WORDS.search(line):
                    continue
                if ADDRESS_WORDS.search(line):
                    continue

                clean_line = re.sub(r"^(?:name|full name|candidate name)\s*[:\-]\s*", "", line, flags=re.IGNORECASE).strip()
                clean_line = clean_line.strip(":-–—|•●■□*➢+ ")
                clean_line = re.split(r"\b(?:Address|Email|E-mail|Phone|Mobile|Contact|Location|Webpage|CV page|Page)\b", clean_line, flags=re.IGNORECASE)[0].strip()
                clean_line = re.split(r"\d", clean_line)[0].strip()
                clean_line = re.sub(r"[^\w\s\.\-']", "", clean_line).strip()

                words = clean_line.split()
                if 2 <= len(words) <= 5 and re.match(r"^[A-Za-z\.\s\-']+$", clean_line):
                    name = clean_line
                    break
            if name:
                break

    return {"name": name, "email": email, "phone": phone, "phones": phones, "address": ""}

def split_into_list(text):
    if not text: return []
    items = re.split(r'\n\s*(?:[-•*➢|\+]|o(?=[ \t])|\d{1,3}[\.\)](?!\d))\s*|\n{2,}', text)
    return [re.sub(r'\s+', ' ', item).strip() for item in items if len(item.strip()) > 5]


# ---------- 3. HYBRID INSTITUTION EXTRACTION & SUB-FIELD PATTERNS ----------
DATE_LINE_START_REGEX = re.compile(
    r"^\s*(?:"
    r"[^\w\s]{0,2}\s*(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*,?\s*(?:(?:19|20)\d{2}|[’']\s?\d{2})"
    r"|[^\w\s]{0,2}\s*\b(?:19|20)\d{2}\s*[-–—]"
    r"|[-•*➢|\+]|o(?=\s)|\d+[\.\)](?!\d)"
    r")",
    re.IGNORECASE
)

DEGREE_LINE_START_REGEX = re.compile(
    r"^\s*(?:"
    r"[-•*➢|o\+]|\d+[\.\)]\s*)?"  # optional bullet/number
    r"(?:"
    r"Doctor of Philosophy|Ph\.?D\.?|PhD|"
    r"Master of Science|M\.?Sc\.?|MSc|"
    r"Master of Technology|M\.?Tech\.?|MTech|"
    r"Master of Engineering|M\.E\.|"
    r"Master of Computer|MCA|MSW|Master of Social Work|"
    r"Master of Philosophy|M\.?Phil\.?|"
    r"Bachelor of Science|B\.?Sc\.?|BSc|"
    r"Bachelor of Technology|B\.?Tech\.?|BTech|"
    r"Bachelor of Engineering|B\.E\.|"
    r"Bachelor of Computer|BCA|Bachelor of computer application|"
    r"Higher Secondary|12th|10th|"
    r"Senior Secondary|"
    r"Secondary(?:\s*School)?\s*Examination|"
    r"HSC|SSC|Madhyamik|"
    r"Metric\s*\(10th\)|"
    r"10\s*\+\s*2(?:th)?|"
    r"Postdoc\.?(?:toral)?|Post\s*Doctoral|"
    r"H\.?S\.?\s*\(?12th\)?|"
    r"Ph\.?D\.?\s*\([^)]*\)|"
    r"M\.?Sc\.?\s*\([^)]*\)|"
    r"B\.?Sc\.?\s*\([^)]*\)|"
    r"B\.?Tech\.?\s*\([^)]*\)|"
    r"M\.?Tech\.?\s*\([^)]*\)|"
    r"BA\s*\(H\)|"
    r"Master\s+(?:of|in)\s+Arts|"
    r"Bachelor\s+of\s+Science\s*\(Honou?rs?\)"
    r")",
    re.IGNORECASE
)

def split_section_into_entries(text: str, is_education: bool = False) -> list[str]:
    if not text:
        return []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    entries = []
    current_entry = []

    for line in lines:
        if re.match(r"^(?:page\s+\d+|\d+)$", line, re.IGNORECASE):
            continue

        is_new_entry_start = bool(DATE_LINE_START_REGEX.search(line))
        # Don't split on standalone years in parentheses: (2023) or 2023)
        if is_new_entry_start and re.match(r"^\s*\(?(?:19|20)\d{2}\)?\s*$", line.strip()):
            is_new_entry_start = False
        
        if is_education and DEGREE_LINE_START_REGEX.search(line):
            is_new_entry_start = True

        if current_entry and is_new_entry_start:
            entries.append(" ".join(current_entry))
            current_entry = [line]
        else:
            current_entry.append(line)

    if current_entry:
        entries.append(" ".join(current_entry))

    if len(entries) <= 1:
        items = re.split(r'\n\s*(?:[-•*➢|o\+]|\d+[\.\)])\s*|\n{2,}', text)
        entries = [re.sub(r'\s+', ' ', item).strip() for item in items if len(item.strip()) > 5]

    return [e for e in entries if len(e) > 5]


DEGREE_PATTERNS = [
    # PhD variants
    r"\bDoctor of Philosophy(?:\s*\(PhD\))?\b",
    r"\bPh\.?D\.?\b",
    r"\bPhD\b",
    
    # Master variants - with parentheses like (M. Sc.)
    r"\bMaster of Science(?:\s*\(M\.?\s?Sc\.?\))?\b",
    r"\bMaster of Science\b",
    r"\bM\.?\s?Sc\.?\b",
    r"\bMSc\b",
    
    r"\bMaster of Technology(?:\s*\(M\.?\s?Tech\.?\))?\b",
    r"\bMaster of Technology\b",
    r"\bM\.?\s?Tech\.?\b",
    r"\bMTech\b",
    
    r"\bMaster of Engineering(?:\s*\(M\.?\s?E\.?\))?\b",
    r"\bMaster of Engineering\b",
    r"\bM\.E\.\b", r"\bM\.E\b", r"\bM\.Eng\.?\b",
    
    r"\bMaster of Computer (?:Science|Application)s?\b",
    r"\bMCA\b",
    r"\bMSW\b",
    r"\bMaster of Social Work\b",
    
    r"\bMaster of Philosophy(?:\s*\(M\.?\s?Phil\.?\))?\b",
    r"\bM\.?\s?Phil\.?\b",
    
    # Bachelor variants - with parentheses like (B. Sc.)
    r"\bBachelor of Science(?:\s*\(B\.?\s?Sc\.?\))?\b",
    r"\bBachelor of Science\b",
    r"\bB\.?\s?Sc\.?\b",
    r"\bBSc\b",
    
    r"\bBachelor of Technology(?:\s*\(B\.?\s?Tech\.?\))?\b",
    r"\bBachelor of Technology\b",
    r"\bB\.?\s?Tech\.?\b",
    r"\bBTech\b",
    
    r"\bBachelor of (?:Computer Application|Engineering)s?\b",
    r"\bBCA\b",
    r"\bB\.E\.\b", r"\bB\.E\b", r"\bB\.Eng\.?\b",
    r"\bBachelor of computer application\b",
    
    # School/Secondary variants
    r"\bHigher Secondary(?:\s*\(10\+2\))?\b",
    r"\b12th(?:\s*\(10\+2\))?\b",
    r"\bMetric(?:\s*\(10th\))?\b",
    r"\b10th\b",
    r"\bSenior Secondary\b",
    r"\bSecondary(?:\s*School)?\s*Examination\b",
    r"\bSecondary\s*\(10\)\b",
    r"\bMadhyamik(?:\s*Examination)?\b",
    r"\b10\s?\+\s?2(?:th)?\b",
    r"\bHSC\b",
    r"\bSSC\b",
    r"\bH\.?S\.?\s*\(?12th\)?\b",
    
    # Arts degrees
    r"\bMaster (?:of|in) Arts(?:\s*\([^)]{1,30}\))?",
    r"\bM\.\s?A\.(?!\w)",
    r"\bBachelor (?:of|in) Arts(?:\s*\([^)]{1,30}\))?",
    r"\bB\.\s?A\.(?!\w)",
    r"(?-i:\bBA)\s*\((?:H|Hons?\.?)\)",
    r"\bBA\s*\(H\)\b",
    
    # Postdoc variants
    r"\bPostdoc\.?(?:toral)?\b",
    r"\bPost\s*Doctoral\s+Research\s+Associate\b",
    r"\bPost\s*Doctoral\s+Fellow\b",
]
DEGREE_REGEX = re.compile("|".join(f"(?:{p})" for p in DEGREE_PATTERNS), re.IGNORECASE)

YEAR_RANGE_REGEX = re.compile(r"\b(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}\b|\b(19|20)\d{2}\b")

CGPA_REGEX = re.compile(
    r"\b\d{1,2}\.\d{1,2}\s*/\s*10(?:\.0)?\b"
    r"|\b\d{1,2}(?:\.\d{1,2})?\s*%"
    r"|First Class(?:\s*\(\s*\d{1,2}(?:\.\d{1,2})?\s*%\s*\))?"
    r"|Second Class(?:\s*\(\s*\d{1,2}(?:\.\d{1,2})?\s*%\s*\))?"
    r"|Distinction",
    re.IGNORECASE
)

INSTITUTION_KEYWORDS = r"(?:University|Institute|College|School|IIT|NIT|IIIT|IIM|Vishwavidhyalay|Vidyalaya|Academy|Centre|Center)"
INSTITUTION_REGEX = re.compile(
    r"((?:[A-Z][\w&\.\-]*\s+){0,6}" + INSTITUTION_KEYWORDS + r"(?:\s+(?:of|for|and|&)\s+[A-Z][\w&\.\-]*(?:\s+[A-Z][\w&\.\-]*){0,5})*)",
)

HEADER_NOISE = {
    "degree university", "board/university", "school examination",
    "degree", "university", "board", "passed all india secondary school",
    "passed all india senior secondary school", "completed 10th education"
}

HEADER_NOISE_WORDS = re.compile(
    r"\b(?:Telephone|Mobile|Office|Email|Contact|Address|Fax|Page|CV|Resume|Curriculum|Vitae|Publication|Journal|Conference|Section|Faculty Development)\b",
    re.IGNORECASE
)

PREPOSITION_ORG_REGEX = re.compile(
    r"\b(?:at\s+|from\s+|in\s+|joined\s+)([A-Z][a-zA-Z0-9&\.\-\s]{3,60}|[A-Z]{2,10}(?:\s+[A-Z]{2,10})+)(?:\([A-Za-z0-9\.\-\s]+\))?(?:\s*,\s*[A-Z][a-zA-Z0-9&\.\-\s]{3,40})*",
)

PREFIX_NOISE = re.compile(
    r"^(?:working as|appeared from|passed(?: with)?|from|at|in year|since|present)\s*",
    re.IGNORECASE
)

# Field-of-study words that sometimes get captured in front of an institution name,
# e.g. "Physics Saurashtra University". Extend this list if new junk words appear.
FIELD_WORDS = {
    "physics", "chemistry", "mathematics", "maths", "philosophy", "economics",
    "engineering", "computing", "analytics", "control", "biology", "biotechnology",
    "mechanics", "statistics", "dft", "informatics",
}

def strip_leading_field_words(text: str) -> str:
    tokens = text.split()
    # drop field words from the front, but always keep at least 2 words
    while len(tokens) > 2 and tokens[0].strip(",.-").lower() in FIELD_WORDS:
        tokens.pop(0)
    return " ".join(tokens)

def clean_institution_span(raw_match: str) -> str | None:
    text = raw_match.strip(" ,.-–")
    if text.lower() in HEADER_NOISE:
        return None
    if len(text) < 3:
        return None
    return strip_leading_field_words(text)

def extract_institution(line: str) -> str:
    """
    Hybrid Institution Extractor:
    1. Primary Method: Fast Keyword Regex (University, Institute, College, School, IIT, NIT, IIIT, IIM, etc.)
    2. Secondary Fallback: Lightweight Statistical NER (spaCy en_core_web_sm ORG entities + preposition context)
    3. Tertiary Fallback: Comma-separated patterns (e.g., "IIT Bombay, Mumbai, India")
    """
    # 1. Primary Method: Keyword Regex Match
    matches = INSTITUTION_REGEX.findall(line)
    for m in matches:
        cleaned = clean_institution_span(m)
        if cleaned:
            return cleaned

    # 2. Secondary Fallback: spaCy Statistical NER + Preposition Context
    org_candidates = []
    if nlp is not None:
        doc = nlp(line)
        for ent in doc.ents:
            if ent.label_ in ("ORG", "FAC"):
                cleaned = clean_institution_span(ent.text)
                if cleaned:
                    org_candidates.append(cleaned)

    prep_m = PREPOSITION_ORG_REGEX.search(line)
    if prep_m:
        prep_span = clean_institution_span(prep_m.group(1))
        if prep_span and len(prep_span) >= 4:
            org_candidates.append(prep_span)

    # 3. Tertiary Fallback: Comma-separated institution patterns (e.g., "IIT Bombay, Mumbai, India")
        # 3. Tertiary Fallback: Comma-separated institution patterns
    if not org_candidates:
        comma_parts = [p.strip() for p in line.split(',') if p.strip()]
        if len(comma_parts) >= 2:
            # Try first part: "IIT Bombay" from "IIT Bombay, Mumbai, India"
            first_part = comma_parts[0]
            if re.search(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,}", first_part):
                cleaned = clean_institution_span(first_part)
                if cleaned and len(cleaned) > 3:
                    org_candidates.append(cleaned)
            
            # Try first TWO parts: "HRI, QIC Group" from "HRI, QIC Group, Prayagraj, India"
            if len(comma_parts) >= 3:
                two_parts = comma_parts[0] + ", " + comma_parts[1]
                if re.search(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,}", two_parts):
                    cleaned = clean_institution_span(two_parts)
                    if cleaned and len(cleaned) > 3:
                        org_candidates.append(cleaned)
            
            # Handle abbreviated boards: "W.B.C.H.S.E., West Bengal, India"
            for i, part in enumerate(comma_parts):
                if re.match(r"^[A-Z]\.(?:[A-Z]\.){2,}", part):  # W.B.C.H.S.E.
                    if i + 1 < len(comma_parts):
                        combined = part + ", " + comma_parts[i + 1]
                        cleaned = clean_institution_span(combined)
                        if cleaned and len(cleaned) > 5:
                            org_candidates.append(cleaned)
                    break
            
            # Handle "Department of X, University" pattern
            for i, part in enumerate(comma_parts):
                if part.lower().startswith("department of") and i + 1 < len(comma_parts):
                    combined = part + ", " + comma_parts[i + 1]
                    cleaned = clean_institution_span(combined)
                    if cleaned and len(cleaned) > 5:
                        org_candidates.append(cleaned)
                    break

    if org_candidates:
        return max(org_candidates, key=len)

    return ""

_MONTH_POINT = re.compile(
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*,?\s*(?:(?:19|20)\d{2}|[’']\s?\d{2})", re.IGNORECASE)
_YEAR_RANGE = re.compile(r"\b(?:19|20)\d{2}\s*[-–—]\s*(?:(?:19|20)\d{2}|Present|Current)", re.IGNORECASE)
_BULLET_LINE = re.compile(r"^\s*(?:[-•*➢|\+◦▪●■➤\uf0b7\uf0d8\uf0a7\u207b]|o(?=\s)|\d{1,3}[\.\)](?!\d))")
_DATE_ONLY_LINE = re.compile(
    r"^[\s\(\[\-–—]*(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?(?:[A-Za-z]{3,9}\.?,?\s*)?(?:(?:19|20)\d{2}|[’']\s?\d{2})"
    r"(?:\s*(?:[-–—]|to)\s*(?:[^\n]{0,30}))?[\s\)\]]*$", re.IGNORECASE)
_OPEN_RANGE_AT_END = re.compile(
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*,?\s*(?:(?:19|20)\d{2}|[’']\s?\d{2})|\b(?:19|20)\d{2})"
    r"\s*[-–—]\s*(?P<tail>[^\d]{0,100})$", re.IGNORECASE)
_DANGLING_END = re.compile(r"(?:[-–—,]|\bto|\bfrom|\d(?:st|nd|rd|th)|\bof)\s*$", re.IGNORECASE)
_ORG_WORD = re.compile(r"\b(?:University|Institute|College|School|Hospital|Centre|Center|Laborator(?:y|ies)|Pvt|Ltd|Inc|Company|Academy)\b", re.IGNORECASE)

def _has_date(text):
    return bool(_MONTH_POINT.search(text) or _YEAR_RANGE.search(text) or DATE_RANGE_REGEX.search(text))

def split_experience_entries(text):
    if not text:
        return []
    text = re.sub(r"(\w)-\n\s*([a-z])", r"\1\2", text)      # rejoin words broken at line end
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    entries, current = [], []
    for line in lines:
        if re.match(r"^(?:page\s+\d+|\d+)$", line, re.IGNORECASE):
            continue
        cur_text = " ".join(current)
        starts_with_date = bool(DATE_LINE_START_REGEX.search(line)) and not _BULLET_LINE.match(line)
        starts_with_date = starts_with_date or bool(re.match(r"^\s*[^\w\s]{0,2}\s*(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?(?:%s)" % _MONTH_POINT.pattern, line, re.IGNORECASE))
        if starts_with_date and re.match(r"^\s*\(?(?:19|20)\d{2}\)?\s*$", line):
            starts_with_date = False
        new_entry = False
        if current:
            if starts_with_date:
                new_entry = True
                open_range = _OPEN_RANGE_AT_END.search(cur_text)
                if open_range and not re.search(r"present|current|till|now|ongoing", open_range.group("tail"), re.IGNORECASE):
                    new_entry = False          # this line is the END date of the job above
                elif _DANGLING_END.search(current[-1]):
                    new_entry = False          # range wrapped over two lines
                elif _DATE_ONLY_LINE.match(line) and not _has_date(cur_text):
                    new_entry = False          # bare date line belongs to the heading above
            elif _BULLET_LINE.match(line):
                job_like = bool(TITLE_REGEX.search(line) or _MONTH_POINT.search(line) or _YEAR_RANGE.search(line))
                header_like = bool(_ORG_WORD.search(line)) and _has_date(cur_text) and len(line) < 140
                new_entry = job_like or header_like      # a plain description bullet is NOT a new job
            elif TITLE_REGEX.match(line) and _has_date(cur_text) and len(line) < 220:
                new_entry = True
        if new_entry:
            entries.append(" ".join(current)); current = [line]
        else:
            current.append(line)
    if current:
        entries.append(" ".join(current))
    return [e for e in entries if len(e) > 5]

_POINT_ANY = r"(?:(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*,?\s*(?:(?:19|20)\d{2}|[’']\s?\d{2}))"
SEPARATED_RANGE_REGEX = re.compile(
    r"(?P<start>" + _POINT_ANY + r")\s*[-–—]\s*(?P<gap>[^\d]{0,140}?)(?P<end>" + _POINT_ANY + r"|Present|Current|till\s*date|Now)", re.IGNORECASE)

def find_experience_dates(entry_text):
    m = DATE_RANGE_REGEX.search(entry_text)
    if m and re.search(r"[-–—]|\bto\b|present|current|till|since", m.group(0), re.IGNORECASE):
        return m.group(0).strip()
    sep = SEPARATED_RANGE_REGEX.search(entry_text)
    if sep:
        return f"{sep.group('start').strip()} - {sep.group('end').strip()}"
    yr = _YEAR_RANGE.search(entry_text)          # e.g. "2015 - Present"
    if yr:
        return yr.group(0).strip()
    return m.group(0).strip() if m else ""

def extract_education_entries(section_text, split_fn=None):
    entries = []
    blocks = split_section_into_entries(section_text, is_education=True)
    for entry_text in blocks:
        stripped = PREFIX_NOISE.sub("", entry_text).strip()
        degree_m = DEGREE_REGEX.search(entry_text)
        year_m = YEAR_RANGE_REGEX.search(entry_text)
        cgpa_m = CGPA_REGEX.search(entry_text)
        institution = extract_institution(entry_text)
        entries.append({
            "degree": degree_m.group(0).strip() if degree_m else "",
            "graduation_year": year_m.group(0).strip() if year_m else "",
            "cgpa": cgpa_m.group(0).strip() if cgpa_m else "",
            "institution": institution,
            "raw_text": entry_text,
        })
    return entries


# ---------- 4. EXPERIENCE SUB-FIELD EXTRACTION ----------
TITLE_PATTERNS = [
    r"Assistant Professor", r"Associate Professor", r"Professor",
    r"Visiting Assistant Professor", r"Post-?doctoral Fellow",
    r"Senior Research Scholar", r"Research Associate", r"Research Scholar",
    r"Project Associate", r"Visiting Researcher", r"Senior Survey Scientist",
    r"Teaching Assistant", r"Research Assistant",
    r"Junior Research Fellow", r"Senior Research Fellow", r"Research Fellow", r"Project Fellow",
    r"Project Assistant(?:\s+(?:I{1,3}|IV|\d))?", r"Project Scientist", r"Research Scientist",
    r"Guest Lecturer", r"Guest Faculty", r"Visiting Faculty", r"Guest Researcher",
    r"Lecturer", r"Principal Investigator", r"Scientist",
    r"Senior \w+",
    r"Senior\s+Research\s+Scholar",
    r"Junior\s+Research\s+Scholar",
    r"Visiting\s+Faculty",
    r"Guest\s+Faculty",
    r"Guest\s+Researcher",
    r"Labour\s+Welfare\s+Trainee",
    r"Research\s+Fellow",
    r"Project\s+Fellow",
    r"Senior\s+Research\s+Scholar",
    r"Junior\s+Research\s+Scholar",
    r"Visiting\s+Faculty",
    r"Guest\s+Faculty",
    r"Research\s+Scholar",  # generic fallback
]
TITLE_REGEX = re.compile("|".join(f"(?:{p})" for p in TITLE_PATTERNS), re.IGNORECASE)

# ===== COMPREHENSIVE DATE PATTERNS =====
# Handle both ASCII and Unicode dashes, quotes, apostrophes
_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
_DAY_ORDINAL = r"(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?"
_YEAR = r"(?:19|20)\d{2}"
_YEAR_SHORT = r"[\u2019']\d{2}"  # handles both ' and '
_DASH = r"(?:--|[\-\u2013\u2014])"  # hyphen, en-dash, em-dash

# Point: 17th August 2023, 8 May 2021, Sep'24, 4th December, 2017, 1st January, 2024
_POINT = _DAY_ORDINAL + _MONTH + r"\s*,?\s*(?:" + _YEAR + r"|" + _YEAR_SHORT + r")"
_END = r"(?:" + _POINT + r"|Present|Current|till\s*date|Now|ongoing)"

_DATE_PATTERNS = [
    # 1. Point - dash - End: 17th August 2023 - Present, 8 May 2021 - 4 Oct 2023
    _POINT + r"\s*" + _DASH + r"\s*" + _END,
    _POINT + r"\s*to\s*" + _END,
    
    # 2. Month Year - Month Year: June 2016 - January 2017, Jan 2020 - March 2024
    _MONTH + r"\s+" + _YEAR + r"\s*" + _DASH + r"\s*" + _MONTH + r"\s+" + _YEAR,
    
    # 3. Apostrophe years: Sep'24- Present, March'21- Dec'22, Sep'18- Feb'20
    _MONTH + _YEAR_SHORT + r"\s*" + _DASH + r"\s*(?:Present|Current|till\s*date|Now)",
    _MONTH + _YEAR_SHORT + r"\s*" + _DASH + r"\s*" + _MONTH + _YEAR_SHORT,
    
    # 4. Ordinal with commas: 4th December, 2017-10th July, 2018
    r"\d{1,2}(?:st|nd|rd|th)?\s+" + _MONTH + r",\s*" + _YEAR + r"\s*" + _DASH + r"\s*\d{1,2}(?:st|nd|rd|th)?\s+" + _MONTH + r",\s*" + _YEAR,
    
    # 5. Since/since: Since 1st January, 2024 / since 5th July 2022
    r"[Ss]ince\s+" + _DAY_ORDINAL + _MONTH + r",?\s*" + _YEAR,
    
    # 6. Single month year: April 2012
    _MONTH + r"\s+" + _YEAR,
    
    # 7. Non-standard: 4th Year of Ph.D.
    r"\d{1,2}(?:st|nd|rd|th)?\s+(?:Year\s+of\s+)?Ph\.?D\.?",
    
    # 8. Year range: 2018 - 2019
    _YEAR + r"\s*" + _DASH + r"\s*" + _YEAR,
]

DATE_RANGE_REGEX = re.compile("|".join(_DATE_PATTERNS), re.IGNORECASE)

def extract_experience_entries(section_text, split_fn=None):
    entries = []
    blocks = split_experience_entries(section_text)
    for entry_text in blocks:
        title_m = TITLE_REGEX.search(entry_text)
        institution = extract_institution(entry_text)
        entries.append({
            "job_title": title_m.group(0).strip() if title_m else "",
            "dates": find_experience_dates(entry_text),
            "institution": institution,
            "raw_text": entry_text,
        })
    return entries


PUBLICATION_TYPE_RULES = [
    ("preprints", [r"\barxiv\b", r"\bpreprint\b", r"\bbiorxiv\b", r"\bssrn\b"]),
    ("technical_reports", [r"\btech(?:nical)?\.?\s*report\b", r"\bwhite\s*paper\b", r"\btr[-\s]?\d{2,}\b"]),
    ("book_chapters", [r"\bbook\s*chapter\b", r"\bchapter\s+\d+\b", r"\(eds?\.\)", r"\bedited\s+by\b", r"\bin\s+[A-Z][\w&,\.\s]{3,60}\(eds?\.?\)"]),
    ("books", [r"\bisbn\b", r"\bmonograph\b"]),
    ("conference_proceedings", [r"\bproceedings\s+of\b", r"\bconf\.?\s*proc\b", r"\bproc\.\s"]),
    ("conference_papers", [r"\bconference\s+on\b", r"\bsymposium\b", r"\bworkshop\b", r"\bicc?\w{0,3}\s*\d{4}\b"]),
    ("communications", [r"\brapid\s+communications?\b", r"\bshort\s+communications?\b"]),
    # journal_articles is DEFAULT fallback - NO explicit rule
]

def classify_publication(entry_text):
    lower = entry_text.lower()
    for bucket, patterns in PUBLICATION_TYPE_RULES:
        if any(re.search(pat, lower) for pat in patterns):
            return bucket
    return "journal_articles"

_NUM_CAND = re.compile(r'(?:(?<=\s)|^)(\d{1,3})\s+(?=[A-Z])')
_AUTHOR_YEAR = re.compile(
    r"(?<=[\.\]\)])\s+(?=[A-Z][A-Za-z'’\-]+(?:\s+[A-Z]\.?){1,3}"
    r"(?:\s*(?:,|and|&)\s*[A-Z][A-Za-z'’\-]+(?:\s+[A-Z]\.?){1,3})*\s*\((?:19|20)\d{2}\))")

def _split_numbered_chain(text):
    """Split at 'n Capital...' only when the numbers run n, n+1, n+2... (a real list)."""
    cands = [(m.start(), m.end(), int(m.group(1))) for m in _NUM_CAND.finditer(text)]
    best = []
    for i in range(len(cands)):
        chain = [cands[i]]
        for c in cands[i + 1:]:
            if c[2] == chain[-1][2] + 1 and c[0] > chain[-1][1]:
                chain.append(c)
        if len(chain) > len(best):
            best = chain
    if len(best) < 3:
        return [text]
    parts, prev = [], 0
    for start, end, _ in best:
        if start > prev:
            parts.append(text[prev:start])
        prev = end
    parts.append(text[prev:])
    return parts

def split_publication_entries(text):
    entries = []
    for item in split_into_list(text):
        for part in _split_numbered_chain(item):
            for piece in _AUTHOR_YEAR.split(part):
                if len(piece.strip()) > 5:
                    entries.append(piece.strip())
    return entries

_START_AUTH = re.compile(
    r"\s+(?=(?:[A-Z][A-Za-z'’\-]+,\s*(?:[A-Z]\.\s*){1,3}"
    r"|(?:[A-Z]\.\s*){1,3}[A-Z][A-Za-z'’\-]{2,}))")
_REF_END = re.compile(r"(?:\b(?:19|20)\d{2}\b|\bpp?\.\s*\d|\d+\s*[-–]\s*\d+|\bdoi\b|\bvol\.?\s*\d)", re.IGNORECASE)

def split_glued_references(text, min_len=350, min_piece=60):
    if len(text) < min_len or len(set(re.findall(r"\b(?:19|20)\d{2}\b", text))) < 2:
        return [text]
    cuts, last = [], 0
    for m in _START_AUTH.finditer(text):
        pos = m.start()
        before = text[last:pos]
        if len(before) < min_piece or text[pos - 1] not in ".)]0123456789" or not _REF_END.search(before[-80:]):
            continue
        cuts.append(pos); last = pos
    parts, prev = [], 0
    for c in cuts + [len(text)]:
        piece = text[prev:c].strip()
        if piece: parts.append(piece)
        prev = c
    return parts or [text]

def split_publications_by_type(text):
    buckets = {
        "journal_articles": [], "conference_papers": [], "conference_proceedings": [],
        "communications": [], "book_chapters": [], "books": [],
        "technical_reports": [], "preprints": [],
    }
    for entry in [q for e in split_publication_entries(text) for q in split_glued_references(e)]:
        buckets[classify_publication(entry)].append(entry)
    return buckets

def process_resume(section_file):
    with open(section_file, "r", encoding="utf-8") as f: data = json.load(f)
    file_name = data.get("file_name", section_file.name)
    sections = data.get("sections", {})
    prediction = get_empty_gt_schema()
    
    prediction["personal_details"] = extract_personal_details(sections)
    summary_text = get_section_text(sections, "summary")
    prediction["summary"] = [summary_text] if summary_text else []
    
    prediction["education"] = extract_education_entries(get_section_text(sections, "education"))
    prediction["experience"] = extract_experience_entries(get_section_text(sections, "experience"))

    list_fields = [
        "research_interests", "skills", "projects", "certifications",
        "awards", "achievements", "memberships", "societies",
        "responsibilities", "references"
    ]
    for field in list_fields:
        content = get_section_text(sections, field)
        if not content and field in ("awards", "achievements"):
            content = get_section_text(sections, "achievements") or get_section_text(sections, "awards")
        elif not content and field in ("memberships", "societies"):
            content = get_section_text(sections, "memberships") or get_section_text(sections, "societies")

        prediction[field] = split_into_list(content)
        
    pub_text = get_section_text(sections, "publications")
    if pub_text:
        prediction["publications"] = split_publications_by_type(pub_text)

    norm_name = section_file.name.replace("_sections.json", ".json")
    output_file = PREDICTIONS_DIR / norm_name
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(prediction, f, indent=4, ensure_ascii=False)

def main():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    json_files = sorted(SECTIONS_DIR.glob("*.json"))
    print(f"Extracting structured data for {len(json_files)} resumes...")
    for file in json_files: process_resume(file)
    print(f"Predictions saved to {PREDICTIONS_DIR}")

if __name__ == "__main__":
    main()