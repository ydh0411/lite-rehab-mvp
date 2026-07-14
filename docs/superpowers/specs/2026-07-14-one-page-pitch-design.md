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

Use an A4 portrait academic product brief rather than a miniature research poster. The page should read from top to bottom, with an asymmetric two-column body beneath the title.

1. A slim institutional row using the Glasgow, CUHK, and UESTC marks already embedded in the course slide deck.
2. Product name, course context, and one short value proposition.
3. A concise problem-to-response narrative led by message-based headings rather than generic labels.
4. A compact horizontal system flow: wearable motion sensing and camera posture tracking feed synchronized analysis, which produces an immediate coaching cue.
5. A short account of what the working prototype does today.
6. A paired patient and physiotherapist value block.
7. A single next step: supervised usability testing with physiotherapists and representative users.
8. A restrained footer stating that the work is a coursework engineering prototype and not a medical device.

The main column should carry the problem, response, and flow. The narrower column should carry current capability, user value, and the next step. Avoid a sequence of equally weighted boxes.

## Required evidence

The pitch may state that the current MVP:

- samples forearm motion with an MPU6050 at 50 Hz;
- sends motion data from an ESP32 wearable to an ESP32-S3 receiver over BLE;
- combines IMU motion information with computer-based MediaPipe posture checks using a MaixCAM2 video stream;
- recognises the demonstrated elbow-flexion and forearm-rotation exercises;
- provides feedback for excessive speed, insufficient range, and trunk compensation;
- displays local status and repetition count and provides LED or buzzer feedback;
- records synchronized IMU and pose information for later review;
- automatically loads a classroom CNN-BiGRU baseline trained on a small public upper-limb IMU subset.

Do not include test counts, build targets, smoke-test results, or similar software-development evidence in the visible pitch. These details are useful for internal engineering validation but do not strengthen the audience-facing product story. The pitch must not imply clinical effectiveness, diagnostic accuracy, or improved patient outcomes.

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

## Format and layout

Produce the final pitch in LaTeX as a single A4 portrait page. Keep the source editable and compile it into a submission-ready PDF.

Use a clean academic product-brief layout rather than a poster or a two-column conference-paper template. Borrow the visual discipline of top-conference posters---clear alignment, decisive hierarchy, economical text, and an obvious reading path---without filling the page with research figures. The page should have a strong title area, an asymmetric two-column grid, a simple vector system-flow graphic, and controlled rather than excessive whitespace.

Use a Times-like academic serif (`newtxtext`) for body copy and a Helvetica-like sans serif (`helvet` or TeX Gyre Heros) for the title, message headings, labels, and flow nodes. This hybrid should feel more familiar than Latin Modern while preserving fast scanning. Keep body copy at least 9 pt, use visibly larger message headings, and distinguish levels primarily through size, weight, spacing, and alignment rather than repeated coloured boxes.

Use Glasgow navy as the primary accent and a restrained cyan/teal as a secondary accent, consistent with the course slides. The institutional row must keep all three marks optically balanced even though their original aspect ratios differ. Extract the original embedded SVG/PNG assets from `Day 3 Slide Deck.pptx`; do not download substitutes or rasterize the Glasgow SVG unnecessarily.

The system flow should use four flat, horizontally aligned nodes with thin directional connectors and short verb-led labels. It should read:

> Wearable motion sensing + Camera posture tracking -> Synchronized analysis -> Immediate coaching cue

The two sensing inputs should visibly converge before analysis. Use no gradients, shadows, 3D effects, stock icons, or ornamental arrows.

Replace formulaic headings such as "The gap", "Our response", "How it works", and "Who benefits" with headings that carry the argument. Working examples are:

- `Feedback arrives too late`
- `LiteRehab responds during the repetition`
- `Motion and posture, seen together`
- `What the prototype does today`
- `Built for both sides of rehabilitation`
- `Next: supervised usability testing`

Use these as working language, not a rigid template. The final wording should be natural, concise, and balanced in the available space.

Remove the current bottom `\vfill` behaviour and allocate the page height explicitly. The final layout should not contain a conspicuous empty lower third. Whitespace should separate ideas and establish hierarchy, while the content should still occupy the page confidently at normal print size.

The compiled page must have no overflow, clipped text, unresolved references, missing glyphs, or content on a second page. Verify the final PDF by rendering it to an image and inspecting the full page at normal reading size.

## Visual references

The design takes principles, not a literal template, from:

- the CVPR 2025 poster guidance, especially its advice on column-based reading, limited text, and designing for a crowded session;
- the ICML 2025 poster instructions and public poster examples, especially their strong title hierarchy, content-specific headings, and clear left-to-right flow;
- the BMEG3920 course slides, which establish the three-institution header and navy/cyan visual identity.

## Deliverables

The writing phase will produce:

- an editable LaTeX source file for a polished one-page English pitch;
- a compiled, submission-ready A4 PDF;
- a compact version suitable for placing directly into a single-page visual layout;
- a brief claim audit identifying which statements are demonstrated, proposed, or future work;
- a final Humanizer pass that preserves the technical meaning and course-appropriate tone.
