from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")


def validate_stage4_run(run_dir: Path) -> Dict[str, Any]:
    print("=== INDEPENDENT STAGE 4 ARTIFACT VALIDATOR (PATH B) ===")
    print(f"Target Directory: {run_dir}\n")

    doc_files = list(run_dir.rglob("extracted_resume.json"))
    print(f"Total Extracted Resume Artifacts Found: {len(doc_files)}")

    total_processed = len(doc_files)
    total_entities = 0
    total_conflicts = 0
    total_offset_valid = 0
    total_offset_checked = 0

    for doc_path in doc_files:
        with open(doc_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        res_id = data.get("resume_id", "")
        prof = data.get("profile", {})
        total_entities += int(data.get("total_entities", 0))
        total_conflicts += int(data.get("conflict_count", 0))

        # Check provenance offset validity
        def check_entity_offset(e_dict: Dict[str, Any]) -> bool:
            if not e_dict:
                return True
            raw_text = e_dict.get("raw_line_text", "")
            val = e_dict.get("value", "")
            st = e_dict.get("start_char", 0)
            en = e_dict.get("end_char", 0)
            if raw_text and val:
                sliced = raw_text[st:en]
                return sliced.lower() == val.lower()
            return True

        # Check personal details
        p_details = prof.get("personal_details", {})
        for k in ("name", "email", "phone", "location"):
            e_obj = p_details.get(k)
            if e_obj:
                total_offset_checked += 1
                if check_entity_offset(e_obj):
                    total_offset_valid += 1

        # Check list entities
        for list_key in ("skills", "projects", "publications", "certifications", "research_interests", "awards", "languages"):
            for e_obj in prof.get(list_key, []):
                total_offset_checked += 1
                if check_entity_offset(e_obj):
                    total_offset_valid += 1

    validity_rate = (total_offset_valid / total_offset_checked) if total_offset_checked > 0 else 1.0

    print("=== STAGE 4 VALIDATION SUMMARY ===")
    print(f"Total Resumes Processed: {total_processed}")
    print(f"Total Extracted Entities: {total_entities}")
    print(f"Total Conflicts Resolved: {total_conflicts}")
    print(f"Offset Validity Rate: {validity_rate:.4f} ({total_offset_valid}/{total_offset_checked})\n")

    return {
        "total_processed": total_processed,
        "total_entities": total_entities,
        "total_conflicts": total_conflicts,
        "offset_validity_rate": round(validity_rate, 4),
    }


if __name__ == "__main__":
    target = PROJECT_ROOT / "output" / "ner" / "stage4_run"
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    validate_stage4_run(target)
