from collections import deque

import numpy as np

from literehab.dashboard_view import (
    DashboardViewState,
    display_label,
    feedback_presentation,
    render_dashboard,
    status_tone,
)
from literehab.telemetry import TelemetrySample


def base_state(**changes):
    values = dict(
        exercise="elbow_flexion",
        repetitions=4,
        feedback="Good repetition",
        mode="Fusion",
        source="multimodal model",
        side="left",
        serial_status="connected",
        camera_status="connected: 0",
        rom_deg=82.5,
        confidence_text="Fusion 0.91",
    )
    values.update(changes)
    return DashboardViewState(**values)


def sample(gx=10.0, gy=20.0, gz=30.0):
    return TelemetrySample(
        1,
        (0.0, 0.0, 1.0),
        (gx, gy, gz),
        "idle",
        0,
        "none",
    )


def test_internal_labels_are_human_readable():
    assert display_label("elbow_flexion") == "Elbow Flexion"
    assert display_label("IMU-only") == "IMU Only"
    assert display_label("") == "--"


def test_device_statuses_have_semantic_tones():
    assert status_tone("connected: 0") == "success"
    assert status_tone("reconnecting: port lost") == "warning"
    assert status_tone("unavailable: 0; retrying") == "danger"
    assert status_tone("disabled") == "muted"


def test_feedback_copy_and_severity_are_normalized():
    assert feedback_presentation("Avoid trunk compensation") == (
        "AVOID TRUNK COMPENSATION",
        "danger",
    )
    assert feedback_presentation("Move more slowly") == (
        "SLOW DOWN",
        "warning",
    )
    assert feedback_presentation("Good repetition") == (
        "GOOD FORM",
        "success",
    )
    assert feedback_presentation("Ready") == ("READY", "muted")
    assert feedback_presentation("New coaching state") == (
        "NEW COACHING STATE",
        "info",
    )


def test_view_state_accepts_missing_optional_metrics():
    state = DashboardViewState(
        exercise="idle",
        repetitions=0,
        feedback="Ready",
        mode="IMU-only",
        source="rule fallback",
        side="left",
        serial_status="connecting",
        camera_status="unavailable",
        rom_deg=None,
        confidence_text="warming up",
    )

    assert state.rom_deg is None


def test_renderer_returns_fixed_nonempty_canvas():
    frame = np.full((600, 800, 3), 80, dtype=np.uint8)

    canvas = render_dashboard(
        frame,
        deque([sample(), sample(-10, 5, 40)]),
        base_state(),
    )

    assert canvas.shape == (720, 1280, 3)
    assert canvas.dtype == np.uint8
    assert np.any(canvas[:64] != canvas[64:128].mean())


def test_renderer_handles_empty_history_and_missing_rom():
    frame = np.zeros((600, 800, 3), dtype=np.uint8)

    canvas = render_dashboard(frame, [], base_state(rom_deg=None))

    assert canvas.shape == (720, 1280, 3)
