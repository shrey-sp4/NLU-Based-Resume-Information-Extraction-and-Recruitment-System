# Evaluation Outputs

This folder contains safe, pushable evaluation outputs for the NLU-Based Resume Information Extraction and Recruitment System.

The raw resumes, extracted resume text, section-wise JSON files, and candidate-level profile files are intentionally not included because they may contain personal information such as names, emails, phone numbers, education details, and publication records.

## Files

- `pipeline_run_summary.csv`  
  Overall stage-wise summary of the pipeline.

- `extraction_metrics.csv`  
  Aggregate metrics for PDF text extraction.

- `section_quality_metrics.csv`  
  Aggregate metrics for section segmentation quality checks.

- `profile_quality_metrics.csv`  
  Aggregate metrics for candidate profile extraction quality checks.

- `sample_field_metrics.csv`  
  Field-level accuracy metrics from manually verified sample ground truth.  
  This file is generated after sample ground truth evaluation.

- `sample_error_report.csv`  
  Error report from manually verified sample ground truth.  
  This file is generated after sample ground truth evaluation.

## Privacy Note

Only aggregate or anonymized result files should be committed to this folder.
Do not commit raw resumes, extracted full text, candidate profiles containing personal details, or section JSON files.
