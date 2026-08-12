# Experimental Sectioning Design

This branch now carries a separate experimental sectioning stack for the new NLU pipeline.

## Input

- Robust extraction artifacts from `output/extraction/<run_id>/documents/*/pages/*/page.json`
- The sectioning code consumes `final_text` and page metadata directly.

## Core idea

- Start with explainable line-level heading candidates.
- Build annotation-friendly line records before training.
- Keep heading detection, section normalization, and segmentation as separate stages.
- Use a pure-Python linear model and TF-IDF-style sparse features so the stack stays self-contained.

## Outputs

- Annotation-ready JSONL under `data/section_annotations/`
- Section segmentation artifacts that preserve page and line order
- Evaluation helpers for boundary and section classification

## Label space

Canonical labels are intentionally compact:

- education
- experience
- skills
- projects
- publications
- certifications
- research_interests
- achievements
- personal_details
- summary
- references
- responsibilities
- memberships
- patents
- declaration
- other

