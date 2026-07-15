from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np


CANVAS_SIZE = (1280, 720)
COLORS = {
    "background": (31, 24, 14),
    "surface": (46, 37, 24),
    "surface_alt": (60, 49, 32),
    "border": (82, 68, 44),
    "text": (244, 247, 250),
    "muted_text": (166, 174, 184),
    "primary": (212, 184, 62),
    "primary_soft": (116, 92, 34),
    "success": (126, 202, 84),
    "info": (224, 168, 67),
    "warning": (66, 184, 245),
    "danger": (83, 83, 239),
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


def _resolve_color(
    color: str | int | tuple[int, int, int],
) -> int | tuple[int, int, int]:
    return COLORS[color] if isinstance(color, str) else color


def _rounded_rect(
    image: np.ndarray,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    color: str | int | tuple[int, int, int],
    radius: int,
) -> None:
    x1, y1 = top_left
    x2, y2 = bottom_right
    radius = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    resolved = _resolve_color(color)
    cv2.rectangle(image, (x1 + radius, y1), (x2 - radius, y2), resolved, -1)
    cv2.rectangle(image, (x1, y1 + radius), (x2, y2 - radius), resolved, -1)
    for center in (
        (x1 + radius, y1 + radius),
        (x2 - radius, y1 + radius),
        (x1 + radius, y2 - radius),
        (x2 - radius, y2 - radius),
    ):
        cv2.circle(image, center, radius, resolved, -1, cv2.LINE_AA)


def _rounded_card(
    image: np.ndarray,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    fill: str = "surface",
    border: str = "border",
    radius: int = 16,
) -> None:
    _rounded_rect(image, top_left, bottom_right, border, radius)
    x1, y1 = top_left
    x2, y2 = bottom_right
    _rounded_rect(
        image,
        (x1 + 1, y1 + 1),
        (x2 - 1, y2 - 1),
        fill,
        max(0, radius - 1),
    )


def _rounded_overlay(
    image: np.ndarray,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    color: str | tuple[int, int, int],
    alpha: float,
    radius: int = 14,
) -> None:
    overlay = image.copy()
    _rounded_rect(overlay, top_left, bottom_right, color, radius)
    cv2.addWeighted(overlay, alpha, image, 1.0 - alpha, 0, image)


def _text(
    image: np.ndarray,
    text: str,
    origin: tuple[int, int],
    scale: float,
    color: str | tuple[int, int, int] = "text",
    thickness: int = 1,
) -> None:
    cv2.putText(
        image,
        text,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        _resolve_color(color),
        thickness,
        cv2.LINE_AA,
    )


def _chip(
    image: np.ndarray,
    x: int,
    y: int,
    label: str,
    status: str,
) -> int:
    tone = status_tone(status)
    text_width = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1
    )[0][0]
    width = max(104, 31 + text_width)
    _rounded_card(
        image,
        (x, y),
        (x + width, y + 28),
        fill="surface_alt",
        border="border",
        radius=14,
    )
    cv2.circle(image, (x + 14, y + 14), 4, COLORS[tone], -1, cv2.LINE_AA)
    _text(image, label, (x + 25, y + 18), 0.38, "muted_text")
    return width


def confidence_fraction(text: str) -> float | None:
    match = re.search(r"(?:^|\s)(0(?:\.\d+)?|1(?:\.0+)?)\s*$", text)
    if match is None:
        return None
    return min(1.0, max(0.0, float(match.group(1))))


def _draw_arc(
    image: np.ndarray,
    center: tuple[int, int],
    radius: int,
    fraction: float,
    tone: str,
    thickness: int = 8,
) -> None:
    fraction = min(1.0, max(0.0, fraction))
    cv2.ellipse(
        image,
        center,
        (radius, radius),
        0,
        135,
        405,
        COLORS["surface_alt"],
        thickness,
        cv2.LINE_AA,
    )
    cv2.ellipse(
        image,
        center,
        (radius, radius),
        0,
        135,
        135 + int(270 * fraction),
        COLORS[tone],
        thickness,
        cv2.LINE_AA,
    )


def _draw_repetition_card(
    image: np.ndarray,
    state: DashboardViewState,
) -> None:
    _rounded_card(image, (840, 80), (1260, 224))
    _text(image, "SESSION REPS", (862, 108), 0.4, "muted_text")
    _draw_arc(image, (1182, 152), 46, 0.82, "primary", thickness=7)
    _text(image, str(state.repetitions), (866, 190), 2.25, "text", 4)
    _text(image, "COMPLETED", (1118, 157), 0.34, "muted_text")


def _draw_rom_card(image: np.ndarray, rom_deg: float | None) -> None:
    _rounded_card(image, (840, 346), (1048, 454))
    _text(image, "RANGE OF MOTION", (856, 372), 0.34, "muted_text")
    fraction = (
        0.0
        if rom_deg is None
        else min(1.0, max(0.0, rom_deg / 180.0))
    )
    _draw_arc(image, (1006, 410), 25, fraction, "primary", thickness=5)
    value = "--" if rom_deg is None else f"{rom_deg:.1f} deg"
    _text(image, value, (856, 426), 0.66, "text", 2)


def _draw_model_card(image: np.ndarray, confidence_text: str) -> None:
    _rounded_card(image, (1058, 346), (1260, 454))
    _text(image, "MODEL STATUS", (1074, 372), 0.34, "muted_text")
    _text(image, confidence_text, (1074, 408), 0.43, "text")
    cv2.line(
        image,
        (1074, 431),
        (1242, 431),
        COLORS["surface_alt"],
        6,
        cv2.LINE_AA,
    )
    fraction = confidence_fraction(confidence_text)
    if fraction is not None:
        end_x = 1074 + int(168 * fraction)
        cv2.line(
            image,
            (1074, 431),
            (end_x, 431),
            COLORS["success"],
            6,
            cv2.LINE_AA,
        )


def _rounded_blit(
    canvas: np.ndarray,
    source: np.ndarray,
    top_left: tuple[int, int],
    radius: int,
) -> None:
    x, y = top_left
    height, width = source.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    _rounded_rect(mask, (0, 0), (width - 1, height - 1), 255, radius)
    target = canvas[y:y + height, x:x + width]
    cv2.copyTo(source, mask, target)


def _draw_exercise_badge(image: np.ndarray, exercise: str) -> None:
    label = display_label(exercise).upper()
    text_width = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1
    )[0][0]
    right = 48 + text_width + 28
    _rounded_overlay(image, (38, 98), (right, 136), "background", 0.82, 19)
    cv2.circle(image, (54, 117), 4, COLORS["primary"], -1, cv2.LINE_AA)
    _text(image, label, (66, 122), 0.48, "text", 1)


def _draw_feedback_banner(image: np.ndarray, feedback: str) -> None:
    message, tone = feedback_presentation(feedback)
    _rounded_overlay(image, (38, 602), (802, 662), "background", 0.86, 14)
    cv2.line(image, (48, 616), (48, 648), COLORS[tone], 5, cv2.LINE_AA)
    _text(image, "COACHING", (64, 623), 0.32, "muted_text")
    _text(image, message, (64, 648), 0.65, "text", 2)


def draw_gyro_chart(panel: np.ndarray, history) -> None:
    height, width = panel.shape[:2]
    _text(panel, "IMU GYROSCOPE", (10, 21), 0.38, "muted_text")
    plot_left, plot_right = 10, width - 10
    plot_top, plot_bottom = 34, height - 25
    for fraction in (0.0, 0.5, 1.0):
        y = int(plot_top + fraction * (plot_bottom - plot_top))
        cv2.line(
            panel,
            (plot_left, y),
            (plot_right, y),
            COLORS["surface_alt"],
            1,
        )

    samples = list(history)
    axis_colors = (COLORS["danger"], COLORS["success"], COLORS["primary"])
    if len(samples) >= 2:
        values = np.asarray(
            [sample.gyro_dps for sample in samples],
            dtype=np.float32,
        )
        scale = max(100.0, float(np.abs(values).max()))
        center_y = (plot_top + plot_bottom) / 2
        amplitude = (plot_bottom - plot_top) * 0.43
        for axis, color in enumerate(axis_colors):
            points = []
            for index, value in enumerate(values[:, axis]):
                x = int(
                    plot_left
                    + index * (plot_right - plot_left) / max(1, len(values) - 1)
                )
                y = int(center_y - value * amplitude / scale)
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
        x = 12 + index * 48
        cv2.circle(panel, (x, height - 8), 3, color, -1, cv2.LINE_AA)
        _text(panel, label, (x + 8, height - 4), 0.3, "muted_text")


def _camera_panel(frame: np.ndarray, camera_status: str) -> np.ndarray:
    if status_tone(camera_status) == "success":
        return cv2.resize(frame, (800, 600))

    panel = np.full((600, 800, 3), COLORS["surface"], dtype=np.uint8)
    cv2.circle(panel, (400, 260), 30, COLORS["surface_alt"], -1, cv2.LINE_AA)
    cv2.line(
        panel,
        (386, 260),
        (414, 260),
        COLORS["muted_text"],
        2,
        cv2.LINE_AA,
    )
    _text(panel, "CAMERA UNAVAILABLE", (266, 320), 0.72, "text", 2)
    _text(
        panel,
        "Continuing with IMU-only feedback",
        (258, 354),
        0.46,
        "muted_text",
    )
    return panel


def render_dashboard(
    frame: np.ndarray,
    history,
    state: DashboardViewState,
) -> np.ndarray:
    width, height = CANVAS_SIZE
    canvas = np.full((height, width, 3), COLORS["background"], dtype=np.uint8)

    _text(canvas, "LiteRehab", (20, 37), 0.78, "text", 2)
    _text(canvas, "MOTION INTELLIGENCE", (20, 56), 0.31, "muted_text")
    chip_x = 700
    for label, status in (
        ("SERIAL", state.serial_status),
        ("CAMERA", state.camera_status),
        (display_label(state.mode).upper(), state.mode),
    ):
        chip_x += _chip(canvas, chip_x, 22, label, status) + 8

    camera_panel = _camera_panel(frame, state.camera_status)
    _rounded_card(canvas, (19, 79), (821, 681), fill="background", radius=19)
    _rounded_blit(canvas, camera_panel, (20, 80), radius=18)
    _draw_exercise_badge(canvas, state.exercise)
    _draw_feedback_banner(canvas, state.feedback)

    _draw_repetition_card(canvas, state)
    _rounded_card(canvas, (840, 236), (1260, 334))
    _text(canvas, "CURRENT EXERCISE", (860, 262), 0.34, "muted_text")
    _text(
        canvas,
        display_label(state.exercise),
        (860, 298),
        0.66,
        "text",
        2,
    )
    context = (
        f"{display_label(state.side)} side  /  "
        f"{display_label(state.source)}"
    )
    _text(canvas, context, (860, 320), 0.34, "muted_text")

    _draw_rom_card(canvas, state.rom_deg)
    _draw_model_card(canvas, state.confidence_text)

    _rounded_card(canvas, (840, 466), (1260, 664))
    chart = canvas[476:652, 850:1250]
    draw_gyro_chart(chart, history)
    _text(
        canvas,
        "B  BASELINE     R  RESET ROM     Q  QUIT",
        (900, 694),
        0.36,
        "muted_text",
    )
    return canvas
