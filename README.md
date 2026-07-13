# LiteRehab-Fusion MVP

[English](README.md) | [中文](README_zh.md)

LiteRehab is a dual-board upper-limb rehabilitation prototype. A wearable IMU detects arm movement, an ESP32-S3 receiver provides immediate feedback, and a MaixCAM 2 supplies video for pose-based checks. The desktop dashboard combines both streams and records synchronized session data.

This is an engineering prototype for coursework and demonstration. It is not a medical device and does not replace a physiotherapist.

## What the prototype demonstrates

- Counts elbow flexion and forearm rotation using a wearable MPU6050.
- Flags movements that are too fast or have insufficient range.
- Uses MaixCAM 2 pose landmarks to estimate elbow range of motion and trunk compensation.
- Falls back to IMU-only feedback if video is lost, then restores fusion automatically.
- Records every received IMU sample with the nearest valid pose features in CSV.
- Auto-loads a small CNN-BiGRU trained from a public upper-limb IMU subset; no user-recorded training session is required.

## System overview

```text
Right-arm wearable                         Vision
MYOSA ESP32 + MPU6050                     MaixCAM 2
        │ BLE                                  │ USB UVC (default)
        ▼                                      │ or RTSP
ESP32-S3 receiver                              ▼
LED + buzzer + USB serial ─────────────► Python dashboard
                                          MediaPipe pose
                                          rule/model fusion
                                          synchronized CSV
```

The camera and ESP32 boards do not share GPIO wiring. MaixCAM 2 and the ESP32-S3 receiver connect to the laptop with separate USB data cables.

## Hardware

| Quantity | Part | Use |
|---:|---|---|
| 1 | MYOSA ESP32 WROOM-32E | Wearable controller and BLE peripheral |
| 1 | ESP32-S3-DevKitC-1 N16R8 | BLE receiver and USB serial gateway |
| 1 | MPU6050 | Six-axis arm motion sensing |
| 1 | SSD1306 128×64 OLED | Wearable status and repetition count |
| 1 | MaixCAM 2 | UVC/RTSP vision source |
| 1 each | Passive buzzer, LED, 220–330 Ω resistor | Receiver feedback |
| 2 | Four-pin JST cables | Wearable I²C chain |
| 2–3 | USB data cables | Receiver, MaixCAM 2, and wearable power/flashing |

### Connections

```text
Wearable:
MYOSA I²C ── JST ── MPU6050 ── JST ── SSD1306 OLED

Receiver:
GPIO2  ── 220–330 Ω ── LED anode; LED cathode ── GND
GPIO18 ── 100–330 Ω ── passive buzzer (+); buzzer (-) ── GND

Camera and host:
MaixCAM 2 Type-C ── USB data cable ── laptop
ESP32-S3 native USB ── separate USB data cable ── laptop
```

Mount the MPU6050 firmly on the back of the forearm, with its X axis pointing toward the hand and Z axis pointing away from the skin. See [WIRING_GUIDE.md](WIRING_GUIDE.md) before powering the boards.

## Quick start

### 1. Flash the two ESP32 boards

```bash
source ~/.espressif/v6.0.2/esp-idf/export.sh

./scripts/flash_wearable.sh /dev/cu.usbserial-WEARABLE
./scripts/flash_receiver.sh /dev/cu.usbmodem-RECEIVER
```

The current MaixCAM 2 update does not require reflashing either ESP32 board.

### 2. Install the desktop environment

```bash
conda create -n literehab python=3.12 -y
conda activate literehab
pip install -r python/requirements.txt
```

Allow camera access when macOS asks. If your MediaPipe package uses the Tasks API, place `pose_landmarker_lite.task` in `python/models/`.

### 3. Start MaixCAM 2 in UVC mode

1. On MaixCAM 2, open `Settings → USB Settings` and enable `UVC`.
2. Connect MaixCAM 2 to the laptop with a Type-C data cable.
3. Open [maixcam2/main.py](maixcam2/main.py) in MaixVision.
4. Keep `MODE = "uvc"` and run the file.

Find the camera index by running the probe once with MaixCAM 2 disconnected and once after reconnecting it:

```bash
PYTHONPATH=python python scripts/probe_cameras.py
```

The newly appearing index is normally MaixCAM 2.

### 4. Start the right-arm dashboard

```bash
PYTHON=python ./scripts/start_maixcam2_demo.sh <maixcam-index>
```

Equivalent command:

```bash
python python/run_dashboard.py \
  --port auto \
  --camera-source <maixcam-index> \
  --side right \
  --output python/sessions/maixcam2_demo.csv
```

The overlay should show `Serial: connected`, `Camera: connected`, and `Mode: Fusion`. If it remains in `IMU-only`, step back until the right shoulder, elbow, wrist, and hip are all visible.

## RTSP fallback

Use RTSP if the laptop cannot open the UVC device:

1. Connect MaixCAM 2 and the laptop to the same network.
2. Change `MODE` in [maixcam2/main.py](maixcam2/main.py) to `"rtsp"`.
3. Run it in MaixVision and copy the printed stream URL.
4. Start the dashboard with that URL:

```bash
PYTHON=python ./scripts/start_maixcam2_demo.sh \
  rtsp://<device-ip>:8554/live
```

The desktop camera layer accepts `auto`, a local camera index, or an `rtsp://` URL. It rate-limits reconnect attempts and keeps IMU logging active during camera loss.

## Demonstration sequence

Place MaixCAM 2 horizontally at chest height, about 1.5–2.0 m from the participant.

1. Stand upright with the right arm relaxed. Click the dashboard window and press lowercase `b` once to set the trunk baseline.
2. Perform one slow elbow flexion and return to neutral over 2–3 seconds.
3. Hold the elbow near 90° and rotate the forearm while keeping the upper arm still.
4. Repeat elbow flexion too quickly to trigger `too_fast` and two low tones.
5. Perform a small partial movement to demonstrate `insufficient_range`.
6. Lean the torso during elbow flexion to show visual trunk-compensation feedback.
7. Briefly cover the camera. The mode changes to `IMU-only` and returns to `Fusion` when the pose is visible again.

Dashboard controls:

| Key | Action |
|---|---|
| `b` | Reset the neutral trunk baseline |
| `r` | Reset the current repetition range |
| `q` or `Esc` | Quit and close the CSV file |

The default session file is `python/sessions/maixcam2_demo.csv`.

## Detection and feedback

| Output | Source | Meaning |
|---|---|---|
| `elbow_flexion` | IMU rules | Forearm bends and returns around the elbow |
| `forearm_rotation` | IMU rules | Forearm rotates around its long axis |
| `too_fast` | IMU rules | Peak angular velocity exceeds the configured limit |
| `insufficient_range` | IMU rules | Integrated movement angle is too small |
| `trunk_compensation` | Vision | Shoulder-to-hip displacement exceeds the allowed baseline change |

Firmware rules remain the safety fallback. The dashboard auto-loads `python/models/imu_cnnbigru.pt`, trained from a small public right-wrist IMU subset using 100-sample windows. ESP32 rule gating supplies the idle state, so no user-recorded training data are required. This checkpoint is a classroom demonstration baseline, not evidence of clinical accuracy.

## Tests

Run the full local check:

```bash
./scripts/test_all.sh
```

It runs the C motion/packet tests, Python tests, syntax checks, dashboard smoke test, and both ESP-IDF builds. The current suite contains 3 C host tests and 49 Python tests.

## Repository layout

```text
wearable/        MYOSA ESP32 firmware
receiver/        ESP32-S3 BLE receiver firmware
shared/          Packet, motion, and feedback logic shared by host tests
python/          Dashboard, synchronization, models, training, and tests
maixcam2/        MaixPy UVC/RTSP camera application
scripts/         Build, flash, camera probe, and demo launch helpers
tests/           Host-side C tests
docs/            Design and implementation records
```

## More documentation

- [MaixCAM 2 setup](maixcam2/README.md)
- [Complete wiring guide](WIRING_GUIDE.md)
- [Step-by-step demonstration guide](DEMO_GUIDE.md)
- [Bilingual component list](COMPONENTS.md)

## Safety and scope

LiteRehab is not intended for diagnosis, clinical scoring, treatment prescription, or unsupervised rehabilitation decisions. During a demonstration, stop immediately if the participant feels pain, dizziness, numbness, or unusual discomfort.
