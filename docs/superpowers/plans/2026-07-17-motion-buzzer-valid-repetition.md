# Motion Buzzer Valid-Repetition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit a motion buzzer tone only when `rep_count` increases, while keeping failed/incomplete attempts silent and preserving the independent ECG high-BPM alert.

**Architecture:** Replace the current active-to-idle motion transition detector with a monotonic repetition-count edge detector in portable `feedback_logic`. Reset its baseline on BLE disconnection so wearable restarts cannot create a false tone, and update user documentation to match the new silent-warning behavior.

**Tech Stack:** C17 host tests, ESP-IDF 6.0.2, FreeRTOS receiver output queue.

## Global Constraints

- The first motion packet establishes a silent `rep_count` baseline.
- Emit exactly one `FEEDBACK_EVENT_SUCCESS` when `rep_count` is strictly greater than the stored baseline.
- Equal or lower counters are silent and cannot lower the stored baseline.
- Motion state transitions and quality values never produce a buzzer event by themselves.
- Fast, insufficient-range, and incomplete attempts remain visible/recorded but silent.
- BLE disconnection resets feedback state; the first packet after reconnection is silent.
- The confirmed ECG high-BPM five-pulse alarm remains unchanged.
- Do not remove `FEEDBACK_EVENT_WARNING` from the public enum; retain source compatibility.

---

### Task 1: Trigger motion feedback from valid repetition count only

**Files:**
- Modify: `shared/feedback_logic.h`
- Modify: `shared/feedback_logic.c`
- Modify: `tests/test_feedback_logic.c`

**Interfaces:**
- Consumes: `motion_packet_t.rep_count` and the existing `feedback_logic_update(feedback_logic_t *, const motion_packet_t *)` signature.
- Produces: `feedback_logic_t { uint16_t previous_rep_count; bool initialized; }` and success events only for strictly increasing counts.

- [ ] **Step 1: Replace transition-based assertions with failing count-edge tests**

Keep the existing `packet(...)` helper, add this assertion helper, and replace
`main` with:

```c
static void expect_event(feedback_logic_t *logic, motion_state_t state,
                         motion_quality_t quality, uint16_t reps,
                         feedback_event_t expected)
{
    motion_packet_t sample = packet(state, quality, reps);
    assert(feedback_logic_update(logic, &sample) == expected);
}

int main(void)
{
    feedback_logic_t logic;
    feedback_logic_init(&logic);

    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_NONE, 0,
                 FEEDBACK_EVENT_NONE);
    expect_event(&logic, MOTION_STATE_ELBOW_FLEXION, MOTION_QUALITY_NONE, 0,
                 FEEDBACK_EVENT_NONE);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_TOO_FAST, 0,
                 FEEDBACK_EVENT_NONE);
    expect_event(&logic, MOTION_STATE_IDLE,
                 MOTION_QUALITY_INSUFFICIENT_RANGE, 0, FEEDBACK_EVENT_NONE);

    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 1,
                 FEEDBACK_EVENT_SUCCESS);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 1,
                 FEEDBACK_EVENT_NONE);

    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 3,
                 FEEDBACK_EVENT_SUCCESS);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 2,
                 FEEDBACK_EVENT_NONE);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 3,
                 FEEDBACK_EVENT_NONE);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 4,
                 FEEDBACK_EVENT_SUCCESS);

    feedback_logic_init(&logic);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 0,
                 FEEDBACK_EVENT_NONE);

    puts("test_feedback_logic: PASS");
    return 0;
}
```

- [ ] **Step 2: Run the focused host test and verify RED**

Run:

```bash
cc -std=c17 -Wall -Wextra -Werror -Ishared \
  tests/test_feedback_logic.c shared/feedback_logic.c \
  -o /tmp/test_feedback_logic && /tmp/test_feedback_logic
```

Expected: the old active-to-idle implementation returns a warning for a failed
attempt or fails the count-jump expectations.

- [ ] **Step 3: Implement the minimal count-edge state**

Change the state type to:

```c
typedef struct {
    uint16_t previous_rep_count;
    bool initialized;
} feedback_logic_t;
```

Implement initialization and update as:

```c
void feedback_logic_init(feedback_logic_t *logic)
{
    if (logic == NULL) return;
    logic->previous_rep_count = 0;
    logic->initialized = false;
}

feedback_event_t feedback_logic_update(feedback_logic_t *logic,
                                       const motion_packet_t *packet)
{
    if (logic == NULL || packet == NULL) return FEEDBACK_EVENT_NONE;
    if (!logic->initialized) {
        logic->previous_rep_count = packet->rep_count;
        logic->initialized = true;
        return FEEDBACK_EVENT_NONE;
    }
    if (packet->rep_count <= logic->previous_rep_count) {
        return FEEDBACK_EVENT_NONE;
    }
    logic->previous_rep_count = packet->rep_count;
    return FEEDBACK_EVENT_SUCCESS;
}
```

- [ ] **Step 4: Run all host C tests and verify GREEN**

Run:

```bash
./tests/run_host_tests.sh
```

Expected: all six host executables print `PASS`, including
`test_feedback_logic: PASS`.

- [ ] **Step 5: Commit the count-edge detector**

```bash
git add shared/feedback_logic.h shared/feedback_logic.c \
  tests/test_feedback_logic.c
git commit -m "fix: beep only for counted repetitions"
```

---

### Task 2: Reset the motion baseline on BLE disconnect

**Files:**
- Modify: `receiver/main/app_main.c`

**Interfaces:**
- Consumes: `feedback_logic_init(&feedback_logic)` from Task 1.
- Produces: a silent first packet after every BLE reconnection.

- [ ] **Step 1: Add the disconnect reset**

Change the existing disconnect branch in `connection_changed` to:

```c
if (!connected) {
    have_sequence = false;
    feedback_logic_init(&feedback_logic);
}
```

Do not alter the ECG callback or `sample->result.high_bpm_alert` condition.

- [ ] **Step 2: Build the receiver firmware**

Run:

```bash
. /Users/yuedonghan/.espressif/v6.0.2/esp-idf/export.sh >/dev/null 2>&1
idf.py -C receiver build
```

Expected: `Project build complete` with exit code 0.

- [ ] **Step 3: Commit the connection reset**

```bash
git add receiver/main/app_main.c
git commit -m "fix: reset motion buzzer baseline on reconnect"
```

---

### Task 3: Update feedback documentation and verify the complete system

**Files:**
- Modify: `README.md`
- Modify: `README_zh.md`
- Modify: `WIRING_GUIDE.md`
- Modify: `DEMO_GUIDE.md`

**Interfaces:**
- Documents the exact motion behavior produced by Tasks 1–2.

- [ ] **Step 1: Replace warning-tone descriptions with silent warning behavior**

Use this English behavior text:

```text
Only an increase in `rep_count` produces the single 880 Hz motion tone.
Fast, insufficient-range, incomplete, repeated, and stale motion packets are
silent. Their quality remains visible and recorded.
```

Use this Chinese behavior text:

```text
只有 `rep_count` 增加时才发出一声 880 Hz 动作提示音。过快、幅度不足、
未完成、重复和过期动作数据均保持静音，但质量状态仍会显示和记录。
```

Update the `feedback_logic.c` repository-structure description from
active-to-idle transitions to repetition-count increments. Keep the ECG alert
documentation unchanged.

- [ ] **Step 2: Verify active documentation no longer promises motion warning tones**

Run:

```bash
rg -n 'Two low warning tones|two low warning tones|两声低音|两声低频警告音|两声警告音|active 转为 idle|active to idle' \
  README.md README_zh.md WIRING_GUIDE.md DEMO_GUIDE.md
```

Expected: no matches.

- [ ] **Step 3: Run full software verification**

```bash
./tests/run_host_tests.sh
PYTHONPATH=python /opt/anaconda3/bin/python3.13 -m pytest -q python/tests
./scripts/build_all.sh
git diff --check
```

Expected: six C host executables pass, 118 Python tests pass, both ESP-IDF
firmware builds complete, and the diff check exits 0.

- [ ] **Step 4: Commit documentation**

```bash
git add README.md README_zh.md WIRING_GUIDE.md DEMO_GUIDE.md
git commit -m "docs: make failed motion attempts silent"
```

- [ ] **Step 5: Flash and physically check the receiver after user approval**

Detect `/dev/cu.usbmodem*`, then run:

```bash
./scripts/flash_receiver.sh /dev/cu.usbmodem-RECEIVER
```

Verify one tone for a counted valid repetition, silence for fast/short/incomplete
attempts, and preservation of the separate five-pulse confirmed ECG alert.
