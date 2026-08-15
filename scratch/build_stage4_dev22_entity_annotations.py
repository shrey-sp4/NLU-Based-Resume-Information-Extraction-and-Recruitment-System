from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

STAGE3_RUN_DIR = PROJECT_ROOT / "output" / "sectioning" / "clean_stage3_8_run" / "sectioning_run_20260811T100030Z"
HUMAN_GT_FILE = PROJECT_ROOT / "data" / "section_annotations" / "human_annotations.jsonl"

OUT_DIR = PROJECT_ROOT / "data" / "entity_annotations"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "entity_annotations_dev22.jsonl"

# Load ground truth resume IDs
all_docs = []
with open(HUMAN_GT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        if item["resume_id"] not in all_docs:
            all_docs.append(item["resume_id"])

# Use the 22 Development Resumes (10 Dev + 12 Non-Benchmark)
dev_22_docs = all_docs[:22]
print(f"Building entity annotations for {len(dev_22_docs)} Development Resumes...")

# Regex patterns for auto-extracting silver/gold seed spans
EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+", re.IGNORECASE)
PHONE_REGEX = re.compile(r"(?:\+91[\s\-]*)?(?:[6-9]\d[\d\s\-]{8,12})")
DOI_REGEX = re.compile(r"\b10\.\d{4,}/[-._;()/:A-Za-z0-9]+\b")
YEAR_REGEX = re.compile(r"\b(19|20)\d{2}\b")
GRADE_REGEX = re.compile(r"\b\d+\.\d+\s*(?:CGPA|CPI|GPA|%)\b|\b\d+%\b", re.IGNORECASE)

DEGREE_KEYWORDS = ["B.Tech", "M.Tech", "Ph.D.", "PhD", "B.E.", "M.E.", "B.Sc", "M.Sc", "Diploma", "HSC", "SSC", "Matriculation", "Intermediate", "Bachelor", "Master", "Doctor of Philosophy"]
ROLE_KEYWORDS = ["Professor", "Assistant Professor", "Associate Professor", "Research Assistant", "Teaching Assistant", "Lecturer", "Engineer", "Developer", "Postdoctoral Fellow", "Project Fellow", "Intern", "Consultant", "Head of Department", "Principal"]

annotations = []
total_spans_count = 0

for doc_id in dev_22_docs:
    sec_path = STAGE3_RUN_DIR / "documents" / doc_id / "sections.json"
    if not sec_path.exists():
        continue
    with open(sec_path, "r", encoding="utf-8") as f:
        sec_data = json.load(f)

    doc_spans = []

    for span in sec_data.get("sections", []):
        sec_id = span["section_id"]
        sec_type = span["normalized_heading"]

        for l_rec in span.get("lines", []):
            text = l_rec.get("text", "").strip()
            p_num = l_rec["page_number"]
            l_num = l_rec["line_number"]
            l_idx = l_rec["line_index"]

            if not text or l_rec.get("is_heading", False):
                continue

            # Candidate Name in Preamble/Contact line 1
            if sec_type in ("preamble", "contact") and l_idx == 1 and not EMAIL_REGEX.search(text) and not PHONE_REGEX.search(text):
                clean_name = re.sub(r"^(Dr\.|Prof\.|Mr\.|Mrs\.|Ms\.)\s+", "", text, flags=re.IGNORECASE).strip()
                if len(clean_name.split()) >= 2 and len(clean_name) <= 35:
                    st = text.find(clean_name)
                    if st >= 0:
                        doc_spans.append({
                            "token_text": clean_name,
                            "label": "NAME",
                            "start_char": st,
                            "end_char": st + len(clean_name),
                            "line_text": text,
                            "page_number": p_num,
                            "line_number": l_num,
                            "line_index": l_idx,
                            "source_section_id": sec_id,
                            "source_section_type": sec_type,
                        })

            # Email Regex
            for m in EMAIL_REGEX.finditer(text):
                doc_spans.append({
                    "token_text": m.group(0),
                    "label": "EMAIL",
                    "start_char": m.start(),
                    "end_char": m.end(),
                    "line_text": text,
                    "page_number": p_num,
                    "line_number": l_num,
                    "line_index": l_idx,
                    "source_section_id": sec_id,
                    "source_section_type": sec_type,
                })

            # Phone Regex
            for m in PHONE_REGEX.finditer(text):
                doc_spans.append({
                    "token_text": m.group(0),
                    "label": "PHONE",
                    "start_char": m.start(),
                    "end_char": m.end(),
                    "line_text": text,
                    "page_number": p_num,
                    "line_number": l_num,
                    "line_index": l_idx,
                    "source_section_id": sec_id,
                    "source_section_type": sec_type,
                })

            # Degree Keywords in Education
            if sec_type == "education":
                for deg in DEGREE_KEYWORDS:
                    if deg.lower() in text.lower():
                        st = text.lower().find(deg.lower())
                        doc_spans.append({
                            "token_text": text[st:st+len(deg)],
                            "label": "DEGREE",
                            "start_char": st,
                            "end_char": st + len(deg),
                            "line_text": text,
                            "page_number": p_num,
                            "line_number": l_num,
                            "line_index": l_idx,
                            "source_section_id": sec_id,
                            "source_section_type": sec_type,
                        })

                # Grade / CGPA
                for m in GRADE_REGEX.finditer(text):
                    doc_spans.append({
                        "token_text": m.group(0),
                        "label": "GRADE",
                        "start_char": m.start(),
                        "end_char": m.end(),
                        "line_text": text,
                        "page_number": p_num,
                        "line_number": l_num,
                        "line_index": l_idx,
                        "source_section_id": sec_id,
                        "source_section_type": sec_type,
                    })

            # Job Role Titles in Experience
            if sec_type == "experience":
                for role in ROLE_KEYWORDS:
                    if role.lower() in text.lower():
                        st = text.lower().find(role.lower())
                        doc_spans.append({
                            "token_text": text[st:st+len(role)],
                            "label": "TITLE",
                            "start_char": st,
                            "end_char": st + len(role),
                            "line_text": text,
                            "page_number": p_num,
                            "line_number": l_num,
                            "line_index": l_idx,
                            "source_section_id": sec_id,
                            "source_section_type": sec_type,
                        })

            # DOI Regex in Publications
            if sec_type == "publications":
                for m in DOI_REGEX.finditer(text):
                    doc_spans.append({
                        "token_text": m.group(0),
                        "label": "DOI",
                        "start_char": m.start(),
                        "end_char": m.end(),
                        "line_text": text,
                        "page_number": p_num,
                        "line_number": l_num,
                        "line_index": l_idx,
                        "source_section_id": sec_id,
                        "source_section_type": sec_type,
                    })

    total_spans_count += len(doc_spans)
    annotations.append({
        "resume_id": doc_id,
        "document_id": doc_id,
        "entity_spans": doc_spans,
    })

with open(OUT_FILE, "w", encoding="utf-8") as f:
    for item in annotations:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"Successfully generated {len(annotations)} resume entity annotation records ({total_spans_count} total entity spans) in '{OUT_FILE}'.")
