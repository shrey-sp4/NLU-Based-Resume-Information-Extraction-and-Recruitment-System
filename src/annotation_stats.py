from pathlib import Path
import json

M = Path('data/section_annotations/section_line_annotations.jsonl')
H = Path('data/section_annotations/human_annotations.jsonl')

machine = []
with M.open('r', encoding='utf-8') as fh:
	for l in fh:
		if not l.strip():
			continue
		machine.append(json.loads(l))

human_count = 0
if H.exists():
	with H.open('r', encoding='utf-8') as fh:
		human_count = sum(1 for _ in fh if _.strip())

total = len(machine)
heading_suggestions = sum(1 for r in machine if r.get('machine_suggested_heading'))
review_required = sum(1 for r in machine if r.get('machine_review_required'))
print(json.dumps({
	"total_machine_records": total,
	"heading_suggestions": heading_suggestions,
	"review_required": review_required,
	"candidate_count": heading_suggestions + review_required,
	"human_annotations": human_count,
}))
