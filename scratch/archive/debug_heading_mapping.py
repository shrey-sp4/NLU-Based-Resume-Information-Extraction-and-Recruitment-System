import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

# 1. Inspect output/sections/*.json for GT resumes with awards
gt_award_docs = [
    "Anibrata_Pal_Resume", "CV-Anurag_Choudhary", "CV_Arghya_Maity",
    "CV_Chandan", "Dr_Akash_Thakkar_CV", "cv_aakash_daiict"
]

print("=== 1. RAW SECTION DATA IN output/sections/*.json FOR GT RESUMES WITH AWARDS ===")
for doc in gt_award_docs:
    sec_file = PROJECT_ROOT / "output" / "sections" / f"{doc}_sections.json"
    if not sec_file.exists():
        sec_file = PROJECT_ROOT / "output" / "sections" / f"{doc}.json"
    if sec_file.exists():
        with open(sec_file, "r", encoding="utf-8") as f:
            sec_dict = json.load(f).get("sections", {})
        print(f"\nDocument: {doc}")
        print("  sections.keys():", list(sec_dict.keys()))
        print("  awards        :", sec_dict.get("awards", "NOT FOUND")[:100] if "awards" in sec_dict else "NOT FOUND")
        print("  achievements  :", sec_dict.get("achievements", "NOT FOUND")[:100] if "achievements" in sec_dict else "NOT FOUND")

# 2. Inspect config/section_normalization_map.json for awards/achievements/memberships
map_file = PROJECT_ROOT / "config" / "section_normalization_map.json"
if map_file.exists():
    with open(map_file, "r", encoding="utf-8") as f:
        norm_map = json.load(f)
    print("\n=== 2. CURRENT HEADING NORMALIZATION MAP (awards/achievements/memberships) ===")
    award_headings = [k for k, v in norm_map.items() if v in ("awards", "achievements")]
    member_headings = [k for k, v in norm_map.items() if v in ("memberships", "societies")]
    print(f"  Headings mapped to 'awards'/'achievements' ({len(award_headings)}):", award_headings[:15])
    print(f"  Headings mapped to 'memberships'/'societies' ({len(member_headings)}):", member_headings[:15])

# 3. Inspect where membership/society content lands in misrouted examples
misrouted_docs = ["Anibrata_Pal_Resume", "CV-Anurag_Choudhary", "Resume_Kritishnu_Sanyal"]
print("\n=== 3. MISROUTING CHECK FOR MEMBERSHIPS / SOCIETIES IN SECTIONS ===")
for doc in misrouted_docs:
    sec_file = PROJECT_ROOT / "output" / "sections" / f"{doc}_sections.json"
    if sec_file.exists():
        with open(sec_file, "r", encoding="utf-8") as f:
            sec_dict = json.load(f).get("sections", {})
        print(f"\nDocument: {doc}")
        for k, v in sec_dict.items():
            if any(term in v.lower() for term in ["member", "society", "ieee", "acm", "fellow", "association"]):
                print(f"  Section '{k}' contains membership terms! ({len(v)} chars)")
                print(f"    Snippet: \"{v[:150]}\"")
