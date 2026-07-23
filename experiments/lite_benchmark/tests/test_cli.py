from literehab_benchmark.cli import build_parser


def test_cli_exposes_prepare_run_and_figures_commands():
    parser = build_parser()

    prepare = parser.parse_args([
        "prepare-mri", "--features", "features", "--annotations", "split.json",
        "--output", "data.npz", "--labels", "elbow", "shoulder",
    ])
    run = parser.parse_args([
        "run", "--dataset", "data.npz", "--output", "results",
        "--holdout-subjects", "S04",
    ])
    figures = parser.parse_args(["figures", "--results", "results"])

    assert prepare.command == "prepare-mri"
    assert prepare.labels == ["elbow", "shoulder"]
    assert run.command == "run"
    assert run.holdout_subjects == ["S04"]
    assert figures.command == "figures"
