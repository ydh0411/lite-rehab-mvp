# LiteRehab Dashboard Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the existing 1280 x 720 OpenCV dashboard into a presentation-ready clinical rehabilitation interface without changing its runtime behavior.

**Architecture:** Keep `python/literehab/dashboard_view.py` as the complete presentation boundary and add focused drawing helpers for rounded surfaces, semantic overlays, arcs, and confidence bars. Keep all sensor, inference, repetition, synchronization, logging, and keyboard behavior in `python/run_dashboard.py`; only the pose overlay colors change there.

**Tech Stack:** Python 3, OpenCV (`cv2`), NumPy, pytest, existing LiteRehab telemetry dataclasses.

## Global Constraints

- Preserve the fixed 1280 x 720 OpenCV canvas.
- Preserve camera, pose, telemetry, inference, synchronization, CSV logging, and keyboard behavior.
- Use no new UI framework, font, image asset, or runtime dependency.
- Keep interface copy concise and in English because OpenCV's built-in font remains in use.
- Use deep navy and blue-gray surfaces; reserve green for healthy/correct, amber for coaching warnings, red for unsafe or failed states, and cool gray for idle or unavailable states.
- Do not invent a repetition target or a new clinical decision.
- `B`, `R`, `Q`, and `Esc` retain their current behavior.

---

### Task 1: Clinical Theme and Rounded Drawing Primitives

**Files:**
- Modify: `python/literehab/dashboard_view.py:9-132`
- Test: `python/tests/test_dashboard_view.py:5-63`

**Interfaces:**
- Consumes: Existing BGR `np.ndarray` canvases and semantic color names.
- Produces: `COLORS`, `_rounded_rect(image, top_left, bottom_right, color, radius) -> None`, `_rounded_card(image, top_left, bottom_right, fill="surface", border="border", radius=16) -> None`, and `_rounded_overlay(image, top_left, bottom_right, color, alpha, radius=14) -> None`.

- [ ] **Step 1: Write failing theme and rounded-surface tests**

Update the import block and add these tests to `python/tests/test_dashboard_view.py`:

```python
from literehab.dashboard_view import (
    COLORS,
    DashboardViewState,
    _rounded_card,
    display_label,
    feedback_presentation,
    render_dashboard,
    status_tone,
)


def test_clinical_theme_has_distinct_surface_border_and_primary_colors():
    assert COLORS["background"][0] > COLORS["background"][2]
    assert COLORS["surface"] != COLORS["background"]
    assert COLORS["border"] != COLORS["surface"]
    assert COLORS["primary"] != COLORS["success"]


def test_rounded_card_preserves_corner_and_draws_border_and_fill():
    image = np.zeros((48, 48, 3), dtype=np.uint8)

    _rounded_card(image, (4, 4), (43, 43), radius=10)

    assert tuple(image[4, 4]) == (0, 0, 0)
    assert tuple(image[4, 14]) == COLORS["border"]
    assert tuple(image[24, 24]) == COLORS["surface"]
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `cd python && pytest -q tests/test_dashboard_view.py -k "clinical_theme or rounded_card"`

Expected: collection fails because `_rounded_card` is not defined, or assertions fail because `border` and `primary` do not exist.

- [ ] **Step 3: Replace the palette and implement rounded primitives**

Replace `COLORS`, remove `_card`, and add the following color and shape helpers in `python/literehab/dashboard_view.py`. Keep `display_label`, `status_tone`, and `feedback_presentation` unchanged.

```python
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


def _resolve_color(
    color: str | int | tuple[int, int, int],
) -> int | tuple[int, int, int]:
    return COLORS[color] if isinstance(color, str) else color


def _rounded_rect(
    image: np.ndarray,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    color: str | tuple[int, int, int],
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
```

Replace `_text` so every component uses the same color resolver:

```python
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
```

Replace `_chip` with this quieter rounded version:

```python
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
```

- [ ] **Step 4: Run the complete dashboard-view test module**

Run: `cd python && pytest -q tests/test_dashboard_view.py`

Expected: all dashboard-view tests pass.

- [ ] **Step 5: Commit the visual foundation**

```bash
git add python/literehab/dashboard_view.py python/tests/test_dashboard_view.py
git commit -m "feat: add polished dashboard visual primitives"
```

---

### Task 2: ROM, Repetition, and Confidence Visualizations

**Files:**
- Modify: `python/literehab/dashboard_view.py:135-182`
- Test: `python/tests/test_dashboard_view.py`

**Interfaces:**
- Consumes: `rom_deg: float | None`, `confidence_text: str`, a BGR panel, and semantic tone names.
- Produces: `confidence_fraction(text: str) -> float | None`, `_draw_arc(image, center, radius, fraction, tone, thickness=8) -> None`, `_draw_repetition_card(image, state) -> None`, `_draw_rom_card(image, rom_deg) -> None`, and `_draw_model_card(image, confidence_text) -> None`.

- [ ] **Step 1: Write failing parsing and metric-rendering tests**

Add `confidence_fraction` and `_draw_arc` to the test import block, then add:

```python
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
    frame = np.full((600, 800, 3), 70, dtype=np.uint8)

    canvas = render_dashboard(
        frame,
        [],
        base_state(rom_deg=None, confidence_text="warming up (30/100)"),
    )

    assert canvas.shape == (720, 1280, 3)
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run: `cd python && pytest -q tests/test_dashboard_view.py -k "confidence_fraction or draw_arc or metric_cards"`

Expected: collection fails because `confidence_fraction` and `_draw_arc` are not defined.

- [ ] **Step 3: Implement probability parsing and arc rendering**

Add `import re` near the top of `dashboard_view.py`, then add:

```python
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
        image, center, (radius, radius), 0, 135, 405,
        COLORS["surface_alt"], thickness, cv2.LINE_AA,
    )
    cv2.ellipse(
        image, center, (radius, radius), 0, 135,
        135 + int(270 * fraction), COLORS[tone], thickness, cv2.LINE_AA,
    )
```

- [ ] **Step 4: Implement the three metric components**

Add these helpers to `dashboard_view.py`:

```python
def _draw_repetition_card(image: np.ndarray, state: DashboardViewState) -> None:
    _rounded_card(image, (840, 80), (1260, 224))
    _text(image, "SESSION REPS", (862, 108), 0.4, "muted_text")
    _draw_arc(image, (1182, 152), 46, 0.82, "primary", thickness=7)
    _text(image, str(state.repetitions), (866, 190), 2.25, "text", 4)
    _text(image, "COMPLETED", (1118, 157), 0.34, "muted_text")


def _draw_rom_card(image: np.ndarray, rom_deg: float | None) -> None:
    _rounded_card(image, (840, 346), (1048, 454))
    _text(image, "RANGE OF MOTION", (856, 372), 0.34, "muted_text")
    fraction = 0.0 if rom_deg is None else min(1.0, max(0.0, rom_deg / 180.0))
    _draw_arc(image, (1006, 410), 25, fraction, "primary", thickness=5)
    value = "--" if rom_deg is None else f"{rom_deg:.1f} deg"
    _text(image, value, (856, 426), 0.66, "text", 2)


def _draw_model_card(image: np.ndarray, confidence_text: str) -> None:
    _rounded_card(image, (1058, 346), (1260, 454))
    _text(image, "MODEL STATUS", (1074, 372), 0.34, "muted_text")
    _text(image, confidence_text, (1074, 408), 0.43, "text")
    cv2.line(image, (1074, 431), (1242, 431), COLORS["surface_alt"], 6,
             cv2.LINE_AA)
    fraction = confidence_fraction(confidence_text)
    if fraction is not None:
        end_x = 1074 + int(168 * fraction)
        cv2.line(image, (1074, 431), (end_x, 431), COLORS["success"], 6,
                 cv2.LINE_AA)
```

- [ ] **Step 5: Run the dashboard-view tests**

Run: `cd python && pytest -q tests/test_dashboard_view.py`

Expected: all dashboard-view tests pass.

- [ ] **Step 6: Commit the metric visualizations**

```bash
git add python/literehab/dashboard_view.py python/tests/test_dashboard_view.py
git commit -m "feat: add rehabilitation metric visuals"
```

---

### Task 3: Compose the Polished Dashboard Hierarchy

**Files:**
- Modify: `python/literehab/dashboard_view.py:135-272`
- Test: `python/tests/test_dashboard_view.py`

**Interfaces:**
- Consumes: `DashboardViewState`, a camera `np.ndarray`, and an iterable of `TelemetrySample` values.
- Produces: `_rounded_blit(canvas, source, top_left, radius) -> None`, `_draw_feedback_banner(canvas, feedback) -> None`, and the final `render_dashboard(frame, history, state) -> np.ndarray`.

- [ ] **Step 1: Write failing hierarchy and semantic-banner tests**

Add these tests to `python/tests/test_dashboard_view.py`:

```python
def test_polished_composition_uses_rounded_camera_and_right_rail():
    frame = np.full((600, 800, 3), 90, dtype=np.uint8)

    canvas = render_dashboard(frame, [sample(), sample(-10, 5, 40)], base_state())

    assert tuple(canvas[80, 20]) == COLORS["background"]
    assert tuple(canvas[79, 40]) == COLORS["border"]
    assert tuple(canvas[100, 860]) == COLORS["surface"]
    assert np.any(canvas[470:650, 850:1250] != np.asarray(COLORS["surface"]))


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
    assert np.any(canvas[330:350, 250:600] != np.asarray(COLORS["surface"]))
```

- [ ] **Step 2: Run the hierarchy tests and verify they fail**

Run: `cd python && pytest -q tests/test_dashboard_view.py -k "polished_composition or feedback_banner or camera_failure"`

Expected: at least the rounded-corner or banner accent assertions fail against the old composition.

- [ ] **Step 3: Add rounded image placement and coaching overlays**

Add these helpers to `dashboard_view.py`:

```python
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
```

Replace `_camera_panel` with:

```python
def _camera_panel(frame: np.ndarray, camera_status: str) -> np.ndarray:
    if status_tone(camera_status) == "success":
        return cv2.resize(frame, (800, 600))

    panel = np.full((600, 800, 3), COLORS["surface"], dtype=np.uint8)
    cv2.circle(panel, (400, 260), 30, COLORS["surface_alt"], -1, cv2.LINE_AA)
    cv2.line(panel, (386, 260), (414, 260), COLORS["muted_text"], 2,
             cv2.LINE_AA)
    _text(panel, "CAMERA UNAVAILABLE", (266, 320), 0.72, "text", 2)
    _text(panel, "Continuing with IMU-only feedback", (258, 354), 0.46,
          "muted_text")
    return panel
```

- [ ] **Step 4: Update the gyro chart for the new card interior**

Replace `draw_gyro_chart` with this version. It deliberately does not fill the panel so the parent rounded card remains intact.

```python
def draw_gyro_chart(panel: np.ndarray, history) -> None:
    height, width = panel.shape[:2]
    _text(panel, "IMU GYROSCOPE", (10, 21), 0.38, "muted_text")
    plot_left, plot_right = 10, width - 10
    plot_top, plot_bottom = 34, height - 25
    for fraction in (0.0, 0.5, 1.0):
        y = int(plot_top + fraction * (plot_bottom - plot_top))
        cv2.line(panel, (plot_left, y), (plot_right, y), COLORS["surface_alt"], 1)

    samples = list(history)
    axis_colors = (COLORS["danger"], COLORS["success"], COLORS["primary"])
    if len(samples) >= 2:
        values = np.asarray([sample.gyro_dps for sample in samples], dtype=np.float32)
        scale = max(100.0, float(np.abs(values).max()))
        center_y = (plot_top + plot_bottom) / 2
        amplitude = (plot_bottom - plot_top) * 0.43
        for axis, color in enumerate(axis_colors):
            points = []
            for index, value in enumerate(values[:, axis]):
                x = int(plot_left + index * (plot_right - plot_left)
                        / max(1, len(values) - 1))
                y = int(center_y - value * amplitude / scale)
                points.append((x, y))
            cv2.polylines(panel, [np.asarray(points)], False, color, 2,
                          cv2.LINE_AA)

    for index, (label, color) in enumerate(zip("XYZ", axis_colors)):
        x = 12 + index * 48
        cv2.circle(panel, (x, height - 8), 3, color, -1, cv2.LINE_AA)
        _text(panel, label, (x + 8, height - 4), 0.3, "muted_text")
```

- [ ] **Step 5: Replace `render_dashboard` with the selected hierarchy**

Use this complete function:

```python
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
    _rounded_blit(canvas, camera_panel, (20, 80), radius=18)
    _rounded_card(canvas, (19, 79), (821, 681), fill="background", radius=19)
    _rounded_blit(canvas, camera_panel, (20, 80), radius=18)
    _draw_exercise_badge(canvas, state.exercise)
    _draw_feedback_banner(canvas, state.feedback)

    _draw_repetition_card(canvas, state)
    _rounded_card(canvas, (840, 236), (1260, 334))
    _text(canvas, "CURRENT EXERCISE", (860, 262), 0.34, "muted_text")
    _text(canvas, display_label(state.exercise), (860, 298), 0.66, "text", 2)
    context = f"{display_label(state.side)} side  /  {display_label(state.source)}"
    _text(canvas, context, (860, 320), 0.34, "muted_text")

    _draw_rom_card(canvas, state.rom_deg)
    _draw_model_card(canvas, state.confidence_text)

    _rounded_card(canvas, (840, 466), (1260, 664))
    chart = canvas[476:652, 850:1250]
    draw_gyro_chart(chart, history)
    _text(canvas, "B  BASELINE     R  RESET ROM     Q  QUIT", (900, 694),
          0.36, "muted_text")
    return canvas
```

- [ ] **Step 6: Run the focused dashboard-view tests**

Run: `cd python && pytest -q tests/test_dashboard_view.py`

Expected: all dashboard-view tests pass.

- [ ] **Step 7: Commit the page composition**

```bash
git add python/literehab/dashboard_view.py python/tests/test_dashboard_view.py
git commit -m "feat: compose polished rehabilitation dashboard"
```

---

### Task 4: Pose Overlay and End-to-End Verification

**Files:**
- Modify: `python/run_dashboard.py:38-45,154-164`
- Modify: `python/tests/test_dashboard_cli.py`
- Verify: `python/literehab/dashboard_view.py`
- Verify: `python/tests/test_dashboard_view.py`

**Interfaces:**
- Consumes: Existing MediaPipe landmark objects with `x`, `y`, and `visibility` attributes.
- Produces: `POSE_LINE_COLOR`, `POSE_JOINT_COLOR`, and the existing `draw_pose(frame, landmarks) -> None` with updated presentation only.

- [ ] **Step 1: Write a failing pose-palette rendering test**

Add these imports to `python/tests/test_dashboard_cli.py`:

```python
from types import SimpleNamespace

import numpy as np

from run_dashboard import POSE_JOINT_COLOR, POSE_LINE_COLOR, draw_pose
```

Add this test:

```python
def test_pose_overlay_uses_clinical_palette():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    landmarks = [
        SimpleNamespace(x=0.2 + index * 0.01, y=0.5, visibility=1.0)
        for index in range(33)
    ]

    draw_pose(frame, landmarks)

    pixels = frame.reshape(-1, 3)
    assert np.any(np.all(pixels == np.asarray(POSE_LINE_COLOR), axis=1))
    assert np.any(np.all(pixels == np.asarray(POSE_JOINT_COLOR), axis=1))
```

- [ ] **Step 2: Run the pose test and verify it fails**

Run: `cd python && pytest -q tests/test_dashboard_cli.py::test_pose_overlay_uses_clinical_palette`

Expected: collection fails because `POSE_LINE_COLOR` and `POSE_JOINT_COLOR` are not defined.

- [ ] **Step 3: Add the new pose palette without changing the function interface**

Add these constants after `POSE_CONNECTIONS` in `python/run_dashboard.py`:

```python
POSE_LINE_COLOR = (212, 184, 62)
POSE_JOINT_COLOR = (244, 219, 118)
POSE_JOINT_OUTLINE = (31, 24, 14)
```

Replace `draw_pose` with:

```python
def draw_pose(frame: np.ndarray, landmarks) -> None:
    h, w = frame.shape[:2]
    for a_idx, b_idx in POSE_CONNECTIONS:
        a, b = landmarks[a_idx], landmarks[b_idx]
        if a.visibility > 0.5 and b.visibility > 0.5:
            cv2.line(
                frame,
                (int(a.x * w), int(a.y * h)),
                (int(b.x * w), int(b.y * h)),
                POSE_LINE_COLOR,
                2,
                cv2.LINE_AA,
            )
    for landmark in landmarks:
        if landmark.visibility > 0.5:
            center = (int(landmark.x * w), int(landmark.y * h))
            cv2.circle(frame, center, 4, POSE_JOINT_OUTLINE, -1, cv2.LINE_AA)
            cv2.circle(frame, center, 2, POSE_JOINT_COLOR, -1, cv2.LINE_AA)
```

- [ ] **Step 4: Run the pose and dashboard tests**

Run: `cd python && pytest -q tests/test_dashboard_cli.py tests/test_dashboard_view.py`

Expected: all focused tests pass.

- [ ] **Step 5: Generate one representative PNG for visual inspection**

Run from the repository root:

```bash
PYTHONPATH=python python - <<'PY'
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from literehab.dashboard_view import DashboardViewState, render_dashboard
from literehab.telemetry import TelemetrySample

frame = np.full((600, 800, 3), (72, 64, 58), dtype=np.uint8)
cv2.rectangle(frame, (270, 90), (530, 540), (100, 92, 84), -1)
history = deque(
    TelemetrySample(i, (0.0, 0.0, 1.0),
                    (40 * np.sin(i / 8), 30 * np.cos(i / 10), 18 * np.sin(i / 5)),
                    "elbow_flexion", 6, "ok")
    for i in range(80)
)
state = DashboardViewState(
    exercise="elbow_flexion",
    repetitions=6,
    feedback="Good repetition",
    mode="Fusion",
    source="multimodal model",
    side="left",
    serial_status="connected",
    camera_status="connected: 0",
    rom_deg=86.4,
    confidence_text="Fusion 0.91",
)
output = Path("output/dashboard_polished_preview.png")
output.parent.mkdir(parents=True, exist_ok=True)
assert cv2.imwrite(str(output), render_dashboard(frame, history, state))
print(output)
PY
```

Expected: prints `output/dashboard_polished_preview.png`; inspect it for clipped text, broken rounded corners, poor contrast, or overlays that obscure the camera subject.

- [ ] **Step 6: Run the full Python regression suite and dashboard smoke test**

Run:

```bash
cd python
pytest -q
PYTHONPATH=. python run_dashboard.py --headless-smoke-test
```

Expected: all Python tests pass, followed by `LiteRehab dashboard smoke test: PASS`.

- [ ] **Step 7: Commit the pose polish and verification changes**

```bash
git add python/run_dashboard.py python/tests/test_dashboard_cli.py
git commit -m "feat: polish dashboard pose overlay"
```

Do not add `output/dashboard_polished_preview.png` to the commit unless the user explicitly requests the preview artifact to be versioned.
