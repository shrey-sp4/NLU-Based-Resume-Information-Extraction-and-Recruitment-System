from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
GT_DIR = PROJECT_ROOT / "ground_truth"
SECTIONS_DIR = PROJECT_ROOT / "output" / "sections"
PREDICTIONS_DIR = PROJECT_ROOT / "output" / "predictions"

INSTITUTION_KEYWORDS = r"(?:University|Institute|College|School|IIT|NIT|IIIT|IIM|Vishwavidhyalay|Vidyalaya|Academy|Centre|Center)"
INSTITUTION_REGEX = re.compile(INSTITUTION_KEYWORDS, re.IGNORECASE)

def find_source_line(text: str, target: str) -> str:
    """Locates the line in text that contains target or the closest matching line."""
    if not text or not target:
        return ""
    target_clean = target.strip().lower()
    for line in text.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        if target_clean in line_clean.lower() or line_clean.lower() in target_clean:
            return line_clean
    tokens = [t.lower() for t in target.split() if len(t) > 3]
    if tokens:
        for line in text.splitlines():
            if any(t in line.lower() for t in tokens):
                return line.strip()
    return ""

def build_explainability_report(resume_name: str) -> Dict[str, Any]:
    """
    Builds a comprehensive, rule-based explainability report for a given resume.
    Loads prediction JSON, section text JSON, and optional ground truth JSON.
    """
    base_name = resume_name.replace("_sections.json", "").replace(".json", "")
    pred_file = PREDICTIONS_DIR / f"{base_name}.json"
    sec_file = SECTIONS_DIR / f"{base_name}_sections.json"
    gt_file = GT_DIR / f"{base_name}.json"

    if not pred_file.exists() or not sec_file.exists():
        raise FileNotFoundError(f"Missing artifacts for {resume_name}: pred={pred_file.exists()}, sec={sec_file.exists()}")

    with open(pred_file, "r", encoding="utf-8") as f:
        pred = json.load(f)
    with open(sec_file, "r", encoding="utf-8") as f:
        sec_data = json.load(f)
        sections = sec_data.get("sections", {})

    has_gt = gt_file.exists()
    gt = {}
    if has_gt:
        with open(gt_file, "r", encoding="utf-8") as f:
            gt = json.load(f)

    preamble_text = sections.get("preamble", "")
    details_text = sections.get("personal_details", "")
    combined_contact_text = f"{preamble_text}\n{details_text}".strip()

    field_reports = {}
    flags = []

    # --- 1. Personal Details ---
    p_details = pred.get("personal_details", {})
    gt_details = gt.get("personal_details", {}) if has_gt else {}

    # Name
    name_val = p_details.get("name", "")
    name_source = find_source_line(combined_contact_text, name_val) if name_val else ""
    name_reason = "" if name_val else "No multi-word non-email name heading found in preamble or personal details text."
    name_flag = ""
    if not name_val:
        name_flag = "missing_personal_name"
        flags.append({"field": "personal_name", "flag": name_flag, "description": "Candidate name is missing."})
    elif len(name_val.split()) == 1:
        name_flag = "possible_incomplete_name"
        flags.append({"field": "personal_name", "flag": name_flag, "description": "Name contains only a single word."})

    name_gt_status = "NO_GT"
    if has_gt:
        gt_n = str(gt_details.get("name", "") or "").strip().lower()
        pr_n = str(name_val or "").strip().lower()
        name_gt_status = "MATCH" if (gt_n and pr_n and (gt_n in pr_n or pr_n in gt_n)) else ("MISMATCH" if gt_n else "NO_GT")

    field_reports["personal_name"] = {
        "value": name_val or "[Not Found]",
        "source_line": name_source or (combined_contact_text[:120] if combined_contact_text else "[Section Empty]"),
        "reason_if_empty": name_reason,
        "flag": name_flag,
        "gt_value": gt_details.get("name", "") if has_gt else None,
        "gt_match_status": name_gt_status
    }

    # Email
    email_val = p_details.get("email", "")
    email_source = find_source_line(combined_contact_text, email_val) if email_val else ""
    email_reason = "" if email_val else "No standard email pattern (user@domain.tld) matched in preamble or personal details."
    email_flag = ""
    if not email_val:
        email_flag = "missing_contact_email"
        flags.append({"field": "personal_email", "flag": email_flag, "description": "No email address extracted."})

    email_gt_status = "NO_GT"
    if has_gt:
        gt_e = str(gt_details.get("email", "") or "").strip().lower()
        pr_e = str(email_val or "").strip().lower()
        email_gt_status = "MATCH" if (gt_e and pr_e and gt_e == pr_e) else ("MISMATCH" if gt_e else "NO_GT")

    field_reports["personal_email"] = {
        "value": email_val or "[Not Found]",
        "source_line": email_source or (combined_contact_text[:120] if combined_contact_text else "[Section Empty]"),
        "reason_if_empty": email_reason,
        "flag": email_flag,
        "gt_value": gt_details.get("email", "") if has_gt else None,
        "gt_match_status": email_gt_status
    }

    # Phone
    phone_val = p_details.get("phone", "") or (p_details.get("phones", [""])[0] if p_details.get("phones") else "")
    phone_source = find_source_line(combined_contact_text, phone_val) if phone_val else ""
    phone_reason = "" if phone_val else "No 10-digit mobile number pattern matched in preamble or personal details."
    phone_flag = ""
    if not phone_val:
        phone_flag = "missing_contact_phone"
        flags.append({"field": "personal_phone", "flag": phone_flag, "description": "No phone number extracted."})
    elif find_source_line(preamble_text, phone_val):
        phone_flag = "verify_phone_source_preamble"
        flags.append({"field": "personal_phone", "flag": phone_flag, "description": "Phone number extracted from preamble text; verify manually."})

    phone_gt_status = "NO_GT"
    if has_gt:
        gt_p = str(gt_details.get("phone", "") or "").strip()
        phone_gt_status = "MATCH" if (gt_p and phone_val and (re.sub(r"\D", "", gt_p) in re.sub(r"\D", "", phone_val) or re.sub(r"\D", "", phone_val) in re.sub(r"\D", "", gt_p))) else ("MISMATCH" if gt_p else "NO_GT")

    field_reports["personal_phone"] = {
        "value": phone_val or "[Not Found]",
        "source_line": phone_source or (combined_contact_text[:120] if combined_contact_text else "[Section Empty]"),
        "reason_if_empty": phone_reason,
        "flag": phone_flag,
        "gt_value": gt_details.get("phone", "") if has_gt else None,
        "gt_match_status": phone_gt_status
    }

    # --- 2. Education Entries ---
    edu_text = sections.get("education", "")
    pred_edu = pred.get("education", [])
    gt_edu = gt.get("education", []) if has_gt else []

    edu_entry_reports = []
    if not edu_text.strip():
        flags.append({"field": "education", "flag": "missing_education_section", "description": "Education section text is completely empty or missing."})
    elif not pred_edu:
        flags.append({"field": "education", "flag": "no_education_entries_parsed", "description": "Education section text exists but no structured entries were parsed."})

    for idx, raw_entry in enumerate(pred_edu):
        if isinstance(raw_entry, dict):
            entry = raw_entry
            raw_t = entry.get("raw_text", "") or edu_text
        else:
            raw_t = str(raw_entry)
            entry = {"degree": raw_t, "institution": "", "graduation_year": "", "cgpa": "", "raw_text": raw_t}

        deg = entry.get("degree", "")
        inst = entry.get("institution", "")
        yr = entry.get("graduation_year", "")
        cgpa = entry.get("cgpa", "")

        deg_reason = "" if deg else "No degree keyword (PhD/M.Sc/B.Tech/etc.) matched in entry line."
        inst_reason = "" if inst else ("No institution keyword (University/Institute/College/etc.) matched in entry line." if INSTITUTION_REGEX.search(raw_t) else "Entry line contains no university or institution keyword.")
        yr_reason = "" if yr else "No 4-digit year pattern (19XX/20XX) matched in entry line."
        cgpa_reason = "" if cgpa else "No grade/percentage/CGPA pattern matched in entry line."

        entry_flags = []
        if deg and not inst:
            f_item = "possible_missed_institution"
            entry_flags.append(f_item)
            flags.append({"field": f"education_entry_{idx+1}", "flag": f_item, "description": f"Entry {idx+1}: Degree found ('{deg}') but institution is empty."})
        if inst and not deg:
            f_item = "degree_missing_in_education_entry"
            entry_flags.append(f_item)
            flags.append({"field": f"education_entry_{idx+1}", "flag": f_item, "description": f"Entry {idx+1}: Institution found ('{inst}') but degree is empty."})

        edu_entry_reports.append({
            "entry_index": idx + 1,
            "raw_text": raw_t,
            "degree": {"value": deg or "[Not Found]", "reason_if_empty": deg_reason},
            "institution": {"value": inst or "[Not Found]", "reason_if_empty": inst_reason},
            "graduation_year": {"value": yr or "[Not Found]", "reason_if_empty": yr_reason},
            "cgpa": {"value": cgpa or "[Not Found]", "reason_if_empty": cgpa_reason},
            "flags": entry_flags
        })

    field_reports["education"] = {
        "section_text": edu_text,
        "entry_count": len(pred_edu),
        "entries": edu_entry_reports,
        "gt_entries": gt_edu if has_gt else None
    }

    # --- 3. Experience Entries ---
    exp_text = sections.get("experience", "") + sections.get("academic_experience", "")
    pred_exp = pred.get("experience", [])
    gt_exp = (gt.get("experience", []) + gt.get("academic_experience", [])) if has_gt else []

    exp_entry_reports = []
    if not exp_text.strip():
        flags.append({"field": "experience", "flag": "missing_experience_section", "description": "Experience section text is completely empty or missing."})
    elif not pred_exp:
        flags.append({"field": "experience", "flag": "no_experience_entries_parsed", "description": "Experience section text exists but no structured entries were parsed."})

    for idx, raw_entry in enumerate(pred_exp):
        if isinstance(raw_entry, dict):
            entry = raw_entry
            raw_t = entry.get("raw_text", "") or exp_text
        else:
            raw_t = str(raw_entry)
            entry = {"job_title": raw_t, "institution": "", "dates": "", "raw_text": raw_t}

        title = entry.get("job_title", "") or entry.get("title", "")
        inst = entry.get("institution", "")
        dates = entry.get("dates", "")

        title_reason = "" if title else "No job title keyword (Assistant Professor/Research Associate/etc.) matched in entry line."
        inst_reason = "" if inst else "No organization/university keyword matched in entry line."
        dates_reason = "" if dates else "No date range pattern (Month Year - Month Year / Year-Year) matched in entry line."

        entry_flags = []
        if title and not inst:
            f_item = "possible_missed_company_institution"
            entry_flags.append(f_item)
            flags.append({"field": f"experience_entry_{idx+1}", "flag": f_item, "description": f"Entry {idx+1}: Job title found ('{title}') but institution is empty."})
        if inst and not title:
            f_item = "title_missing_in_experience_entry"
            entry_flags.append(f_item)
            flags.append({"field": f"experience_entry_{idx+1}", "flag": f_item, "description": f"Entry {idx+1}: Institution found ('{inst}') but job title is empty."})

        exp_entry_reports.append({
            "entry_index": idx + 1,
            "raw_text": raw_t,
            "job_title": {"value": title or "[Not Found]", "reason_if_empty": title_reason},
            "institution": {"value": inst or "[Not Found]", "reason_if_empty": inst_reason},
            "dates": {"value": dates or "[Not Found]", "reason_if_empty": dates_reason},
            "flags": entry_flags
        })

    field_reports["experience"] = {
        "section_text": exp_text,
        "entry_count": len(pred_exp),
        "entries": exp_entry_reports,
        "gt_entries": gt_exp if has_gt else None
    }

    # --- 4. Standard List Sections ---
    for sec in ("skills", "projects", "certifications", "research_interests", "responsibilities", "references", "summary"):
        sec_text = sections.get(sec, "")
        pred_items = pred.get(sec, [])
        gt_items = gt.get(sec, []) if has_gt else None

        reason = ""
        if not sec_text:
            reason = f"Section header '{sec}' was not detected in document sectioning."
        elif not pred_items:
            reason = f"Section text for '{sec}' exists but contained no valid list items."

        sec_flag = ""
        if not sec_text and sec in ("skills", "projects"):
            sec_flag = f"missing_{sec}_section"
            flags.append({"field": sec, "flag": sec_flag, "description": f"Important section '{sec}' is missing."})

        field_reports[sec] = {
            "value": pred_items if pred_items else "[Not Found]",
            "item_count": len(pred_items) if isinstance(pred_items, list) else (1 if pred_items else 0),
            "source_snippet": sec_text[:150] if sec_text else "[Section Not Detected]",
            "reason_if_empty": reason,
            "flag": sec_flag,
            "gt_value": gt_items
        }

    # --- 5. Publications Subtypes ---
    gt_pubs = gt.get("publications", {}) if has_gt and isinstance(gt.get("publications"), dict) else {}
    pred_pubs = pred.get("publications", {}) if isinstance(pred.get("publications"), dict) else {}
    pub_section_text = sections.get("publications", "")

    pub_reports = {}
    pub_subtypes = [
        "journal_articles", "conference_papers", "conference_proceedings",
        "communications", "book_chapters", "books", "technical_reports", "preprints"
    ]

    for st in pub_subtypes:
        items = pred_pubs.get(st, [])
        gt_st_items = gt_pubs.get(st, []) if has_gt else None
        st_reason = ""
        if not pub_section_text:
            st_reason = "Publications section was not detected in document."
        elif not items:
            st_reason = f"No publication citations matched classification rule for '{st}'."

        pub_reports[st] = {
            "value": items if items else "[None Extracted]",
            "count": len(items),
            "reason_if_empty": st_reason,
            "gt_value": gt_st_items
        }

    field_reports["publications"] = {
        "section_text_snippet": pub_section_text[:150] if pub_section_text else "[Section Not Detected]",
        "total_predicted_publications": sum(len(v) for v in pred_pubs.values()) if isinstance(pred_pubs, dict) else 0,
        "subtypes": pub_reports
    }

    return {
        "resume_name": resume_name,
        "base_name": base_name,
        "has_ground_truth": has_gt,
        "field_reports": field_reports,
        "flags": flags,
        "total_flags": len(flags)
    }

def get_available_resumes() -> List[Dict[str, Any]]:
    """Returns a list of all available resume predictions with GT indicator."""
    resumes = []
    for pred_path in sorted(PREDICTIONS_DIR.glob("*.json")):
        base_name = pred_path.stem
        sec_path = SECTIONS_DIR / f"{base_name}_sections.json"
        if not sec_path.exists():
            continue
        gt_path = GT_DIR / pred_path.name
        resumes.append({
            "base_name": base_name,
            "file_name": pred_path.name,
            "has_ground_truth": gt_path.exists()
        })
    return resumes
