import json
import re
from pathlib import Path

# Paths
SECTIONS_DIR = Path("output/sections")
PREDICTIONS_DIR = Path("output/predictions")

def get_empty_gt_schema():
    return {
        "personal_details": {"name": "", "email": "", "phone": "", "address": ""},
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

def extract_personal_details(sections):
    text = get_section_text(sections, "personal_details")
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    email = email_match.group(0).strip() if email_match else ""
    phone_match = re.search(r"(?:\+91|0)?[ -]*[6-9](?:[ -]*\d){9}", text)
    phone = re.sub(r"[^\d+]", "", phone_match.group(0)) if phone_match else ""
    name = ""
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 3]
    for line in lines:
        if "@" in line or re.search(r"\d", line): continue
        clean_line = re.sub(r"^(name|full name|candidate name)\s*[:\-]\s*", "", line, flags=re.IGNORECASE).strip()
        clean_line = clean_line.strip(":-–—|•●■□*➢ ")
        if len(clean_line.split()) >= 2:
            name = clean_line
            break
    return {"name": name, "email": email, "phone": phone, "address": ""}

def split_into_list(text):
    if not text: return []
    items = re.split(r'\n\s*(?:[-•*➢|o\+]|\d+[\.\)])\s*|\n{2,}', text)
    return [re.sub(r'\s+', ' ', item).strip() for item in items if len(item.strip()) > 5]

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
    
    list_fields = ["education", "experience", "research_interests", "skills", "projects", "certifications", "responsibilities", "references"]
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