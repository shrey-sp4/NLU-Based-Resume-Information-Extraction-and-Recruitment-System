from __future__ import annotations

import argparse
from pathlib import Path

from .output import write_annotation_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Experimental sectioning utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    annotations = subparsers.add_parser(
        "build-annotations",
        help="Convert robust extraction run outputs into annotation-friendly line records.",
    )
    annotations.add_argument("--run-dir", type=Path, required=True)
    annotations.add_argument(
        "--output",
        type=Path,
        default=Path("data/section_annotations/section_line_annotations.jsonl"),
    )
    annotations.add_argument(
        "--schema-output",
        type=Path,
        default=Path("data/section_annotations/section_annotation_schema.json"),
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "build-annotations":
        schema = write_annotation_dataset(args.run_dir, args.output, args.schema_output)
        print(f"Wrote annotation dataset to {args.output}")
        print(f"Wrote schema to {args.schema_output}")
        print(f"Records: {schema['record_count']}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

