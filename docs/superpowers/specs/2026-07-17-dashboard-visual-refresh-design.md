# LiteRehab Dashboard Visual Refresh Design

**Date:** 2026-07-17
**Status:** Approved by user direction to select and implement the clearest reusable style
**Scope:** Existing local React dashboard only; no hardware, API, session-storage, or report-calculation changes

## Objective

Make the local LiteRehab dashboard feel like a mature product rather than a generic admin template. Improve typography first, then visual hierarchy, density, spacing, and component consistency across Live Training, Session History, and Session Report. Preserve the current information architecture and local-only behavior.

## Research reviewed

- [Vercel Geist typography](https://vercel.com/geist/typography): pair explicit size, line-height, letter-spacing, and weight; use tabular or mono numerals for measurements.
- [Vercel Geist colors](https://vercel.com/geist/colors): separate page backgrounds, component backgrounds, borders, and text roles instead of assigning one-off colors.
- [Vercel Web Interface Guidelines](https://vercel.com/design/guidelines): use tabular numerals, redundant status cues, stable states, direct labels, and inline help.
- [GitHub Primer Product UI](https://primer.style/product/): build from shared color, spacing, typography, and layout primitives.
- [GitHub Primer DataTable](https://primer.style/product/components/data-table/): use normal density by default, condensed density only where visibility materially benefits.
- [IBM Carbon dashboard guidance](https://carbondesignsystem.com/data-visualization/dashboards/): establish a strong hierarchy, limit visible metrics, use white space deliberately, and keep chart layout and color assignments consistent.
- [shadcn/ui](https://github.com/shadcn-ui/ui): reviewed as a 119k-star reference for restrained, accessible, composable product UI.
- [Plane](https://github.com/makeplane/plane): reviewed as a 54k-star reference for a dense but calm product workspace.
- [Cal.com](https://github.com/calcom/cal.com): reviewed as a 46k-star reference for form, scheduling, and table hierarchy.
- [Tabler](https://github.com/tabler/tabler): reviewed as a 41k-star dashboard reference for responsive information density.

## Approaches considered

### A. Geist + Primer + Carbon product workspace — selected

Use Geist Sans as the bundled offline interface font, system fallbacks for resilience, and Geist Mono only for measurement-heavy values. Adopt Primer-like neutral surfaces and data-table density, with Carbon-style hierarchy for live KPIs and reports.

This direction is selected because it improves clarity without replacing the existing React architecture or importing an entire component framework. It also avoids both a clinical-software cliché and a fashionable but low-information landing-page aesthetic.

### B. Full Tabler-style admin dashboard

This would provide many ready-made dashboard patterns, but its Bootstrap-derived visual language would make LiteRehab feel like a generic admin template. It would also introduce a second component system and unnecessary migration cost.

### C. Pure shadcn-style monochrome minimalism

This would produce clean components quickly, but the default sparse aesthetic under-emphasizes the live camera, repetition count, ROM, and connection state. The rehabilitation demo needs a stronger measurement hierarchy than a settings-oriented SaaS interface.

## Chosen visual system

### Typography

- Bundle Geist Sans locally so the interface renders consistently without internet access.
- Use the following semantic scale:
  - page title: 26–30 px, 650 weight;
  - section title: 15–16 px, 600–650 weight;
  - body and table cells: 13–14 px;
  - labels and metadata: 12–13 px;
  - never render product copy below 12 px.
- Replace excessive uppercase tracking with sentence case. Uppercase is reserved for genuinely short instrument labels.
- Use tabular numerals for all measurements; use Geist Mono selectively for BPM, repetitions, ROM, durations, timestamps, and session identifiers.
- Increase line-height for explanatory copy and reduce the number of near-duplicate small font sizes.

### Color and surfaces

- Shift from the heavy navy sidebar to a light neutral product shell with a narrow graphite navigation rail.
- Keep teal as the primary action and live-signal accent, but reduce its use in decorative labels.
- Use a small semantic palette: neutral, success, warning, danger, and live/primary.
- Keep backgrounds nearly neutral: warm-white page, white cards, subtle cool-gray secondary surfaces.
- Use 1 px borders and low-elevation shadows only for floating overlays. Most cards rely on borders and spacing.
- Preserve status labels and icons so meaning never depends on color alone.

### Layout and spacing

- Keep the existing two-route navigation and the three-page architecture.
- Reduce sidebar width slightly and make the workspace bar visually quieter.
- Use an 8 px spacing grid with consistent 12, 16, 24, and 32 px groups.
- Maintain the Live Training page within a 1280 × 720 viewport without page scrolling.
- Keep reports scrollable and printable; maintain the current A4 landscape print path.
- Preserve responsive collapse behavior below desktop widths.

## Page designs

### App shell

- Light sidebar with a high-contrast graphite brand mark.
- Active navigation uses a subtle neutral fill and a thin teal indicator rather than a large colored block.
- Local-only and prototype notices become compact secondary text, not large promotional cards.
- Add a small product-context line so users always know whether they are in Live Training or Records.

### Live Training

- The live camera remains the dominant panel.
- Participant/session controls remain in the header but use clearer 40 px controls and 13–14 px text.
- Device states become consistent compact status chips.
- Repetition count is the largest numeric element; ROM and affected side remain secondary.
- The feedback overlay becomes a calm floating instrument panel with clearer label/value separation.
- ECG keeps its full-width strip but uses more legible labels, a cleaner grid, and tabular numeric treatment.

### Session History

- Summary metrics become a single restrained overview strip rather than four visually separate dashboard cards.
- Search and filter controls share one height and focus treatment.
- Table headers use sentence case and 12 px text; cells use 13 px text with clearer row rhythm.
- Participant and session ID remain visually distinct through sans/mono pairing.
- Report actions appear as compact text buttons with a visible hover/focus state.

### Session Report

- Metadata is grouped directly beneath the participant title.
- Four summary measurements use the same metric pattern as Live Training.
- All charts share header spacing, axis typography, tooltip styling, and semantic color tokens.
- Data-quality notes are visually secondary but retain warning labels and completeness values.
- Print styles remain black-on-white and omit application chrome.

## Component and code strategy

- Keep the current React components and API contracts.
- Add locally bundled font assets through a small font package or checked-in licensed files; no runtime CDN calls.
- Refactor `styles.css` around semantic CSS custom properties and a compact type scale.
- Change markup only where it improves semantics or enables a reusable visual pattern.
- Do not introduce a full UI framework or new application state.
- Keep Lucide icons and Recharts.

## Testing strategy

- Add DOM-level tests for the refreshed shell semantics and any changed labels before production changes.
- Preserve all current Live Training, history filtering, report, and API tests.
- Run the complete frontend test suite and production build.
- Run the local fixture smoke test to verify the built frontend is served correctly.
- Check the final diff for accidental API or hardware changes.

## Acceptance criteria

- The app uses a deterministic bundled primary font offline.
- No normal interface text is below 12 px.
- Numeric measurements use tabular spacing and a consistent numeric style.
- Live Training still fits at 1280 × 720 without document scrolling.
- History and Report remain functionally identical and printable.
- Color, borders, radii, controls, status chips, cards, and table density use shared tokens.
- Frontend tests, TypeScript production build, and local web smoke test pass.
- No hardware, session data, API, or report-calculation behavior changes.
