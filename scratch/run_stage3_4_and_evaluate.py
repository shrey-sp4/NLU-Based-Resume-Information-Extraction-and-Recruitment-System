import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

from src.sectioning.pipeline import SectioningPipeline
from scratch.independent_stage3_validator import validate_run
import scratch.evaluate_stage3_ground_truth as eval_gt

clean_output = PROJECT_ROOT / "output" / "sectioning" / "clean_stage3_4_run"
if clean_output.exists():
    shutil.rmtree(clean_output)

extraction_run = PROJECT_ROOT / "output" / "extraction" / "run_20260811T100030Z"
pipeline = SectioningPipeline(output_root=clean_output)
pipe_res = pipeline.run_on_extraction(extraction_run)

print("=== CLEAN-ROOM STAGE 3.4 RUN COMPLETED ===")
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

# Point evaluator to clean_stage3_4_run
eval_gt.STAGE3_RUN_DIR = pipe_res.run_dir
print("\n=== EVALUATING STAGE 3.4 AGAINST FROZEN BASELINE ===")
eval_res = eval_gt.evaluate()

m = eval_res["metrics"]
print("\n======================================================================")
print("STAGE 3.2 FROZEN BASELINE VS STAGE 3.4 IMPROVED COMPARISON")
print("======================================================================")
print(f"Metric                       Baseline (3.2)   Improved (3.4)   Delta")
print(f"----------------------------------------------------------------------")
print(f"True Positives (TP)          98               {m['true_positives']:<16} {m['true_positives'] - 98:+d}")
print(f"False Positives (FP)         43               {m['false_positives']:<16} {m['false_positives'] - 43:+d}")
print(f"False Negatives (FN)         39               {m['false_negatives']:<16} {m['false_negatives'] - 39:+d}")
print(f"Heading Precision            0.6950 (69.50%)  {m['heading_precision']:.4f} ({m['heading_precision']*100:.2f}%)   {m['heading_precision'] - 0.6950:+.4f}")
print(f"Heading Recall               0.7153 (71.53%)  {m['heading_recall']:.4f} ({m['heading_recall']*100:.2f}%)   {m['heading_recall'] - 0.7153:+.4f}")
print(f"Heading F1 Score             0.7050 (70.50%)  {m['heading_f1']:.4f} ({m['heading_f1']*100:.2f}%)   {m['heading_f1'] - 0.7050:+.4f}")
print(f"Classification Accuracy      0.7347 (73.47%)  {m['classification_accuracy']:.4f} ({m['classification_accuracy']*100:.2f}%)   {m['classification_accuracy'] - 0.7347:+.4f}")
print("======================================================================")
