from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


CANVAS_SIZE = (1280, 720)
COLORS = {
    "background": (18, 22, 30),
    "surface": (28, 34, 45),
    "surface_alt": (35, 43, 56),
    "text": (240, 244, 248),
    "muted_text": (156, 165, 178),
    "success": (105, 200, 91),
    "info": (232, 156, 65),
    "warning": (65, 181, 245),
    "danger": (79, 79, 239),
    "muted": (112, 120, 132),
}


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


def _text(
    image: np.ndarray,
    text: str,
    origin: tuple[int, int],
    scale: float,
    color: str | tuple[int, int, int] = "text",
    thickness: int = 1,
) -> None:
    resolved = COLORS[color] if isinstance(color, str) else color
    cv2.putText(
        image,
        text,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        resolved,
        thickness,
        cv2.LINE_AA,
    )


def _card(
    image: np.ndarray,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
) -> None:
    cv2.rectangle(image, top_left, bottom_right, COLORS["surface"], -1)


def _chip(
    image: np.ndarray,
    x: int,
    y: int,
    label: str,
    status: str,
) -> int:
    tone = status_tone(status)
    text_width = cv2.getTextSize(
        label,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        1,
    )[0][0]
    width = max(112, 32 + text_width)
    cv2.rectangle(
        image,
        (x, y),
        (x + width, y + 30),
        COLORS["surface_alt"],
        -1,
    )
    cv2.circle(image, (x + 14, y + 15), 5, COLORS[tone], -1)
    _text(image, label, (x + 26, y + 20), 0.42)
    return width


def draw_gyro_chart(panel: np.ndarray, history) -> None:
    panel[:] = COLORS["surface"]
    height, width = panel.shape[:2]
    _text(panel, "IMU GYROSCOPE", (16, 25), 0.48, "muted_text")
    plot_left, plot_right = 16, width - 16
    plot_top, plot_bottom = 40, height - 34
    for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = int(plot_top + fraction * (plot_bottom - plot_top))
        cv2.line(
            panel,
            (plot_left, y),
            (plot_right, y),
            COLORS["surface_alt"],
            1,
        )

    samples = list(history)
    axis_colors = ((90, 110, 245), (105, 200, 91), (232, 156, 65))
    if len(samples) >= 2:
        values = np.asarray(
            [sample.gyro_dps for sample in samples],
            dtype=np.float32,
        )
        scale = max(100.0, float(np.abs(values).max()))
        center = (plot_top + plot_bottom) / 2
        amplitude = (plot_bottom - plot_top) * 0.44
        for axis, color in enumerate(axis_colors):
            points = []
            for index, value in enumerate(values[:, axis]):
                x = int(
                    plot_left
                    + index * (plot_right - plot_left) / max(1, len(values) - 1)
                )
                y = int(center - value * amplitude / scale)
                points.append((x, y))
            cv2.polylines(
                panel,
                [np.asarray(points)],
                False,
                color,
                2,
                cv2.LINE_AA,
            )

    for index, (label, color) in enumerate(zip("XYZ", axis_colors)):
        x = 18 + index * 52
        cv2.circle(panel, (x, height - 14), 4, color, -1)
        _text(panel, label, (x + 9, height - 10), 0.35, "muted_text")


def _camera_panel(frame: np.ndarray, camera_status: str) -> np.ndarray:
    if "connected" in camera_status.lower():
        return cv2.resize(frame, (800, 600))

    panel = np.full((600, 800, 3), COLORS["surface"], dtype=np.uint8)
    _text(panel, "CAMERA UNAVAILABLE", (230, 278), 0.88, thickness=2)
    _text(panel, "Continuing with IMU-only feedback", (226, 316), 0.54,
          "muted_text")
    return panel


def render_dashboard(
    frame: np.ndarray,
    history,
    state: DashboardViewState,
) -> np.ndarray:
    width, height = CANVAS_SIZE
    canvas = np.full(
        (height, width, 3),
        COLORS["background"],
        dtype=np.uint8,
    )
    _text(canvas, "LiteRehab", (20, 39), 0.82, thickness=2)
    _text(canvas, "LIVE REHABILITATION", (20, 58), 0.35, "muted_text")

    chip_x = 675
    for label, status in (
        ("SERIAL", state.serial_status),
        ("CAMERA", state.camera_status),
        (display_label(state.mode).upper(), state.mode),
    ):
        chip_x += _chip(canvas, chip_x, 22, label, status) + 10

    canvas[80:680, 20:820] = _camera_panel(frame, state.camera_status)
    shade = canvas.copy()
    cv2.rectangle(shade, (36, 96), (390, 146), COLORS["background"], -1)
    cv2.addWeighted(shade, 0.78, canvas, 0.22, 0, canvas)
    _text(
        canvas,
        display_label(state.exercise).upper(),
        (54, 130),
        0.68,
        thickness=2,
    )

    message, tone = feedback_presentation(state.feedback)
    banner = canvas.copy()
    cv2.rectangle(banner, (36, 606), (804, 664), COLORS[tone], -1)
    cv2.addWeighted(banner, 0.88, canvas, 0.12, 0, canvas)
    _text(canvas, message, (58, 644), 0.75, thickness=2)

    _card(canvas, (840, 80), (1260, 218))
    _text(canvas, "REPETITIONS", (862, 110), 0.45, "muted_text")
    _text(canvas, str(state.repetitions), (858, 194), 2.35, thickness=4)

    _card(canvas, (840, 230), (1260, 340))
    _text(canvas, "CURRENT EXERCISE", (862, 258), 0.42, "muted_text")
    _text(
        canvas,
        display_label(state.exercise),
        (862, 297),
        0.72,
        thickness=2,
    )
    context = (
        f"{display_label(state.side)} side  |  "
        f"{display_label(state.source)}"
    )
    _text(canvas, context, (862, 325), 0.4, "muted_text")

    _card(canvas, (840, 352), (1044, 438))
    _card(canvas, (1056, 352), (1260, 438))
    _text(canvas, "RANGE OF MOTION", (856, 378), 0.36, "muted_text")
    rom = "--" if state.rom_deg is None else f"{state.rom_deg:.1f} deg"
    _text(canvas, rom, (856, 417), 0.7, thickness=2)
    _text(canvas, "MODEL STATUS", (1072, 378), 0.36, "muted_text")
    _text(canvas, state.confidence_text, (1072, 417), 0.45)

    chart = canvas[450:646, 840:1260]
    draw_gyro_chart(chart, history)
    _text(
        canvas,
        "B  Baseline    R  Reset ROM    Q  Quit",
        (870, 684),
        0.42,
        "muted_text",
    )
    return canvas
