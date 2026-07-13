# OpenCV Dashboard Visual Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the crowded OpenCV text overlay with a clear dark dashboard that separates device health, exercise progress, safety feedback, and IMU measurements.

**Architecture:** Add a focused `literehab.dashboard_view` rendering module that converts existing runtime values into semantic presentation state and composes a fixed 1280×720 BGR image. Keep sensor acquisition, model decisions, pose processing, synchronization, and logging in `run_dashboard.py`; the main loop will construct a view state and pass it to the renderer.

**Tech Stack:** Python 3, OpenCV (`cv2`), NumPy, pytest, existing LiteRehab telemetry dataclasses.

## Global Constraints

- Preserve the existing OpenCV desktop runtime; do not create a browser frontend.
- Preserve camera, telemetry, inference, synchronization, CSV logging, and keyboard-control behavior.
- Keep UI labels in English and use no new font, image, or UI-framework dependency.
- Use green for healthy/correct, blue for active/neutral, amber for recoverable warnings, red for compensation/disconnection, and gray for idle/disabled/warming-up.
- Safety feedback has priority over range and speed coaching; unknown feedback remains visible through a fallback label.
- `B`, `R`, `Q`, and `Esc` retain their current behavior.

---

### Task 1: Semantic presentation state

**Files:**
- Create: `python/literehab/dashboard_view.py`
- Create: `python/tests/test_dashboard_view.py`

**Interfaces:**
- Consumes: Plain runtime strings and numeric values already produced by `run_dashboard.py`.
- Produces: `DashboardViewState`, `display_label(value: str) -> str`, `status_tone(status: str) -> str`, and `feedback_presentation(feedback: str) -> tuple[str, str]`.

- [ ] **Step 1: Write failing semantic mapping tests**

```python
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
        "AVOID TRUNK COMPENSATION", "danger")
    assert feedback_presentation("Move more slowly") == ("SLOW DOWN", "warning")
    assert feedback_presentation("Good repetition") == ("GOOD FORM", "success")
    assert feedback_presentation("Ready") == ("READY", "muted")
    assert feedback_presentation("New coaching state") == (
        "NEW COACHING STATE", "info")


def test_view_state_accepts_missing_optional_metrics():
    state = DashboardViewState(
        exercise="idle", repetitions=0, feedback="Ready", mode="IMU-only",
        source="rule fallback", side="left", serial_status="connecting",
        camera_status="unavailable", rom_deg=None, confidence_text="warming up",
    )
    assert state.rom_deg is None
```

- [ ] **Step 2: Run tests and verify the new module is missing**

Run: `cd python && pytest -q tests/test_dashboard_view.py`

Expected: collection fails with `ModuleNotFoundError: No module named 'literehab.dashboard_view'`.

- [ ] **Step 3: Implement the immutable view state and mapping helpers**

```python
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
```

- [ ] **Step 4: Run semantic tests**

Run: `cd python && pytest -q tests/test_dashboard_view.py`

Expected: `4 passed`.

- [ ] **Step 5: Commit semantic presentation state**

```bash
git add python/literehab/dashboard_view.py python/tests/test_dashboard_view.py
git commit -m "feat: add dashboard presentation state"
```

---

### Task 2: Dashboard renderer

**Files:**
- Modify: `python/literehab/dashboard_view.py`
- Modify: `python/tests/test_dashboard_view.py`

**Interfaces:**
- Consumes: `DashboardViewState`, a camera `np.ndarray`, and an iterable of `TelemetrySample` values.
- Produces: `render_dashboard(frame: np.ndarray, history: Iterable[TelemetrySample], state: DashboardViewState) -> np.ndarray` and `draw_gyro_chart(panel: np.ndarray, history: Iterable[TelemetrySample]) -> None`.

- [ ] **Step 1: Write failing renderer tests**

```python
from collections import deque

import numpy as np

from literehab.dashboard_view import render_dashboard
from literehab.telemetry import TelemetrySample


def sample(gx=10.0, gy=20.0, gz=30.0):
    return TelemetrySample(1, (0.0, 0.0, 1.0), (gx, gy, gz), "idle", 0, "none")


def test_renderer_returns_fixed_nonempty_canvas():
    frame = np.full((600, 800, 3), 80, dtype=np.uint8)
    canvas = render_dashboard(frame, deque([sample(), sample(-10, 5, 40)]), base_state())
    assert canvas.shape == (720, 1280, 3)
    assert canvas.dtype == np.uint8
    assert np.any(canvas[:64] != canvas[64:128].mean())


def test_renderer_handles_empty_history_and_missing_rom():
    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    canvas = render_dashboard(frame, [], base_state(rom_deg=None))
    assert canvas.shape == (720, 1280, 3)
```

Add this reusable fixture helper in the same test module:

```python
def base_state(**changes):
    values = dict(
        exercise="elbow_flexion", repetitions=4, feedback="Good repetition",
        mode="Fusion", source="multimodal model", side="left",
        serial_status="connected", camera_status="connected: 0",
        rom_deg=82.5, confidence_text="Fusion 0.91",
    )
    values.update(changes)
    return DashboardViewState(**values)
```

- [ ] **Step 2: Run renderer tests and verify the import fails**

Run: `cd python && pytest -q tests/test_dashboard_view.py -k renderer`

Expected: collection fails because `render_dashboard` is not defined.

- [ ] **Step 3: Add theme constants and drawing primitives**

Add BGR theme values and focused helpers to `dashboard_view.py`:

```python
import cv2
import numpy as np

CANVAS_SIZE = (1280, 720)
COLORS = {
    "background": (18, 22, 30), "surface": (28, 34, 45),
    "surface_alt": (35, 43, 56), "text": (240, 244, 248),
    "muted_text": (156, 165, 178), "success": (105, 200, 91),
    "info": (232, 156, 65), "warning": (65, 181, 245),
    "danger": (79, 79, 239), "muted": (112, 120, 132),
}


def _text(image, text, origin, scale, color="text", thickness=1):
    resolved = COLORS[color] if isinstance(color, str) else color
    cv2.putText(image, text, origin, cv2.FONT_HERSHEY_SIMPLEX, scale,
                resolved, thickness, cv2.LINE_AA)


def _card(image, top_left, bottom_right):
    cv2.rectangle(image, top_left, bottom_right, COLORS["surface"], -1)


def _chip(image, x, y, label, status):
    tone = status_tone(status)
    width = max(112, 32 + cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX,
                                         0.42, 1)[0][0])
    cv2.rectangle(image, (x, y), (x + width, y + 30), COLORS["surface_alt"], -1)
    cv2.circle(image, (x + 14, y + 15), 5, COLORS[tone], -1)
    _text(image, label, (x + 26, y + 20), 0.42, thickness=1)
    return width
```

- [ ] **Step 4: Implement the chart and fixed composition**

Add these complete renderer functions. They draw a dark grid with an adaptive
scale of at least 100 deg/s, place video at `(20, 80):(820, 680)`, and fill the
right rail `(840, 80):(1260, 680)` with the required progress information:

```python
def draw_gyro_chart(panel: np.ndarray, history) -> None:
    panel[:] = COLORS["surface"]
    height, width = panel.shape[:2]
    _text(panel, "IMU GYROSCOPE", (16, 25), 0.48, "muted_text")
    plot_left, plot_right = 16, width - 16
    plot_top, plot_bottom = 40, height - 34
    for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = int(plot_top + fraction * (plot_bottom - plot_top))
        cv2.line(panel, (plot_left, y), (plot_right, y),
                 COLORS["surface_alt"], 1)
    samples = list(history)
    axis_colors = ((90, 110, 245), (105, 200, 91), (232, 156, 65))
    if len(samples) >= 2:
        values = np.asarray([sample.gyro_dps for sample in samples],
                            dtype=np.float32)
        scale = max(100.0, float(np.abs(values).max()))
        center = (plot_top + plot_bottom) / 2
        amplitude = (plot_bottom - plot_top) * 0.44
        for axis, color in enumerate(axis_colors):
            points = []
            for index, value in enumerate(values[:, axis]):
                x = int(plot_left + index * (plot_right - plot_left)
                        / max(1, len(values) - 1))
                y = int(center - value * amplitude / scale)
                points.append((x, y))
            cv2.polylines(panel, [np.asarray(points)], False, color, 2,
                          cv2.LINE_AA)
    for index, (label, color) in enumerate(zip("XYZ", axis_colors)):
        x = 18 + index * 52
        cv2.circle(panel, (x, height - 14), 4, color, -1)
        _text(panel, label, (x + 9, height - 10), 0.35, "muted_text")


def render_dashboard(frame: np.ndarray, history, state: DashboardViewState) -> np.ndarray:
    width, height = CANVAS_SIZE
    canvas = np.full((height, width, 3), COLORS["background"], dtype=np.uint8)
    _text(canvas, "LiteRehab", (20, 39), 0.82, thickness=2)
    _text(canvas, "LIVE REHABILITATION", (20, 58), 0.35, "muted_text")

    chip_x = 675
    for label, status in (
        ("SERIAL", state.serial_status),
        ("CAMERA", state.camera_status),
        (display_label(state.mode).upper(), state.mode),
    ):
        chip_x += _chip(canvas, chip_x, 22, label, status) + 10

    video = cv2.resize(frame, (800, 600))
    canvas[80:680, 20:820] = video
    shade = canvas.copy()
    cv2.rectangle(shade, (36, 96), (390, 146), COLORS["background"], -1)
    cv2.addWeighted(shade, 0.78, canvas, 0.22, 0, canvas)
    _text(canvas, display_label(state.exercise).upper(), (54, 130), 0.68,
          thickness=2)

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
    _text(canvas, display_label(state.exercise), (862, 297), 0.72,
          thickness=2)
    _text(canvas, f"{display_label(state.side)} side  |  {display_label(state.source)}",
          (862, 325), 0.4, "muted_text")

    _card(canvas, (840, 352), (1044, 438))
    _card(canvas, (1056, 352), (1260, 438))
    _text(canvas, "RANGE OF MOTION", (856, 378), 0.36, "muted_text")
    rom = "--" if state.rom_deg is None else f"{state.rom_deg:.1f} deg"
    _text(canvas, rom, (856, 417), 0.7, thickness=2)
    _text(canvas, "MODEL STATUS", (1072, 378), 0.36, "muted_text")
    _text(canvas, state.confidence_text, (1072, 417), 0.52, thickness=1)

    chart = canvas[450:646, 840:1260]
    draw_gyro_chart(chart, history)
    _text(canvas, "B  Baseline    R  Reset ROM    Q  Quit", (870, 684),
          0.42, "muted_text")
    return canvas
```

- [ ] **Step 5: Run all renderer and semantic tests**

Run: `cd python && pytest -q tests/test_dashboard_view.py`

Expected: `6 passed`.

- [ ] **Step 6: Commit the dashboard renderer**

```bash
git add python/literehab/dashboard_view.py python/tests/test_dashboard_view.py
git commit -m "feat: render clear OpenCV dashboard"
```

---

### Task 3: Runtime integration and regression verification

**Files:**
- Modify: `python/run_dashboard.py:16-26,153-172,374-392`
- Modify: `python/tests/test_dashboard_cli.py`
- Modify: `DEMO_GUIDE.md:221-234`

**Interfaces:**
- Consumes: `DashboardViewState` and `render_dashboard` from Task 2.
- Produces: The existing `LiteRehab-Fusion MVP` OpenCV window displaying the new canvas while preserving every existing loop side effect and key binding.

- [ ] **Step 1: Write a failing runtime-boundary test**

Add a source-level regression test that prevents the old crowded overlay and
ensures the new renderer is the UI boundary:

```python
def test_dashboard_runtime_uses_composed_view():
    source = Path(run_dashboard.__file__).read_text()
    assert "DashboardViewState(" in source
    assert "render_dashboard(frame, history, view_state)" in source
    assert "overlay = [" not in source
    assert "np.hstack((frame, chart))" not in source
```

- [ ] **Step 2: Run the boundary test and verify it fails**

Run: `cd python && pytest -q tests/test_dashboard_cli.py::test_dashboard_runtime_uses_composed_view`

Expected: FAIL because `DashboardViewState(` is absent.

- [ ] **Step 3: Replace the old drawing path in `run_dashboard.py`**

Import the new public interface:

```python
from literehab.dashboard_view import DashboardViewState, render_dashboard
```

Delete the old `draw_chart` function. Replace the nine-line overlay and
`np.hstack` section with:

```python
confidence_text = (
    f"Fusion {decision.confidence:.2f}"
    if multimodal_prediction is not None
    else cnn.status_text(cnn_prediction)
)
view_state = DashboardViewState(
    exercise=decision.exercise,
    repetitions=reps,
    feedback=fusion.feedback,
    mode=fusion.mode,
    source=decision.source,
    side=args.side,
    serial_status=reader.status,
    camera_status=camera.status,
    rom_deg=elbow_range,
    confidence_text=confidence_text,
)
canvas = render_dashboard(frame, history, view_state)
cv2.imshow("LiteRehab-Fusion MVP", canvas)
```

- [ ] **Step 4: Update the demonstration guide**

Replace the old left-overlay description with a concise explanation of the
header health chips, camera guidance banner, right-side repetition/ROM cards,
IMU chart, and semantic colors. Preserve the existing startup and operation
instructions.

- [ ] **Step 5: Run focused tests**

Run: `cd python && pytest -q tests/test_dashboard_view.py tests/test_dashboard_cli.py tests/test_dashboard_state.py tests/test_fusion.py`

Expected: all selected tests pass.

- [ ] **Step 6: Run the dashboard smoke test**

Run: `cd python && python run_dashboard.py --headless-smoke-test`

Expected output includes `LiteRehab dashboard smoke test: PASS`.

- [ ] **Step 7: Run formatting and complete regression checks**

Run: `python -m compileall -q python && git diff --check && ./tests/run_host_tests.sh && cd python && pytest -q`

Expected: compile and whitespace checks exit zero, all C host tests pass, and the complete Python suite passes.

- [ ] **Step 8: Commit the integration**

```bash
git add python/run_dashboard.py python/tests/test_dashboard_cli.py DEMO_GUIDE.md
git commit -m "feat: integrate refreshed rehabilitation dashboard"
```
