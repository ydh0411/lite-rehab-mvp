# MaixCAM 2 Camera Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make MaixCAM 2 the LiteRehab vision source through USB UVC by default, with RTSP fallback and automatic desktop-side recovery.

**Architecture:** A focused `CameraSource` class will isolate OpenCV device parsing, opening, health, and reconnect behavior from the dashboard. A MaixPy program will expose the MaixCAM 2 sensor through either UVC/MJPEG or RTSP/NV21, while the existing MediaPipe, synchronization, fusion, BLE, and CSV paths remain unchanged.

**Tech Stack:** Python 3.13, OpenCV, pytest, MediaPipe, MaixPy v4 (`camera`, `uvc`, `rtsp`, `image`, `display`, `app`), POSIX shell

## Global Constraints

- Existing `--camera 0` usage must remain valid.
- `--camera-source` accepts `auto`, a non-negative local index, or an `rtsp://` URL and takes precedence over `--camera`.
- The default demonstration path is MaixCAM 2 USB UVC at 640 x 480 MJPEG.
- RTSP fallback uses `rtsp://<device-ip>:8554/live` and an NV21 camera source.
- Camera failure must not terminate serial IMU collection or permanently disable vision.
- No GPIO connection is added between MaixCAM 2 and either ESP32.
- Existing pose-feature and synchronized CSV schemas must not change.

---

## File Structure

- Create `python/literehab/camera_source.py`: source parsing, capture lifecycle, bounded probing, status, and reconnect timing.
- Create `python/tests/test_camera_source.py`: unit tests with a controlled fake OpenCV capture backend.
- Modify `python/run_dashboard.py`: CLI compatibility and use of `CameraSource`.
- Create `maixcam2/main.py`: directly runnable MaixPy UVC/RTSP application.
- Create `scripts/probe_cameras.py`: bounded local-camera check for the host.
- Create `scripts/start_maixcam2_demo.sh`: stable right-arm UVC dashboard launch command.
- Modify `scripts/test_all.sh`: compile and smoke-check new host files.
- Modify `README.md` and `DEMO_GUIDE.md`: setup, connection, fallback, and demonstration workflow.

---

### Task 1: Tested desktop camera source

**Files:**
- Create: `python/tests/test_camera_source.py`
- Create: `python/literehab/camera_source.py`

**Interfaces:**
- Consumes: an OpenCV-compatible module exposing `VideoCapture`, `CAP_PROP_BUFFERSIZE`, `CAP_PROP_FRAME_WIDTH`, and `CAP_PROP_FRAME_HEIGHT`.
- Produces: `parse_camera_source(value: str | int) -> int | str`, `probe_local_cameras(cv2_module, indices=range(5)) -> list[int]`, and `CameraSource(source, cv2_module, reconnect_interval_s=1.0, max_consecutive_failures=3, clock=time.monotonic)` with `read()`, `close()`, `healthy`, `status`, and `active_source`.

- [ ] **Step 1: Write failing parsing and probing tests**

```python
import pytest

from literehab.camera_source import parse_camera_source, probe_local_cameras


class FakeCapture:
    def __init__(self, frames, opened=True):
        self.frames = list(frames)
        self.opened = opened
        self.released = False
        self.properties = {}

    def isOpened(self):
        return self.opened and not self.released

    def read(self):
        return self.frames.pop(0) if self.frames else (False, None)

    def set(self, key, value):
        self.properties[key] = value
        return True

    def release(self):
        self.released = True


class FakeCV2:
    CAP_PROP_BUFFERSIZE = 1
    CAP_PROP_FRAME_WIDTH = 2
    CAP_PROP_FRAME_HEIGHT = 3

    def __init__(self):
        self.plans = []
        self.captures = []

    def VideoCapture(self, source):
        plan = self.plans.pop(0) if self.plans else {"frames": []}
        capture = FakeCapture(plan.get("frames", []), plan.get("opened", True))
        capture.source = source
        self.captures.append(capture)
        return capture


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def fake_cv2():
    return FakeCV2()


@pytest.fixture
def clock():
    return FakeClock()


def test_parse_camera_source_accepts_index_auto_and_rtsp():
    assert parse_camera_source(2) == 2
    assert parse_camera_source("2") == 2
    assert parse_camera_source("auto") == "auto"
    assert parse_camera_source("rtsp://10.131.167.1:8554/live") == (
        "rtsp://10.131.167.1:8554/live")


@pytest.mark.parametrize("value", ["", "-1", "http://camera/live", "abc"])
def test_parse_camera_source_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        parse_camera_source(value)


def test_probe_returns_only_indices_that_deliver_a_frame(fake_cv2):
    fake_cv2.plans = [
        {"frames": [(False, None)]},
        {"frames": [(True, object())]},
    ]
    assert probe_local_cameras(fake_cv2, indices=range(2)) == [1]
    assert all(capture.released for capture in fake_cv2.captures)
```

- [ ] **Step 2: Run the parsing and probing tests and verify RED**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests/test_camera_source.py`

Expected: collection fails with `ModuleNotFoundError: No module named 'literehab.camera_source'`.

- [ ] **Step 3: Implement source parsing and bounded probing**

```python
def parse_camera_source(value: str | int) -> int | str:
    if isinstance(value, int):
        if value < 0:
            raise ValueError("camera index must be non-negative")
        return value
    text = str(value).strip()
    if text == "auto":
        return text
    if text.isdigit():
        return int(text)
    if text.lower().startswith("rtsp://"):
        return text
    raise ValueError("camera source must be auto, a non-negative index, or rtsp:// URL")


def probe_local_cameras(cv2_module, indices=range(5)) -> list[int]:
    available = []
    for index in indices:
        capture = cv2_module.VideoCapture(index)
        try:
            ok, frame = capture.read() if capture.isOpened() else (False, None)
            if ok and frame is not None:
                available.append(index)
        finally:
            capture.release()
    return available
```

- [ ] **Step 4: Write failing lifecycle and recovery tests**

```python
from literehab.camera_source import CameraSource


def test_camera_source_opens_uvc_with_low_latency_settings(fake_cv2):
    fake_cv2.plans = [{"frames": [(True, object())]}]
    source = CameraSource(1, fake_cv2)
    assert source.active_source == 1
    assert fake_cv2.captures[0].properties[fake_cv2.CAP_PROP_FRAME_WIDTH] == 640
    assert fake_cv2.captures[0].properties[fake_cv2.CAP_PROP_FRAME_HEIGHT] == 480
    assert fake_cv2.captures[0].properties[fake_cv2.CAP_PROP_BUFFERSIZE] == 1


def test_camera_source_becomes_unhealthy_then_rate_limits_reopen(fake_cv2, clock):
    fake_cv2.plans = [
        {"frames": [(False, None)] * 3},
        {"frames": [(True, object())]},
    ]
    source = CameraSource(0, fake_cv2, reconnect_interval_s=1.0,
                          max_consecutive_failures=3, clock=clock)
    source.read()
    source.read()
    source.read()
    assert not source.healthy
    source.read()
    assert len(fake_cv2.captures) == 1
    clock.advance(1.0)
    ok, frame = source.read()
    assert ok and frame is not None
    assert source.healthy
    assert len(fake_cv2.captures) == 2


def test_close_releases_capture(fake_cv2):
    fake_cv2.plans = [{"frames": []}]
    source = CameraSource(0, fake_cv2)
    source.close()
    assert fake_cv2.captures[0].released
```

- [ ] **Step 5: Run lifecycle tests and verify RED**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests/test_camera_source.py`

Expected: parsing tests pass; lifecycle tests fail because `CameraSource` is not defined.

- [ ] **Step 6: Implement minimal lifecycle and recovery behavior**

```python
class CameraSource:
    def __init__(self, source, cv2_module, reconnect_interval_s=1.0,
                 max_consecutive_failures=3, clock=time.monotonic):
        self.requested_source = parse_camera_source(source)
        self.cv2 = cv2_module
        self.reconnect_interval_s = reconnect_interval_s
        self.max_consecutive_failures = max_consecutive_failures
        self.clock = clock
        self.capture = None
        self.active_source = None
        self.failures = 0
        self.next_reconnect_s = 0.0
        self.status = "not connected"
        self._open()

    @property
    def healthy(self):
        return self.capture is not None and self.failures < self.max_consecutive_failures

    def _resolve(self):
        if self.requested_source != "auto":
            return self.requested_source
        found = probe_local_cameras(self.cv2)
        return found[0] if found else None

    def _open(self):
        source = self._resolve()
        if source is None:
            self.status = "no local camera found"
            self.next_reconnect_s = self.clock() + self.reconnect_interval_s
            return
        capture = self.cv2.VideoCapture(source)
        capture.set(self.cv2.CAP_PROP_BUFFERSIZE, 1)
        capture.set(self.cv2.CAP_PROP_FRAME_WIDTH, 640)
        capture.set(self.cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if capture.isOpened():
            self.capture = capture
            self.active_source = source
            self.failures = 0
            self.status = f"connected: {source}"
        else:
            capture.release()
            self.next_reconnect_s = self.clock() + self.reconnect_interval_s
            self.status = f"unavailable: {source}"

    def read(self):
        if self.capture is None or self.failures >= self.max_consecutive_failures:
            if self.clock() < self.next_reconnect_s:
                return False, None
            self._release()
            self._open()
        if self.capture is None:
            return False, None
        ok, frame = self.capture.read()
        if ok and frame is not None:
            self.failures = 0
            self.status = f"connected: {self.active_source}"
            return True, frame
        self.failures += 1
        self.status = f"frame failure {self.failures}/{self.max_consecutive_failures}"
        if self.failures >= self.max_consecutive_failures:
            self.next_reconnect_s = self.clock() + self.reconnect_interval_s
        return False, None

    def _release(self):
        if self.capture is not None:
            self.capture.release()
        self.capture = None

    def close(self):
        self._release()
        self.status = "closed"
```

- [ ] **Step 7: Run focused and full Python tests**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests/test_camera_source.py python/tests`

Expected: all camera-source tests and the existing 34 Python tests pass.

- [ ] **Step 8: Commit the tested camera source**

```bash
git add python/literehab/camera_source.py python/tests/test_camera_source.py
git commit -m "feat: add recoverable camera input"
```

---

### Task 2: Dashboard integration and CLI compatibility

**Files:**
- Create: `python/tests/test_dashboard_cli.py`
- Modify: `python/run_dashboard.py`

**Interfaces:**
- Consumes: `CameraSource(source, cv2_module)` and `parse_camera_source(value)` from Task 1.
- Produces: `build_parser() -> argparse.ArgumentParser` and `resolve_camera_argument(args) -> int | str`; dashboard overlays `Camera: <status>` and uses `CameraSource.read()`/`close()`.

- [ ] **Step 1: Write failing CLI compatibility tests**

```python
from run_dashboard import build_parser, resolve_camera_argument


def test_legacy_camera_argument_remains_supported():
    args = build_parser().parse_args(["--camera", "2"])
    assert resolve_camera_argument(args) == 2


def test_camera_source_takes_precedence_and_accepts_rtsp():
    args = build_parser().parse_args([
        "--camera", "0", "--camera-source", "rtsp://10.0.0.2:8554/live"])
    assert resolve_camera_argument(args) == "rtsp://10.0.0.2:8554/live"
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests/test_dashboard_cli.py`

Expected: import fails because `build_parser` and `resolve_camera_argument` do not exist.

- [ ] **Step 3: Extract parser construction and resolve the new argument**

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LiteRehab live fusion dashboard")
    parser.add_argument("--port", default="auto")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--camera-source")
    parser.add_argument("--output", type=Path,
                        default=Path("sessions/session.csv"))
    parser.add_argument("--model", type=Path)
    parser.add_argument("--fusion-model", type=Path)
    parser.add_argument("--model-confidence", type=float, default=0.70)
    parser.add_argument("--side", choices=["left", "right"], default="left")
    parser.add_argument("--subject", default="")
    parser.add_argument(
        "--label-exercise", default="",
        choices=["", "idle", "forearm_rotation", "elbow_flexion",
                 "shoulder_abduction"])
    parser.add_argument(
        "--label-quality", default="",
        choices=["", "none", "ok", "too_fast", "insufficient_range",
                 "trunk_compensation"])
    parser.add_argument("--headless-smoke-test", action="store_true")
    return parser


def resolve_camera_argument(args) -> int | str:
    selected = args.camera_source if args.camera_source is not None else args.camera
    try:
        return parse_camera_source(selected)
    except ValueError as error:
        raise SystemExit(str(error)) from error
```

- [ ] **Step 4: Replace direct OpenCV capture access with `CameraSource`**

```python
camera = CameraSource(resolve_camera_argument(args), cv2)
camera_configured = mp is not None
# In the frame loop:
ok, frame = camera.read()
camera_healthy = camera_configured and camera.healthy
# In the overlay:
f"Camera: {camera.status}",
# In finally:
camera.close()
```

Remove direct `capture.isOpened()`, `capture.read()`, and `capture.release()` calls. Do not gate MediaPipe object construction on the first camera-open attempt, because a source may recover later.

- [ ] **Step 5: Run focused tests, all Python tests, and the dashboard smoke test**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests && PYTHONPATH=python /opt/anaconda3/bin/python3.13 python/run_dashboard.py --headless-smoke-test --camera-source auto`

Expected: all tests pass and output ends with `LiteRehab dashboard smoke test: PASS`.

- [ ] **Step 6: Commit dashboard integration**

```bash
git add python/run_dashboard.py python/tests/test_dashboard_cli.py
git commit -m "feat: connect dashboard to MaixCAM sources"
```

---

### Task 3: MaixCAM 2 UVC and RTSP application

**Files:**
- Create: `maixcam2/main.py`

**Interfaces:**
- Consumes: MaixPy v4 modules available on MaixCAM 2.
- Produces: `run_uvc()` and `run_rtsp()`; `MODE = "uvc"` is the single deployment setting changed by the operator.

- [ ] **Step 1: Add a host-parseable MaixPy application using only documented APIs**

```python
from maix import app, camera, display, image, rtsp, time, uvc

MODE = "uvc"
WIDTH = 640
HEIGHT = 480


def run_uvc():
    cam = camera.Camera(WIDTH, HEIGHT)
    screen = display.Display()
    streamer = uvc.UvcStreamer()
    streamer.use_mjpg(1)
    while not app.need_exit():
        frame = cam.read()
        streamer.show(frame)
        screen.show(frame)


def run_rtsp():
    cam = camera.Camera(WIDTH, HEIGHT, image.Format.FMT_YVU420SP)
    server = rtsp.Rtsp()
    server.bind_camera(cam)
    server.start()
    print("LiteRehab RTSP:", server.get_url())
    while not app.need_exit():
        time.sleep_ms(200)


if MODE == "uvc":
    run_uvc()
elif MODE == "rtsp":
    run_rtsp()
else:
    raise ValueError("MODE must be 'uvc' or 'rtsp'")
```

- [ ] **Step 2: Verify host syntax without importing unavailable MaixPy modules**

Run: `/opt/anaconda3/bin/python3.13 -m py_compile maixcam2/main.py`

Expected: exit status 0 with no output.

- [ ] **Step 3: Check the implementation against current official API names**

Confirm against Sipeed's MaixPy UVC documentation that `UvcStreamer`, `use_mjpg(1)`, and `show(frame)` are current, and against the RTSP documentation that `FMT_YVU420SP`, `bind_camera`, `start`, and `get_url` are current. Record the source links in `maixcam2/README.md` during Task 4.

- [ ] **Step 4: Commit the MaixCAM 2 application**

```bash
git add maixcam2/main.py
git commit -m "feat: add MaixCAM 2 video application"
```

---

### Task 4: Camera probe, launch helper, documentation, and full verification

**Files:**
- Create: `scripts/probe_cameras.py`
- Create: `scripts/start_maixcam2_demo.sh`
- Create: `maixcam2/README.md`
- Modify: `scripts/test_all.sh`
- Modify: `README.md`
- Modify: `DEMO_GUIDE.md`

**Interfaces:**
- Consumes: `probe_local_cameras` from Task 1 and dashboard CLI from Task 2.
- Produces: human-readable camera discovery output and a right-arm UVC launch command.

- [ ] **Step 1: Add the bounded camera probe**

```python
#!/usr/bin/env python3
import cv2

from literehab.camera_source import probe_local_cameras


def main():
    cameras = probe_local_cameras(cv2)
    if not cameras:
        raise SystemExit("No working UVC camera found")
    print("Working camera indices:", ", ".join(map(str, cameras)))
    print("Use MaixCAM 2 with: --camera-source", cameras[-1])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add the stable right-arm launch helper**

```sh
#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON:-/opt/anaconda3/bin/python3.13}
SOURCE=${1:-auto}
PYTHONPATH="$ROOT/python" "$PYTHON" "$ROOT/python/run_dashboard.py" \
  --port auto --camera-source "$SOURCE" --side right \
  --output "$ROOT/python/sessions/maixcam2_demo.csv"
```

- [ ] **Step 3: Document exact device and fallback workflow**

Add these verified instructions to `maixcam2/README.md`, `README.md`, and `DEMO_GUIDE.md`:

```text
UVC: Settings -> USB Settings -> enable UVC; set MODE = "uvc"; run main.py
from MaixVision; connect MaixCAM 2 and ESP32-S3 receiver with separate data USB
cables; run scripts/probe_cameras.py; run scripts/start_maixcam2_demo.sh <index>.

RTSP: connect MaixCAM 2 and Mac to the same network; set MODE = "rtsp"; run
main.py; copy the printed rtsp://<IP>:8554/live URL; run
scripts/start_maixcam2_demo.sh rtsp://<IP>:8554/live.

Demo: place MaixCAM 2 1.5-2.0 m away, landscape, chest height; keep the right
shoulder, elbow, wrist, and hip visible; wait for Fusion; press b in the dashboard
window while neutral; perform slow elbow flexion, forearm rotation, fast-motion
warning, trunk compensation, and camera-occlusion fallback/recovery.
```

Include official links to Sipeed's MaixCAM 2 quick start, UVC streaming, and RTSP streaming documentation.

- [ ] **Step 4: Extend repository verification**

Add `scripts/probe_cameras.py`, `python/literehab/camera_source.py`, and `maixcam2/main.py` to the existing `py_compile` command in `scripts/test_all.sh`. Do not run the physical camera probe from automated tests.

- [ ] **Step 5: Make helper scripts executable and run full verification**

Run:

```bash
chmod +x scripts/probe_cameras.py scripts/start_maixcam2_demo.sh
./scripts/test_all.sh
git diff --check
git status --short
```

Expected: three C host test binaries pass, all Python tests pass, the dashboard smoke test passes, both ESP-IDF firmware builds pass, `git diff --check` produces no output, and only the intended MaixCAM 2 integration files are modified.

- [ ] **Step 6: Commit documentation and tools**

```bash
git add scripts/probe_cameras.py scripts/start_maixcam2_demo.sh \
  scripts/test_all.sh maixcam2/README.md README.md DEMO_GUIDE.md
git commit -m "docs: add MaixCAM 2 setup and demo workflow"
```

---

## Hardware Acceptance Checklist

- [ ] MaixCAM 2 appears as a UVC camera after its application starts.
- [ ] The probe reports a working index and shows no persistent read errors.
- [ ] Dashboard displays live MaixCAM 2 frames and enters `Fusion` with the right-side landmarks visible.
- [ ] Disconnecting MaixCAM 2 changes the dashboard to `IMU-only` without interrupting repetitions or CSV logging.
- [ ] Reconnecting MaixCAM 2 restores live frames and `Fusion` without restarting the dashboard.
- [ ] RTSP URL opens in the dashboard when UVC is unavailable.
- [ ] The CSV is created at `python/sessions/maixcam2_demo.csv` and contains both IMU and vision fields.
