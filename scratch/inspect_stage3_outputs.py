import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

run_dir = Path("output/sectioning/sectioning_run_20260811T100030Z")
with open(run_dir / "manifest.json", "r", encoding="utf-8") as f:
    manifest = json.load(f)

print("=== MANIFEST SUMMARY ===")
print("Total processed:", manifest["total_processed"])
print("Resumes with sections:", manifest["resumes_with_sections"])
print("Resumes without sections:", manifest["resumes_without_sections"])
print("Avg text coverage ratio:", manifest["avg_text_coverage_ratio"])
print("Unmapped headings count:", manifest["unmapped_headings_count"])
print("Duplicate sections count:", manifest["duplicate_sections_count"])
print("Review required count:", manifest["review_required_count"])

print("\nSection frequencies:")
for cat, count in manifest["section_frequencies"].items():
    print(f"  {cat:<22}: {count}")

print("\n=== DETAILED RESUME INSPECTION (10 SAMPLE RESUMES) ===")
for doc_info in manifest["document_results"][:10]:
    doc_id = doc_info["document_id"]
    sec_file = run_dir / "documents" / doc_id / "sections.json"
    with open(sec_file, "r", encoding="utf-8") as f:
        sec_data = json.load(f)
    print(f"\n--- Doc: {doc_id} ---")
    print("  Total section spans:", len(sec_data["sections"]))
    print("  Text coverage ratio:", sec_data["summary"]["text_coverage_ratio"])
    for span in sec_data["sections"]:
        orig = repr(span["original_heading"])
        norm = span["normalized_heading"]
        sid = span["section_id"]
        lines_str = f"{span['start_line']}-{span['end_line']}"
        text_preview = repr(span["text"][:70])
        print(f"    [{sid}] orig: {orig:<35} norm: {norm:<18} lines: {lines_str:<8} preview: {text_preview}")
