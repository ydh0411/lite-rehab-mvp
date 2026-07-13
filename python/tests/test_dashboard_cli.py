import pytest

from run_dashboard import build_parser, resolve_camera_argument


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

