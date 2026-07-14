# LiteRehab Fusion

*Real-time guidance for more consistent upper-limb rehabilitation practice at home.*

## The gap

A patient can leave a physiotherapy appointment knowing which exercises to practise. At home, the harder question is whether each repetition is controlled, large enough, or being completed by leaning the trunk. Useful feedback may not arrive until the next appointment, after the practice has already happened.

## Our response

LiteRehab Fusion gives feedback while the exercise is happening. The wearable and camera-based prototype identifies the demonstrated movement, counts repetitions, flags common practice errors, and records the session for later review.

## How it works

An MPU6050 on the forearm samples motion at 50 Hz. An ESP32 wearable sends the data over BLE to an ESP32-S3 receiver. At the same time, a MaixCAM2 video stream supplies posture information to the computer dashboard. The dashboard combines both inputs and returns plain prompts such as "Move more slowly", "Increase movement range", or "Avoid trunk compensation".

## What the MVP demonstrates

- It recognises the demonstrated elbow-flexion and forearm-rotation exercises.
- It provides immediate feedback for excessive speed, insufficient range, and trunk compensation.
- The wearable shows the repetition count, while an LED and buzzer provide local feedback.
- The dashboard keeps a synchronized record of IMU and pose information.
- A classroom CNN-BiGRU baseline runs alongside a rule-based fallback.
- Verification includes 70 Python tests, three C host tests, a model-loading smoke test, and successful builds for both ESP32 targets.

## Value

A patient gets a clear cue during the repetition instead of waiting days for feedback. A physiotherapist could review the session record to understand what happened between appointments, while keeping responsibility for exercise selection and clinical decisions.

## Route to use

The proposed first step is a supervised pilot with physiotherapists. A later version could be supplied through rehabilitation providers as part of a prescribed home-exercise programme. The physiotherapist would choose the exercises and review the records.

## Limits

LiteRehab Fusion is an engineering prototype, not a medical device. It does not diagnose, prescribe treatment, score recovery, or replace professional supervision. The current model uses a small public dataset, supports a limited exercise set, and makes no clinical accuracy claim.

## What we need next

We are looking for physiotherapist partners to test usability, refine the feedback, and collect representative movement data under professional supervision.

## Claim audit

| Claim | Status | Basis |
|---|---|---|
| 50 Hz IMU sensing, BLE transfer, camera posture input, feedback, and logging | Demonstrated | Current repository and demo workflow |
| Two demonstrated exercises and three feedback categories | Demonstrated | Current firmware, dashboard, and demo guide |
| Automated test and build totals | Demonstrated | `scripts/test_all.sh` verification |
| Later physiotherapist review and clinic-supplied use | Proposed | Product direction, not a deployed workflow |
| Clinical effectiveness, diagnostic accuracy, and improved outcomes | Not claimed | Requires representative and clinical validation |

## Humanizer audit

The first draft still sounded too assembled in two places: the problem statement used an evenly paced list, and the value statement read like a product brochure. The final copy breaks the rhythm with direct sentences, names the exact feedback delay, and uses "could" only for the proposed physiotherapist workflow. It removes promotional adjectives, generic impact language, vague expert attribution, em dashes, and unsupported clinical implications.
