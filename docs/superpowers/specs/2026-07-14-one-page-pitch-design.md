# LiteRehab Fusion one-page pitch design

## Purpose

Create a one-page English product pitch for the BMEG3920 course. The document must let an academic or industry reviewer understand the user problem, the proposed solution, the working MVP, and the next validation step in roughly one minute.

The page supports the July 17 five-minute team pitch and the later panel presentation. It is a product pitch, not a technical paper, clinical claim, or instruction manual.

## Audience and users

The immediate audience is the BMEG3920 teaching and judging panel.

The primary product user is a person practising prescribed upper-limb rehabilitation exercises at home. A physiotherapist is the secondary user who may later review recorded sessions and adjust the rehabilitation plan. The pitch must not imply that the prototype replaces a physiotherapist or makes treatment decisions.

## Narrative choice

Use a patient-problem-first narrative. Begin with the gap between supervised clinic sessions and unsupervised home practice, then show how LiteRehab provides immediate feedback and records the session.

Do not lead with the hardware stack or AI model. Technical details should support the product claim after the reader understands the problem.

## Core claim

LiteRehab Fusion gives people practising upper-limb rehabilitation at home immediate, understandable feedback by combining wearable motion sensing with camera-based posture checks, while recording each session for later review by a physiotherapist.

## Page structure

1. Product name and short tagline.
2. A concrete description of the home-practice problem.
3. The gap in current practice: limited immediate feedback between appointments.
4. The LiteRehab solution and its user-facing behaviour.
5. A compact system flow: wearable IMU to BLE receiver and computer dashboard, combined with MaixCAM2 pose input.
6. What the MVP currently demonstrates.
7. Benefits for the patient and physiotherapist.
8. A plausible route to adoption, explicit limitations, and a specific next-step request.

## Required evidence

The pitch may state that the current MVP:

- samples forearm motion with an MPU6050 at 50 Hz;
- sends motion data from an ESP32 wearable to an ESP32-S3 receiver over BLE;
- combines IMU motion information with computer-based MediaPipe posture checks using a MaixCAM2 video stream;
- recognises the demonstrated elbow-flexion and forearm-rotation exercises;
- provides feedback for excessive speed, insufficient range, and trunk compensation;
- displays local status and repetition count and provides LED or buzzer feedback;
- records synchronized IMU and pose information for later review;
- automatically loads a classroom CNN-BiGRU baseline trained on a small public upper-limb IMU subset;
- has passed 70 Python tests, three C host tests, a model-loading smoke test, and builds for both ESP32 targets.

Testing and successful builds demonstrate engineering readiness for a classroom proof of concept. They do not demonstrate clinical effectiveness, diagnostic accuracy, or improved patient outcomes.

## Business and adoption framing

Present the initial route to use as a supervised pilot with physiotherapists or rehabilitation providers. A future product could be supplied through clinics as part of a home-exercise programme, with the physiotherapist retaining responsibility for exercise selection and clinical decisions.

Do not invent market size, price, revenue, partnerships, user interviews, clinical trials, or regulatory status. The closing request should seek physiotherapist collaboration for usability testing and collection of representative movement data.

## Safety and limitations

State clearly that LiteRehab Fusion is an engineering prototype, not a medical device. It does not diagnose conditions, prescribe treatment, score clinical recovery, or replace professional supervision.

The current model uses a small public dataset and has no clinical accuracy claim. The MVP supports a limited set of upper-limb exercises and still needs testing with representative users under professional supervision.

## Language and tone

Write in accessible international English. Use short sentences, active voice, and concrete verbs. Define unavoidable technical terms in context and mention each model or component only when it helps explain the product.

Avoid academic abstraction, marketing superlatives, invented quotations, inflated impact statements, and AI-writing habits such as repetitive three-part lists, excessive em dashes, vague expert attribution, or generic conclusions. The final text should sound natural when read aloud by a student team.

The tagline is:

> Real-time guidance for more consistent upper-limb rehabilitation practice at home.

## Deliverables

The writing phase will produce:

- a polished one-page English pitch;
- a compact version suitable for placing directly into a single-page visual layout;
- a brief claim audit identifying which statements are demonstrated, proposed, or future work;
- a final Humanizer pass that preserves the technical meaning and course-appropriate tone.
