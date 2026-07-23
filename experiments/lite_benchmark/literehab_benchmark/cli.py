from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .figures import generate_figures
from .prepare_mri import prepare_mri_windows
from .runner import run_benchmark


DEFAULT_CONFIG = Path(__file__).parents[1] / "configs" / "rtx5060_laptop.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lightweight LiteRehab RGB-pose/IMU benchmark"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare-mri", description="Convert official mRI precomputed pose features"
    )
    prepare.add_argument("--features", type=Path, required=True)
    prepare.add_argument("--annotations", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--labels", nargs="+", default=None)
    prepare.add_argument("--window-size", type=int, default=100)
    prepare.add_argument("--stride", type=int, default=50)

    run = subparsers.add_parser("run", description="Train the small benchmark suite")
    run.add_argument("--dataset", type=Path, required=True)
    run.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    run.add_argument("--output", type=Path, default=Path("results"))
    run.add_argument("--holdout-subjects", nargs="+", default=None)
    run.add_argument("--device", default="auto")

    figures = subparsers.add_parser(
        "figures", description="Export figures4papers-style PNG and PDF figures"
    )
    figures.add_argument("--results", type=Path, required=True)
    figures.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare-mri":
        count = prepare_mri_windows(
            feature_dir=args.features,
            annotation_path=args.annotations,
            output_path=args.output,
            window_size=args.window_size,
            stride=args.stride,
            selected_labels=tuple(args.labels) if args.labels else None,
        )
        print(f"prepared_windows={count} output={args.output}")
        return 0
    if args.command == "run":
        summary = run_benchmark(
            dataset_path=args.dataset,
            config=load_config(args.config),
            output_dir=args.output,
            holdout_subjects=(
                tuple(args.holdout_subjects) if args.holdout_subjects else None
            ),
            device_name=args.device,
        )
        print(f"summary={summary}")
        return 0
    output = args.output or args.results / "figures"
    paths = generate_figures(args.results, output)
    print(f"generated_figures={len(paths)} output={output}")
    return 0
