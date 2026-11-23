"""Command-line entry point for the ophthalmic quantification package."""

from __future__ import annotations

import argparse
from pathlib import Path

from .atlas import write_medical_metric_atlas
from .examples import write_example_bundle
from .lesion_annotation import quantify_annotation_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    examples = subparsers.add_parser("build-examples", help="build the nonclinical synthetic metric bundle")
    examples.add_argument("--output-dir", type=Path, required=True)
    atlas = subparsers.add_parser("build-atlas", help="build the self-contained ophthalmic medical metric atlas")
    atlas.add_argument("--output", type=Path, required=True)
    lesion = subparsers.add_parser(
        "quantify-dr-annotations",
        help="convert outcome-blind DR lesion annotation JSON into E046 measurements",
    )
    lesion.add_argument("--annotations", type=Path, required=True)
    lesion.add_argument("--fov-mask", type=Path, required=True)
    lesion.add_argument("--disc-mask", type=Path)
    lesion.add_argument("--fovea-mask", type=Path)
    lesion.add_argument("--vessel-mask", type=Path)
    lesion.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build-examples":
        outputs = write_example_bundle(args.output_dir)
        for name, path in outputs.items():
            print(f"{name}={path.resolve()}")
    if args.command == "build-atlas":
        print(f"atlas={write_medical_metric_atlas(args.output).resolve()}")
    if args.command == "quantify-dr-annotations":
        output = quantify_annotation_file(
            args.annotations,
            fov_mask_path=args.fov_mask,
            disc_mask_path=args.disc_mask,
            fovea_mask_path=args.fovea_mask,
            vessel_mask_path=args.vessel_mask,
            output_path=args.output,
        )
        print(f"dr_measurements={output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
