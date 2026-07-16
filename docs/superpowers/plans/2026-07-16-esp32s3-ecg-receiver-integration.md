# ESP32-S3 ECG Receiver Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the merged CJMCU-8232 Arduino behavior into the ESP32-S3 receiver, move the demo OLED to that receiver, and add ECG waveform/BPM display and companion logging to the dashboard without changing motion decisions.

**Architecture:** A portable `ecg_logic` module preserves the teammate's fixed threshold, refractory interval, BPM delta, and buzzer pattern. An ESP-IDF receiver task samples GPIO4 and publishes a separate `ECG,...` serial record; Python parses it into an independent queue, renders it, and writes `*_ecg.csv`, while the existing IMU/pose synchronization and models remain untouched.

**Tech Stack:** C17 host tests, ESP-IDF 6.0.2 (ADC oneshot, GPIO, I2C, LEDC, FreeRTOS), Python 3.12, pytest, NumPy, OpenCV.

## Global Constraints

- Preserve ECG threshold `2500`, refractory interval `250 ms`, BPM delta `> 20`, and five `50 ms` on/off rapid buzzer pulses.
- Add only the missing below-threshold latch release and reset stale state when leads disconnect.
- Keep the 26-byte BLE packet and every existing `IMU,...` field unchanged.
- ECG must not feed the CNN, multimodal predictor, repetition count, motion quality, or feedback fusion.
- Use receiver pins GPIO4 ECG OUT, GPIO5 LO+, GPIO6 LO-, GPIO8 OLED SDA, GPIO9 OLED SCL, GPIO18 buzzer, and GPIO2 LED.
- Keep `python/ecg/pulse_and_change_monitor.c` unchanged as teammate reference code.
- Treat OLED/ECG initialization failure as non-fatal to BLE motion reception.

---

### Task 1: Portable teammate ECG logic

**Files:**
- Create: `shared/ecg_logic.h`
- Create: `shared/ecg_logic.c`
- Create: `tests/test_ecg_logic.c`
- Modify: `tests/run_host_tests.sh`

**Interfaces:**
- Produces: `void ecg_logic_init(ecg_logic_t *logic)` and `ecg_result_t ecg_logic_update(ecg_logic_t *logic, int raw_adc, bool leads_off, uint32_t now_ms)`.
- `ecg_result_t` contains `leads_connected`, `beat`, `rapid_change`, and `bpm`.

- [ ] **Step 1: Write failing tests for the teammate behavior**

Cover an accepted threshold crossing after 250 ms, rejection inside 250 ms, below-threshold latch release, `60000 / delta_ms`, rapid change only when `fabsf(bpm-last_bpm) > 20`, and lead-off state reset.

- [ ] **Step 2: Run the focused host test and verify RED**

Run: `cc -std=c17 -Wall -Wextra -Werror -Ishared tests/test_ecg_logic.c shared/ecg_logic.c -lm -o /tmp/test_ecg_logic`

Expected: compilation fails because `shared/ecg_logic.h` and implementation do not exist.

- [ ] **Step 3: Implement the minimal state machine**

Use these constants exactly:

```c
#define ECG_THRESHOLD 2500
#define ECG_REFRACTORY_MS 250u
#define ECG_RAPID_CHANGE_BPM 20.0f
```

Set `beat_detected=false` when `raw_adc <= ECG_THRESHOLD`; on a valid rising crossing calculate BPM from `now_ms-last_beat_ms`, compare with the previous BPM, then latch until the signal falls below threshold. Reset timestamps/BPM/latch when `leads_off` is true.

- [ ] **Step 4: Add and run the host-test target**

Run: `./tests/run_host_tests.sh`

Expected: four C test executables complete with exit code 0.

- [ ] **Step 5: Commit**

```bash
git add shared/ecg_logic.c shared/ecg_logic.h tests/test_ecg_logic.c tests/run_host_tests.sh
git commit -m "feat: port teammate ECG threshold logic"
```

### Task 2: ESP32-S3 ECG sampling and serialized buzzer output

**Files:**
- Create: `receiver/main/ecg_monitor.h`
- Create: `receiver/main/ecg_monitor.c`
- Modify: `receiver/main/serial_telemetry.h`
- Modify: `receiver/main/serial_telemetry.c`
- Modify: `receiver/main/receiver_outputs.h`
- Modify: `receiver/main/receiver_outputs.c`
- Modify: `receiver/main/app_main.c`
- Modify: `receiver/main/CMakeLists.txt`

**Interfaces:**
- Produces: `esp_err_t ecg_monitor_init(ecg_monitor_callback_t callback)` and callback payload `ecg_monitor_sample_t { timestamp_ms, raw_adc, ecg_result_t result }`.
- Produces: `void serial_telemetry_ecg(const ecg_monitor_sample_t *sample)` with format `ECG,t_ms,raw_adc,bpm,leads_connected,beat,rapid_change`.
- Produces: `void receiver_outputs_ecg_alert(void)` that queues, rather than directly plays, the rapid pattern.

- [ ] **Step 1: Extend host-visible tests before firmware code**

Add source assertions or a small host formatting boundary only if needed; the behavioral detector is already covered in Task 1. Verify the new receiver files are absent before implementation.

- [ ] **Step 2: Implement ADC/GPIO task**

Configure ADC1 channel 3, 12-bit default width, 12 dB attenuation, GPIO5/GPIO6 inputs, and a 10 ms FreeRTOS loop. Call the callback every sample and continue sampling during buzzer playback.

- [ ] **Step 3: Extend output queue and serial format**

Replace the queue payload with a receiver-local enum containing motion success, motion warning, and ECG rapid alert. Keep existing tones identical and add five 1000 Hz, 50 ms tones with 50 ms gaps. Add the exact ECG header and record.

- [ ] **Step 4: Wire the callback in `app_main.c`**

For every sample, publish serial telemetry, update display state from Task 3, and enqueue a rapid alert only when `result.rapid_change` is true. Log ECG initialization failure and continue BLE initialization.

- [ ] **Step 5: Build receiver**

Run: `. ~/.espressif/v6.0.2/esp-idf/export.sh >/dev/null 2>&1 && idf.py -C receiver build`

Expected: `Project build complete` and exit code 0.

- [ ] **Step 6: Commit**

```bash
git add receiver/main shared/ecg_logic.c shared/ecg_logic.h
git commit -m "feat: sample CJMCU-8232 on ESP32-S3 receiver"
```

### Task 3: Receiver OLED status

**Files:**
- Create: `receiver/main/receiver_display.h`
- Create: `receiver/main/receiver_display.c`
- Modify: `receiver/main/app_main.c`
- Modify: `receiver/main/CMakeLists.txt`

**Interfaces:**
- Produces: `esp_err_t receiver_display_init(void)`, `receiver_display_set_connected(bool)`, `receiver_display_set_motion(const motion_packet_t *)`, and `receiver_display_set_ecg(const ecg_monitor_sample_t *)`.
- Reuses: `wearable/main/ssd1306.c` and `wearable/main/ssd1306.h` without modifying wearable behavior.

- [ ] **Step 1: Add compile-time interface calls before implementation**

Include `receiver_display.h` from `app_main.c` and add calls for connection, motion, and ECG state. Build once and confirm the missing header failure.

- [ ] **Step 2: Implement non-fatal I2C display task**

Create I2C master bus GPIO8/GPIO9, initialize SSD1306 address `0x3C`, protect shared status with a mutex, and refresh every 200 ms with BLE, BPM/lead, reps, and quality rows. Return errors instead of aborting.

- [ ] **Step 3: Register the shared display source and I2C dependency**

Compile `../../wearable/main/ssd1306.c`, add `../../wearable/main` to include paths, and add `esp_driver_i2c` plus `esp_driver_adc` to receiver private requirements.

- [ ] **Step 4: Build both boards**

Run: `./scripts/build_all.sh`

Expected: wearable and receiver both finish with exit code 0.

- [ ] **Step 5: Commit**

```bash
git add receiver/main
git commit -m "feat: move demo status display to receiver"
```

### Task 4: Dashboard ECG parser, queue, waveform, and companion CSV

**Files:**
- Modify: `python/literehab/telemetry.py`
- Modify: `python/run_dashboard.py`
- Modify: `python/literehab/dashboard_view.py`
- Modify: `python/tests/test_telemetry.py`
- Modify: `python/tests/test_dashboard_cli.py`
- Modify: `python/tests/test_dashboard_view.py`

**Interfaces:**
- Produces: immutable `EcgTelemetrySample(timestamp_ms, raw_adc, bpm, leads_connected, beat, rapid_change)` and `parse_ecg_line(line)`.
- Produces: `ecg_output_path(session_path: Path) -> Path` returning `<stem>_ecg<suffix>`.
- Extends: `DashboardViewState` with `ecg_bpm` and `ecg_connected`; `render_dashboard(..., ecg_history=())` remains backward compatible through a default.

- [ ] **Step 1: Write failing Python tests**

Test valid `ECG,100,2400,72.5,1,1,0`, malformed/invalid booleans and ADC values, companion path `session.csv -> session_ecg.csv`, and an ECG chart that renders both lead-off and connected waveforms.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `PYTHONPATH=python python -m pytest -q python/tests/test_telemetry.py python/tests/test_dashboard_cli.py python/tests/test_dashboard_view.py`

Expected: failures for missing ECG types/functions/state fields.

- [ ] **Step 3: Implement parser and independent bounded queue**

Keep `parse_telemetry_line` unchanged for IMU. Parse ECG separately; store ECG events in `SerialReader.ecg_samples` with the same drop-oldest behavior used by IMU, so ECG can never enter `SampleSynchronizer` or `OptionalCNN.update`.

- [ ] **Step 4: Implement companion CSV**

Open `<session_stem>_ecg.csv`, write `t_ms,received_s,raw_adc,bpm,leads_connected,beat,rapid_change`, flush drained samples, and close it in the existing `finally` block. Do not add ECG columns to `SESSION_FIELDS`.

- [ ] **Step 5: Replace only the lower-right chart**

Render a rolling ECG line with dynamic raw-value range, BPM text, and `LEADS OK/OFF`. Leave exercise, repetitions, ROM, rule/model resolution, and fusion calls unchanged.

- [ ] **Step 6: Run Python tests**

Run: `PYTHONPATH=python python -m pytest -q python/tests`

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add python/literehab python/run_dashboard.py python/tests
git commit -m "feat: display and record receiver ECG telemetry"
```

### Task 5: Wiring guide, README, components, and demo documentation

**Files:**
- Modify: `WIRING_GUIDE.md`
- Modify: `README.md`
- Modify: `README_zh.md`
- Modify: `COMPONENTS.md`
- Modify: `DEMO_GUIDE.md`

**Interfaces:** Documentation must match the exact pins and runtime record formats produced by Tasks 2–4.

- [ ] **Step 1: Update hardware inventory and architecture**

Add CJMCU-8232, three-electrode cable/pads, receiver OLED, separate ECG serial records, dashboard waveform, and companion CSV. State explicitly that ECG does not alter motion decisions.

- [ ] **Step 2: Rewrite wearable and receiver wiring**

Document wearable `MYOSA -> MPU6050` only. Document receiver GPIO2 LED, GPIO4 OUT, GPIO5 LO+, GPIO6 LO-, GPIO8 SDA, GPIO9 SCL, GPIO18 buzzer, 3V3/GND, SDN-to-3V3, USB GPIO19/20 reservation, and avoidance of GPIO35–37.

- [ ] **Step 3: Add mechanical, electrode, and safety checks**

Require rigid wearable mounting, restrained JST cable, short analog wire, physical separation from buzzer, 3.3 V only, labeled RA/LA/RL use, and battery-powered/unplugged-laptop operation while electrodes touch a person.

- [ ] **Step 4: Update demo and troubleshooting flow**

Add `LEADS OFF/OK`, BPM settling, ECG waveform/CSV verification, and checks that motion decisions remain unchanged.

- [ ] **Step 5: Check documentation consistency and commit**

Run: `rg -n "GPIO36|GPIO4|GPIO5|GPIO6|GPIO8|GPIO9|ECG|OLED" README.md README_zh.md WIRING_GUIDE.md COMPONENTS.md DEMO_GUIDE.md`

```bash
git add README.md README_zh.md WIRING_GUIDE.md COMPONENTS.md DEMO_GUIDE.md
git commit -m "docs: add receiver ECG and OLED wiring"
```

### Task 6: Full verification and hardware handoff

**Files:**
- Modify if verification exposes defects: only files already listed above.

- [ ] **Step 1: Run whitespace and repository checks**

Run: `git diff --check && git status --short`

Expected: no whitespace errors; only the user's unrelated untracked course files may remain.

- [ ] **Step 2: Run complete automated verification**

Run: `PYTHON=/opt/anaconda3/bin/python3.13 ./scripts/test_all.sh`

Expected: four host C executables, complete Python suite, syntax checks, dashboard smoke test, and both ESP-IDF builds succeed.

- [ ] **Step 3: Review motion-decision isolation**

Run: `git diff HEAD~5 -- python/literehab/dashboard_state.py python/literehab/fusion.py python/literehab/multimodal.py shared/motion_logic.c shared/motion_packet.h`

Expected: no behavior changes to motion decision, fusion, model, motion logic, or BLE packet schema.

- [ ] **Step 4: Provide physical acceptance checklist**

Report that software/build verification is complete separately from unperformed hardware checks. List lead-off, stable BPM, waveform, OLED, BLE repetition, serialized buzzer, and three-minute soak tests for the user to execute on the physical setup.

