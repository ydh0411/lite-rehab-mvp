from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardViewState:
    exercise: str
    repetitions: int
    feedback: str
    mode: str
    source: str
    side: str
    serial_status: str
    camera_status: str
    rom_deg: float | None
    confidence_text: str


DISPLAY_LABELS = {
    "idle": "Ready",
    "forearm_rotation": "Forearm Rotation",
    "elbow_flexion": "Elbow Flexion",
    "shoulder_abduction": "Shoulder Abduction",
    "IMU-only": "IMU Only",
}


def display_label(value: str) -> str:
    if not value:
        return "--"
    return DISPLAY_LABELS.get(value, value.replace("_", " ").title())


def status_tone(status: str) -> str:
    text = status.lower()
    if "unavailable" in text or "failure" in text or "not connected" in text:
        return "danger"
    if "reconnecting" in text or "connecting" in text or "retrying" in text:
        return "warning"
    if text == "disabled" or "warming up" in text:
        return "muted"
    if "connected" in text or text == "fusion":
        return "success"
    if "imu-only" in text:
        return "warning"
    return "muted"


def feedback_presentation(feedback: str) -> tuple[str, str]:
    known = {
        "Avoid trunk compensation": ("AVOID TRUNK COMPENSATION", "danger"),
        "Move more slowly": ("SLOW DOWN", "warning"),
        "Increase movement range": ("INCREASE RANGE", "warning"),
        "Good repetition": ("GOOD FORM", "success"),
        "Ready": ("READY", "muted"),
    }
    return known.get(feedback, (feedback.upper() or "READY", "info"))
