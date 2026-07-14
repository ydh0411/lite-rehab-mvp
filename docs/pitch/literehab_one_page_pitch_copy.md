# LiteRehab Fusion

*Immediate feedback for upper-limb rehabilitation practice at home.*

## Feedback arrives too late

A patient may leave a physiotherapy appointment knowing what to practise. At home, it is harder to tell whether the movement was controlled and large enough, or whether leaning did part of the work. By the next appointment, those repetitions are already behind them.

## LiteRehab responds during the repetition

LiteRehab gives a cue while the exercise is still happening. A forearm wearable tracks motion, while a camera checks posture. Together, they identify the demonstrated exercise, count repetitions, and flag excessive speed, limited range, or trunk compensation. The dashboard also keeps a synchronized session record.

## Motion and posture, seen together

Wearable motion sensing + Camera posture tracking -> Synchronized analysis -> Immediate coaching cue

## What the prototype does today

- Recognises the demonstrated elbow-flexion and forearm-rotation exercises.
- Gives feedback for excessive speed, insufficient range, and trunk compensation.
- Shows the repetition count on the wearable and records synchronized motion and posture data.
- Uses a classroom CNN-BiGRU baseline with a rule-based fallback.

## A cue now, a record for later

**For the person practising:** A short cue arrives in time to adjust the next repetition.

**For the physiotherapist:** A session record could show what happened between appointments. Exercise selection and clinical decisions remain with the physiotherapist.

## Next: supervised usability testing

Our next step is to test the workflow with physiotherapists and representative users. Their feedback would help us refine the prompts and collect movement data under professional supervision.

## Scope

LiteRehab Fusion is a coursework engineering prototype, not a medical device. It does not diagnose, prescribe treatment, score recovery, or replace professional supervision. The current system supports a limited exercise set and makes no clinical accuracy claim.

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

The working draft used three consecutive rhetorical questions in the problem statement and repeated the same subject-verb pattern across several sections. It also described the product as giving "simple" feedback without explaining what made the feedback simple.

### What makes the below so obviously AI generated?

- The opening was arranged as an overly tidy sequence of three questions.
- Several sentences stacked three benefits or actions in the same rhythm.
- The first user-value heading described an audience category instead of saying what each person receives.

### Final rewrite

The final copy turns the three opening questions into one concrete sentence about control, range, and leaning. It uses shorter sentences where the user story needs emphasis, names the actual prompts and limits, and keeps conditional language for the proposed physiotherapist workflow. Promotional adjectives, vague authority, em dashes, engineering test totals, and unsupported clinical implications have been removed.
