import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

from src.explainability.streamlit_app import run_live_pipeline

test_pdfs = [
    PROJECT_ROOT / "data" / "real_resumes" / "original" / "Curriculum_Vitae_Rakesh.pdf",
    PROJECT_ROOT / "data" / "real_resumes" / "original" / "CV- Amit Parikh (2).pdf"
]

print("======================================================================")
print("LIVE STAGE-BY-STAGE PIPELINE PROCESSING TEST ON 2 NEW RESUMES")
print("======================================================================\n")

for pdf_path in test_pdfs:
    file_bytes = pdf_path.read_bytes()
    res = run_live_pipeline(file_bytes, pdf_path.name)
    
    print(f"======================================================================")
    print(f"FILE: {res['file_name']}")
    print(f"FULLY PARSED STATUS: {res['fully_parsed']}")
    
    if not res['fully_parsed']:
        loss = res['first_stage_loss']
        print(f"\n❌ FIRST STAGE LOSS POINT: {loss['stage']}")
        print(f"   Reason                  : {loss['reason']}")
        print(f"   Raw Text Snippet        : \"{loss['raw_text_snippet'][:180]}...\"")
    else:
        print(f"\n✅ FULLY PARSED: All stages succeeded without information loss.")

    print(f"\n--- Stage 1: Text Extraction ---")
    s1 = res['text_extraction']
    print(f"  Status    : {s1['status']}")
    print(f"  Char Count: {s1['char_count']}")
    if s1['warning']: print(f"  Warning   : {s1['warning']}")

    print(f"\n--- Stage 2: Section Detection ---")
    s2 = res['sectioning']
    print(f"  Status           : {s2['status']}")
    print(f"  Sections Detected: {s2['sections_detected']}")
    if s2['sections_expected_but_missing']:
        print(f"  Missing Expected : {s2['sections_expected_but_missing']}")

    print(f"\n--- Stage 3: Entity Extraction & Explanations ---")
    s3 = res['entity_extraction']
    print(f"  Status        : {s3['status']}")
    print(f"  Total Flags   : {len(s3['flags'])}")
    for f in s3['flags']:
        print(f"    -> [{f['field']}] {f['flag']}: {f['description']}")
    
    print("  Extracted Entities:")
    fr = s3['field_reports']
    print(f"    Name : {fr['personal_name']['value']} (Line: \"{fr['personal_name']['source_line']}\")")
    print(f"    Email: {fr['personal_email']['value']} (Line: \"{fr['personal_email']['source_line']}\")")
    print(f"    Phone: {fr['personal_phone']['value']} (Line: \"{fr['personal_phone']['source_line']}\")")
    
    print(f"    Education Entries ({len(s3['education_report'])}):")
    for e in s3['education_report']:
        print(f"      - Entry {e['entry_index']}: Degree=\"{e['degree']['value']}\" | Inst=\"{e['institution']['value']}\" | Year=\"{e['graduation_year']['value']}\"")
        if e['degree']['reason_if_empty']: print(f"        Reason: {e['degree']['reason_if_empty']}")
        if e['institution']['reason_if_empty']: print(f"        Reason: {e['institution']['reason_if_empty']}")

    print(f"    Experience Entries ({len(s3['experience_report'])}):")
    for e in s3['experience_report']:
        print(f"      - Entry {e['entry_index']}: Title=\"{e['job_title']['value']}\" | Inst=\"{e['institution']['value']}\" | Dates=\"{e['dates']['value']}\"")
        if e['job_title']['reason_if_empty']: print(f"        Reason: {e['job_title']['reason_if_empty']}")

    print(f"    Skills Count: {len(s3['prediction'].get('skills', []))}")
    print(f"    Projects Count: {len(s3['prediction'].get('projects', []))}")
    print("\n" + "="*70 + "\n")
