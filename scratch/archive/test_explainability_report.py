import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

from src.explainability.report_builder import build_explainability_report

test_resumes = [
    "A_Mitesh_CV.json",             # Has Ground Truth
    "AH_CV.json",                    # Unseen resume without GT
    "CV_CSE_ASHISH_SONI.json"        # Unseen resume without GT
]

print("======================================================================")
print("END-TO-END TESTING EXPLAINABILITY REPORT BUILDER ON 3 RESUMES")
print("======================================================================\n")

for r_name in test_resumes:
    report = build_explainability_report(r_name)
    print(f"=== REPORT FOR: {report['resume_name']} (Ground Truth Available: {report['has_ground_truth']}) ===")
    print(f"Total Flags Triggered: {report['total_flags']}")
    for f in report["flags"]:
        print(f"  -> [{f['field']}] {f['flag']}: {f['description']}")
        
    print("\n--- Field-Level Explanations ---")
    fields = report["field_reports"]
    
    # Personal Name
    fn = fields["personal_name"]
    print(f"  Name        : {fn['value']}")
    print(f"    Source Line: \"{fn['source_line']}\"")
    if fn["reason_if_empty"]: print(f"    Reason Empty: {fn['reason_if_empty']}")
    if fn["gt_match_status"] != "NO_GT": print(f"    GT Match    : {fn['gt_match_status']} (Gold: \"{fn['gt_value']}\")")

    # Personal Email
    fe = fields["personal_email"]
    print(f"  Email       : {fe['value']}")
    print(f"    Source Line: \"{fe['source_line']}\"")
    if fe["reason_if_empty"]: print(f"    Reason Empty: {fe['reason_if_empty']}")

    # Personal Phone
    fp = fields["personal_phone"]
    print(f"  Phone       : {fp['value']}")
    print(f"    Source Line: \"{fp['source_line']}\"")
    if fp["reason_if_empty"]: print(f"    Reason Empty: {fp['reason_if_empty']}")

    # Education Entries
    fedu = fields["education"]
    print(f"  Education Entries Count: {fedu['entry_count']}")
    for entry in fedu["entries"]:
        print(f"    Entry {entry['entry_index']}: Degree=\"{entry['degree']['value']}\" | Inst=\"{entry['institution']['value']}\" | Year=\"{entry['graduation_year']['value']}\"")
        if entry["degree"]["reason_if_empty"]: print(f"      Degree Empty Reason: {entry['degree']['reason_if_empty']}")
        if entry["institution"]["reason_if_empty"]: print(f"      Inst Empty Reason  : {entry['institution']['reason_if_empty']}")

    # Experience Entries
    fexp = fields["experience"]
    print(f"  Experience Entries Count: {fexp['entry_count']}")
    for entry in fexp["entries"]:
        print(f"    Entry {entry['entry_index']}: Title=\"{entry['job_title']['value']}\" | Inst=\"{entry['institution']['value']}\" | Dates=\"{entry['dates']['value']}\"")
        if entry["job_title"]["reason_if_empty"]: print(f"      Title Empty Reason: {entry['job_title']['reason_if_empty']}")
        if entry["institution"]["reason_if_empty"]: print(f"      Inst Empty Reason : {entry['institution']['reason_if_empty']}")

    print("\n" + "="*70 + "\n")
