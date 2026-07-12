# LiteRehab-Fusion MVP

Dual-board ESP32 BLE wearable for home upper-limb rehabilitation recording, with real-time IMU motion classification, MediaPipe vision fusion, and an optional CNN-BiGRU model.

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
│  │ Complementary filter      │  │                       │  │ LED (GPIO2)        │   │
│  │ α=0.98 gyro + accel grav  │  │                       │  │ Buzzer (GPIO18)    │   │
│  │ → roll / pitch            │  │                       │  │ LEDC PWM feedback  │   │
│  └───────────┬───────────────┘  │                       │  └─────────┬──────────┘   │
│              │                  │                       │            │              │
│  ┌───────────▼───────────────┐  │                       │  ┌─────────▼──────────┐   │
│  │ Adaptive threshold        │  │                       │  │ Serial telemetry   │   │
│  │ RMS-tracking, 25-150 dps  │  │                       │  │ CSV over USB-CDC   │   │
│  └───────────┬───────────────┘  │                       │  └─────────┬──────────┘   │
│              │                  │                       │            │              │
│  ┌───────────▼───────────────┐  │                       └────────────┼──────────────┘
│  │ 3-phase state machine     │  │                                    │
│  │ idle → enter → exit → rep │  │                           USB Serial
│  └───────────┬───────────────┘  │                                    │
│              │                  │                           ┌────────▼──────────────┐
│  ┌───────────▼───────────────┐  │                           │  Python Dashboard     │
│  │ SSD1306 OLED 128×64      │  │                           │  ┌──────────────────┐ │
│  │ state / reps / quality    │  │                           │  │ MediaPipe Pose   │ │
│  │ BLE connection status     │  │                           │  │ elbow angle      │ │
│  └───────────────────────────┘  │                           │  │ trunk detection  │ │
└─────────────────────────────────┘                           │  ├──────────────────┤ │
                                                              │  │ IMU gyro chart   │ │
                                                              │  │ 3-axis real-time │ │
                                                              │  ├──────────────────┤ │
                                                              │  │ CNN-BiGRU model  │ │
                                                              │  │ (optional)       │ │
                                                              │  ├──────────────────┤ │
                                                              │  │ Session CSV log  │ │
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

### 5. CNN-BiGRU (Obukhov et al. 2025)

Optional deep learning model for comparison with the rule-based classifier:

```
Input: [100 samples × 6 channels]  (2-second window at 50 Hz)
├── Conv1d(6→64, k=3) + BN + ReLU + MaxPool(2)   → [50 × 64]
├── Conv1d(64→128, k=3) + BN + ReLU + MaxPool(2)  → [25 × 128]
├── Conv1d(128→256, k=3) + BN + ReLU              → [25 × 256]
├── BiGRU(256→128×2)                               → [25 × 256]
├── Temporal mean pool                             → [256]
├── Dropout(0.5) + Linear(256 → num_classes)
```

Parameters: ~423K. CPU inference: 5–10 ms per window.

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
│   └── motion_logic.h/c     #   Complementary filter + adaptive threshold + state machine
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
│       └── receiver_outputs.h/c #  LED + LEDC PWM buzzer feedback
├── python/
│   ├── literehab/
│   │   ├── telemetry.py     #   Serial line parser → TelemetrySample
│   │   ├── fusion.py        #   IMU + vision feedback fusion (5 priority levels)
│   │   ├── pose_math.py     #   Joint angle + trunk compensation detection
│   │   ├── cnn.py           #   1D-CNN and CNN-BiGRU model builders
│   │   └── dataset.py       #   Sliding window (100 samples, stride 50)
│   ├── run_dashboard.py     #   OpenCV dashboard with MediaPipe pose
│   ├── collect_data.py      #   Labeled data recorder
│   ├── train_1d_cnn.py      #   CNN training script (--arch cnn_bigru default)
│   └── tests/               #   pytest: telemetry, fusion, pose_math, dataset
├── tests/                   # Host-side C tests
│   ├── test_motion_packet.c #   CRC integrity and tamper detection
│   ├── test_motion_logic.c  #   Rotation/flexion/fast/short-range assertions
│   └── run_host_tests.sh    #   Compile and run C tests
├── scripts/
│   ├── build_all.sh         #   idf.py build for both boards
│   └── test_all.sh          #   C tests + pytest + py_compile + firmware build
├── COMPONENTS.md            #   Bilingual component list
├── WIRING_GUIDE.md          #   Step-by-step assembly with safety checks
└── DEMO_GUIDE.md            #   Full demonstration walkthrough
```

## Quick Start

### 1. Flash firmware

```bash
source ~/.espressif/v6.0.2/esp-idf/export.sh

# Wearable (ESP32)
cd wearable
idf.py set-target esp32
idf.py -p /dev/cu.usbserial-* -b 460800 flash

# Receiver (ESP32-S3) — use native USB port
cd ../receiver
idf.py set-target esp32s3
idf.py -p /dev/cu.usbmodem-* -b 460800 flash
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
python run_dashboard.py --port auto --camera 0 --output sessions/demo.csv
```

Controls: `q`/`Esc` quit, `b` reset torso baseline, `r` reset the current
repetition range.

## Upgraded RGB-IMU workflow

The dashboard runs without a trained model and supports either affected side:

```bash
python run_dashboard.py --port auto --camera 0 --side left \
  --output sessions/demo.csv
```

It now uses MediaPipe video mode, repetition-scoped range, timestamped RGB/IMU
association, and a lossless synchronized CSV schema. To collect one labelled
recording, keep one exercise/quality pair per file:

```bash
python run_dashboard.py --port auto --side right --subject S01 \
  --label-exercise elbow_flexion --label-quality ok \
  --output multimodal_data/S01_elbow_ok.csv
```

Train only after collecting multiple participants, with one entire participant
held out:

```bash
python train_multimodal.py --data multimodal_data --holdout-subject S03 \
  --output models/multimodal_cnn_bigru.pt

python run_dashboard.py --port auto --side right \
  --fusion-model models/multimodal_cnn_bigru.pt
```

Low-confidence or missing model output automatically falls back to the
deterministic wearable rules. No trained multimodal checkpoint is included,
because the existing demo CSV files are not subject-labelled training data.

## Build and flash helpers

Run the complete software and firmware gate:

```bash
./scripts/test_all.sh
```

When the boards are available, identify each port with `ls /dev/cu.*` and flash
one board at a time:

```bash
./scripts/flash_wearable.sh /dev/cu.usbserial-WEARABLE
./scripts/flash_receiver.sh /dev/cu.usbmodem-RECEIVER
```

These commands generate and write the normal ESP-IDF bootloader, partition
table, and application image. Physical BLE, OLED, LED, buzzer, and camera
integration still requires the actual boards and cannot be certified by a
host-only build.

If MediaPipe or camera is unavailable, the dashboard falls back to IMU-only mode.

### 4. Run all tests

```bash
cd ..
./scripts/test_all.sh
```

## Data Collection & Training

Collect 30-second recordings per subject per class:

```bash
python collect_data.py --port auto --subject S01 --label idle --seconds 30
python collect_data.py --port auto --subject S01 --label forearm_rotation --seconds 30
python collect_data.py --port auto --subject S01 --label elbow_flexion --seconds 30
```

Repeat for at least 3 subjects. Train with one subject held out:

```bash
python train_1d_cnn.py --data data --holdout-subject S03 \
  --arch cnn_bigru --epochs 50 --output models/imu_cnn_bigru.pt
```

Run dashboard with the trained model:

```bash
python run_dashboard.py --port auto --model models/imu_cnn_bigru.pt
```

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
