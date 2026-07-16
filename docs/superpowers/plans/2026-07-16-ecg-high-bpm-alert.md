# ECG High-BPM Alert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the receiver request its ECG buzzer pattern only after a filtered BPM remains above 150 for three consecutive valid measurements, while suppressing startup spikes, lead chatter, ADC saturation, and duplicate queued alerts.

**Architecture:** Keep heart-rate decisions in the portable `shared/ecg_logic` module, add a separately testable lead-state debounce filter and atomic ECG-alert gate, then connect those components to the ESP-IDF receiver. Preserve the seven-column ECG wire format while renaming its final event semantically to `high_bpm_alert`; Python retains a compatibility property and continues reading old seven-column records.

**Tech Stack:** C17 host tests, ESP-IDF 6.0.2 ADC/GPIO/LEDC/FreeRTOS, Python 3.12+, pytest.

## Global Constraints

- High BPM means strictly greater than 150 BPM.
- Require three consecutive filtered high-BPM measurements before one alert.
- Require three consecutive filtered measurements at or below 140 BPM to rearm.
- Publish no BPM until at least three valid RR intervals have been collected.
- Calculate BPM from the median of up to five most recent valid RR intervals.
- Accept RR intervals from 250 ms through 2000 ms; reject shorter/longer intervals from BPM and alarm state.
- ADC rail values `0` and `4095` cannot create beats, BPM, or alerts.
- Debounce raw lead-off state for 200 ms; a transient raw lead-off sample cannot reset ECG history.
- An ECG alert already queued or playing cannot be queued again.
- Keep the existing five-pulse 1000 Hz buzzer pattern and all motion feedback behavior.
- This remains a classroom prototype and must not be described as medically validated.

---

### Task 1: Robust RR-based BPM and high-BPM state machine

**Files:**
- Modify: `shared/ecg_logic.h`
- Modify: `shared/ecg_logic.c`
- Modify: `tests/test_ecg_logic.c`

**Interfaces:**
- Consumes: `ecg_logic_update(ecg_logic_t *, int raw_adc, bool leads_off, uint32_t now_ms)`.
- Produces: `ecg_result_t { leads_connected, beat, high_bpm_alert, bpm }`; constants `ECG_HIGH_BPM_THRESHOLD`, `ECG_REARM_BPM_THRESHOLD`, `ECG_RR_WINDOW_SIZE`, and `ECG_RR_WARMUP_COUNT`.

- [ ] **Step 1: Replace the old delta-change tests with failing startup, median, confirmation, latch, rail, and reset tests**

Add a helper that creates a threshold crossing and releases the latch:

```c
static ecg_result_t pulse(ecg_logic_t *logic, uint32_t now_ms)
{
    ecg_result_t result = ecg_logic_update(logic, 3000, false, now_ms);
    (void)ecg_logic_update(logic, 2200, false, now_ms + 10);
    return result;
}
```

Replace the old expectations with focused tests that assert:

```c
static void test_requires_three_rr_intervals_before_publishing_bpm(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);
    assert(pulse(&logic, 1000).bpm == 0.0f);
    assert(pulse(&logic, 1400).bpm == 0.0f);
    assert(pulse(&logic, 1800).bpm == 0.0f);
    ecg_result_t ready = pulse(&logic, 2200);
    assert_close(ready.bpm, 150.0f);
    assert(!ready.high_bpm_alert);
}

static void test_single_short_interval_does_not_create_200_bpm_spike(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);
    (void)pulse(&logic, 1000);
    (void)pulse(&logic, 1400);
    (void)pulse(&logic, 1800);
    assert_close(pulse(&logic, 2200).bpm, 150.0f);
    assert_close(pulse(&logic, 2500).bpm, 150.0f);
}

static void test_alerts_once_after_three_filtered_values_above_150(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);
    uint32_t t = 1000;
    (void)pulse(&logic, t);
    for (int i = 0; i < 5; ++i) {
        t += 380;
        ecg_result_t result = pulse(&logic, t);
        if (i < 4) assert(!result.high_bpm_alert);
        else assert(result.high_bpm_alert);
    }
    assert(!pulse(&logic, t + 380).high_bpm_alert);
}

static void test_rail_samples_and_lead_off_cannot_alert(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);
    assert(!ecg_logic_update(&logic, 0, false, 1000).beat);
    assert(!ecg_logic_update(&logic, 4095, false, 1400).beat);
    assert(!ecg_logic_update(&logic, 3000, true, 1800).high_bpm_alert);
    assert_close(ecg_logic_update(&logic, 2200, false, 1810).bpm, 0.0f);
}
```

Add an end-to-end latch/rearm test. Five 380 ms intervals warm up the median
and create the first alert; five 500 ms intervals shift the median to 120 BPM
for three published measurements and rearm; five more 380 ms intervals create
exactly one new alert:

```c
static void test_three_recovery_values_rearm_one_future_alert(void)
{
    ecg_logic_t logic;
    ecg_logic_init(&logic);
    uint32_t t = 1000;
    (void)pulse(&logic, t);
    bool first_alert = false;
    for (int i = 0; i < 5; ++i) {
        t += 380;
        first_alert = first_alert || pulse(&logic, t).high_bpm_alert;
    }
    assert(first_alert);
    for (int i = 0; i < 5; ++i) {
        t += 500;
        assert(!pulse(&logic, t).high_bpm_alert);
    }
    bool second_alert = false;
    for (int i = 0; i < 5; ++i) {
        t += 380;
        second_alert = second_alert || pulse(&logic, t).high_bpm_alert;
    }
    assert(second_alert);
}
```

Add a counter-reset test for the neutral 140–150 BPM band:

```c
static void test_neutral_bpm_breaks_consecutive_confirmation(void)
{
    ecg_logic_t logic = {
        .last_beat_ms = 1000,
        .rr_ms = {420, 420, 420, 420, 420},
        .rr_count = 5,
        .high_count = 2,
        .have_last_beat = true,
    };
    ecg_result_t neutral = pulse(&logic, 1420);
    assert(neutral.bpm > 140.0f && neutral.bpm < 150.0f);
    assert(logic.high_count == 0);
    assert(logic.recovery_count == 0);
    assert(!logic.alert_latched);
}
```

- [ ] **Step 2: Run the ECG host test and verify RED**

Run:

```bash
cc -std=c17 -Wall -Wextra -Werror -Ishared \
  tests/test_ecg_logic.c shared/ecg_logic.c -lm -o /tmp/test_ecg_logic && \
  /tmp/test_ecg_logic
```

Expected: compilation fails because `high_bpm_alert` and the new constants/state do not exist.

- [ ] **Step 3: Implement the minimal median RR detector and alarm state**

Change the public constants and state to:

```c
#define ECG_THRESHOLD 2500
#define ECG_MIN_RR_MS 250u
#define ECG_MAX_RR_MS 2000u
#define ECG_RR_WINDOW_SIZE 5u
#define ECG_RR_WARMUP_COUNT 3u
#define ECG_HIGH_BPM_THRESHOLD 150.0f
#define ECG_REARM_BPM_THRESHOLD 140.0f
#define ECG_CONFIRM_COUNT 3u

typedef struct {
    uint32_t last_beat_ms;
    uint32_t rr_ms[ECG_RR_WINDOW_SIZE];
    float bpm;
    uint8_t rr_count;
    uint8_t rr_next;
    uint8_t high_count;
    uint8_t recovery_count;
    bool have_last_beat;
    bool beat_detected;
    bool alert_latched;
} ecg_logic_t;

typedef struct {
    bool leads_connected;
    bool beat;
    bool high_bpm_alert;
    float bpm;
} ecg_result_t;
```

Implement a private median helper by copying the active RR values to a five-element local array, insertion-sorting them, and returning the middle element. In `ecg_logic_update`:

```c
if (leads_off) {
    ecg_logic_init(logic);
    return result;
}
result.leads_connected = true;
result.bpm = logic->bpm;
if (raw_adc <= 0 || raw_adc >= 4095) return result;
if (raw_adc <= ECG_THRESHOLD) {
    logic->beat_detected = false;
    return result;
}
if (logic->beat_detected) return result;
logic->beat_detected = true;
if (!logic->have_last_beat) {
    logic->have_last_beat = true;
    logic->last_beat_ms = now_ms;
    result.beat = true;
    return result;
}
const uint32_t rr_ms = now_ms - logic->last_beat_ms;
if (rr_ms < ECG_MIN_RR_MS) return result;
logic->last_beat_ms = now_ms;
if (rr_ms > ECG_MAX_RR_MS) {
    logic->rr_count = 0;
    logic->rr_next = 0;
    logic->bpm = 0.0f;
    logic->high_count = 0;
    logic->recovery_count = 0;
    result.bpm = 0.0f;
    result.beat = true;
    return result;
}
result.beat = true;
```

Store valid RR intervals in the ring. Once `rr_count >= 3`, compute `bpm = 60000 / median_rr`. Update alarm counters only for these published filtered values: increment/saturate `high_count` and clear recovery above 150; increment/saturate recovery and clear high at or below 140; otherwise clear both counters. Emit and latch only when `high_count == 3 && !alert_latched`; clear the latch only when `recovery_count == 3`.

- [ ] **Step 4: Run the focused and complete C host tests and verify GREEN**

Run:

```bash
./tests/run_host_tests.sh
```

Expected: all four host executables print `PASS`, including `test_ecg_logic: PASS`.

- [ ] **Step 5: Commit the detector change**

```bash
git add shared/ecg_logic.h shared/ecg_logic.c tests/test_ecg_logic.c
git commit -m "fix: filter ECG BPM before high alert"
```

---

### Task 2: Debounce lead-off signals before resetting ECG state

**Files:**
- Create: `shared/ecg_lead_filter.h`
- Create: `shared/ecg_lead_filter.c`
- Create: `tests/test_ecg_lead_filter.c`
- Modify: `tests/run_host_tests.sh`
- Modify: `receiver/main/ecg_monitor.c`
- Modify: `receiver/main/CMakeLists.txt`

**Interfaces:**
- Produces: `ecg_lead_filter_init(ecg_lead_filter_t *, uint32_t now_ms)` and `bool ecg_lead_filter_update(ecg_lead_filter_t *, bool raw_leads_off, uint32_t now_ms)`.
- Consumed by: receiver ECG sampling task; returned Boolean is the only lead-off value passed to `ecg_logic_update`.

- [ ] **Step 1: Write a failing host test for 200 ms disconnection and reconnection debounce**

Test these exact transitions:

```c
ecg_lead_filter_t filter;
ecg_lead_filter_init(&filter, 0);
assert(ecg_lead_filter_update(&filter, false, 0));
assert(ecg_lead_filter_update(&filter, false, 199));
assert(!ecg_lead_filter_update(&filter, false, 200));
assert(!ecg_lead_filter_update(&filter, true, 210));
assert(!ecg_lead_filter_update(&filter, false, 300));
assert(!ecg_lead_filter_update(&filter, true, 400));
assert(!ecg_lead_filter_update(&filter, true, 599));
assert(ecg_lead_filter_update(&filter, true, 600));
```

- [ ] **Step 2: Compile the new test and verify RED**

Run:

```bash
cc -std=c17 -Wall -Wextra -Werror -Ishared \
  tests/test_ecg_lead_filter.c shared/ecg_lead_filter.c \
  -o /tmp/test_ecg_lead_filter
```

Expected: compilation fails because the header and implementation do not exist.

- [ ] **Step 3: Implement the debounce filter**

Define:

```c
#define ECG_LEAD_DEBOUNCE_MS 200u

typedef struct {
    uint32_t candidate_since_ms;
    bool stable_leads_off;
    bool candidate_leads_off;
} ecg_lead_filter_t;
```

Initialize safely with `stable_leads_off=true`, `candidate_leads_off=true`, and the supplied timestamp. On every raw-state change, update the candidate and timestamp. Promote the candidate to stable only when `now_ms - candidate_since_ms >= 200`.

- [ ] **Step 4: Connect the filter to the receiver sampling task**

Initialize one filter next to `ecg_logic_t`. Read `raw_leads_off` from GPIO5/6, obtain `leads_off` from the filter, and read ADC only when both values are false. If raw lead-off is transient while stable state remains connected, pass raw ADC `0` with `leads_off=false`; the rail guard in Task 1 ignores it without resetting history. Add `../../shared/ecg_lead_filter.c` to receiver CMake sources.

- [ ] **Step 5: Add the new executable to `tests/run_host_tests.sh` and run all host tests**

Compile `test_ecg_lead_filter.c` with `shared/ecg_lead_filter.c`, execute it after `test_ecg_logic`, and expect `test_ecg_lead_filter: PASS` plus all existing PASS lines.

- [ ] **Step 6: Commit lead debounce**

```bash
git add shared/ecg_lead_filter.h shared/ecg_lead_filter.c \
  tests/test_ecg_lead_filter.c tests/run_host_tests.sh \
  receiver/main/ecg_monitor.c receiver/main/CMakeLists.txt
git commit -m "fix: debounce ECG lead status"
```

---

### Task 3: Coalesce duplicate ECG buzzer events

**Files:**
- Create: `shared/ecg_alert_gate.h`
- Create: `shared/ecg_alert_gate.c`
- Create: `tests/test_ecg_alert_gate.c`
- Modify: `tests/run_host_tests.sh`
- Modify: `receiver/main/receiver_outputs.c`
- Modify: `receiver/main/CMakeLists.txt`
- Modify: `receiver/main/app_main.c`

**Interfaces:**
- Produces: `ecg_alert_gate_init`, `ecg_alert_gate_try_acquire`, and `ecg_alert_gate_release` backed by C17 `atomic_bool`.
- Consumes: `ecg_result_t.high_bpm_alert` from Task 1.

- [ ] **Step 1: Write a failing gate test**

```c
ecg_alert_gate_t gate;
ecg_alert_gate_init(&gate);
assert(ecg_alert_gate_try_acquire(&gate));
assert(!ecg_alert_gate_try_acquire(&gate));
ecg_alert_gate_release(&gate);
assert(ecg_alert_gate_try_acquire(&gate));
```

- [ ] **Step 2: Compile and verify RED**

Run:

```bash
cc -std=c17 -Wall -Wextra -Werror -Ishared \
  tests/test_ecg_alert_gate.c shared/ecg_alert_gate.c \
  -o /tmp/test_ecg_alert_gate
```

Expected: compilation fails because the gate header and implementation do not
exist.

- [ ] **Step 3: Implement the atomic gate**

Use:

```c
typedef struct { atomic_bool pending; } ecg_alert_gate_t;

void ecg_alert_gate_init(ecg_alert_gate_t *gate)
{
    atomic_init(&gate->pending, false);
}

bool ecg_alert_gate_try_acquire(ecg_alert_gate_t *gate)
{
    return !atomic_exchange(&gate->pending, true);
}

void ecg_alert_gate_release(ecg_alert_gate_t *gate)
{
    atomic_store(&gate->pending, false);
}
```

Return safely for null pointers.

- [ ] **Step 4: Use the gate around receiver queueing and playback**

Initialize a static gate in `receiver_outputs_init`. In `receiver_outputs_ecg_alert`, return if acquisition fails; if `xQueueSend` fails, release immediately. In the output task, release after the five-pulse ECG pattern completes. Add the gate source to receiver CMake.

Change `app_main.c` to call `receiver_outputs_ecg_alert()` only when `sample->result.high_bpm_alert` is true.

- [ ] **Step 5: Run all host tests and commit**

Expected: the new gate test and all prior host tests pass.

```bash
git add shared/ecg_alert_gate.h shared/ecg_alert_gate.c \
  tests/test_ecg_alert_gate.c tests/run_host_tests.sh \
  receiver/main/receiver_outputs.c receiver/main/app_main.c \
  receiver/main/CMakeLists.txt
git commit -m "fix: coalesce ECG buzzer alerts"
```

---

### Task 4: Rename ECG telemetry event while preserving old data compatibility

**Files:**
- Modify: `receiver/main/serial_telemetry.c`
- Modify: `python/literehab/telemetry.py`
- Modify: `python/literehab/web_runtime.py`
- Modify: `python/run_dashboard.py`
- Modify: `python/tests/test_telemetry.py`
- Modify: `python/tests/test_real_web_runtime.py`
- Modify: `python/tests/test_session_repository.py`

**Interfaces:**
- Produces: new header `ECG,t_ms,raw_adc,bpm,leads_connected,beat,high_bpm_alert` with the same seven positional values.
- Produces: `EcgTelemetrySample.high_bpm_alert` plus read-only `rapid_change` compatibility property.

- [ ] **Step 1: Write failing Python tests for the explicit field and compatibility alias**

Update the valid ECG parser test to assert:

```python
sample = parse_ecg_line("ECG,5678,2184,155.0,1,1,1")
assert sample is not None
assert sample.high_bpm_alert
assert sample.rapid_change  # compatibility alias for older callers
```

Construct the sample with its last positional value set to `True`, then update
the runtime CSV test to require:

```python
assert "high_bpm_alert" in ecg_row
assert "rapid_change" not in ecg_row
assert ecg_row["high_bpm_alert"] == "1"
```

Update the session-repository CSV fixture header and row dictionaries from
`rapid_change` to `high_bpm_alert`; its BPM-summary assertions must remain
unchanged, demonstrating that old report calculations do not depend on the
event-column name.

- [ ] **Step 2: Run the focused Python tests and verify RED**

Run:

```bash
PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q \
  python/tests/test_telemetry.py python/tests/test_real_web_runtime.py \
  python/tests/test_session_repository.py
```

Expected: failures for missing `high_bpm_alert` attribute/CSV field.

- [ ] **Step 3: Implement the telemetry rename and compatibility property**

Rename the dataclass field to `high_bpm_alert` and add:

```python
@property
def rapid_change(self) -> bool:
    return self.high_bpm_alert
```

Keep `parse_ecg_line` at seven positional fields, so both old and new firmware records parse. Rename the new CSV field and writer key in both dashboard runtimes. Old CSV files remain readable because `session_repository` only consumes timestamp, BPM, and lead status.

- [ ] **Step 4: Rename the receiver header and serialized result field**

Change the header suffix to `high_bpm_alert` and serialize `sample->result.high_bpm_alert` as the seventh field.

- [ ] **Step 5: Run focused and complete Python tests, then commit**

Run the focused command from Step 2, then:

```bash
PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests
```

Expected: all Python tests pass.

```bash
git add receiver/main/serial_telemetry.c python/literehab/telemetry.py \
  python/literehab/web_runtime.py python/run_dashboard.py \
  python/tests/test_telemetry.py python/tests/test_real_web_runtime.py \
  python/tests/test_session_repository.py
git commit -m "feat: report confirmed high BPM alerts"
```

---

### Task 5: Update user-facing behavior documentation

**Files:**
- Modify: `README.md`
- Modify: `README_zh.md`
- Modify: `WIRING_GUIDE.md`
- Modify: `DEMO_GUIDE.md`

**Interfaces:**
- Documents the exact thresholds and CSV field produced by Tasks 1–4.

- [ ] **Step 1: Replace obsolete delta-change descriptions**

Use this behavior text in the English documentation:

```text
The ECG demo alert fires once only after filtered BPM remains above 150 for
three consecutive valid measurements. It rearms after three filtered
measurements at or below 140 BPM. This classroom alert is not medically
validated.
```

Use this behavior text in the Chinese documentation:

```text
ECG 演示报警仅在滤波后的 BPM 连续 3 次高于 150 时触发一次；连续 3 次降至
140 BPM 或以下后才重新允许报警。该课堂演示规则未经医学验证。
```

Replace `rapid_change` with `high_bpm_alert` in descriptions of newly recorded
CSV files.

- [ ] **Step 2: Verify no active user documentation describes the old alarm rule**

Run:

```bash
rg -n 'BPM change `> 20`|BPM 变化 `> 20`|相邻 BPM 相差大于 20|rapid_change' \
  README.md README_zh.md WIRING_GUIDE.md DEMO_GUIDE.md
```

Expected: no matches.

- [ ] **Step 3: Commit documentation**

```bash
git add README.md README_zh.md WIRING_GUIDE.md DEMO_GUIDE.md
git commit -m "docs: explain confirmed high BPM alert"
```

---

### Task 6: Full verification

**Files:**
- Verify only; do not add unrelated files.

**Interfaces:**
- Verifies all deliverables against the approved design.

- [ ] **Step 1: Run all host C and Python tests plus syntax checks**

```bash
./tests/run_host_tests.sh
PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests
PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m py_compile \
  python/run_dashboard.py python/collect_data.py python/train_1d_cnn.py \
  python/train_multimodal.py python/prepare_public_imu.py \
  python/literehab/*.py scripts/probe_cameras.py maixcam2/main.py
```

Expected: every C executable prints `PASS`, pytest reports zero failures, and `py_compile` exits 0.

- [ ] **Step 2: Build both ESP-IDF firmware projects**

```bash
./scripts/build_all.sh
```

Expected: wearable and receiver builds finish successfully with exit code 0.

- [ ] **Step 3: Inspect final scope and whitespace**

```bash
git diff --check HEAD~5..HEAD
git status --short
```

Expected: no whitespace errors; only pre-existing unrelated untracked files remain.

- [ ] **Step 4: Report hardware verification separately**

State that software verification is complete only if all commands above pass. List the remaining physical checks: stable LO+/LO-, ADC not pinned at 0/4095, plausible BPM after three RR intervals, no alert for isolated artifacts, one alert after three filtered values over 150, and rearm after recovery at or below 140.
