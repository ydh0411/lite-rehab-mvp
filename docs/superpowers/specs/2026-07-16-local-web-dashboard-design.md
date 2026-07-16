# LiteRehab Local Web Dashboard Design

## Goal

Turn the existing LiteRehab Python/OpenCV demonstration into a polished,
offline web application for a classroom presentation. The application must
preserve the current ESP32-S3 serial telemetry, MaixCAM2 camera, MediaPipe pose
analysis, IMU inference, ECG display, feedback rules, and CSV recording while
adding clear history and report views.

The primary audience is course instructors and classmates. The interface
should make the system understandable within a few seconds, remain stable on a
single presentation laptop, and look like a coherent rehabilitation product
rather than a generic admin template.

LiteRehab remains an engineering prototype. The web application and its
reports must state that they are not medical diagnosis, treatment, or clinical
assessment tools.

## Selected Direction

Use a local FastAPI backend with a React, TypeScript, and Vite single-page
frontend. Tailwind CSS and shadcn/ui-style components provide a consistent
design system; Recharts renders historical and summary charts. The complete
application runs on one laptop without internet access.

The earlier lightweight HTML option would minimize dependencies but would make
a refined multi-page product interface slower to build and maintain. Streamlit
would accelerate tables and charts but offers less control over the live
training composition and presentation polish. A cloud-hosted or Next.js system
would add deployment, authentication, and network complexity without helping
the classroom demonstration.

## Design References

The frontend may adapt interaction and layout patterns from these open-source
projects without copying an entire template:

- [shadcn/ui](https://github.com/shadcn-ui/ui): accessible component patterns,
  dashboard hierarchy, cards, tables, dialogs, and chart containers;
- [shadcn-admin](https://github.com/satnaing/shadcn-admin): a proven
  Vite/TypeScript application shell, compact navigation, responsive tables,
  and practical empty/error states;
- [OpenStatus](https://github.com/openstatusHQ/openstatus): restrained
  real-time monitoring, connection state, freshness, and incident presentation;
- [Tremor OSS dashboard](https://github.com/tremorlabs/template-dashboard-oss):
  readable time-series charts, summary-to-detail hierarchy, and dense but calm
  analytics layouts;
- [Nightscout](https://github.com/nightscout/cgm-remote-monitor): real sensor
  freshness, threshold states, disconnected-data handling, and caregiver-first
  monitoring priorities;
- [Medplum](https://github.com/medplum/medplum): restrained healthcare product
  language and patient-context presentation.

Only the patterns needed by LiteRehab will be implemented. Authentication,
billing, chat, appointment management, cloud storage, and generic admin pages
are outside the scope.

## Information Architecture

The application has a persistent left navigation rail and three primary pages.
On narrower screens the rail collapses, but the classroom target is a 1280 x
720 or larger laptop display.

### Live Training

This is the default and presentation-critical page.

- The upper bar shows the LiteRehab identity, current participant ID, session
  timer, recording state, and compact serial/camera/model health indicators.
- The left two-thirds show the annotated camera feed. Pose landmarks and the
  current exercise label remain visible without covering the participant.
- A prominent coaching banner communicates `READY`, `GOOD FORM`, `SLOW DOWN`,
  `INCREASE RANGE`, or `AVOID TRUNK COMPENSATION` using text, icon, and color.
- The right column prioritizes repetition count, range of motion, and current
  exercise. Model confidence is visible but secondary.
- A full-width lower card shows the scrolling ECG waveform, BPM when leads are
  connected, and an explicit `LEADS OFF` state. ECG is labelled as a
  demonstration signal and is not interpreted clinically.
- Session controls allow starting, stopping, recapturing the posture baseline,
  and resetting the range tracker. Destructive actions require confirmation.

The live page avoids dense tables and decorative gauges that do not represent
real goals. Every displayed metric comes from the existing runtime state.

### Session History

The history page presents locally recorded sessions.

- Summary cards show total sessions, total valid repetitions, average session
  duration, and the most recently recorded session.
- A searchable and sortable table shows participant ID, date, duration,
  exercises observed, repetitions, good-form percentage, maximum range of
  motion, and device/data completeness.
- Selecting a row opens its report page.
- Filters include participant, exercise, and date. Empty, malformed, and
  partially recorded sessions have explicit states instead of disappearing.

Participant identifiers are labels entered for the classroom demonstration,
not a clinical patient registry. No names or other personally identifying
fields are required.

### Session Report

The report page summarizes one selected session.

- Header: participant ID, session date/time, duration, sensor availability,
  and exercise coverage.
- KPI row: valid repetitions, good-form percentage, maximum observed range of
  motion, and average BPM over connected ECG samples.
- Charts: repetitions over time, range-of-motion trend, feedback/quality
  distribution, and BPM trend when ECG data is available.
- Notes explain missing camera, pose, model, or ECG data and distinguish
  measured values from unavailable values.
- A print action uses a dedicated print stylesheet so the browser can save a
  clean PDF locally. The printed report includes the prototype disclaimer.

The report does not assign a rehabilitation score, diagnose ECG findings,
recommend treatment, or claim patient improvement from a single session.

## Visual System

The default theme uses a calm light clinical workspace rather than the current
dark OpenCV canvas. A deep navy navigation rail anchors the application;
off-white page surfaces and white cards improve projector readability. Teal is
the primary action and live-data color. Green indicates confirmed good form or
healthy connections, amber indicates coaching attention or incomplete data,
and red is reserved for unsafe compensation and failed inputs.

The UI uses a restrained radius, subtle borders, minimal shadow, consistent
spacing, tabular numerals for live metrics, and Lucide icons. Status must never
depend on color alone. Motion is limited to small state transitions and chart
updates; no decorative animation competes with the live demonstration.

The result must not look like a generic AI-generated dashboard. In particular,
it avoids gradient text, glowing borders, oversized rounded cards, glassmorphism,
decorative blobs, excessive badges, fake percentage KPIs, uniformly centered
content, and generic marketing copy. Card sizes follow the importance and shape
of real data rather than a repeated template. Labels use the terminology already
present in LiteRehab, and every chart or number must answer a concrete
demonstration question.

Typography and spacing preserve readability at 1280 x 720. The live training
page should fit without vertical scrolling at that resolution. History and
report pages may scroll normally.

## Architecture and Component Boundaries

### Runtime Engine

Extract the reusable acquisition and processing loop from
`python/run_dashboard.py` into a focused runtime service. It owns serial and
camera lifecycle, pose extraction, synchronization, inference, feedback,
session CSV writers, and the latest annotated frame. It exposes immutable live
snapshots and explicit commands such as start session, stop session, recapture
baseline, and reset range.

The existing OpenCV dashboard remains available during migration. Business
rules stay in their current modules; the web layer does not reimplement motion,
feedback, ECG, or fusion decisions.

### FastAPI Application

The local backend owns the runtime engine and provides:

- REST endpoints for system configuration, session commands, session lists,
  session summaries, and report data;
- one WebSocket stream for live metrics, ECG samples, statuses, and feedback;
- one annotated-camera stream using browser-compatible JPEG frames;
- static hosting for the built frontend in the packaged demonstration mode.

The server binds to `127.0.0.1` by default and opens the system browser. It does
not require an account, internet connection, external database, or cloud API.

### React Frontend

The frontend is divided into page-level features (`live`, `history`, and
`report`) plus shared layout, status, chart, and formatting components. A small
API client contains all REST and WebSocket access. Live telemetry is kept in a
bounded client-side buffer so charts do not grow indefinitely.

The frontend never reads hardware directly. It renders backend state and sends
explicit user commands, keeping hardware-specific behavior testable in Python.

### Local Session Repository

Existing session and ECG CSV files remain the source data. A repository service
discovers valid session pairs, parses them defensively, derives summaries, and
returns stable API models. This avoids a data migration and preserves
compatibility with training scripts. Derived summaries may be cached in memory,
but CSV files remain authoritative.

### Derived Metric Definitions

Report metrics must be reproducible from existing columns:

- session duration is the difference between the first and last valid
  `received_s` values;
- valid repetitions are the positive increments in `rep_count`, with counter
  resets starting a new segment instead of producing a negative event;
- exercise coverage is the set of non-idle `state` values observed;
- quality counts use distinct non-`none` quality events rather than counting
  every telemetry row that repeats the same state;
- good-form percentage is `ok` events divided by all recognized quality events
  and is unavailable when no quality event exists;
- range of motion is the peak-to-peak elbow or shoulder angle over contiguous
  valid-pose intervals for the relevant exercise. It is unavailable for an
  exercise without a supported visual angle or sufficient valid pose rows;
- average BPM uses positive BPM values from ECG rows where
  `leads_connected` is true;
- data completeness is reported separately for serial, valid pose, and
  connected ECG samples, so one source cannot hide another source's absence.

These definitions are engineering summaries for the demonstration and are not
clinical outcome measures.

## Data Flow

1. The Python runtime receives IMU and ECG serial records and camera frames.
2. Existing modules calculate pose features, inference, repetition state, and
   feedback while the session writers append CSV rows.
3. The backend publishes bounded live snapshots over WebSocket and the latest
   annotated video frame over the camera endpoint.
4. React updates live cards and charts without refreshing the page.
5. The history repository reads completed CSV files and derives session-level
   statistics.
6. The report page requests one derived summary and renders printable charts
   and explanatory data-quality notes.

## Failure and Recovery States

- Serial unavailable: keep the application open, show a reconnecting state,
  disable session start when no meaningful data can be recorded, and continue
  automatic reconnection.
- Camera unavailable: switch clearly to IMU-only mode while preserving serial
  feedback and ECG recording.
- Pose unavailable: retain the video feed, mark visual metrics unavailable,
  and avoid displaying zero as a genuine measurement.
- ECG leads off: show a flat placeholder state and record the existing
  connection flag; do not present BPM as zero.
- WebSocket interruption: display `Reconnecting`, retry with backoff, and
  replace the live buffer with a fresh snapshot after reconnection.
- Malformed or incomplete CSV: keep the session visible with a data-quality
  warning and omit statistics that cannot be derived reliably.
- Camera frame delay: show the last-frame timestamp and a stale indicator
  rather than silently freezing.

## Testing and Verification

Python tests cover runtime command boundaries, REST response models, WebSocket
snapshot serialization, camera stream availability, CSV discovery, derived
session metrics, incomplete data, and missing hardware behavior.

Frontend tests cover state labels, live-card formatting, bounded chart buffers,
history filtering, empty/error states, report metric formatting, and print-only
content. A browser-level smoke test verifies navigation among all three pages
against a deterministic local fixture backend.

Final verification includes the existing C and Python test suites, a frontend
production build, the new backend and frontend tests, a headless browser smoke
test, and manual inspection at 1280 x 720. A hardware-independent fixture mode
is permitted for automated tests only; the classroom UI must clearly display
real connection status.

## Scope Limits

This version does not add cloud hosting, user accounts, remote access, a mobile
application, clinician messaging, treatment plans, data editing, a clinical
database, or diagnostic ECG analysis. It does not change wearable or receiver
firmware, motion thresholds, model outputs, or feedback rules.
