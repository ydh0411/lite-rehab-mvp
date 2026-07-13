from types import SimpleNamespace
from pathlib import Path

import pytest
import torch

import run_dashboard
from literehab.cnn import build_model
from literehab.telemetry import TelemetrySample
from run_dashboard import (
    OptionalCNN,
    build_parser,
    choose_port,
    resolve_camera_argument,
)


def test_legacy_camera_argument_remains_supported():
    args = build_parser().parse_args(["--camera", "2"])

    assert resolve_camera_argument(args) == 2


def test_camera_source_takes_precedence_and_accepts_rtsp():
    args = build_parser().parse_args(
        [
            "--camera",
            "0",
            "--camera-source",
            "rtsp://10.0.0.2:8554/live",
        ]
    )

    assert resolve_camera_argument(args) == "rtsp://10.0.0.2:8554/live"


def test_camera_source_accepts_auto():
    args = build_parser().parse_args(["--camera-source", "auto"])

    assert resolve_camera_argument(args) == "auto"


def test_invalid_camera_source_exits_with_clear_message():
    args = build_parser().parse_args(["--camera-source", "http://bad"])

    with pytest.raises(SystemExit, match="camera source must be"):
        resolve_camera_argument(args)


def test_auto_port_prefers_receiver_usbmodem_over_wearable_usbserial(monkeypatch):
    monkeypatch.setattr(
        run_dashboard.list_ports,
        "comports",
        lambda: [
            SimpleNamespace(device="/dev/cu.usbserial-130"),
            SimpleNamespace(device="/dev/cu.usbmodem1101"),
        ],
    )

    assert choose_port("auto") == "/dev/cu.usbmodem1101"


def test_dashboard_uses_shipped_imu_model_by_default():
    args = build_parser().parse_args([])

    assert args.model == (
        Path(run_dashboard.__file__).resolve().parent
        / "models"
        / "imu_cnnbigru.pt"
    )


def test_missing_imu_model_fails_loudly(tmp_path):
    missing = tmp_path / "missing.pt"

    with pytest.raises(FileNotFoundError, match="IMU CNN checkpoint not found"):
        OptionalCNN(missing)


def test_loaded_imu_model_reports_warmup_instead_of_not_loaded(tmp_path):
    checkpoint = tmp_path / "model.pt"
    labels = ["elbow_flexion", "forearm_rotation", "idle"]
    model = build_model(len(labels), arch="cnn_1d")
    torch.save({
        "state_dict": model.state_dict(),
        "labels": labels,
        "mean": torch.zeros(6),
        "std": torch.ones(6),
        "window_size": 100,
        "arch": "cnn_1d",
        "heldout_subject": "test",
        "accuracy": 0.0,
    }, checkpoint)

    cnn = OptionalCNN(checkpoint)

    assert cnn.status_text(None) == "warming up (0/100)"


def test_public_action_model_uses_rule_gate_for_idle(tmp_path):
    checkpoint = tmp_path / "model.pt"
    labels = ["elbow_flexion", "forearm_rotation", "shoulder_abduction"]
    model = build_model(len(labels), arch="cnn_1d")
    torch.save({
        "state_dict": model.state_dict(),
        "labels": labels,
        "mean": torch.zeros(6),
        "std": torch.ones(6),
        "window_size": 100,
        "arch": "cnn_1d",
        "heldout_subject": "test",
        "accuracy": 0.0,
    }, checkpoint)
    cnn = OptionalCNN(checkpoint)
    sample = TelemetrySample(0, (0.0, 0.0, 1.0), (0.0, 0.0, 0.0),
                             "idle", 0, "none")

    prediction = None
    for _ in range(100):
        prediction = cnn.update(sample)

    assert prediction == "idle"


def test_headless_smoke_test_validates_model_before_passing(tmp_path, monkeypatch):
    missing = tmp_path / "missing.pt"
    monkeypatch.setattr(
        "sys.argv",
        ["run_dashboard.py", "--headless-smoke-test", "--model", str(missing)],
    )

    with pytest.raises(FileNotFoundError, match="IMU CNN checkpoint not found"):
        run_dashboard.main()
