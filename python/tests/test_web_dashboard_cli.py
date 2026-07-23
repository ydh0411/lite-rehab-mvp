from pathlib import Path

import pytest

import run_web_dashboard


def test_web_launcher_defaults_to_local_only():
    args = run_web_dashboard.build_parser().parse_args([])

    assert args.host == "127.0.0.1"
    assert args.web_port == 8000
    assert args.port == "auto"
    assert args.camera_source == "auto"
    assert args.side == "right"
    assert args.mobile is False


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


def test_mobile_cli_builds_persistent_pairing_config(tmp_path):
    token_file = tmp_path / "token"
    args = run_web_dashboard.build_parser().parse_args([
        "--mobile",
        "--host", "0.0.0.0",
        "--advertised-host", "192.168.1.8",
        "--mobile-token-file", str(token_file),
    ])

    config, payload = run_web_dashboard.mobile_access_from_args(args)

    assert config is not None
    assert payload is not None
    assert config.token == token_file.read_text(encoding="utf-8").strip()
    assert payload["base_url"] == "http://192.168.1.8:8000"
    assert payload["pairing_token"] == config.token


def test_mobile_mode_rejects_loopback_binding():
    args = run_web_dashboard.build_parser().parse_args([
        "--mobile",
        "--host", "127.0.0.1",
    ])

    with pytest.raises(
        SystemExit,
        match="mobile mode requires a LAN bind address",
    ):
        run_web_dashboard.mobile_access_from_args(args)


def test_non_mobile_mode_has_no_pairing_payload():
    args = run_web_dashboard.build_parser().parse_args([])

    config, payload = run_web_dashboard.mobile_access_from_args(args)

    assert config is None
    assert payload is None
