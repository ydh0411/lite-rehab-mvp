from pathlib import Path

import run_web_dashboard


def test_web_launcher_defaults_to_local_only():
    args = run_web_dashboard.build_parser().parse_args([])

    assert args.host == "127.0.0.1"
    assert args.web_port == 8000
    assert args.port == "auto"
    assert args.camera_source == "auto"
    assert args.side == "right"


def test_web_launcher_builds_runtime_config(tmp_path):
    args = run_web_dashboard.build_parser().parse_args([
        "--sessions-dir", str(tmp_path),
        "--camera-source", "2",
        "--side", "left",
        "--model", "none",
    ])

    config = run_web_dashboard.config_from_args(args)

    assert config.sessions_dir == tmp_path
    assert config.camera_source == 2
    assert config.side == "left"
    assert config.model is None


def test_fixture_headless_smoke_test_passes(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_web_dashboard.py",
            "--fixture",
            "--headless-smoke-test",
            "--sessions-dir", str(tmp_path),
            "--frontend-dir", str(Path("missing-frontend")),
        ],
    )

    run_web_dashboard.main()

    assert "LiteRehab web dashboard smoke test: PASS" in capsys.readouterr().out
