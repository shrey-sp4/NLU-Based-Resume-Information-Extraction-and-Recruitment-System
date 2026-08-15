import json
import re
from pathlib import Path

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


# ---------- 1. PHONE FIX ----------
PHONE_CANDIDATE_REGEX = re.compile(
    r"(?:\(?\+?91\)?|0091|0)?[\s\-\(\)]*(?:[6-9][\s\-\(\)\.]*){1}(?:\d[\s\-\(\)\.]*){9,11}"
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
    """Evaluator-side fix: normalize GT's raw labeled string the same way before comparing."""
    pred_digits = re.sub(r"\D", "", pred or "")
    gt_digits_all = extract_all_phones(gt_raw or "")
    return pred_digits in gt_digits_all if pred_digits and gt_digits_all else (pred == gt_raw)

def normalize_phone_for_compare(p):
    """Use this on BOTH prediction and ground truth before comparing in the evaluator."""
    digits = re.sub(r"\D", "", p or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits


# ---------- 2. REDESIGNED PERSONAL DETAILS EXTRACTION ----------
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
    
    text_blocks = [b for b in [preamble, details, summary, other] if b]
    text = "\n".join(text_blocks).strip()
    full_doc_text = "\n".join(str(v) for v in sections.values() if isinstance(v, str))

    search_text = text if (text and len(text) > 20) else full_doc_text

    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", search_text)
    email = emails[0].strip() if emails else ""

    phones = extract_all_phones(search_text)
    phone = phones[0] if phones else ""

    raw_lines = [l.strip() for l in search_text.splitlines() if len(l.strip()) > 1]
    name = ""

    # 1. First check if top 2 lines are single-word parts of a name (e.g. "Doyel" \n "Mukherjee")
    if len(raw_lines) >= 2:
        l1, l2 = raw_lines[0], raw_lines[1]
        if (len(l1.split()) == 1 and len(l2.split()) == 1 and 
            re.match(r"^[A-Z][a-z]+$", l1) and re.match(r"^[A-Z][a-z]+$", l2)):
            name = f"{l1} {l2}"

    # 2. Check candidate lines from top of document
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
    items = re.split(r'\n\s*(?:[-•*➢|o\+]|\d+[\.\)])\s*|\n{2,}', text)
    return [re.sub(r'\s+', ' ', item).strip() for item in items if len(item.strip()) > 5]


# ---------- 3. ENTRY-LEVEL SPLITTING & SUB-FIELD EXTRACTION ----------
DATE_LINE_START_REGEX = re.compile(
    r"^\s*(?:"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|July|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}"
    r"|\b(?:19|20)\d{2}\s*[-–—]"
    r"|[-•*➢|o\+]|\d+[\.\)]"
    r")",
    re.IGNORECASE
)

DEGREE_LINE_START_REGEX = re.compile(
    r"^\s*(?:"
    r"Doctor of Philosophy|Ph\.?D\.?|Master of Science|M\.?Sc\.?|Master of Technology|M\.?Tech\.?|"
    r"Master of Engineering|M\.E\.|B\.?Tech\.?|B\.?Sc\.?|Higher Secondary|12th|10th"
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
    r"\bDoctor of Philosophy(?:\s*\(PhD\))?\b", r"\bPh\.?D\.?\b",
    r"\bMaster of Science(?:\s*\(M\.?\s?Sc\.?\))?\b", r"\bM\.?\s?Sc\.?\b",
    r"\bMaster of Technology(?:\s*\(M\.?\s?Tech\.?\))?\b", r"\bM\.?\s?Tech\.?\b",
    r"\bMaster of Engineering(?:\s*\(M\.?\s?E\.?\))?\b", r"\bM\.E\.\b", r"\bM\.E\b", r"\bM\.Eng\.?\b",
    r"\bMaster of Philosophy(?:\s*\(M\.?\s?Phil\.?\))?\b", r"\bM\.?\s?Phil\.?\b",
    r"\bMaster of Computer (?:Science|Application)s?\b", r"\bMCA\b", r"\bMSW\b",
    r"\bBachelor of Science(?:\s*\(B\.?\s?Sc\.?\))?\b", r"\bB\.?\s?Sc\.?\b",
    r"\bBachelor of Technology(?:\s*\(B\.?\s?Tech\.?\))?\b", r"\bB\.?\s?Tech\.?\b",
    r"\bBachelor of (?:Computer Application|Engineering)s?\b", r"\bBCA\b", r"\bB\.E\.\b", r"\bB\.E\b", r"\bB\.Eng\.?\b",
    r"\bHigher Secondary(?:\s*\(10\+2\))?\b", r"\b12th(?:\s*\(10\+2\))?\b",
    r"\bMetric(?:\s*\(10th\))?\b", r"\b10th\b",
]
DEGREE_REGEX = re.compile("|".join(f"(?:{p})" for p in DEGREE_PATTERNS), re.IGNORECASE)

YEAR_RANGE_REGEX = re.compile(r"\b(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}\b|\b(19|20)\d{2}\b")

CGPA_REGEX = re.compile(
    r"\b\d{1,2}\.\d{1,2}\s*/\s*10(?:\.0)?\b"       # 8.5/10
    r"|\b\d{1,2}(?:\.\d{1,2})?\s*%"                 # 84.30%
    r"|First Class(?:\s*\(\s*\d{1,2}(?:\.\d{1,2})?\s*%\s*\))?"
    r"|Second Class(?:\s*\(\s*\d{1,2}(?:\.\d{1,2})?\s*%\s*\))?"
    r"|Distinction",
    re.IGNORECASE
)

INSTITUTION_KEYWORDS = r"(?:University|Institute|College|School|IIT|NIT|IIIT|IIM|Vishwavidhyalay|Vidyalaya|Academy|Centre|Center)"
INSTITUTION_REGEX = re.compile(
    r"((?:[A-Z][\w&\.\-]*\s+){0,6}" + INSTITUTION_KEYWORDS + r"(?:\s+(?:of|for|and|&)\s+[A-Z][\w&\.\-]*(?:\s+[A-Z][\w&\.\-]*){0,5})*)",
)

HEADER_NOISE = {"degree university", "board/university", "school examination",
                "degree", "university", "board", "passed all india secondary school",
                "passed all india senior secondary school"}

PREFIX_NOISE = re.compile(
    r"^(?:working as|appeared from|passed(?: with)?|from|at|in year|since|present|"
    r"doctor of philosophy|master of \w+|bachelor of \w+|ph\.?d\.?|m\.?tech\.?|"
    r"b\.?tech\.?|m\.?sc\.?|b\.?sc\.?)\s*",
    re.IGNORECASE
)

def clean_institution_span(raw_match):
    text = raw_match.strip(" ,.-–")
    if text.lower() in HEADER_NOISE:
        return None
    if len(text) < 4:
        return None
    return text

def extract_institution(line):
    matches = INSTITUTION_REGEX.findall(line)
    for m in matches:
        cleaned = clean_institution_span(m)
        if cleaned:
            return cleaned
    return ""

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


# ---------- 4. ENTRY-LEVEL EXPERIENCE SUB-FIELD EXTRACTION ----------
TITLE_PATTERNS = [
    r"Assistant Professor", r"Associate Professor", r"Professor",
    r"Visiting Assistant Professor", r"Post-?doctoral Fellow",
    r"Senior Research Scholar", r"Research Associate", r"Research Scholar",
    r"Project Associate", r"Visiting Researcher", r"Senior Survey Scientist",
    r"Teaching Assistant", r"Research Assistant", r"Senior \w+",
]
TITLE_REGEX = re.compile("|".join(f"(?:{p})" for p in TITLE_PATTERNS), re.IGNORECASE)

DATE_RANGE_REGEX = re.compile(
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}\s*[-–—]\s*"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}|"
    r"Present|Current|till date)"
    r"|" + YEAR_RANGE_REGEX.pattern,
    re.IGNORECASE
)

def extract_experience_entries(section_text, split_fn=None):
    entries = []
    blocks = split_section_into_entries(section_text, is_education=False)
    for entry_text in blocks:
        title_m = TITLE_REGEX.search(entry_text)
        date_m = DATE_RANGE_REGEX.search(entry_text)
        institution = extract_institution(entry_text)
        entries.append({
            "job_title": title_m.group(0).strip() if title_m else "",
            "dates": date_m.group(0).strip() if date_m else "",
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
]

def classify_publication(entry_text):
    lower = entry_text.lower()
    for bucket, patterns in PUBLICATION_TYPE_RULES:
        if any(re.search(pat, lower) for pat in patterns):
            return bucket
    return "journal_articles"

def split_publications_by_type(text):
    buckets = {
        "journal_articles": [], "conference_papers": [], "conference_proceedings": [],
        "communications": [], "book_chapters": [], "books": [],
        "technical_reports": [], "preprints": [],
    }
    for entry in split_into_list(text):
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