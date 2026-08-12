Annotation reviewer

This folder contains the machine suggestions and the human annotation sidecar.

Files
- `section_line_annotations.jsonl`: immutable machine-generated suggestions (DO NOT MODIFY).
- `human_annotations.jsonl`: sidecar file where human decisions are stored.

Human annotations are NOT machine predictions or ground truth. Use the CLI reviewer to create annotations.

Start reviewer

Run from repository root:

```bash
python src/review_annotations.py
```

Commands while reviewing
- The reviewer presents ONLY machine-suggested heading candidates (records where `machine_suggested_heading` is not null). It will NOT show ordinary non-candidate lines.
- `y` confirm as heading (you will be prompted for canonical section; Enter accepts machine suggestion)
- `n` mark as NOT heading (stored with `section_label: other`)
- `s` skip for now (no annotation saved)
- `q` quit and save progress
- (Enter) accept machine suggestion as heading and section
- `p` print summary statistics

Notes
- The reviewer loads `section_line_annotations.jsonl` and writes `human_annotations.jsonl`.
- Each human annotation record contains only the human decision fields and identifiers; machine fields are not duplicated.
- Skipped candidates remain unresolved and will be presented again on next run.
# Section Annotation Dataset

This folder contains the annotation-friendly dataset generated from the robust extraction run at `output/extraction/run_20260811T100030Z/`.

## Files

- `section_line_annotations.jsonl` - one line record per JSON object
- `section_annotation_schema.json` - field and label schema

## What to annotate

Each JSONL record represents one ordered line from a resume page.

Fill in only these human fields:

- `is_heading`
- `section_label`
- `annotator_notes` if needed

Do not change the machine suggestion fields:

- `machine_suggested_heading`
- `machine_suggested_section`
- `machine_confidence`
- `machine_suggestion_method`
- `machine_review_required`

## Annotation rules

- Use `true` for `is_heading` only when the line is a real section heading.
- Use one of the canonical labels listed in the schema for `section_label`.
- Use `null` for `section_label` when the line is not a heading.
- If a heading does not fit the taxonomy, use `other`.
- Do not treat machine suggestions as ground truth.

## Suggested workflow

1. Review the machine suggestions first.
2. Correct `is_heading` where needed.
3. Assign the canonical `section_label` to heading lines.
4. Leave non-heading content lines as `is_heading = false` and `section_label = null`.
5. Use `annotator_notes` for ambiguous cases only.

