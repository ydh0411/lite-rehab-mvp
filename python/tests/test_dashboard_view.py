from collections import deque

import numpy as np

from literehab.dashboard_view import (
    COLORS,
    DashboardViewState,
    _draw_arc,
    _draw_model_card,
    _draw_repetition_card,
    _draw_rom_card,
    _rounded_card,
    confidence_fraction,
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


def test_clinical_theme_has_distinct_surface_border_and_primary_colors():
    assert COLORS["background"][0] > COLORS["background"][2]
    assert COLORS["surface"] != COLORS["background"]
    assert COLORS["border"] != COLORS["surface"]
    assert COLORS["primary"] != COLORS["success"]


def test_rounded_card_preserves_corner_and_draws_border_and_fill():
    image = np.zeros((48, 48, 3), dtype=np.uint8)

    _rounded_card(image, (4, 4), (43, 43), radius=10)

    assert tuple(image[4, 4]) == (0, 0, 0)
    assert tuple(image[4, 20]) == COLORS["border"]
    assert tuple(image[24, 24]) == COLORS["surface"]


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


def test_confidence_fraction_only_accepts_terminal_probability():
    assert confidence_fraction("Fusion 0.91") == 0.91
    assert confidence_fraction("Fusion 1.00") == 1.0
    assert confidence_fraction("warming up (30/100)") is None
    assert confidence_fraction("disabled") is None


def test_draw_arc_clamps_fraction_and_marks_the_canvas():
    image = np.full((120, 120, 3), COLORS["surface"], dtype=np.uint8)

    _draw_arc(image, (60, 60), 38, 1.8, "primary", thickness=6)

    assert np.any(image != np.asarray(COLORS["surface"], dtype=np.uint8))


def test_metric_cards_render_with_missing_values():
    canvas = np.full((720, 1280, 3), COLORS["background"], dtype=np.uint8)

    _draw_repetition_card(canvas, base_state())
    _draw_rom_card(canvas, None)
    _draw_model_card(canvas, "warming up (30/100)")

    assert np.any(canvas[80:454, 840:1260] != np.asarray(COLORS["background"]))


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


def test_polished_composition_uses_rounded_camera_and_right_rail():
    frame = np.full((600, 800, 3), 90, dtype=np.uint8)

    canvas = render_dashboard(
        frame,
        [sample(), sample(-10, 5, 40)],
        base_state(),
    )

    assert tuple(canvas[80, 20]) == COLORS["background"]
    assert tuple(canvas[79, 60]) == COLORS["border"]
    assert tuple(canvas[100, 860]) == COLORS["surface"]
    assert np.any(
        canvas[470:650, 850:1250] != np.asarray(COLORS["surface"])
    )


def test_feedback_banner_uses_accent_strip_not_solid_danger_fill():
    frame = np.full((600, 800, 3), 90, dtype=np.uint8)

    canvas = render_dashboard(
        frame,
        [],
        base_state(feedback="Avoid trunk compensation"),
    )

    assert tuple(canvas[632, 48]) == COLORS["danger"]
    assert tuple(canvas[632, 100]) != COLORS["danger"]


def test_camera_failure_keeps_designed_empty_state():
    frame = np.full((600, 800, 3), 255, dtype=np.uint8)

    canvas = render_dashboard(
        frame,
        [],
        base_state(camera_status="not connected"),
    )

    assert tuple(canvas[300, 400]) == COLORS["surface"]
    assert np.any(
        canvas[330:360, 250:600] != np.asarray(COLORS["surface"])
    )
