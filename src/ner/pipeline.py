from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .extractors import HybridEntityExtractor
from .models import (
    CandidateProfile,
    EducationEntry,
    ExperienceEntry,
    ExtractedEntity,
    PersonalDetails,
    Stage4ExtractionResult,
)


class Stage4NERPipeline:
    def __init__(
        self,
        output_root: Optional[Path] = None,
        extractor: Optional[HybridEntityExtractor] = None,
    ) -> None:
        self.output_root = output_root or Path("output/ner/stage4_run")
        self.extractor = extractor or HybridEntityExtractor()

    def process_sections_artifact(self, sections_json_path: Path) -> Stage4ExtractionResult:
        with open(sections_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        res_id = data.get("resume_id", sections_json_path.parent.name)
        doc_id = data.get("document_id", res_id)
        run_id = "ner_run_20260811T100030Z"

        all_extracted: List[ExtractedEntity] = []

        for section in data.get("sections", []):
            sec_id = section["section_id"]
            sec_type = section["normalized_heading"]

            for l_rec in section.get("lines", []):
                text = l_rec.get("text", "").strip()
                p_num = l_rec["page_number"]
                l_num = l_rec["line_number"]
                l_idx = l_rec["line_index"]

                if not text or l_rec.get("is_heading", False):
                    continue

                # Layer 1: Deterministic Regex
                det_entities = self.extractor.extract_deterministic_entities(
                    text, p_num, l_num, l_idx, sec_id, sec_type
                )
                all_extracted.extend(det_entities)

                # Layer 2: Gazetteer Engine
                gaz_entities = self.extractor.extract_gazetteer_entities(
                    text, p_num, l_num, l_idx, sec_id, sec_type
                )
                all_extracted.extend(gaz_entities)

                # Layer 3: Learned CRF NER Engine
                crf_entities = self.extractor.extract_crf_entities(
                    text, p_num, l_num, l_idx, sec_id, sec_type
                )
                all_extracted.extend(crf_entities)

        # Conflict resolution
        resolved_entities, conflict_cnt = self.extractor.resolve_conflicts(all_extracted)
        resolved_entities = self.extractor.recover_entity_span_boundaries(resolved_entities)

        # Construct Candidate Profile
        profile = CandidateProfile(
            resume_id=res_id,
            document_id=doc_id,
            source_run_id=run_id,
        )

        for entity in resolved_entities:
            e_type = entity.entity_type
            if e_type == "name" and not profile.personal_details.name:
                profile.personal_details.name = entity
            elif e_type == "email" and not profile.personal_details.email:
                profile.personal_details.email = entity
            elif e_type == "phone" and not profile.personal_details.phone:
                profile.personal_details.phone = entity
            elif e_type == "location" and not profile.personal_details.location:
                profile.personal_details.location = entity
            elif e_type == "skill":
                profile.skills.append(entity)
            elif e_type == "degree":
                profile.education_entries.append(EducationEntry(degree=entity, source_section_id=entity.source_section_id))
            elif e_type == "title":
                profile.experience_entries.append(ExperienceEntry(job_title=entity, source_section_id=entity.source_section_id))
            elif e_type == "publication" or e_type == "doi":
                profile.publications.append(entity)

        res = Stage4ExtractionResult(
            resume_id=res_id,
            document_id=doc_id,
            run_id=run_id,
            profile=profile,
            total_entities=len(resolved_entities),
            conflict_count=conflict_cnt,
        )

        # Write output JSON artifact
        out_doc_dir = self.output_root / "documents" / doc_id
        out_doc_dir.mkdir(parents=True, exist_ok=True)
        out_json_path = out_doc_dir / "extracted_resume.json"
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(res.to_dict(), f, indent=2, ensure_ascii=False)

        return res
