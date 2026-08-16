from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pypdf
import streamlit as st

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
GT_DIR = PROJECT_ROOT / "ground_truth"
SECTIONS_DIR = PROJECT_ROOT / "output" / "sections"
PREDICTIONS_DIR = PROJECT_ROOT / "output" / "predictions"
NORMALIZATION_MAP_PATH = PROJECT_ROOT / "config" / "section_normalization_map.json"

from src.extract_structured_information import (
    extract_personal_details,
    extract_education_entries,
    extract_experience_entries,
    split_into_list,
    split_publications_by_type,
    get_empty_gt_schema,
    normalize_phone_for_compare,
    extract_all_phones
)
from src.explainability.report_builder import find_source_line
from src.segment_resumes_into_sections import (
    load_heading_lookup,
    detect_heading,
    clean_line,
    is_page_marker
)

INSTITUTION_KEYWORDS = r"(?:University|Institute|College|School|IIT|NIT|IIIT|IIM|Vishwavidhyalay|Vidyalaya|Academy|Centre|Center)"
INSTITUTION_REGEX = re.compile(INSTITUTION_KEYWORDS, re.IGNORECASE)

GERUND_PATTERNS = re.compile(
    r"^\s*(?:Conducting|Designing|Preparing|Crafting|Executing|Managing|Developing|Leading|Coordinating|Creating|Implementing|Formulating|Providing|Handling|Organizing)\b",
    re.IGNORECASE
)

NARRATIVE_PHRASES = [
    "years of exposure", "skills and ethics", "critical thinking skills to",
    "strong ability to", "skilled in coordinating", "experience with analytical",
    "ability to identify", "good communication ability", "possess organizing"
]

def is_narrative_skill_item(item: str) -> bool:
    """Checks if a skill item is narrative prose/sentence rather than an itemized skill."""
    words = item.split()
    if len(words) > 13:
        return True
    if GERUND_PATTERNS.search(item):
        return True
    item_lower = item.lower()
    if any(phrase in item_lower for phrase in NARRATIVE_PHRASES):
        return True
    return False

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Tuple[str, int]:
    """Extracts raw text from PDF bytes using pypdf."""
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    full_text = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            full_text.append(txt)
    text = "\n".join(full_text).strip()
    return text, len(text)

def live_section_text(raw_text: str) -> Dict[str, str]:
    """Segments raw text live into a dictionary of normalized section texts."""
    heading_lookup = load_heading_lookup()
    lines = raw_text.splitlines()
    sections_store: Dict[str, List[str]] = {}
    current_section = "preamble"

    for line_idx, line in enumerate(lines, start=1):
        raw_line = line.rstrip("\n")
        cleaned = clean_line(raw_line)
        if not cleaned or is_page_marker(raw_line):
            continue
        heading_info = detect_heading(raw_line, heading_lookup, line_idx)
        if heading_info is not None:
            canonical = heading_info["canonical_section"]
            if canonical != "ignore":
                current_section = canonical
                if current_section not in sections_store:
                    sections_store[current_section] = []
                remaining = heading_info.get("remaining_text", "").strip()
                if remaining:
                    sections_store[current_section].append(remaining)
                continue
        if current_section not in sections_store:
            sections_store[current_section] = []
        sections_store[current_section].append(raw_line)

    sections_dict = {}
    for sec, sec_lines in sections_store.items():
        joined = "\n".join(sec_lines).strip()
        if joined:
            sections_dict[sec] = joined
    return sections_dict

def run_live_pipeline(file_bytes: bytes, file_name: str) -> Dict[str, Any]:
    """
    Executes the full live 3-stage resume processing pipeline:
    Stage 1: Text Extraction -> Stage 2: Section Detection -> Stage 3: Entity Extraction.
    Returns status objects for each stage, fully_parsed flag, and stage-level failure explanation.
    """
    base_name = Path(file_name).stem.replace("_sections", "")
    
    # --- STAGE 1: Text Extraction ---
    if file_name.lower().endswith(".txt"):
        raw_text = file_bytes.decode("utf-8", errors="ignore").strip()
        char_count = len(raw_text)
    else:
        raw_text, char_count = extract_text_from_pdf_bytes(file_bytes)

    if char_count == 0:
        stage1_status = {
            "status": "failed",
            "char_count": 0,
            "warning": "No text extracted from PDF. Document may be empty or a scanned image-only PDF."
        }
    elif char_count < 100:
        stage1_status = {
            "status": "partial",
            "char_count": char_count,
            "warning": f"Very short text extracted ({char_count} chars). PDF may be partially scanned or image-based."
        }
    else:
        stage1_status = {
            "status": "success",
            "char_count": char_count,
            "warning": ""
        }

    # --- STAGE 2: Section Detection ---
    sections = live_section_text(raw_text) if raw_text else {}
    sections_detected = list(sections.keys())
    
    expected_canonical = ["education"]
    sections_expected_but_missing = []
    if "education" not in sections_detected:
        sections_expected_but_missing.append("education")

    if not sections_detected:
        stage2_status = {
            "status": "failed",
            "sections_detected": [],
            "sections_expected_but_missing": expected_canonical,
            "sections_dict": {}
        }
    else:
        stage2_status = {
            "status": "success",
            "sections_detected": sections_detected,
            "sections_expected_but_missing": sections_expected_but_missing,
            "sections_dict": sections
        }

    # --- STAGE 3: Entity Extraction ---
    prediction = get_empty_gt_schema()
    prediction["personal_details"] = extract_personal_details(sections)
    
    edu_text = sections.get("education", "")
    prediction["education"] = extract_education_entries(edu_text, split_into_list) if edu_text else []
    
    exp_text = sections.get("experience", "") + sections.get("academic_experience", "")
    prediction["experience"] = extract_experience_entries(exp_text, split_into_list) if exp_text else []

    list_fields = ["research_interests", "skills", "projects", "certifications", "responsibilities", "references"]
    for field in list_fields:
        sec_content = sections.get(field, "")
        prediction[field] = split_into_list(sec_content) if sec_content else []

    pub_text = sections.get("publications", "")
    if pub_text:
        prediction["publications"] = split_publications_by_type(pub_text)

    # Build Field Explanations using report_builder logic
    gt_file = GT_DIR / f"{base_name}.json"
    has_gt = gt_file.exists()
    gt = json.loads(gt_file.read_text(encoding="utf-8")) if has_gt else {}

    field_reports = {}
    flags = []

    # Personal Details Explanations
    p_details = prediction.get("personal_details", {})
    preamble_text = sections.get("preamble", "")
    details_text = sections.get("personal_details", "")
    combined_contact = f"{preamble_text}\n{details_text}".strip()

    has_contact_info = bool(p_details.get("name") and p_details.get("email"))
    if not has_contact_info:
        sections_expected_but_missing.append("contact_details (name & email)")

    name_val = p_details.get("name", "")
    name_source = find_source_line(combined_contact, name_val) if name_val else ""
    field_reports["personal_name"] = {
        "value": name_val or "[Not Found]",
        "source_line": name_source or (combined_contact[:120] if combined_contact else "[Section Empty]"),
        "reason_if_empty": "" if name_val else "No multi-word candidate name heading found in preamble/contact text."
    }

    email_val = p_details.get("email", "")
    email_source = find_source_line(combined_contact, email_val) if email_val else ""
    field_reports["personal_email"] = {
        "value": email_val or "[Not Found]",
        "source_line": email_source or (combined_contact[:120] if combined_contact else "[Section Empty]"),
        "reason_if_empty": "" if email_val else "No email pattern (user@domain.tld) matched in preamble/contact text."
    }

    phone_val = p_details.get("phone", "")
    phone_source = find_source_line(combined_contact, phone_val) if phone_val else ""
    field_reports["personal_phone"] = {
        "value": phone_val or "[Not Found]",
        "source_line": phone_source or (combined_contact[:120] if combined_contact else "[Section Empty]"),
        "reason_if_empty": "" if phone_val else "No 10-digit mobile number pattern matched in preamble/contact text."
    }

    # Education Entry Explanations
    edu_entries_report = []
    for idx, entry in enumerate(prediction.get("education", [])):
        raw_t = entry.get("raw_text", "")
        deg = entry.get("degree", "")
        inst = entry.get("institution", "")
        deg_reason = "" if deg else "No degree keyword (PhD/M.Sc/B.Tech/etc.) matched in entry line."
        inst_reason = "" if inst else ("No institution keyword (University/Institute/College/etc.) matched in entry line." if INSTITUTION_REGEX.search(raw_t) else "Entry line contains no university or institution keyword.")
        if deg and not inst:
            flags.append({"field": f"education_entry_{idx+1}", "flag": "possible_missed_institution", "description": f"Entry {idx+1}: Degree found ('{deg}') but institution is empty."})
        edu_entries_report.append({
            "entry_index": idx + 1,
            "raw_text": raw_t,
            "degree": {"value": deg or "[Not Found]", "reason_if_empty": deg_reason},
            "institution": {"value": inst or "[Not Found]", "reason_if_empty": inst_reason},
            "graduation_year": {"value": entry.get("graduation_year", "") or "[Not Found]"},
            "cgpa": {"value": entry.get("cgpa", "") or "[Not Found]"}
        })

    # Experience Entry Explanations
    exp_entries_report = []
    for idx, entry in enumerate(prediction.get("experience", [])):
        raw_t = entry.get("raw_text", "")
        title = entry.get("job_title", "")
        inst = entry.get("institution", "")
        title_reason = "" if title else "No job title keyword (Assistant Professor/Research Associate/etc.) matched in entry line."
        inst_reason = "" if inst else "No organization/university keyword matched in entry line."
        if title and not inst:
            flags.append({"field": f"experience_entry_{idx+1}", "flag": "possible_missed_company_institution", "description": f"Entry {idx+1}: Job title found ('{title}') but institution is empty."})
        exp_entries_report.append({
            "entry_index": idx + 1,
            "raw_text": raw_t,
            "job_title": {"value": title or "[Not Found]", "reason_if_empty": title_reason},
            "institution": {"value": inst or "[Not Found]", "reason_if_empty": inst_reason},
            "dates": {"value": entry.get("dates", "") or "[Not Found]"}
        })

    # Skills Narrative Quality Flag Check
    skills_list = prediction.get("skills", [])
    if any(is_narrative_skill_item(item) for item in skills_list):
        flags.append({
            "field": "skills",
            "flag": "possible_narrative_skills_not_itemized",
            "description": "Skills section content is written as narrative paragraphs/sentences rather than itemized bullet points; found skills content but could not reliably itemize individual skills."
        })

    stage3_status = {
        "status": "success" if (prediction.get("education") or prediction.get("experience") or prediction.get("skills")) else "partial",
        "prediction": prediction,
        "education_report": edu_entries_report,
        "experience_report": exp_entries_report,
        "field_reports": field_reports,
        "flags": flags
    }

    # --- DEFINITION OF FULLY PARSED & FIRST STAGE LOSS PINPOINTING ---
    fully_parsed = True
    first_stage_loss = None

    if stage1_status["status"] == "failed" or stage1_status["char_count"] < 100:
        fully_parsed = False
        first_stage_loss = {
            "stage": "Stage 1: Text Extraction",
            "reason": stage1_status["warning"] or "Extracted text is empty or less than 100 characters.",
            "raw_text_snippet": raw_text[:200]
        }
    elif not sections_detected:
        fully_parsed = False
        first_stage_loss = {
            "stage": "Stage 2: Section Detection",
            "reason": "Sectioning failed to detect any canonical headings in extracted text.",
            "raw_text_snippet": raw_text[:300]
        }
    elif not has_contact_info:
        fully_parsed = False
        first_stage_loss = {
            "stage": "Stage 3: Entity Extraction (Contact Details)",
            "reason": "Failed to extract both candidate name and email address from document contact text.",
            "raw_text_snippet": (sections.get("preamble", "") + "\n" + sections.get("personal_details", ""))[:300]
        }
    elif "education" in sections_expected_but_missing:
        fully_parsed = False
        first_stage_loss = {
            "stage": "Stage 2: Section Detection",
            "reason": "Required core section 'education' was missing from document sectioning.",
            "raw_text_snippet": raw_text[:300]
        }
    else:
        section_failures = []
        for sec in sections_detected:
            sec_text_content = sections[sec].strip()
            if not sec_text_content or sec in ("preamble", "personal_details"):
                continue
            
            if sec == "education" and not prediction.get("education"):
                section_failures.append({
                    "section": "education",
                    "reason": f"Sectioning detected an 'education' section ({len(sec_text_content)} chars), but Entity Extraction pulled 0 entries from it.",
                    "snippet": sec_text_content[:300]
                })
            elif sec in ("experience", "academic_experience") and not prediction.get("experience"):
                section_failures.append({
                    "section": "experience",
                    "reason": f"Sectioning detected an 'experience' section ({len(sec_text_content)} chars), but Entity Extraction pulled 0 entries from it.",
                    "snippet": sec_text_content[:300]
                })

        if flags:
            fully_parsed = False
            first_flag = flags[0]
            first_stage_loss = {
                "stage": f"Stage 3: Entity Extraction (Flag '{first_flag['flag']}')",
                "reason": f"Entity extraction quality rule flag raised for [{first_flag['field']}]: {first_flag['description']}",
                "raw_text_snippet": sections.get("skills", "")[:300] or sections.get("education", "")[:300] or raw_text[:300]
            }
        elif section_failures:
            fully_parsed = False
            first_fail = section_failures[0]
            first_stage_loss = {
                "stage": f"Stage 3: Entity Extraction (Section '{first_fail['section']}')",
                "reason": first_fail["reason"],
                "raw_text_snippet": first_fail["snippet"]
            }

    return {
        "file_name": file_name,
        "base_name": base_name,
        "has_ground_truth": has_gt,
        "fully_parsed": fully_parsed,
        "first_stage_loss": first_stage_loss,
        "text_extraction": stage1_status,
        "sectioning": stage2_status,
        "entity_extraction": stage3_status
    }

# --- STREAMLIT UI ---
def main_ui():
    st.set_page_config(page_title="Live Resume Processing & Failure Diagnostics", layout="wide")
    st.title("⚡ Live Resume Processing & Stage-Level Failure Diagnostics")
    st.markdown("Upload a PDF resume to execute live 3-stage processing: **Text Extraction → Section Detection → Entity Extraction**")

    uploaded_file = st.file_uploader("Upload PDF Resume", type=["pdf", "txt"])

    sample_pdfs = sorted(list((PROJECT_ROOT / "data" / "real_resumes" / "original").glob("*.pdf")))
    sample_choice = st.selectbox("Or Select Sample PDF Resume from Data:", ["-- Select Sample PDF --"] + [p.name for p in sample_pdfs])

    target_bytes = None
    target_name = None

    if uploaded_file is not None:
        target_bytes = uploaded_file.read()
        target_name = uploaded_file.name
    elif sample_choice != "-- Select Sample PDF --":
        sample_path = PROJECT_ROOT / "data" / "real_resumes" / "original" / sample_choice
        target_bytes = sample_path.read_bytes()
        target_name = sample_choice

    if target_bytes and target_name:
        st.divider()
        st.subheader(f"📄 Processing: `{target_name}`")

        with st.spinner("Executing live 3-stage extraction pipeline..."):
            result = run_live_pipeline(target_bytes, target_name)

        if result["fully_parsed"]:
            st.success("✅ **FULLY PARSED**: All text extracted cleanly, sectioned, and every detected section produced structured entity entries!")
        else:
            st.error("❌ **PARSE INCOMPLETE / INFORMATION LOSS DETECTED**")
            loss = result["first_stage_loss"]
            if loss:
                st.warning(f"**First Stage Loss Point**: `{loss['stage']}`\n\n**Reason**: {loss['reason']}")
                with st.expander("🔍 Inspect Raw Source Text at Loss Point"):
                    st.code(loss["raw_text_snippet"], language="text")

        tab1, tab2, tab3 = st.tabs(["1️⃣ Text Extraction", "2️⃣ Section Detection", "3️⃣ Entity Extraction & Explanations"])

        with tab1:
            st.write("### Stage 1: Text Extraction")
            s1 = result["text_extraction"]
            st.metric("Total Extracted Characters", s1["char_count"])
            if s1["warning"]:
                st.warning(f"Warning: {s1['warning']}")
            else:
                st.success("Status: SUCCESS")

        with tab2:
            st.write("### Stage 2: Section Detection")
            s2 = result["sectioning"]
            st.write("**Sections Detected**:", s2["sections_detected"])
            if s2["sections_expected_but_missing"]:
                st.info(f"Expected Sections Not Found: {s2['sections_expected_but_missing']}")
            
            with st.expander("Inspect Detected Section Texts"):
                for sec_k, sec_v in s2["sections_dict"].items():
                    st.markdown(f"#### Section: `{sec_k}` ({len(sec_v)} chars)")
                    st.text(sec_v[:400] + ("..." if len(sec_v) > 400 else ""))

        with tab3:
            st.write("### Stage 3: Entity Extraction & Explanations")
            s3 = result["entity_extraction"]
            
            if s3["flags"]:
                st.markdown("#### ⚠️ Categorical Quality Rule Flags")
                for f in s3["flags"]:
                    st.warning(f"**[{f['field']}] `{f['flag']}`**: {f['description']}")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 👤 Personal Details")
                for k, v in s3["field_reports"].items():
                    st.write(f"**{k}**: `{v['value']}`")
                    st.caption(f"Line: \"{v['source_line']}\"")

                st.markdown("#### 🎓 Education Entries")
                for e in s3["education_report"]:
                    st.markdown(f"**Entry {e['entry_index']}**: Degree=`{e['degree']['value']}` | Inst=`{e['institution']['value']}`")
                    if e["degree"]["reason_if_empty"]:
                        st.caption(f"Degree Reason: {e['degree']['reason_if_empty']}")
                    if e["institution"]["reason_if_empty"]:
                        st.caption(f"Inst Reason: {e['institution']['reason_if_empty']}")

            with col2:
                st.markdown("#### 💼 Experience Entries")
                for e in s3["experience_report"]:
                    st.markdown(f"**Entry {e['entry_index']}**: Title=`{e['job_title']['value']}` | Inst=`{e['institution']['value']}`")
                    if e["job_title"]["reason_if_empty"]:
                        st.caption(f"Title Reason: {e['job_title']['reason_if_empty']}")

                st.markdown("#### 🛠️ Skills & Projects")
                pred = s3["prediction"]
                st.write("**Skills**:", pred.get("skills", []))
                st.write("**Projects**:", pred.get("projects", []))

if __name__ == "__main__":
    main_ui()
