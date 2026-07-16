# ESP32-S3 ECG Receiver Integration Design

## Goal

Integrate the merged CJMCU-8232 ECG proof of concept into the existing ESP-IDF receiver firmware while keeping the wearable light enough for a stable rehabilitation demo. The result must preserve the current MPU6050-to-BLE motion path, reuse the receiver buzzer, move the OLED to the receiver, and provide explicit lead-off and heart-rate status.

This is a classroom prototype, not a medical device. ECG values are demonstration signals only and must not be presented as diagnostic measurements.

## Selected hardware architecture

The wearable contains only the MYOSA ESP32 and MPU6050. Both boards are fixed to the same rigid backing, and the short JST cable is strain-relieved so it cannot swing and contaminate motion readings.

The ESP32-S3 receiver becomes the wired display and feedback hub:

| Function | ESP32-S3 pin | Peripheral pin |
|---|---:|---|
| Connection LED | GPIO2 | LED through 220–330 ohm resistor |
| ECG analog input | GPIO4 / ADC1_CH3 | CJMCU-8232 `OUTPUT` |
| ECG positive lead-off | GPIO5 | CJMCU-8232 `LO+` |
| ECG negative lead-off | GPIO6 | CJMCU-8232 `LO-` |
| OLED SDA | GPIO8 | SSD1306 `SDA` |
| OLED SCL | GPIO9 | SSD1306 `SCL` |
| Passive buzzer | GPIO18 | Buzzer through 100–330 ohm resistor |
| Power | 3V3 | CJMCU-8232 and OLED VCC |
| Ground | GND | All receiver-side grounds |
| ECG enable | 3V3 | CJMCU-8232 `SDN` |

GPIO19 and GPIO20 remain reserved for native USB. GPIO35–GPIO37 are not used because the N16R8 module uses octal memory and GPIO36 is not an ESP32-S3 ADC input. The merged Arduino sketch's GPIO36 assignment is therefore intentionally not preserved.

## Alternatives considered

1. **Receiver hub with OLED and ECG — selected.** This removes the OLED tail from the wearable, avoids BLE protocol changes, and keeps all user-visible feedback together.
2. **Keep OLED on the wearable.** This changes less firmware but adds mass and a moving I2C cable beside the MPU6050, which is undesirable for the demo.
3. **Send ECG through the wearable BLE packet.** This would make the subject fully wireless but requires new wearable wiring, a new packet version, higher BLE traffic, and coordinated changes across firmware and Python. It is outside the minimum-change goal.

## Firmware structure

### Minimal port of the teammate ECG detector

Add `shared/ecg_logic.c` and `shared/ecg_logic.h`. This is a direct, testable C port of the teammate's intended Arduino behavior. It accepts timestamped raw ADC samples and a lead-off flag, and returns connection state, beat event, BPM, and rapid-change alert.

The following teammate-defined constants and behavior remain unchanged:

- raw ADC threshold: 2500;
- minimum interval between accepted beats: 250 ms;
- BPM calculation: `60000 / interval_ms`;
- rapid-change threshold: absolute difference greater than 20 BPM;
- rapid buzzer pattern: five 50 ms on / 50 ms off pulses;
- either lead-off input high means the electrodes are disconnected.

One required latch release is added: after the ADC value falls back below 2500, `beatDetected` becomes false. The merged sketch never clears this flag, so without this correction it can only detect one threshold crossing and can never calculate a second BPM. This correction implements the sketch's apparent intended edge-detection behavior without introducing adaptive thresholds, smoothing, clinical ranges, or a new detection algorithm.

All timing and detection behavior remains independent of ESP-IDF so it can be covered by host tests.

### Receiver ECG driver

Add `receiver/main/ecg_monitor.c` and `ecg_monitor.h`. It owns an ESP-IDF ADC oneshot handle, configures GPIO5/GPIO6 as lead-off inputs, and samples GPIO4 at 100 Hz in a FreeRTOS task. This fixed delay replaces the Arduino `loop()` without changing the threshold logic or monopolizing the receiver CPU.

The receiver emits the following additional serial record at up to 100 Hz:

```text
ECG,t_ms,raw_adc,bpm,leads_connected,beat,rapid_change
```

The task invokes callbacks for display state and rapid-change alerts. ADC initialization failure is non-fatal to BLE reception: the receiver logs the error, shows ECG unavailable, and continues its existing motion path.

### OLED placement

Keep the wearable OLED implementation intact for compatibility. The receiver reuses that existing SSD1306 driver and adds only a receiver-side display wrapper. The documented demo wiring places the single OLED on the receiver; the wearable already continues normally when no OLED is found.

The receiver initializes I2C on GPIO8/GPIO9 and refreshes the OLED no faster than 5 Hz. The screen shows:

```text
LITEREHAB
BLE OK / WAIT
ECG BPM 072
LEADS OK / OFF
REPS 005
OK / FAST / RANGE
```

Display absence or an I2C error is non-fatal; BLE, serial telemetry, ECG sampling, LED, and buzzer continue.

### Buzzer coordination

Keep GPIO18 and the existing LEDC configuration. Extend the receiver output queue with a receiver-local rapid-alert command rather than changing shared motion feedback semantics. Motion success/warning patterns and ECG rapid alerts are serialized through the same output task, so two parts of the firmware never drive the buzzer concurrently.

The ECG rapid pattern is five 50 ms high-frequency tones separated by 50 ms pauses. ECG sampling continues while the pattern plays because the buzzer runs in its own task.

### Dashboard integration and compatibility

The 26-byte motion packet and wearable BLE service remain unchanged. Existing `IMU,...` serial records keep exactly the same schema. Python adds an `ECG,...` parser and a separate queue so the new records do not enter the IMU synchronizer or CNN.

The dashboard replaces the lower-right gyroscope plot with a rolling ECG waveform plus BPM and lead status. It writes the received ECG records to a companion `*_ecg.csv` file. The existing synchronized IMU/pose session CSV, multimodal model inputs, exercise decisions, and feedback fusion remain unchanged. ECG is displayed and recorded, but it does not alter rehabilitation decisions.

The merged `python/ecg/pulse_and_change_monitor.c` Arduino sketch remains unchanged as the teammate's reference implementation. The runnable ESP-IDF port lives in the receiver project because Arduino APIs and GPIO36 cannot run in the current ESP32-S3 N16R8 receiver configuration.

## Mechanical and electrical arrangement

- Fix the wearable ESP32 and MPU6050 on one rigid plate; tape down the entire JST cable except for a small strain-relief curve.
- Put the CJMCU-8232 at the opposite side of the receiver breadboard from the buzzer and USB cable.
- Keep the CJMCU `OUTPUT` to GPIO4 wire short and do not bundle it with the buzzer wire.
- Use only the ESP32-S3 3.3 V rail for the CJMCU-8232 and OLED.
- Identify RA, LA, and RL from the electrode connector labels rather than relying only on cable colors.
- While electrodes are attached to a person, run the laptop from battery with its mains charger disconnected.

## Verification

### Automated

- Add host tests for lead-off behavior, threshold latch release, 250 ms refractory rejection, BPM calculation, and the greater-than-20-BPM rapid-change event.
- Add Python tests for the new ECG serial record, bounded ECG queue, dashboard waveform/status rendering, and companion CSV naming.
- Run all existing C and Python tests.
- Build both ESP-IDF firmware projects with ESP-IDF 6.0.2.
- Confirm the Python telemetry parser still ignores `# ECG` comment lines.

### Hardware acceptance

1. Boot the S3 with no ECG electrodes: BLE continues scanning, OLED shows `LEADS OFF`, and no ECG alert sounds.
2. Attach leads and remain still for signal settling: OLED changes to `LEADS OK` and shows a plausible, stable BPM after several beats.
3. Disconnect one lead: OLED returns to `LEADS OFF`, beat history resets, and the buzzer remains silent.
4. Run the wearable simultaneously: BLE connects, repetitions and quality still update on the receiver OLED, and serial motion telemetry remains valid.
5. Trigger motion success/warning and an ECG test alert: all tones are serialized without receiver reset or stuck output.
6. Run the complete setup for at least three minutes and check that USB serial, BLE, OLED, ADC, LED, and buzzer remain responsive.
