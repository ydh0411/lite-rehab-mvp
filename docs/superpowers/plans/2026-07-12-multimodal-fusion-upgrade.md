# LiteRehab Multimodal Fusion Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a tested two-board upper-limb rehabilitation MVP with one-shot physical feedback, timestamped left/right vision features, synchronized RGB/IMU records, and an optional confidence-gated multimodal CNN-BiGRU.

**Architecture:** Preserve the 26-byte BLE protocol and deterministic wearable classifier. Add pure, host-testable firmware decision modules; split desktop pose extraction, repetition tracking, synchronization, and multimodal inference into focused Python modules; keep the dashboard as the orchestration and visualization layer.

**Tech Stack:** ESP-IDF 6.0.2, C17, NimBLE, Python 3.12/3.13, NumPy, OpenCV, MediaPipe, PyTorch, pytest.

## Global Constraints

- Keep the existing ESP32, MPU6050, OLED, ESP32-S3, LED, buzzer, and laptop webcam.
- Preserve `motion_packet_t` version 1 and its 26-byte packed layout.
- No UWB, depth camera, cloud dependency, GPU requirement, diagnosis, prescription, or clinical-score prediction.
- Every production behavior change must first have a test that fails for the expected reason.
- Model performance claims require subject-disjoint evaluation; no accuracy claim is generated from existing unlabelled sessions.

---

### Task 1: Repair and harden wearable motion logic

**Files:**
- Modify: `tests/test_motion_logic.c`
- Modify: `shared/motion_logic.c`

**Interfaces:**
- Consumes: `motion_logic_update(logic, gx, gy, gz, ax, ay, az, timestamp_ms)`.
- Produces: the same public API with idle-only adaptive noise updates and warning-free C17 compilation.

- [ ] **Step 1: Reproduce and record the current compiler failure**

Run: `./tests/run_host_tests.sh`

Expected: compilation fails because `test_motion_logic.c` passes five arguments after `logic` instead of seven, and `update_complementary_filter()` has an unused `gz` parameter.

- [ ] **Step 2: Update existing calls and add a failing adaptive-threshold regression**

Pass stationary acceleration `(0.0f, 0.0f, 1.0f)` to every existing call. Add this regression before production changes:

```c
motion_logic_init(&logic, &config);
now = 0;
for (int i = 0; i < 20; ++i) {
    now += 20;
    (void)motion_logic_update(&logic, 2.0f, 1.0f, 0.0f,
                              0.0f, 0.0f, 1.0f, now);
}
const float idle_threshold = logic.adaptive_enter;
now += 20;
(void)motion_logic_update(&logic, 300.0f, 0.0f, 0.0f,
                          1.0f, 0.0f, 0.0f, now);
assert(logic.adaptive_enter == idle_threshold);
```

- [ ] **Step 3: Run the focused test and verify RED**

Run the compile command from `tests/run_host_tests.sh` for `test_motion_logic`.

Expected: compilation succeeds after call-shape correction, then the new threshold assertion fails because active movement currently updates RMS.

- [ ] **Step 4: Implement the minimal motion-logic fix**

Remove `gz` from the private complementary-filter signature. Update adaptive statistics only when the filtered X/Y magnitude is below the configured fixed entry threshold:

```c
const float signal_mag = fmaxf(fabsf(gx), fabsf(gy));
if (logic->phase == 0 && signal_mag < logic->config.enter_threshold_dps) {
    update_adaptive_thresholds(logic, signal_mag);
}
```

- [ ] **Step 5: Verify GREEN and review the diff**

Run: `./tests/run_host_tests.sh && git diff --check && git diff -- shared/motion_logic.c tests/test_motion_logic.c`

Expected: both host executables pass; no warnings or whitespace errors; the public packet/API layout is unchanged.

- [ ] **Step 6: Commit**

```bash
git add shared/motion_logic.c tests/test_motion_logic.c
git commit -m "Fix motion logic tests and adaptive thresholding"
```

---

### Task 2: Make receiver feedback event-driven

**Files:**
- Create: `shared/feedback_logic.h`
- Create: `shared/feedback_logic.c`
- Create: `tests/test_feedback_logic.c`
- Modify: `tests/run_host_tests.sh`
- Modify: `receiver/main/CMakeLists.txt`
- Modify: `receiver/main/app_main.c`
- Modify: `receiver/main/receiver_outputs.h`
- Modify: `receiver/main/receiver_outputs.c`

**Interfaces:**
- Produces: `feedback_logic_init(feedback_logic_t *)` and `feedback_logic_update(feedback_logic_t *, const motion_packet_t *) -> feedback_event_t`.
- Produces: `receiver_outputs_feedback(feedback_event_t event)`; `FEEDBACK_EVENT_NONE`, `FEEDBACK_EVENT_SUCCESS`, and `FEEDBACK_EVENT_WARNING`.

- [ ] **Step 1: Write a failing pure-C event test**

The test sends `idle -> active -> idle(ok)`, repeats the same idle packet, then sends another active cycle ending in `insufficient_range`. Assert exactly one success and one warning event:

```c
feedback_logic_t logic;
feedback_logic_init(&logic);
assert(feedback_logic_update(&logic, &idle) == FEEDBACK_EVENT_NONE);
assert(feedback_logic_update(&logic, &active) == FEEDBACK_EVENT_NONE);
assert(feedback_logic_update(&logic, &completed_ok) == FEEDBACK_EVENT_SUCCESS);
assert(feedback_logic_update(&logic, &completed_ok) == FEEDBACK_EVENT_NONE);
assert(feedback_logic_update(&logic, &active) == FEEDBACK_EVENT_NONE);
assert(feedback_logic_update(&logic, &completed_short) == FEEDBACK_EVENT_WARNING);
assert(feedback_logic_update(&logic, &completed_short) == FEEDBACK_EVENT_NONE);
```

- [ ] **Step 2: Register and run the new host test to verify RED**

Run: `./tests/run_host_tests.sh`

Expected: compilation fails because `feedback_logic.h` does not exist.

- [ ] **Step 3: Implement the minimal transition detector**

Store only the previous motion state and initialization flag. Emit an event on a non-idle to idle transition; select warning for `too_fast` or `insufficient_range`, success for `ok`, otherwise none.

- [ ] **Step 4: Route explicit events to the physical-output queue**

In `packet_received()`, call the pure transition detector and pass its event to `receiver_outputs_feedback()`. The output task maps success to one 880 Hz tone and warning to one two-tone sequence; it does not inspect persistent packet quality.

- [ ] **Step 5: Verify GREEN and inspect queue behavior**

Run: `./tests/run_host_tests.sh && git diff --check && git diff -- shared/feedback_logic.* receiver/main tests`

Expected: three host tests pass and no code path queues `FEEDBACK_EVENT_NONE`.

- [ ] **Step 6: Commit**

```bash
git add shared/feedback_logic.* tests receiver/main
git commit -m "Trigger receiver feedback once per repetition"
```

---

### Task 3: Add side-aware pose features and repetition-scoped range

**Files:**
- Create: `python/literehab/pose_features.py`
- Create: `python/tests/test_pose_features.py`
- Modify: `python/literehab/pose_math.py`

**Interfaces:**
- Produces: immutable `PoseFeatures(timestamp_s, valid, elbow_angle_deg, shoulder_angle_deg, trunk_displacement, wrist_x, wrist_y, elbow_velocity_dps, shoulder_velocity_dps, visibility)`.
- Produces: `extract_pose_features(landmarks, side, timestamp_s, baseline, previous) -> PoseFeatures`.
- Produces: `RepetitionRangeTracker.update(state, rep_count, angle) -> float | None` and `.reset()`.

- [ ] **Step 1: Write failing tests for left/right symmetry, visibility, and range reset**

Use small fake landmark objects with `x`, `y`, and `visibility`. Assert mirrored left/right fixtures produce equal joint angles, visibility below 0.5 yields `valid=False`, and a completed repetition cannot leak its range into the next active repetition.

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests/test_pose_features.py`

Expected: import fails because `literehab.pose_features` does not exist.

- [ ] **Step 3: Implement the dataclass, side map, feature extraction, and tracker**

Use the MediaPipe indices `{left: 11/13/15/23, right: 12/14/16/24}`. Calculate elbow angle with shoulder-elbow-wrist, shoulder angle with elbow-shoulder-hip, normalize wrist coordinates relative to shoulder-to-hip torso length, and calculate velocities only when the previous valid timestamp is earlier.

- [ ] **Step 4: Verify GREEN and all pose tests**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests/test_pose_math.py python/tests/test_pose_features.py`

Expected: all pose tests pass.

- [ ] **Step 5: Commit**

```bash
git add python/literehab/pose_features.py python/literehab/pose_math.py python/tests/test_pose_features.py
git commit -m "Add side-aware rehabilitation pose features"
```

---

### Task 4: Synchronize and preserve every telemetry sample

**Files:**
- Create: `python/literehab/synchronization.py`
- Create: `python/tests/test_synchronization.py`
- Modify: `python/literehab/telemetry.py`

**Interfaces:**
- Produces: `ReceivedTelemetry(sample, received_s)`, `TimedPose(features)`, and `SynchronizedSample(telemetry, pose)`.
- Produces: `SampleSynchronizer(tolerance_s=0.05)` with `add_imu()`, `add_pose()`, `drain(now_s, force=False)`.

- [ ] **Step 1: Write failing tests for nearest matching, missing vision, and lossless draining**

Insert three IMU samples and two pose samples. Assert each IMU sample appears exactly once, the nearest pose inside 50 ms is selected, and an expired sample outside tolerance has `pose=None`.

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests/test_synchronization.py`

Expected: import fails because the synchronization module does not exist.

- [ ] **Step 3: Implement bounded nearest-neighbor association**

Keep small deques sorted by desktop monotonic receive time. Drain IMU samples after they are older than the tolerance, choose the pose with minimum absolute time difference when it is within tolerance, and retain an explicit missing pose otherwise.

- [ ] **Step 4: Verify GREEN and parser compatibility**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests/test_telemetry.py python/tests/test_synchronization.py`

Expected: all tests pass and `TelemetrySample` wire parsing remains unchanged.

- [ ] **Step 5: Commit**

```bash
git add python/literehab/synchronization.py python/literehab/telemetry.py python/tests/test_synchronization.py
git commit -m "Add lossless RGB IMU sample synchronization"
```

---

### Task 5: Implement confidence-gated multimodal CNN-BiGRU

**Files:**
- Create: `python/literehab/multimodal.py`
- Create: `python/tests/test_multimodal.py`
- Create: `python/train_multimodal.py`
- Modify: `python/literehab/dataset.py`
- Modify: `python/requirements.txt`

**Interfaces:**
- Produces: `build_multimodal_model(num_exercises, num_qualities, imu_channels=6, pose_channels=9)`.
- Produces: `load_multimodal_checkpoint(path)` with architecture-version and feature-name validation.
- Produces: exercise logits, quality logits, and an effective visual confidence value.

- [ ] **Step 1: Write failing architecture and checkpoint tests**

Create tensors shaped `[2, 6, 100]`, `[2, 9, 100]`, and confidence `[2, 1]`. Assert output shapes are `[2, exercise_count]` and `[2, quality_count]`; assert zero confidence makes output invariant to changed visual input; assert an unsupported checkpoint version raises `ValueError`.

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests/test_multimodal.py`

Expected: import fails because `literehab.multimodal` does not exist.

- [ ] **Step 3: Implement the smallest dual-branch network and validated loader**

Each branch uses two Conv1D blocks followed by a bidirectional GRU. Multiply the visual embedding by clamped mean visibility before concatenation. Store `architecture_version=1`, ordered feature names, normalization arrays, labels, window size, state dict, holdout subject, and measured accuracy in the checkpoint.

- [ ] **Step 4: Add subject-disjoint training**

`train_multimodal.py` reads synchronized labeled CSV files, rejects missing subjects or missing holdout data, creates 100-sample windows with stride 50, normalizes using training subjects only, trains both heads with summed cross-entropy, reports both held-out accuracies, and saves the validated metadata.

- [ ] **Step 5: Verify GREEN and training CLI syntax**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests/test_dataset.py python/tests/test_multimodal.py && PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m py_compile python/train_multimodal.py python/literehab/multimodal.py`

Expected: tests and compilation pass without training on unlabelled data.

- [ ] **Step 6: Commit**

```bash
git add python/literehab/multimodal.py python/literehab/dataset.py python/tests/test_multimodal.py python/train_multimodal.py python/requirements.txt
git commit -m "Add confidence-gated multimodal CNN-BiGRU"
```

---

### Task 6: Integrate the upgraded pipeline into the dashboard

**Files:**
- Create: `python/literehab/dashboard_state.py`
- Create: `python/tests/test_dashboard_state.py`
- Modify: `python/run_dashboard.py`
- Modify: `python/literehab/fusion.py`
- Modify: `python/tests/test_fusion.py`

**Interfaces:**
- Adds CLI options: `--side {left,right}`, `--fusion-model PATH`, `--model-confidence FLOAT`, `--subject ID`, `--label-exercise LABEL`, `--label-quality LABEL`, and `--headless-smoke-test`.
- Produces CSV rows containing every IMU sample plus synchronized pose values, `vision_valid`, model predictions, confidence, subject, and optional ground-truth labels.

- [ ] **Step 1: Write failing state tests**

Test that low model confidence selects the deterministic rule, high confidence selects model output, trunk compensation is ignored while idle, one failed camera frame does not permanently disable vision, and all synchronized samples are converted to CSV rows.

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests/test_dashboard_state.py python/tests/test_fusion.py`

Expected: new imports or assertions fail before production integration.

- [ ] **Step 3: Implement pure dashboard state and fusion decisions**

Keep UI-independent fallback and row construction in `dashboard_state.py`. Extend `fuse_feedback()` with optional model class/confidence while preserving existing callers and rule-priority safety behavior.

- [ ] **Step 4: Integrate MediaPipe VIDEO mode and side-aware extraction**

For Tasks API, construct `PoseLandmarkerOptions(running_mode=VIDEO)` and call `detect_for_video(image, timestamp_ms)`. Keep legacy mode functional. Feed pose features and received telemetry into `SampleSynchronizer`, drain all ready samples to CSV, and build model windows from synchronized rows.

- [ ] **Step 5: Add the headless smoke path**

`--headless-smoke-test` validates arguments, creates the pure runtime state, prints `LiteRehab dashboard smoke test: PASS`, and exits before opening serial, camera, or GUI resources.

- [ ] **Step 6: Verify GREEN and inspect the complete Python diff**

Run: `PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests && PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m py_compile python/run_dashboard.py python/train_multimodal.py python/literehab/*.py && PYTHONPATH=python /opt/anaconda3/bin/python3.13 python/run_dashboard.py --headless-smoke-test`

Expected: all Python tests pass, compilation passes, and the smoke-test message is printed without hardware.

- [ ] **Step 7: Commit**

```bash
git add python/run_dashboard.py python/literehab/dashboard_state.py python/literehab/fusion.py python/tests
git commit -m "Integrate synchronized multimodal rehabilitation feedback"
```

---

### Task 7: Update documentation and perform the publication gate

**Files:**
- Modify: `README.md`
- Modify: `DEMO_GUIDE.md`
- Modify: `WIRING_GUIDE.md`
- Modify: `scripts/test_all.sh`

**Interfaces:**
- Documents exact CLI options, CSV schema, model limitations, left/right selection, training commands, and unchanged wiring.

- [ ] **Step 1: Update the all-in-one test script**

Include `train_multimodal.py`, all package modules, and the headless dashboard smoke command in `scripts/test_all.sh`.

- [ ] **Step 2: Update user documentation**

Document the three demonstration exercises, one-shot feedback, `--side`, synchronized data collection labels, subject-disjoint multimodal training, confidence fallback, and the fact that no trained multimodal checkpoint ships until data are collected.

- [ ] **Step 3: Run the full completion gate**

Run:

```bash
./scripts/test_all.sh
git diff --check
git status -sb
```

Expected: all host tests, all Python tests, Python compilation, smoke test, wearable build, and receiver build pass with exit code 0.

- [ ] **Step 4: Perform the detailed code review**

Review `git diff main...HEAD` against the design and explicitly check packet size/version, event transitions, queue writes, timestamp association, left/right index symmetry, invalid-vision masking, checkpoint schema, training split leakage, fallback priority, resource cleanup, test coverage, and documentation accuracy. Resolve every critical or important finding with a new red-green cycle.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md DEMO_GUIDE.md WIRING_GUIDE.md scripts/test_all.sh
git commit -m "Document the upgraded multimodal MVP"
```

- [ ] **Step 6: Publish through the GitHub workflow**

After fresh verification, push `codex/multimodal-fusion-upgrade`, create a draft PR targeting `main`, and report the branch, commits, checks, and PR URL.
