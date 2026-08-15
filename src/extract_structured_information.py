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


# ---------- 1. PHONE FIX (phone_fix_v2.py) ----------
# Handles: +91, 0091, (M)/(+91) labels, space or dash separated groups, multiple numbers.
PHONE_CANDIDATE_REGEX = re.compile(
    r"(?:\+?91|0091|0)?[\s\-\(\)]*[6-9](?:[\s\-]?\d){9}"
)

def extract_all_phones(text):
    """Returns ALL phone numbers found (list), normalized to bare 10-digit strings."""
    results = []
    for m in PHONE_CANDIDATE_REGEX.finditer(text or ""):
        digits = re.sub(r"\D", "", m.group(0))
        # strip country/trunk prefixes to get to the 10-digit mobile number
        if digits.startswith("0091"):
            digits = digits[4:]
        elif digits.startswith("91") and len(digits) == 12:
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


def extract_personal_details(sections):
    preamble = get_section_text(sections, "preamble")
    details = get_section_text(sections, "personal_details")
    text = f"{preamble}\n{details}".strip()
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    email = email_match.group(0).strip() if email_match else ""
    phones = extract_all_phones(text)
    phone = phones[0] if phones else ""
    name = ""
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 3]
    for line in lines:
        if "@" in line or re.search(r"\d", line): continue
        if re.search(r"\b(curricu?lam|curriculum|vitae|resume|biodata|profile)\b", line, re.IGNORECASE): continue
        clean_line = re.sub(r"^(name|full name|candidate name)\s*[:\-]\s*", "", line, flags=re.IGNORECASE).strip()
        clean_line = clean_line.strip(":-–—|•●■□*➢ ")
        if len(clean_line.split()) >= 2:
            name = clean_line
            break
    return {"name": name, "email": email, "phone": phone, "phones": phones, "address": ""}

def split_into_list(text):
    if not text: return []
    items = re.split(r'\n\s*(?:[-•*➢|o\+]|\d+[\.\)])\s*|\n{2,}', text)
    return [re.sub(r'\s+', ' ', item).strip() for item in items if len(item.strip()) > 5]


# ---------- 2. ENTRY-LEVEL EDUCATION SUB-FIELD EXTRACTION ----------
DEGREE_PATTERNS = [
    r"Doctor of Philosophy(?:\s*\(PhD\))?", r"Ph\.?D\.?",
    r"Master of Science(?:\s*\(M\.?\s?Sc\.?\))?", r"M\.?Sc\.?",
    r"Master of Technology(?:\s*\(M\.?\s?Tech\.?\))?", r"M\.?Tech\.?",
    r"Master of Engineering(?:\s*\(M\.?\s?E\.?\))?", r"M\.?E\.?",
    r"Master of Computer (?:Science|Application)s?", r"MCA", r"MSW",
    r"Bachelor of Science(?:\s*\(B\.?\s?Sc\.?\))?", r"B\.?Sc\.?",
    r"Bachelor of Technology(?:\s*\(B\.?\s?Tech\.?\))?", r"B\.?Tech\.?",
    r"Bachelor of (?:Computer Application|Engineering)s?", r"BCA", r"B\.?E\.?",
    r"Higher Secondary(?:\s*\(10\+2\))?", r"12th(?:\s*\(10\+2\))?",
    r"Metric(?:\s*\(10th\))?", r"10th",
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

def extract_education_entries(section_text, split_into_list_fn):
    """Replaces raw blob-per-entry with parsed sub-fields per entry line."""
    entries = []
    for entry_text in split_into_list_fn(section_text):
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


# ---------- 3. ENTRY-LEVEL EXPERIENCE SUB-FIELD EXTRACTION ----------
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

def extract_experience_entries(section_text, split_into_list_fn):
    entries = []
    for entry_text in split_into_list_fn(section_text):
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


# Ordered keyword rules for classifying a publication citation
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
    
    prediction["education"] = extract_education_entries(get_section_text(sections, "education"), split_into_list)
    prediction["experience"] = extract_experience_entries(get_section_text(sections, "experience"), split_into_list)

    list_fields = ["research_interests", "skills", "projects", "certifications", "responsibilities", "references"]
    for field in list_fields:
        prediction[field] = split_into_list(get_section_text(sections, field))
        
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