import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

from src.sectioning.pipeline import SectioningPipeline
from scratch.independent_stage3_validator import validate_run
import scratch.evaluate_held_out_and_full_corpus as eval_cor

dev_output = PROJECT_ROOT / "output" / "sectioning" / "dev_stage3_6_run"
if dev_output.exists():
    shutil.rmtree(dev_output)

extraction_run = PROJECT_ROOT / "output" / "extraction" / "run_20260811T100030Z"
pipeline = SectioningPipeline(output_root=dev_output)
pipe_res = pipeline.run_on_extraction(extraction_run)

print("=== STAGE 3.6 DEV SET RUN COMPLETED ===")
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

# Point evaluator to dev_stage3_6_run
eval_cor.STAGE3_RUN_DIR = pipe_res.run_dir

doc_gt, all_docs = eval_cor.load_ground_truth()
predictions = eval_cor.load_stage3_predictions(all_docs)

dev_10_docs = all_docs[:10]
dev_res = eval_cor.eval_subset(dev_10_docs, doc_gt, predictions)

m = dev_res
print("\n======================================================================")
print("STAGE 3.6 DEVELOPMENT SET (10 RESUMES) EVALUATION METRICS")
print("======================================================================")
print(f"True Positives (TP):  {m['tp']}")
print(f"False Positives (FP): {m['fp']}")
print(f"False Negatives (FN): {m['fn']}")
print(f"True Negatives (TN):  {m['tn']}")
print(f"Heading Precision:    {m['precision']:.4f} ({m['precision']*100:.2f}%)")
print(f"Heading Recall:       {m['recall']:.4f} ({m['recall']*100:.2f}%)")
print(f"Heading F1 Score:     {m['f1']:.4f} ({m['f1']*100:.2f}%)")
print(f"Classification Acc:   {m['classification_accuracy']:.4f} ({m['classification_accuracy']*100:.2f}%) [{m['classification_correct']}/{m['classification_total']}]")
print("======================================================================")
