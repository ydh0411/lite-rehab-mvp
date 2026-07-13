from literehab.dashboard_view import (
    DashboardViewState,
    display_label,
    feedback_presentation,
    status_tone,
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
