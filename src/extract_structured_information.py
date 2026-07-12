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
    
    # Aggressive Email Match
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    email = email_match.group(0).strip() if email_match else ""
    
    # Aggressive Phone Match (Indian context + standard 10 digits)
    phone_match = re.search(r"(?:\+91|0)?[ -]*[6-9](?:[ -]*\d){9}", text)
    phone = re.sub(r"[^\d+]", "", phone_match.group(0)) if phone_match else ""
    
    # Smarter Name Extraction (ignores labels like "Name:")
    name = ""
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 3]
    for line in lines:
        if "@" in line or re.search(r"\d", line):
            continue
        # Strip common prefixes (Fixed Regex flag)
        clean_line = re.sub(r"^(name|full name|candidate name)\s*[:\-]\s*", "", line, flags=re.IGNORECASE).strip()
        clean_line = clean_line.strip(":-–—|•●■□*➢ ")
        if len(clean_line.split()) >= 2:
            name = clean_line
            break

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "address": "" 
    }

def split_into_list(text):
    if not text:
        return []
    # Catch complex bullets, arrows, numbers, and multiple newlines
    items = re.split(r'\n\s*(?:[-•*➢|o\+]|\d+[\.\)])\s*|\n{2,}', text)
    
    # Clean and filter empty strings
    return [re.sub(r'\s+', ' ', item).strip() for item in items if len(item.strip()) > 5]

def process_resume(section_file):
    with open(section_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    file_name = data.get("file_name", section_file.name)
    sections = data.get("sections", {})
    
    prediction = get_empty_gt_schema()
    
    # Personal Details
    prediction["personal_details"] = extract_personal_details(sections)
    
    # Summary
    summary_text = get_section_text(sections, "summary")
    prediction["summary"] = [summary_text] if summary_text else []
    
    # Standard Lists
    list_fields = ["education", "experience", "research_interests", "skills", "projects", "certifications", "responsibilities", "references"]
    for field in list_fields:
        prediction[field] = split_into_list(get_section_text(sections, field))
        
    # Publications (Dumping all into journal_articles as a fallback heuristic)
    pub_text = get_section_text(sections, "publications")
    if pub_text:
        prediction["publications"]["journal_articles"] = split_into_list(pub_text)

    # Ensure the prediction file name cleanly matches the Ground Truth file name for evaluation
    norm_name = section_file.name.replace("_sections.json", ".json")
    output_file = PREDICTIONS_DIR / norm_name
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(prediction, f, indent=4, ensure_ascii=False)

def main():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    json_files = sorted(SECTIONS_DIR.glob("*.json"))
    
    print(f"Extracting structured data for {len(json_files)} resumes...")
    for file in json_files:
        process_resume(file)
    print(f"Predictions saved to {PREDICTIONS_DIR}")

if __name__ == "__main__":
    main()