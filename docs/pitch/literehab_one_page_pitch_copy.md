# LiteRehab Fusion

*Real-time feedback for upper-limb rehabilitation practice at home.*

## Summary

LiteRehab Fusion is a coursework engineering prototype that combines a forearm-worn motion sensor with camera-based posture estimation. The system recognises the demonstrated exercise, counts repetitions, checks selected movement features, and records synchronized motion and posture data. It is designed to support home practice under professional guidance; it does not make treatment decisions or assess clinical recovery.

## Background

Home-exercise programmes ask patients to practise away from the clinic. During these sessions, a patient may not notice that a movement is too fast, that the range is limited, or that the trunk is compensating. The physiotherapist usually reviews progress at a later appointment rather than observing each repetition.

## Aim

The project examines whether wearable motion sensing and a camera view of posture can provide immediate, understandable feedback during a prescribed upper-limb exercise. A synchronized session record is retained for possible later review.

## System design

**Wearable unit:** An MPU6050 samples forearm motion at 50 Hz. An ESP32 wearable transmits the samples over BLE to an ESP32-S3 receiver, which maintains the local exercise state and repetition count.

**Posture input:** A MaixCAM2 video stream supplies a wider view of the movement. Computer-based posture estimation is used to check trunk position alongside the forearm signal.

**Analysis and interface:** The dashboard aligns the motion and posture streams, displays the current status, and stores a synchronized session record. A classroom CNN-BiGRU baseline is available with a rule-based fallback.

## Prototype capabilities

The current MVP demonstrates:

- elbow-flexion and forearm-rotation exercise recognition;
- repetition counting from the wearable motion signal;
- checks for excessive speed and insufficient movement range;
- a posture check for trunk compensation;
- local status feedback and synchronized IMU and pose logging.

## Intended use

**During home practice:** The person receives feedback while performing the exercise, leaving time to adjust a later repetition in the same session.

**Between appointments:** A physiotherapist could review the session record when discussing home practice. Exercise selection and all clinical decisions remain with the physiotherapist.

## Limitations and next steps

The exercise set is limited, and the classroom model was trained on a small public dataset. The prototype has not been clinically validated and makes no claim about diagnostic accuracy or patient outcomes.

The next step is supervised usability testing with physiotherapists and representative users. This work would examine the clarity and timing of the feedback and guide the collection of more representative movement data.

## Scope

LiteRehab Fusion is a coursework engineering prototype, not a medical device. It does not diagnose, prescribe treatment, score recovery, or replace professional supervision.

## Claim audit

| Claim | Status | Basis |
|---|---|---|
| Forearm motion sensing, BLE transfer, camera posture input, immediate feedback, and synchronized logging | Demonstrated | Current repository and demo workflow |
| Elbow flexion and forearm rotation, with feedback for speed, range, and trunk compensation | Demonstrated | Current firmware, dashboard, and demo guide |
| Wearable repetition count and classroom CNN-BiGRU baseline with rule-based fallback | Demonstrated | Current firmware and dashboard |
| Later physiotherapist review and supervised usability testing | Proposed | Product direction, not a deployed workflow |
| Clinical effectiveness, diagnostic accuracy, and improved outcomes | Not claimed | Requires representative and clinical validation |

## Humanizer audit

### Draft rewrite

The earlier version used message-led headings, a diagram with promotional cue labels, and repeated contrasts between immediate feedback and later review. Those choices made the page read like a generated product infographic.

### What makes the below so obviously AI generated?

- Slogan-like headings tried to do the work of the argument.
- The three quoted prompts looked invented because the interface wording was not being documented.
- Repeated short labels and coloured nodes made a small prototype look more polished than the evidence supports.
- Several sentences grouped benefits into overly tidy sets of three.

### Final rewrite

The final copy uses conventional report headings and describes the system in plain technical language. It separates demonstrated capability from intended use, keeps conditional wording for later physiotherapist review, and states the limits directly. The flow diagram and invented prompt strip have been removed. The remaining claims are bounded by the current repository and demo workflow.
