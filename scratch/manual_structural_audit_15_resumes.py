import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
run_dir = PROJECT_ROOT / "output" / "sectioning" / "clean_stage3_2_run" / "sectioning_run_20260811T100030Z"

with open(run_dir / "manifest.json", "r", encoding="utf-8") as f:
    manifest = json.load(f)

doc_ids = [d["document_id"] for d in manifest["document_results"]]

# Select 15 diverse resumes across different structural characteristics
selected_15 = [
    doc_ids[0],   # AH_CV_5598e665
    doc_ids[2],   # CV_CSE_ASHISH_SONI_c0c1d28d
    doc_ids[3],   # CV_Chandan_f5f89208
    doc_ids[5],   # CV_RakeshBhatnagar_July_2024_035c91cf
    doc_ids[7],   # Dr_Ashish_Sariwal_CV_1288288c
    doc_ids[9],   # Dr_Karan_Kapur_CV_July_2024_0453ed1a
    doc_ids[12],  # Dr_Sanjay_Singh_CV_0845a90d
    doc_ids[15],  # Prof_A_K_Suresh_CV_2024_f6016e34
    doc_ids[18],  # Resume-09-05-2024_0664eac6
    doc_ids[20],  # Updated_CV-_Dr_Soumen_Mukherjee_6ec3405c
    doc_ids[22],  # Vibha_Vaswani_CV_July_2024_20f32fa1
    doc_ids[25],  # Dibakar_Resume_June_2024_e198e3b3
    doc_ids[28],  # Afzal_Beg_Resume_fa289535
    doc_ids[32],  # Arghya_Maity_CV_2024_e4d9c792
    doc_ids[35],  # Ketan_Mehta_Resume_2024_0219cfa0
]

print("======================================================================")
print("STAGE 3.2 MANUAL STRUCTURAL AUDIT (15 DIVERSE REAL RESUMES)")
print("======================================================================")

audit_results = []

for idx, doc_id in enumerate(selected_15, start=1):
    sec_file = run_dir / "documents" / doc_id / "sections.json"
    if not sec_file.exists():
        continue
    with open(sec_file, "r", encoding="utf-8") as f:
        sec_data = json.load(f)

    sections = sec_data["sections"]
    print(f"\n--- [{idx}/15] Document ID: {doc_id} ---")
    print(f"Total Section Spans: {len(sections)} | Text Coverage Ratio: {sec_data['summary']['text_coverage_ratio']}")

    doc_audit = {
        "doc_id": doc_id,
        "total_spans": len(sections),
        "coverage": sec_data["summary"]["text_coverage_ratio"],
        "spans": []
    }

    for span in sections:
        orig = span["original_heading"]
        norm = span["normalized_heading"]
        stype = span["section_type"]
        lvl = span["level"]
        parent = span["parent_section_id"]
        sid = span["section_id"]
        line_range = f"{span['start_line']}-{span['end_line']}"
        text_prev = span["text"][:60].replace("\n", " ")

        print(f"  [{sid}] orig: {repr(orig):<32} norm: {norm:<16} type: {stype:<10} lvl: {lvl} parent: {str(parent):<12} lines: {line_range}")

        doc_audit["spans"].append({
            "section_id": sid,
            "original_heading": orig,
            "normalized_heading": norm,
            "section_type": stype,
            "level": lvl,
            "parent_section_id": parent,
            "line_range": line_range,
        })
    audit_results.append(doc_audit)

with open(PROJECT_ROOT / "scratch" / "audit_15_resumes_summary.json", "w", encoding="utf-8") as f:
    json.dump(audit_results, f, indent=2, ensure_ascii=False)

print("\nManual structural audit script completed.")
