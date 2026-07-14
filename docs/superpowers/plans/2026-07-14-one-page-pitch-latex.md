# LiteRehab Fusion one-page pitch redesign implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the LiteRehab Fusion one-page pitch as a polished A4 academic product brief with three institutional marks, natural English copy, a compact converging system flow, and no conspicuous unused space.

**Architecture:** Keep claim-bounded copy and its audit in Markdown, store the three original course-slide logos as local assets, and typeset both through one editable LaTeX source. Use an asymmetric two-column grid, a Times-like body face, a Helvetica-like display face, and a flat TikZ flow. Compile and inspect the PDF mechanically and visually after every meaningful layout change.

**Tech Stack:** Markdown; pdfLaTeX; `newtxtext`, `helvet`, `geometry`, `microtype`, `graphicx`, `xcolor`, `tabularx`, `enumitem`, and TikZ; Poppler `pdfinfo`, `pdffonts`, `pdftotext`, and `pdftoppm`; original PNG assets embedded in `Day 3 Slide Deck.pptx`.

## Global constraints

- Produce exactly one A4 portrait page.
- Use the academic product-brief design approved as option B, not a literal ICML or CVPR poster template.
- Use `newtxtext` for body copy and Helvetica (`helvet`, scaled to 0.94) for the title, message headings, labels, and flow nodes.
- Keep body copy at or above 9 pt and preserve a clear top-to-bottom reading order.
- Place the original University of Glasgow, CUHK, and UESTC marks in a slim, optically balanced institutional row.
- Use Glasgow navy as the primary accent and restrained cyan/teal as the secondary accent.
- Use message-led headings instead of generic labels such as "The gap", "Our response", "How it works", and "Who benefits".
- Do not include test counts, build targets, smoke-test results, or other software-development validation in the visible pitch.
- State that LiteRehab Fusion is an engineering prototype, not a medical device, and make no clinical-effectiveness claim.
- Preserve the user's modified source files and unrelated untracked course documents; stage only pitch deliverables.

---

### Task 1: Prepare the three institutional logo assets

**Files:**
- Source: `Day 3 Slide Deck.pptx`
- Create: `assets/institutions/university-of-glasgow.png`
- Create: `assets/institutions/cuhk.png`
- Create: `assets/institutions/uestc.png`

**Interfaces:**
- Consumes: `ppt/media/image2.png`, `ppt/media/image3.png`, and `ppt/media/image4.png` from the course slide deck.
- Produces: three transparent PNG assets that LaTeX includes with `\includegraphics`.

- [ ] **Step 1: Extract the original embedded PNGs**

Run:

```bash
mkdir -p assets/institutions tmp/logo-extract
unzip -j "Day 3 Slide Deck.pptx" \
  ppt/media/image2.png ppt/media/image3.png ppt/media/image4.png \
  -d tmp/logo-extract
cp tmp/logo-extract/image2.png assets/institutions/university-of-glasgow.png
cp tmp/logo-extract/image3.png assets/institutions/cuhk.png
cp tmp/logo-extract/image4.png assets/institutions/uestc.png
```

Expected: the three named files exist under `assets/institutions/`; no other course-slide media are copied into the deliverable assets folder.

- [ ] **Step 2: Verify file type and source dimensions**

Run:

```bash
file assets/institutions/*.png
sips -g pixelWidth -g pixelHeight assets/institutions/*.png
```

Expected dimensions: Glasgow `313 x 170`, CUHK `316 x 76`, and UESTC `322 x 309`. All files are PNGs with alpha channels.

- [ ] **Step 3: Commit only the logo assets**

```bash
git add assets/institutions/university-of-glasgow.png \
  assets/institutions/cuhk.png assets/institutions/uestc.png
git commit -m "docs: add institutional marks for pitch"
```

### Task 2: Rewrite and humanize the pitch copy

**Files:**
- Modify: `docs/pitch/literehab_one_page_pitch_copy.md`

**Interfaces:**
- Consumes: verified project capabilities from `README.md`, `DEMO_GUIDE.md`, and the approved design specification.
- Produces: final message-led copy for the LaTeX document, plus a claim and Humanizer audit.

- [ ] **Step 1: Replace the visible copy with the approved narrative**

Use this wording as the working draft:

```markdown
# LiteRehab Fusion

*Immediate feedback for upper-limb rehabilitation practice at home.*

## Feedback arrives too late

A patient may know which exercises to practise after a physiotherapy appointment, but still be unsure about the next repetition at home. Was the movement controlled? Was the range large enough? Did the trunk compensate? By the next appointment, that practice has already happened.

## LiteRehab responds during the repetition

The prototype combines a forearm wearable with camera-based posture tracking. It identifies the demonstrated exercise, counts repetitions, and gives a short cue when the movement is too fast, too small, or assisted by trunk movement. The session is recorded for later review.

## Motion and posture, seen together

Wearable motion sensing + Camera posture tracking -> Synchronized analysis -> Immediate coaching cue

## What the prototype does today

- Recognises the demonstrated elbow-flexion and forearm-rotation exercises.
- Gives feedback for excessive speed, insufficient range, and trunk compensation.
- Shows the repetition count on the wearable and records synchronized motion and posture data.
- Uses a classroom CNN-BiGRU baseline with a rule-based fallback.

## Built for both sides of rehabilitation

**For the patient:** A clear cue arrives while the repetition can still be corrected.

**For the physiotherapist:** A session record could show what happened between appointments. Exercise selection and clinical decisions remain with the physiotherapist.

## Next: supervised usability testing

The next step is to test the workflow with physiotherapists and representative users, then refine the feedback and collect movement data under professional supervision.

LiteRehab Fusion is a coursework engineering prototype, not a medical device. It does not diagnose, prescribe treatment, score recovery, or replace professional supervision. The current system supports a limited exercise set and makes no clinical accuracy claim.
```

- [ ] **Step 2: Apply the Humanizer skill audit**

Check the draft for promotional wording, vague authority, repetitive groups of three, negative parallelism, em-dash overuse, filler, and evenly paced sentences. Ask: "What makes the below so obviously AI generated?" Record the remaining tells, then revise once more. Preserve `could` for the proposed physiotherapist workflow and keep demonstrated capabilities in the present tense.

Expected: natural international English that a student team can read aloud; no marketing superlatives, generic conclusions, or invented evidence.

- [ ] **Step 3: Update the claim audit**

The audit table must classify motion sensing, camera posture input, two demonstrated exercises, three feedback categories, repetition count, and synchronized logging as demonstrated. It must classify later physiotherapist review and supervised usability testing as proposed. It must explicitly mark clinical effectiveness and diagnostic accuracy as not claimed. Remove the row for automated test and build totals.

- [ ] **Step 4: Run copy boundary checks**

Run:

```bash
rg -n -i "70 Python|host tests|smoke test|builds for|clinically proven|improves recovery|prevents injury|approved|market size|revenue|partnership" docs/pitch/literehab_one_page_pitch_copy.md
```

Expected: no matches.

- [ ] **Step 5: Commit the copy**

```bash
git add docs/pitch/literehab_one_page_pitch_copy.md
git commit -m "docs: rewrite one-page pitch narrative"
```

### Task 3: Rebuild the LaTeX page with the approved option B layout

**Files:**
- Modify: `output/pdf/literehab_one_page_pitch.tex`
- Regenerate: `output/pdf/literehab_one_page_pitch.pdf`

**Interfaces:**
- Consumes: the three logo assets from Task 1 and final humanized copy from Task 2.
- Produces: an editable A4 LaTeX source and a compiled single-page PDF.

- [ ] **Step 1: Replace the typography and page primitives**

Use this preamble and hierarchy:

```latex
\documentclass[10pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage{newtxtext}
\usepackage[scaled=0.94]{helvet}
\usepackage[protrusion=true,expansion=true]{microtype}
\usepackage[left=14mm,right=14mm,top=10mm,bottom=10mm]{geometry}
\usepackage{graphicx,xcolor,tabularx,enumitem,tikz}
\usetikzlibrary{arrows.meta,positioning,calc}

\definecolor{PitchNavy}{HTML}{071B58}
\definecolor{PitchTeal}{HTML}{35BFC8}
\definecolor{PitchInk}{HTML}{182234}
\definecolor{PitchMuted}{HTML}{5B6470}
\definecolor{PitchPale}{HTML}{EEF6F7}
\definecolor{PitchRule}{HTML}{D7DEE5}

\newcommand{\displayfont}{\fontfamily{phv}\selectfont}
\newcommand{\messagehead}[1]{{\displayfont\bfseries\color{PitchNavy}\fontsize{13.2}{14.5}\selectfont #1\par}}
\newcommand{\eyebrow}[1]{{\displayfont\bfseries\color{PitchTeal!70!PitchNavy}\fontsize{7.8}{8.5}\selectfont\MakeUppercase{#1}}}
```

Remove `lmodern`, the navy full-width title box, generic `\sectiontitle`, repeated vertical rules, and the bottom `\vfill`.

- [ ] **Step 2: Build the institutional and title area**

Create a `tabularx` row with the Glasgow wordmark on the left, CUHK wordmark centred, and UESTC seal on the right. Set optical heights rather than equal widths: approximately `11.5mm`, `8.0mm`, and `13.0mm`. Place `BMEG3920 · ONE-PAGE PITCH` beneath a thin rule, followed by a 27-29 pt Helvetica title and the humanized tagline. Keep the header white and use navy text instead of a heavy colour block.

- [ ] **Step 3: Build the asymmetric two-column body**

Use a `0.625\linewidth` main column and `0.335\linewidth` side column separated by whitespace. The main column contains:

1. `Feedback arrives too late` with the complete problem paragraph.
2. `LiteRehab responds during the repetition` with the complete response paragraph.
3. `Motion and posture, seen together` followed by the TikZ flow.

The side column contains:

1. a pale capability panel headed `What the prototype does today`;
2. a user-value block headed `Built for both sides of rehabilitation`;
3. a teal-accented next-step block headed `Next: supervised usability testing`.

Use 9.35 pt body text with 11.1 pt leading and compact bullets. Do not solve overflow by reducing body text below 9 pt.

- [ ] **Step 4: Draw the converging flow**

Use two small input nodes on the left (`Wearable motion` and `Camera posture`), thin arrows converging into `Synchronized analysis`, and one arrow to `Immediate coaching cue`. Use flat white or pale fills, 0.55 pt rules, modest 1 mm corner radii, and Helvetica node labels. Keep device names such as MPU6050 and MaixCAM2 in small supporting text, not in the primary reading line.

- [ ] **Step 5: Add the limitation footer**

Use a thin top rule and one compact paragraph across the full width. Start with `COURSEWORK PROTOTYPE · NOT A MEDICAL DEVICE` in a small sans-serif label. Include the complete limitation language without creating another large content box.

- [ ] **Step 6: Compile and inspect warnings**

Run:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error -cd output/pdf/literehab_one_page_pitch.tex
rg -n "Overfull|Underfull|LaTeX Warning|undefined references|Font Warning" output/pdf/literehab_one_page_pitch.log
```

Expected: compilation exits 0; the PDF exists; there are no overfull boxes, unresolved references, missing files, or font warnings. Fix meaningful underfull boxes through layout changes.

- [ ] **Step 7: Commit the source and PDF**

```bash
git add output/pdf/literehab_one_page_pitch.tex output/pdf/literehab_one_page_pitch.pdf
git commit -m "docs: redesign LiteRehab one-page pitch"
```

### Task 4: Verify the PDF mechanically and visually

**Files:**
- Verify: `output/pdf/literehab_one_page_pitch.pdf`
- Create temporarily: `tmp/pdfs/literehab_pitch.png`

**Interfaces:**
- Consumes: the compiled PDF from Task 3.
- Produces: verification evidence for page count, A4 geometry, embedded fonts, complete text, balanced page use, and intact rendering.

- [ ] **Step 1: Check page count and geometry**

Run:

```bash
pdfinfo output/pdf/literehab_one_page_pitch.pdf | rg "Pages|Page size"
```

Expected:

```text
Pages:           1
Page size:       595.276 x 841.89 pts (A4)
```

- [ ] **Step 2: Check fonts**

Run:

```bash
pdffonts output/pdf/literehab_one_page_pitch.pdf
```

Expected: embedded NewTX/Times-compatible body fonts and Helvetica-compatible display fonts; every row has `emb` set to `yes`.

- [ ] **Step 3: Check extractable text and prohibited content**

Run:

```bash
mkdir -p tmp/pdfs
pdftotext output/pdf/literehab_one_page_pitch.pdf tmp/pdfs/literehab_pitch.txt
rg "LiteRehab Fusion|Feedback arrives too late|Motion and posture, seen together|not a medical device|supervised usability testing" tmp/pdfs/literehab_pitch.txt
! rg -i "70 Python|host tests|smoke test|builds for" tmp/pdfs/literehab_pitch.txt
```

Expected: all five required phrases are present and prohibited engineering-test language is absent.

- [ ] **Step 4: Render and inspect at full-page scale**

Run:

```bash
mkdir -p tmp/pdfs
pdftoppm -png -r 180 -f 1 -singlefile \
  output/pdf/literehab_one_page_pitch.pdf tmp/pdfs/literehab_pitch
```

Inspect the PNG and confirm: all three logos are sharp and optically balanced; the title is dominant; the body reads main column then side column; the flow arrows converge correctly; no text or logo is clipped; no node collides; the lower part of the page is intentionally occupied; and whitespace separates ideas without leaving an empty lower third.

- [ ] **Step 5: Re-run after any visual correction**

If visual inspection finds a defect, revise the LaTeX source, recompile, and repeat Tasks 3 Step 6 and 4 Steps 1-4. Do not report completion from an older render.

- [ ] **Step 6: Remove temporary reference downloads and keep verification renders out of the deliverables**

Run:

```bash
rm -rf tmp/poster_refs tmp/logo-extract tmp/pdfs
git status --short
```

Expected: only the user's pre-existing source changes and untracked course files remain; the final `.tex`, `.pdf`, Markdown copy, logo assets, specification, and plan are tracked.
