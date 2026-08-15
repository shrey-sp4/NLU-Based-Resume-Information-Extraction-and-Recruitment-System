import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

from src.sectioning.pipeline import SectioningPipeline
from scratch.independent_stage3_validator import validate_run
import scratch.evaluate_held_out_and_full_corpus as eval_cor

clean_output = PROJECT_ROOT / "output" / "sectioning" / "clean_stage3_6_run"
if clean_output.exists():
    shutil.rmtree(clean_output)

extraction_run = PROJECT_ROOT / "output" / "extraction" / "run_20260811T100030Z"
pipeline = SectioningPipeline(output_root=clean_output)
pipe_res = pipeline.run_on_extraction(extraction_run)

print("=== ONE-SHOT STAGE 3.6 RUN COMPLETED ===")
print("Run ID:", pipe_res.run_id)
print("Run Dir:", pipe_res.run_dir)

val_res = validate_run(pipe_res.run_dir)
print("\n=== PATH A vs PATH B MATCH CHECK ===")
match = (
    pipe_res.total_processed == val_res["total_processed"] and
    pipe_res.resumes_with_sections == val_res["resumes_with_sections"] and
    pipe_res.top_level_canonical_sections_count == val_res["top_level_canonical_sections_count"] and
    pipe_res.subsections_count == val_res["subsections_count"] and
    pipe_res.custom_sections_count == val_res["custom_sections_count"] and
    pipe_res.preamble_sections_count == val_res["preamble_sections_count"] and
    pipe_res.unmapped_headings_count == val_res["unmapped_headings_count"] and
    pipe_res.repeated_category_occurrences == val_res["repeated_category_occurrences"] and
    pipe_res.duplicate_identical_spans_count == val_res["duplicate_identical_spans_count"] and
    pipe_res.overlapping_spans_count == val_res["overlapping_spans_count"]
)
print("PATH A == PATH B Match?:", match)

# Point evaluator to clean_stage3_6_run
eval_cor.STAGE3_RUN_DIR = pipe_res.run_dir
eval_cor.run_full_evaluation()
