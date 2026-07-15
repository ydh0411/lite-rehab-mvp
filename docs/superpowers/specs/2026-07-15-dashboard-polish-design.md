# LiteRehab Dashboard Polish Design

## Goal

Polish the existing 1280 x 720 OpenCV dashboard into a presentation-ready
rehabilitation interface. The new version should feel like a focused clinical
product rather than a collection of monitoring panels, while preserving all
camera, pose, telemetry, inference, synchronization, logging, and keyboard
behavior.

## Selected Direction

Use a clinical-technology visual language with a rehabilitation-coach focus.
The camera remains the dominant surface, while repetitions, range of motion,
model confidence, and IMU activity form a deliberate secondary hierarchy.
Device health stays visible but does not compete with patient feedback.

The alternative directions were a dense clinical monitor and an extremely
minimal presentation screen. The selected direction balances technical
credibility with clarity during a live project demonstration.

## Visual System

The interface uses a deep navy background, slightly lighter blue-gray surfaces,
and a restrained semantic palette:

- cyan and teal identify active measurements and primary interaction;
- green identifies healthy devices and correct movement;
- amber identifies coaching that needs attention;
- red is reserved for unsafe compensation and failed inputs;
- cool gray identifies idle, unavailable, or warming-up information.

Colors should be less saturated than the current dashboard so the camera and
patient feedback remain the visual focus. Cards use subtle borders, rounded
corners, and limited highlights instead of large flat rectangles. Spacing,
label sizes, and numeric typography follow a consistent scale. OpenCV's built-in
font remains in use, so interface copy stays concise and in English.

## Layout and Components

The composition keeps the existing fixed canvas and divides it into three
visual levels:

1. A compact header contains the LiteRehab identity and small health chips for
   serial, camera, and fusion mode. Health chips use a status dot and concise
   label, and remain visually quieter than rehabilitation feedback.
2. The left two-thirds contain the live camera in a rounded, bordered frame.
   A compact exercise pill sits at the top-left. The highest-priority coaching
   message appears near the bottom as a translucent banner with a semantic
   accent strip rather than a large solid color block.
3. The right rail begins with a dominant repetition card. Below it, range of
   motion uses a compact arc or gauge, model confidence uses a thin progress
   indicator, and the IMU chart receives the remaining space. The footer keeps
   the existing keyboard shortcuts.

The repetition visualization uses the existing repetition count and a
decorative progress arc; it does not invent a session target. The ROM gauge
shows the measured degree value and gracefully handles missing data. Confidence
shows existing status or confidence text without changing how the model is
evaluated.

## Camera and Pose Treatment

Pose landmarks remain drawn over the camera feed. Lines and joints adopt the
new cyan/teal visual language, with unsafe feedback allowed to switch the
relevant overlay emphasis to amber or red. The renderer does not infer new
clinical states; it only visualizes the existing feedback severity.

Camera overlays must preserve the visibility of the patient. Translucent
surfaces, short copy, and edge-aligned placement prevent the UI from obscuring
important body landmarks.

## Architecture and Data Flow

`python/literehab/dashboard_view.py` remains the presentation boundary. It
continues to receive `DashboardViewState`, the current camera frame, and recent
telemetry history from `python/run_dashboard.py`.

The rendering module will add small, isolated helpers for rounded cards,
progress arcs, confidence bars, status chips, and feedback banners. These
helpers consume presentation values only. Sensor acquisition, pose analysis,
fusion decisions, repetition counting, logging, and runtime controls remain in
their existing modules.

The data flow is unchanged:

1. Runtime modules acquire and evaluate camera and IMU data.
2. `run_dashboard.py` builds the existing presentation state.
3. `dashboard_view.py` maps state to semantic colors and composes the canvas.
4. OpenCV displays the completed frame and processes the existing keyboard
   controls.

## Interaction and Failure States

Existing controls remain unchanged: `B` recaptures the posture baseline, `R`
resets the range tracker, and `Q` or `Esc` exits.

When the camera is unavailable, the camera surface shows a centered, designed
IMU-only state with a short explanation. Missing ROM or confidence values show
`--` or the existing warm-up message. Disconnected inputs use the same card
geometry as healthy states so failures do not disturb the layout. Unknown
future feedback still appears through the existing fallback mapping.

## Verification

Tests will cover semantic tone mapping, rounded-card and progress rendering at
canvas edges, missing optional values, disconnected camera states, empty IMU
history, and successful 1280 x 720 composition. A representative rendered PNG
will be generated for visual inspection. The focused dashboard tests and the
existing headless dashboard smoke test must pass before completion.

## Scope Limits

This polish does not add a web frontend, new UI dependency, custom font,
session goal, persistence, animation loop, or new clinical decision. It does
not change the wearable or receiver firmware, model outputs, camera pipeline,
CSV logging, or shortcut behavior.
