import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

from src.explainability.streamlit_app import run_live_pipeline

test_pdfs = [
    PROJECT_ROOT / "data" / "real_resumes" / "original" / "Anibrata Pal_Resume.pdf",
    PROJECT_ROOT / "data" / "real_resumes" / "original" / "Dr. Akash Thakkar_CV.pdf",
    PROJECT_ROOT / "data" / "real_resumes" / "original" / "Doyel-Mukherjee-25.06.2024.pdf",
    PROJECT_ROOT / "data" / "real_resumes" / "original" / "Dibakar_Resume_June_2024.pdf"
]

print("======================================================================")
print("LIVE STAGE-BY-STAGE PIPELINE TEST ON 4 NEW RESUMES")
print("======================================================================\n")

for pdf_path in test_pdfs:
    file_bytes = pdf_path.read_bytes()
    res = run_live_pipeline(file_bytes, pdf_path.name)
    
    print(f"======================================================================")
    print(f"FILE: {res['file_name']}")
    print(f"FULLY PARSED STATUS: {res['fully_parsed']}")
    
    if not res['fully_parsed']:
        loss = res['first_stage_loss']
        print(f"\n❌ PARSE INCOMPLETE / STAGE LOSS: {loss['stage']}")
        print(f"   Reason          : {loss['reason']}")
        print(f"   Snippet         : \"{loss['raw_text_snippet'][:180]}...\"")
    else:
        print(f"\n✅ FULLY PARSED: All text extracted cleanly, sectioned, and structured!")

    print(f"\n--- Stage 1: Text Extraction ---")
    s1 = res['text_extraction']
    print(f"  Status: {s1['status']} | Char Count: {s1['char_count']}")

    print(f"\n--- Stage 2: Section Detection ---")
    s2 = res['sectioning']
    print(f"  Status           : {s2['status']}")
    print(f"  Sections Detected: {s2['sections_detected']}")

    print(f"\n--- Stage 3: Entity Extraction & Explanations ---")
    s3 = res['entity_extraction']
    fr = s3['field_reports']
    print(f"  Name : {fr['personal_name']['value']} (Line: \"{fr['personal_name']['source_line']}\")")
    print(f"  Email: {fr['personal_email']['value']} (Line: \"{fr['personal_email']['source_line']}\")")
    print(f"  Phone: {fr['personal_phone']['value']} (Line: \"{fr['personal_phone']['source_line']}\")")

    skills_list = s3['prediction'].get('skills', [])
    print(f"\n  Skills Section ({len(skills_list)} items extracted):")
    for sk_idx, sk_item in enumerate(skills_list[:8]):
        print(f"    [{sk_idx+1}] \"{sk_item}\"")

    print("\n" + "="*70 + "\n")
