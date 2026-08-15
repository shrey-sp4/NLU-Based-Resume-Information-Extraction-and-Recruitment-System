from __future__ import annotations

import argparse
from pathlib import Path

from .output import write_annotation_dataset
from .pipeline import SectioningPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage 3 Section Detection & Normalization utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    annotations = subparsers.add_parser(
        "build-annotations",
        help="Convert extraction run outputs into annotation-friendly line records.",
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

    stage3 = subparsers.add_parser(
        "run-stage3",
        help="Run Stage 3 Section Detection & Normalization over Stage 2 extraction output.",
    )
    stage3.add_argument("--run-dir", type=Path, required=True, help="Path to Stage 2 extraction run directory.")
    stage3.add_argument(
        "--output-root",
        type=Path,
        default=Path("output/sectioning"),
        help="Root output directory for Stage 3 artifacts.",
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

    if args.command == "run-stage3":
        pipeline = SectioningPipeline(output_root=args.output_root)
        result = pipeline.run_on_extraction(args.run_dir)
        print(f"Stage 3 Sectioning Run Completed: {result.run_id}")
        print(f"Total processed: {result.total_processed}")
        print(f"Resumes with sections: {result.resumes_with_sections}")
        print(f"Resumes without sections: {result.resumes_without_sections}")
        print(f"Text coverage ratio: {result.avg_text_coverage_ratio:.4f}")
        print(f"Section frequencies: {result.section_frequencies}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
