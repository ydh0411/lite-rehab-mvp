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
3. A concise problem-to-response narrative under conventional academic section headings.
4. A concise prose description of the wearable unit, posture input, and analysis interface.
5. A short account of what the working prototype does today.
6. A paired patient and physiotherapist value block.
7. A single next step: supervised usability testing with physiotherapists and representative users.
8. A restrained footer stating that the work is a coursework engineering prototype and not a medical device.

The full-width summary should establish the project and its scope. The two equal body columns should then cover the background, aim, system design, demonstrated capabilities, intended use, limitations, and next step. Avoid a sequence of equally weighted boxes.

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

Use a clean one-page technical report rather than a poster, brochure, or infographic. Borrow only the typographic discipline of current ICML, CVPR, and AAAI materials: clear alignment, economical text, a strong title area, and an obvious reading path. Place a short full-width summary beneath the title, followed by a regular two-column report body. Do not include a flow diagram.

Use one Helvetica-like sans serif family (`helvet`, rendered as Nimbus Sans) throughout the title, headings, body copy, and labels. Keep body copy at least 9 pt. Establish hierarchy through size, weight, spacing, and alignment rather than mixed typefaces, repeated coloured boxes, underlines, or decorative rules.

Use muted institutional navy (`#16324F`) as the only chromatic accent. Use charcoal for body text and neutral greys for supporting text, rules, and the one optional background panel. Do not use bright cyan or teal. The institutional row must keep all three marks optically balanced even though their aspect ratios differ: size the Glasgow wordmark by width, the CUHK wordmark by width, and the UESTC seal by height rather than applying one common image height.

Describe the system under `System design` using three short subheadings: `Wearable unit`, `Posture input`, and `Analysis and interface`. Do not use nodes, connectors, icons, gradients, shadows, or a prompt strip.

Use conventional academic poster headings. This is more appropriate here than slogan-like or message-led headings. The required headings are:

- `Background`
- `Aim`
- `System design`
- `Prototype capabilities`
- `Intended use`
- `Limitations and next steps`

Do not add a strip of example prompts such as "Slow down", "Increase the range", or "Keep the trunk still". Describe feedback categories in the prose without presenting them as invented interface copy.

Remove the current bottom `\vfill` behaviour and allocate the page height explicitly. The final layout should not contain a conspicuous empty lower third. Whitespace should separate ideas and establish hierarchy, while the content should still occupy the page confidently at normal print size.

The compiled page must have no overflow, clipped text, unresolved references, missing glyphs, or content on a second page. Verify the final PDF by rendering it to an image and inspecting the full page at normal reading size.

## Visual references

The design takes principles, not a literal template, from:

- the CVPR 2025 poster guidance, especially its advice on column-based reading, limited text, and designing for a crowded session;
- the ICML 2025 poster instructions and public poster examples, especially their strong title hierarchy, economical text, and clear alignment;
- the BMEG3920 course slides, which establish the three-institution header.

## Deliverables

The writing phase will produce:

- an editable LaTeX source file for a polished one-page English pitch;
- a compiled, submission-ready A4 PDF;
- a compact version suitable for placing directly into a single-page visual layout;
- a brief claim audit identifying which statements are demonstrated, proposed, or future work;
- a final Humanizer pass that preserves the technical meaning and course-appropriate tone.
