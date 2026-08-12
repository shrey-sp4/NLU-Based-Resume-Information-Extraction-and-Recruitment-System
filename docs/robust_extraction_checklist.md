# Robust PDF Extraction Checklist

Scope: 40 real resume PDFs in `data/real_resumes/original/`. Ignore `data/real_resumes/original/.gitkeep`.

- [ ] Create a fresh extraction package under `src/extraction/`.
- [ ] Keep the old extraction scripts untouched.
- [ ] Discover only the 40 PDF resumes as inputs.
- [ ] Build a run manifest with hashes, file sizes, and document IDs.
- [ ] Preflight each PDF for page count, encryption, and basic readability.
- [ ] Try native text extraction first on every page.
- [ ] Fall back to an independent native extractor if the first one is weak.
- [ ] Try layout-aware extraction when text order or spacing matters.
- [ ] OCR scanned or image-only pages at page level.
- [ ] Record every attempt, fallback, and reason in audit files.
- [ ] Write final page outputs and document summaries under `output/extraction/<run_id>/`.
- [ ] Route unresolved or low-confidence pages to review.
- [ ] Produce a run-level review queue.
- [ ] Verify the pipeline end to end on a small sample before scaling to all 40 PDFs.

