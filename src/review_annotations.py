import sys
from pathlib import Path
from annotation_reviewer import (
    load_machine_records,
    load_human_annotations,
    save_human_annotations,
    generate_queue,
    get_context,
    create_annotation_from_machine,
    CANONICAL_SECTIONS,
    summarize,
    make_key,
)


DEFAULT_MACHINE_PATH = Path("data/section_annotations/section_line_annotations.jsonl")
DEFAULT_HUMAN_PATH = Path("data/section_annotations/human_annotations.jsonl")


def display_context(ctx):
    for marker, r in ctx:
        tag = "   "
        if marker == "candidate":
            tag = ">>>"
        print(f"[{r.get('resume_id')} p{r.get('page_number')} l{r.get('line_number')}] {tag} {r.get('text')}")


def prompt_section(default: str) -> str:
    prompt = f"Section [{default}]: "
    val = input(prompt).strip()
    if val == "":
        return default
    if val not in CANONICAL_SECTIONS:
        print("Invalid section. Falling back to 'other'.")
        return "other"
    return val


def run_cli(machine_path: Path = DEFAULT_MACHINE_PATH, human_path: Path = DEFAULT_HUMAN_PATH):
    machine_path = Path(machine_path)
    human_path = Path(human_path)
    if not machine_path.exists():
        print(f"machine file not found: {machine_path}")
        return 2
    machine_records = load_machine_records(machine_path)
    human_annotations = load_human_annotations(human_path)
    queue = generate_queue(machine_records, human_annotations)
    print(f"Loaded {len(machine_records)} machine records; {len(queue)} machine-suggested heading candidates to review.")

    i = 0
    while i < len(queue):
        rec = queue[i]
        # find index of rec in machine_records to generate context
        try:
            idx = next(j for j, r in enumerate(machine_records) if make_key(r) == make_key(rec))
        except StopIteration:
            idx = None
        print("\n---\n")
        print(f"Resume: {rec.get('resume_id')}  Page: {rec.get('page_number')}  Line: {rec.get('line_number')}")
        if idx is not None:
            ctx = get_context(machine_records, idx, before=4, after=4)
            display_context(ctx)
        print("\nMachine prediction:")
        print(f"  Heading: {bool(rec.get('machine_suggested_heading'))}")
        print(f"  Section: {rec.get('machine_suggested_section')}")
        print(f"  Confidence: {rec.get('machine_confidence')}")
        print(f"  Method: {rec.get('machine_suggestion_method')}")

        cmd = input("[y/n/s/q/p] (Enter accepts machine section): ").strip()
        if cmd == "":
            # accept machine suggestion as heading
            is_heading = True if rec.get('machine_suggested_heading') else True
            section = rec.get('machine_suggested_section') or "other"
            ann = create_annotation_from_machine(rec, is_heading, section, "", "annotated")
            human_annotations[ann["_key"]] = ann
            save_human_annotations(human_path, human_annotations)
            i += 1
            continue
        if cmd.lower() == "y":
            default = rec.get('machine_suggested_section') or "other"
            section = prompt_section(default)
            ann = create_annotation_from_machine(rec, True, section, "", "annotated")
            human_annotations[ann["_key"]] = ann
            save_human_annotations(human_path, human_annotations)
            i += 1
            continue
        if cmd.lower() == "n":
            ann = create_annotation_from_machine(rec, False, "other", "", "annotated")
            human_annotations[ann["_key"]] = ann
            save_human_annotations(human_path, human_annotations)
            i += 1
            continue
        if cmd.lower() == "s":
            print("Skipped for now.")
            i += 1
            continue
        if cmd.lower() == "p":
            stats = summarize(queue[i:], human_annotations)
            print(json.dumps(stats, indent=2))
            continue
        if cmd.lower() == "q":
            print("Quitting and saving progress.")
            save_human_annotations(human_path, human_annotations)
            return 0
        print("Unknown command")

    print("All candidates in queue processed (skipped items are not saved).")
    save_human_annotations(human_path, human_annotations)
    return 0


if __name__ == "__main__":
    mp = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MACHINE_PATH
    hp = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_HUMAN_PATH
    sys.exit(run_cli(mp, hp))
