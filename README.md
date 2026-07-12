# LiteRehab-Fusion MVP

Dual-board ESP32 BLE wearable for home upper-limb rehabilitation recording, with real-time IMU motion classification, MediaPipe vision fusion, and an optional multimodal CNN-BiGRU model.

## System Architecture

```
┌─────────────────────────────────┐     BLE (NimBLE)     ┌──────────────────────────┐
│  MYOSA ESP32 (wearable)         │ ◄──────────────────► │  ESP32-S3 (receiver)      │
│  ┌───────────────────────────┐  │   motion_packet      │  ┌────────────────────┐   │
│  │ MPU6050  6-axis IMU       │  │   26 bytes            │  │ CRC-16 validation  │   │
│  │ 250 Hz, ±250 dps / ±2 g   │  │   magic + seq + ts   │  │ sequence gap check │   │
│  └───────────┬───────────────┘  │   accel×3 + gyro×3   │  └─────────┬──────────┘   │
│              │                  │   state + quality     │            │              │
│  ┌───────────▼───────────────┐  │   + rep_count         │  ┌─────────▼──────────┐   │
│  │ Complementary filter      │  │                       │  │ Feedback state     │   │
│  │ α=0.98 gyro + accel grav  │  │                       │  │ machine: one-shot  │   │
│  │ → roll / pitch            │  │                       │  │ buzzer per event   │   │
│  └───────────┬───────────────┘  │                       │  └─────────┬──────────┘   │
│              │                  │                       │            │              │
│  ┌───────────▼───────────────┐  │                       │  ┌─────────▼──────────┐   │
│  │ Adaptive threshold        │  │                       │  │ LED (GPIO2)        │   │
│  │ RMS-tracking, 25-150 dps  │  │                       │  │ Buzzer (GPIO18)    │   │
│  │ (rest-only update)        │  │                       │  │ LEDC PWM feedback  │   │
│  └───────────┬───────────────┘  │                       │  └─────────┬──────────┘   │
│              │                  │                       │            │              │
│  ┌───────────▼───────────────┐  │                       │  ┌─────────▼──────────┐   │
│  │ 3-phase state machine     │  │                       │  │ Serial telemetry   │   │
│  │ idle → enter → exit → rep │  │                       │  │ CSV over USB-CDC   │   │
│  └───────────┬───────────────┘  │                       │  └─────────┬──────────┘   │
│              │                  │                       │            │              │
│  ┌───────────▼───────────────┐  │                       └────────────┼──────────────┘
│  │ SSD1306 OLED 128×64      │  │                                    │
│  │ state / reps / quality    │  │                           USB Serial
│  │ BLE connection status     │  │                                    │
│  └───────────────────────────┘  │                           ┌────────▼──────────────┐
└─────────────────────────────────┘                           │  Python Dashboard     │
                                                              │  ┌──────────────────┐ │
                                                              │  │ MediaPipe Pose   │ │
                                                              │  │ left/right side  │ │
                                                              │  │ elbow + shoulder │ │
                                                              │  │ trunk detection  │ │
                                                              │  ├──────────────────┤ │
                                                              │  │ IMU gyro chart   │ │
                                                              │  │ 3-axis real-time │ │
                                                              │  ├──────────────────┤ │
                                                              │  │ Multimodal model │ │
                                                              │  │ IMU + vision CNN │ │
                                                              │  │ confidence gate +│ │
                                                              │  │ rule fallback    │ │
                                                              │  ├──────────────────┤ │
                                                              │  │ Sync CSV log     │ │
                                                              │  │ lossless IMU+RGB │ │
                                                              │  └──────────────────┘ │
                                                              └───────────────────────┘
```

### Recognized States

| State | Identifier | Description |
|-------|-----------|-------------|
| Idle | `idle` | No motion detected |
| Forearm rotation | `forearm_rotation` | Wrist rotation around forearm axis |
| Elbow flexion | `elbow_flexion` | Forearm bending/extending at elbow |

### Feedback Quality

| Quality | Identifier | Buzzer | Meaning |
|---------|-----------|--------|---------|
| OK | `ok` | Single high beep (880 Hz) | Range and speed within bounds |
| Too fast | `too_fast` | Two low tones (280→220 Hz) | Peak angular velocity exceeded |
| Insufficient range | `insufficient_range` | Two low tones | Total rotation angle too small |
| Trunk compensation | `trunk_compensation` | Visual only | Shoulder-hip displacement ≥ 15% torso |

## Algorithm

### 1. Complementary Filter (Wang 2026)

Gyroscope integration provides short-term orientation; accelerometer gravity vector corrects long-term drift:

```
roll  = 0.98 × (roll  + gx × dt) + 0.02 × atan2(ay, az)
pitch = 0.98 × (pitch + gy × dt) + 0.02 × atan2(-ax, √(ay² + az²))
```

### 2. Adaptive Threshold (Khalilipour 2025)

Resting-signal RMS is tracked with exponential smoothing (α=0.95). It is
updated only below the fixed entry threshold, so an active repetition cannot
raise its own reversal threshold:

```
rms = √(0.95 × rms² + 0.05 × signal²)
enter = clamp(45 + 0.8 × rms, 25, 150) dps
exit  = enter × 0.33
```

This prevents false triggers during rest while keeping sensitivity for slow movements.

### 3. Three-Phase State Machine

```
      idle detection           direction change          velocity ↓ exit
 ┌──────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
 │ phase 0: idle    │───►│ phase 1: accumulate   │───►│ phase 2: exit    │───► rep counted
 │ |gyro| > enter?  │    │ integrate abs angle   │    │ |gyro| ≤ exit?   │
 │ classify axis    │    │ track peak dps        │    │                  │
 └──────────────────┘    └──────────────────────┘    └─────────────────┘
                                 │                          │
                           max_rep_duration exceeded ───────┘ → discarded
                                 (5000 ms)
```

### 4. Axis Classification

Gyroscope dominance ratio distinguishes rotation from flexion:

- `|gx| / |gy| ≥ 1.30` and accelerometer X-dominant → forearm rotation
- `|gy| / |gx| ≥ 1.30` and accelerometer Y-dominant → elbow flexion
- Otherwise → hold previous state

### 5. Feedback State Machine

The receiver runs a one-shot feedback state machine that tracks per-state
transitions. A success beep only fires once per completed repetition, and
warning events do not retrigger until the motion state changes. This prevents
persistent BLE quality values from queuing repeated buzzer events.

### 6. Multimodal CNN-BiGRU (Obukhov et al. 2025)

Optional dual-branch model that fuses IMU and vision. Confidence-gated: the
vision branch is attenuated by per-window visibility, and low-confidence
outputs automatically fall back to the deterministic wearable rules.

```
IMU branch:                            Pose branch:
[100×6]                                [100×9]
├── Conv1d(6→32,k5)+BN+ReLU+MP(2)      ├── Conv1d(9→32,k5)+BN+ReLU+MP(2)
├── Conv1d(32→64,k3)+BN+ReLU+MP(2)     ├── Conv1d(32→64,k3)+BN+ReLU+MP(2)
├── BiGRU(64→64×2)                     ├── BiGRU(64→64×2)
└── mean pool → [128]                  └── mean pool × confidence → [128]

Fusion: Concat[256] → Linear(256→128) + ReLU + Dropout(0.3)
        ├── Exercise head: Linear(128 → num_exercises)
        └── Quality head:  Linear(128 → num_qualities)
```

Parameters: ~300K. CPU inference: 5–10 ms per window.

## Decision Resolution

```
if rule quality is warning (too_fast / insufficient_range):
    → rule safety override (always)
elif model available and confidence ≥ threshold:
    → multimodal model prediction
else:
    → deterministic rule fallback
```

## Hardware

### Required Components

| Qty | Component | Purpose |
|----:|-----------|---------|
| 1 | MYOSA ESP32 WROOM-32E | Wearable sensing and BLE peripheral |
| 1 | ESP32-S3-DevKitC-1 N16R8 | BLE central receiver and USB gateway |
| 1 | MPU6050 6-axis IMU | Arm motion sensing |
| 1 | SSD1306 128×64 OLED | Local status display |
| 2 | 4-pin JST F-F cables | MYOSA → MPU6050 → OLED cascade |
| 1 | Passive buzzer | Audio feedback |
| 1 | LED + 220 Ω resistor | Receiver status indicator |
| 1 | Breadboard + jumper wires | Receiver wiring |
| 2 | USB data cables | Power, flashing, serial |
| 1 | Laptop with webcam | Vision + Python dashboard |

### Wiring

**Wearable** — JST cascade only, no breadboard:

```
MYOSA I2C port ── JST ──► MPU6050 ── JST ──► SSD1306 OLED
```

MPU6050 orientation: fixed on dorsal forearm, X axis toward hand, Z axis outward.

**Receiver** — breadboard:

```
ESP32-S3 GPIO2  ── 220Ω ── LED (+)    │   LED (-) ── GND
ESP32-S3 GPIO18 ── 100Ω ── Buzzer (+) │ Buzzer (-) ── GND
```

Use the native USB port (labeled **USB**), not the UART port.

## Folder Structure

```
lite_rehab_mvp/
├── shared/                  # Cross-board C modules
│   ├── motion_packet.h/c    #   CRC-16 BLE packet (26 bytes)
│   ├── motion_logic.h/c     #   Complementary filter + adaptive threshold + state machine
│   └── feedback_logic.h/c   #   One-shot buzzer state machine (per-state debounce)
├── wearable/                # MYOSA ESP32 firmware (NimBLE Peripheral)
│   └── main/
│       ├── app_main.c       #   20 ms sampling loop
│       ├── mpu6050.h/c      #   I2C driver, 250 Hz, 100-sample gyro bias calibration
│       ├── ssd1306.h/c      #   I2C OLED, 5×7 bitmap font
│       ├── ble_server.h/c   #   NimBLE GATT notify server
│       └── wearable_status.h/c  # GPIO2 status LED
├── receiver/                # ESP32-S3 firmware (NimBLE Central)
│   └── main/
│       ├── app_main.c       #   Packet dispatch with sequence gap detection
│       ├── ble_client.h/c   #   BLE scan → connect → service discovery → CCCD subscribe
│       ├── serial_telemetry.h/c #  CSV output over USB-CDC
│       └── receiver_outputs.h/c #  Feedback state machine + LED + LEDC PWM buzzer
├── python/
│   ├── literehab/
│   │   ├── telemetry.py     #   Serial line parser → TelemetrySample
│   │   ├── fusion.py        #   IMU + vision feedback fusion (5 priority levels)
│   │   ├── pose_math.py     #   Joint angle + trunk compensation detection
│   │   ├── pose_features.py #   Side-aware pose extraction (left/right)
│   │   ├── synchronization.py   #  Timestamped IMU-RGB sample pairing
│   │   ├── multimodal.py    #   Dual-branch CNN-BiGRU + checkpoint load + predictor
│   │   ├── dashboard_state.py   #  Decision resolution + camera health + CSV schema
│   │   ├── cnn.py           #   1D-CNN and CNN-BiGRU model builders
│   │   └── dataset.py       #   Sliding window (100 samples, stride 50)
│   ├── run_dashboard.py     #   OpenCV dashboard with MediaPipe + synchronized logging
│   ├── collect_data.py      #   Labeled IMU data recorder (rule-only)
│   ├── train_1d_cnn.py      #   IMU-only CNN training (--arch cnn_bigru default)
│   ├── train_multimodal.py  #   Multimodal IMU+vision training
│   ├── requirements.txt     #   numpy, opencv, pyserial, pytest, mediapipe, torch
│   └── tests/               #   pytest: telemetry, fusion, pose_math, pose_features,
│                             #          synchronization, multimodal, dashboard_state
├── tests/                   # Host-side C tests (3 executables)
│   ├── test_motion_packet.c #   CRC integrity and tamper detection
│   ├── test_motion_logic.c  #   Rotation/flexion/fast/short-range assertions
│   ├── test_feedback_logic.c#   One-shot state transition coverage
│   └── run_host_tests.sh    #   Compile and run all C tests
├── scripts/
│   ├── build_all.sh         #   idf.py build for both boards
│   ├── test_all.sh          #   C tests + pytest + py_compile + firmware build
│   ├── flash_wearable.sh    #   ESP32 flash helper
│   └── flash_receiver.sh    #   ESP32-S3 flash helper
├── COMPONENTS.md            #   Bilingual component list
├── WIRING_GUIDE.md          #   Step-by-step assembly with safety checks
└── DEMO_GUIDE.md            #   Full demonstration walkthrough
```

## Quick Start

### 1. Flash firmware

```bash
source ~/.espressif/v6.0.2/esp-idf/export.sh

./scripts/flash_wearable.sh /dev/cu.usbserial-WEARABLE
./scripts/flash_receiver.sh /dev/cu.usbmodem-RECEIVER
```

For ESP32-S3 flashing issues, use manual download mode: hold BOOT, press RST, release BOOT, then flash.

### 2. Install Python dependencies

```bash
conda create -n literehab python=3.12 -y
conda activate literehab
cd python
pip install -r requirements.txt
```

### 3. Launch dashboard

```bash
python run_dashboard.py --port auto --camera 0 --side left \
  --output sessions/demo.csv
```

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `auto` | Serial port or `auto` |
| `--camera` | `0` | Camera device index |
| `--side` | required | `left` or `right` (affected limb) |
| `--output` | `sessions/session.csv` | CSV log path |
| `--model` | none | IMU-only CNN-BiGRU checkpoint |
| `--fusion-model` | none | Multimodal IMU+vision checkpoint |
| `--subject` | `""` | Subject ID for labelled recording |
| `--label-exercise` | `""` | Exercise label for one recording |
| `--label-quality` | `""` | Quality label for one recording |

Controls: `q`/`Esc` quit, `b` reset torso baseline, `r` reset repetition range.

If MediaPipe or camera is unavailable, the dashboard falls back to IMU-only mode.

### 4. Run all tests

```bash
cd ..
./scripts/test_all.sh
```

This runs: 3 C host executables + 34 Python tests + py_compile syntax check + both firmware builds.

## Data Collection & Training

### IMU-only (rule-based labels)

```bash
python collect_data.py --port auto --subject S01 --label idle --seconds 30
python collect_data.py --port auto --subject S01 --label forearm_rotation --seconds 30
python collect_data.py --port auto --subject S01 --label elbow_flexion --seconds 30

python train_1d_cnn.py --data data --holdout-subject S03 \
  --arch cnn_bigru --epochs 50 --output models/imu_cnn_bigru.pt

python run_dashboard.py --port auto --model models/imu_cnn_bigru.pt
```

### Multimodal (IMU + vision, side-aware)

Collect labelled recordings directly from the dashboard — one exercise/quality pair per file:

```bash
python run_dashboard.py --port auto --side right --subject S01 \
  --label-exercise elbow_flexion --label-quality ok \
  --output multimodal_data/S01_elbow_ok.csv

python run_dashboard.py --port auto --side right --subject S01 \
  --label-exercise elbow_flexion --label-quality too_fast \
  --output multimodal_data/S01_elbow_fast.csv
```

Train with one participant held out:

```bash
python train_multimodal.py --data multimodal_data --holdout-subject S03 \
  --output models/multimodal_cnn_bigru.pt

python run_dashboard.py --port auto --side right \
  --fusion-model models/multimodal_cnn_bigru.pt
```

Low-confidence model output falls back to deterministic wearable rules automatically.

## CSV Schema

Every received IMU sample is logged. When no matching video frame is found
within the synchronization tolerance (50 ms), vision columns are explicit
missing markers (= 0.0, `vision_valid` = 0).

| Column | Description |
|--------|-------------|
| `t_ms`, `received_s` | Device timestamp (ms) + host receive time (s) |
| `ax`–`gz` | Accelerometer (g) and gyroscope (dps) |
| `state`, `rep_count`, `quality` | Wearable classifier output |
| `elbow_angle_deg`–`visibility` | 9 pose feature channels |
| `vision_valid` | 1.0 when a matching frame exists |
| `model_exercise`–`model_confidence` | Multimodal model output (empty if unused) |
| `visual_confidence` | Per-window visibility × validity |
| `subject`, `label_exercise`, `label_quality` | Human labels for training |

## Threshold Calibration

Default thresholds are defined in `motion_default_config()` (`shared/motion_logic.c`). Key parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enter_threshold_dps` | 45 | Entry threshold (dps) |
| `exit_threshold_dps` | 15 | Exit threshold (dps) |
| `dominance_ratio` | 1.30 | Gyro axis dominance ratio |
| `min_range_deg` | 35 | Minimum rotation range per rep |
| `too_fast_peak_dps` | 280 | Peak speed warning threshold |
| `min_rep_duration_ms` | 450 | Shortest valid repetition |
| `max_rep_duration_ms` | 5000 | Longest valid repetition |
| `refractory_ms` | 300 | Cooldown between reps |
| `adapt_k` | 0.8 | Adaptive threshold gain |
| `adapt_floor_dps` / `adapt_ceil_dps` | 25 / 150 | Adaptive bounds |

If axes are reversed by physical mounting, change the two gyro inputs passed to `motion_logic_update()` in `wearable/main/app_main.c`.

## Safety & Scope

This is an engineering prototype. It does **not** diagnose injury, prescribe treatment, predict clinical scores, or replace a physiotherapist.

## References

- Wang, Y. et al. (2026). Complementary filtering for wearable IMU orientation estimation.
- Khalilipour, S. et al. (2025). Adaptive thresholding for IMU-based rehabilitation exercise detection.
- Obukhov, A. et al. (2025). CNN-BiGRU architectures for time-series human activity recognition.
