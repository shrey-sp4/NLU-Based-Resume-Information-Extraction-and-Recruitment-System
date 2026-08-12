from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import ExtractionConfig
from .pipeline import ExtractionPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the new resume PDF extraction pipeline.")
    parser.add_argument("--input-root", type=Path, default=ExtractionConfig().input_root)
    parser.add_argument("--output-root", type=Path, default=ExtractionConfig().output_root)
    parser.add_argument("--run-prefix", type=str, default="run")
    parser.add_argument("--summary-only", action="store_true", help="Print the run directory without verbose logging.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = ExtractionConfig(
        input_root=args.input_root,
        output_root=args.output_root,
        run_prefix=args.run_prefix,
    )
    run_dir = ExtractionPipeline(config).run()
    if args.summary_only:
        print(run_dir)
    else:
        print(json.dumps({"run_dir": str(run_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

