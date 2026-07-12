# LiteRehab Multimodal Fusion Upgrade Design

## Goal

Upgrade the working LiteRehab dual-board MVP into a reliable, demonstrable home upper-limb rehabilitation coach that combines one forearm MPU6050 with one ordinary laptop RGB camera. The system will assess repetitions, range, speed, and trunk compensation while remaining usable when the camera or a trained model is unavailable.

## Product boundary

The target user is a patient performing therapist-selected shoulder, elbow, or forearm exercises between in-person sessions. The prototype records exercise quality and provides immediate audiovisual feedback; it does not diagnose injury, prescribe treatment, estimate clinical scores, or replace a physiotherapist.

The supported demonstration exercises are:

1. Elbow flexion and extension.
2. Shoulder abduction.
3. Forearm pronation and supination.

The supported feedback classes are `ok`, `too_fast`, `insufficient_range`, and `trunk_compensation`. The affected side is selectable as `left` or `right`.

## Constraints

- Keep the existing MYOSA ESP32 wearable, MPU6050, OLED, ESP32-S3 receiver, LED, buzzer, and laptop webcam.
- Do not require UWB, depth cameras, multiple IMUs, cloud services, or a GPU.
- Preserve deterministic IMU-only operation as the safe fallback.
- Treat deep-learning output as an engineering estimate, not a clinical result.
- Do not claim model accuracy until evaluated with a subject-disjoint split.

## Architecture

```text
MYOSA wearable (50 Hz)
  MPU6050 -> filtering/state machine -> BLE packet
                                         |
                                         v
ESP32-S3 receiver -> event-latched LED/buzzer -> timestamped USB telemetry
                                         |
                                         v
Laptop
  serial samples ---- timestamp synchronizer ---- synchronized windows
  webcam frames ----- MediaPipe VIDEO mode ------ pose features
                                                    |
                    rule assessment <---------------+
                    optional dual-branch CNN-BiGRU <-+
                                                    |
                                                    v
                    confidence-gated fusion -> UI + session CSV
```

## Firmware reliability changes

The motion logic API and its host tests will be synchronized. Adaptive noise statistics will update only while idle so that a large active movement cannot raise its own reversal threshold. The complementary filter will not accept an unused gyroscope argument.

Repetition completion will be an explicit event. The receiver will emit at most one feedback event per completed repetition or quality transition, preventing a persistent quality field from filling the buzzer queue. BLE packet layout remains version 1 and 26 bytes for compatibility.

## Vision processing

MediaPipe Tasks will run in `VIDEO` mode with monotonically increasing timestamps. Legacy MediaPipe remains supported. The affected side selects the corresponding shoulder, elbow, wrist, and hip landmarks.

Each valid frame produces a `PoseFeatures` record containing timestamp, elbow angle, shoulder angle, trunk displacement, normalized wrist position, angular velocities, and mean landmark visibility. Invalid or occluded frames carry a validity mask instead of fabricated coordinates.

Visual range is accumulated inside a repetition window. It resets when a new repetition begins or when the user presses `r`; it is never shared indefinitely across unrelated repetitions. Trunk compensation is evaluated only during an active exercise.

## Time synchronization and recording

IMU timestamps originate on the wearable. Camera timestamps use the desktop monotonic clock. The desktop establishes a session offset when the first IMU sample arrives, maps IMU time into the desktop clock, and associates each camera frame with the nearest IMU sample within a bounded tolerance.

All drained IMU samples are recorded, not only the most recent sample displayed by the UI. Synchronized training rows contain raw IMU channels, derived pose features, visibility, exercise state, repetition identifier, quality, label, and subject identifier. Missing visual samples remain explicit through a mask.

## Multimodal model

The optional model is a compact dual-branch CNN-BiGRU:

- IMU branch: six channels through Conv1D layers and a bidirectional GRU.
- Vision branch: pose-feature channels through Conv1D layers and a bidirectional GRU.
- Fusion: concatenate branch embeddings after multiplying the visual embedding by its visibility-derived confidence.
- Heads: exercise class and feedback class.

The inference checkpoint stores labels, normalization statistics, window size, pose-feature names, and architecture version. A checkpoint with incompatible metadata is rejected with a clear message.

The dashboard uses the model only when a valid checkpoint and a complete window are available. Otherwise it uses the deterministic rules. When model confidence is below a configurable threshold, rule output wins and the UI states `rule fallback`.

## Demonstration behavior

The dashboard shows the camera skeleton, selected side, current exercise, repetition count, current joint angle, repetition range, feedback, modality availability, model confidence, BLE/serial state, and live IMU chart.

- A correct repetition produces green feedback and one high tone.
- A fast or short-range repetition produces one two-tone warning.
- Trunk compensation produces a visual warning without repeated buzzer events.
- Low landmark visibility displays a camera-positioning prompt and continues in IMU-only mode.
- Session completion produces a CSV suitable for summary statistics and later training.

## Error handling

- Serial reconnection preserves the UI and resets synchronization state.
- One failed camera frame does not permanently disable vision; repeated failures temporarily select IMU-only mode.
- Missing pose model, missing camera, or missing CNN checkpoint does not stop the application.
- Malformed telemetry remains ignored by the validated parser.
- Queue overflow drops the oldest display sample while the recorder drains every sample it receives.

## Testing

Host C tests cover packet integrity, motion completion, insufficient range, excessive speed, idle-only adaptive thresholds, and one-shot receiver feedback decisions. Python tests cover side selection, pose feature extraction, per-repetition range reset, timestamp association, missing-vision masks, model metadata validation, confidence-gated fusion, and CSV row completeness.

The completion gate is:

1. Host C tests pass with `-Wall -Wextra -Werror`.
2. All Python tests and syntax compilation pass.
3. Wearable and receiver ESP-IDF builds pass.
4. Dashboard starts in a headless smoke test without a camera or serial device.
5. Documentation and command examples match the implemented interfaces.

## Review discipline

Every production-code change follows a red-green-refactor cycle. Existing failures are investigated with reproducible commands and recent-change tracing before a fix is proposed. After each independently testable task, the actual Git diff is reviewed for requirement alignment, interface mismatches, persistent-state bugs, error handling, and untested branches.

Before publication, the complete branch is reviewed against this design rather than only against whether the tests happen to pass. The final review must confirm BLE packet compatibility, one-shot physical feedback, timestamped multimodal records, left/right symmetry, camera-loss fallback, checkpoint validation, subject-disjoint training support, and accurate documentation. No unresolved critical or important review finding may be pushed as completed work.

## Non-goals

- Full-body 3D pose reconstruction.
- Clinical outcome prediction or Fugl-Meyer scoring.
- Training a publishable model from the existing unlabelled demo CSV files.
- Reproducing TAR-ViTPose, SAME, HiPoser, UMotion, or diffusion models in full.
- Automatic exercise prescription or natural-language medical advice.

## Academic rationale

The implementation follows the practical evidence from RGB-camera and wrist-sensor rehabilitation studies: extract biomechanical pose time series, fuse them with inertial signals over short temporal windows, preserve computed interpretable features, and evaluate on held-out subjects. Recent top-conference work motivates temporal pose aggregation and reliability-aware multimodal fusion, but the MVP uses a smaller architecture appropriate for the available hardware and dataset.
