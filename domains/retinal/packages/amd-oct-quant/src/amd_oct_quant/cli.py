"""Command-line interface for reusable quantification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .metrics2d import extract_2d_metrics, metric_dictionary
from .palette import load_amd_sd_combined_png
from .pipeline import extract_amd_sd_manifest
from .qc import validate_metric_table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="amd-oct-quant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    one = subparsers.add_parser("one", help="decode and quantify one AMD-SD combined PNG")
    one.add_argument("image")

    batch = subparsers.add_parser("extract-amd-sd", help="extract a manifest to Parquet")
    batch.add_argument("--manifest", required=True)
    batch.add_argument("--project-root", required=True)
    batch.add_argument("--output", required=True)
    batch.add_argument("--qc-output", required=True)

    dictionary = subparsers.add_parser("metric-dictionary", help="write the package metric dictionary")
    dictionary.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "one":
        _, labels, info = load_amd_sd_combined_png(args.image)
        print(json.dumps({"decoder": info.to_dict(), "metrics": extract_2d_metrics(labels)}, indent=2))
        return
    if args.command == "metric-dictionary":
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        metric_dictionary().to_csv(output, index=False)
        return
    table = extract_amd_sd_manifest(args.manifest, project_root=args.project_root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(output, index=False)
    qc = validate_metric_table(table)
    qc_path = Path(args.qc_output)
    qc_path.parent.mkdir(parents=True, exist_ok=True)
    qc_path.write_text(json.dumps(qc, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
