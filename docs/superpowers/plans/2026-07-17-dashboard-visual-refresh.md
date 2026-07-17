# Dashboard Visual Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the existing local LiteRehab dashboard with deterministic offline typography, a clearer product shell, and consistent live, history, and report visual hierarchy.

**Architecture:** Preserve the React routes, components, API contracts, Lucide icons, and Recharts. Add self-hosted Geist font packages, expose semantic layout landmarks in existing components, and replace the stylesheet with one token-driven visual system. No backend or hardware code changes.

**Tech Stack:** React 19, TypeScript 5.9, Vite 8, Vitest, Testing Library, CSS custom properties, Geist Sans/Mono, Lucide React, Recharts

## Global Constraints

- The app must remain fully local and make no runtime font or asset requests to a CDN.
- No normal interface text may render below 12 px.
- Live Training must fit in a 1280 × 720 viewport without document scrolling.
- History and Report behavior, API contracts, local records, and A4 landscape printing must remain unchanged.
- Numeric measurements must use tabular spacing and a consistent numeric style.
- Do not modify hardware, session data, API, or report-calculation behavior.

---

### Task 1: Offline typography and design-token contract

**Files:**
- Create: `web/src/designSystem.test.ts`
- Modify: `web/package.json`
- Modify: `web/package-lock.json`
- Modify: `web/src/main.tsx`
- Modify: `web/src/styles.css`

**Interfaces:**
- Consumes: Vite CSS imports and the existing single global stylesheet.
- Produces: locally bundled `Geist Variable` and `Geist Mono Variable` families plus semantic CSS properties such as `--font-sans`, `--font-mono`, `--text-*`, `--surface-*`, and `--status-*`.

- [x] **Step 1: Write the failing design-system contract test**

```ts
import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"

const styles = readFileSync(new URL("./styles.css", import.meta.url), "utf8")
const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"))

describe("dashboard design system", () => {
  it("bundles Geist and defines one semantic type scale", () => {
    expect(pkg.dependencies).toHaveProperty("@fontsource-variable/geist")
    expect(pkg.dependencies).toHaveProperty("@fontsource-variable/geist-mono")
    expect(styles).toContain("--font-sans")
    expect(styles).toContain("--font-mono")
    expect(styles).toContain("--text-xs: 0.75rem")
    expect(styles).not.toMatch(/font-size:\s*0\.(?:[0-6]\d|7[0-4])rem/)
  })
})
```

- [x] **Step 2: Run the test and verify the missing font dependency/tokens fail**

Run: `cd web && npm test -- --run src/designSystem.test.ts`
Expected: FAIL because the font packages and semantic tokens are absent.

- [x] **Step 3: Install and import the offline fonts**

Run: `cd web && npm install @fontsource-variable/geist@5.2.9 @fontsource-variable/geist-mono@5.2.8`

Add before `./styles.css` in `web/src/main.tsx`:

```ts
import "@fontsource-variable/geist"
import "@fontsource-variable/geist-mono"
```

Define the semantic foundation at the start of `styles.css`:

```css
:root {
  --font-sans: "Geist Variable", "SF Pro Text", "Segoe UI", sans-serif;
  --font-mono: "Geist Mono Variable", "SFMono-Regular", Consolas, monospace;
  --text-xs: 0.75rem;
  --text-sm: 0.8125rem;
  --text-md: 0.875rem;
  --text-lg: 1rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.75rem;
}
```

- [x] **Step 4: Replace sub-12 px declarations with the semantic scale and run the test**

Run: `cd web && npm test -- --run src/designSystem.test.ts`
Expected: PASS.

- [x] **Step 5: Commit typography foundation**

```bash
git add web/package.json web/package-lock.json web/src/main.tsx web/src/styles.css web/src/designSystem.test.ts
git commit -m "style: add offline dashboard typography"
```

### Task 2: Product shell and live instrument hierarchy

**Files:**
- Modify: `web/src/app/App.test.tsx`
- Modify: `web/src/app/AppShell.tsx`
- Modify: `web/src/features/live/LivePage.test.tsx`
- Modify: `web/src/features/live/LivePage.tsx`
- Modify: `web/src/styles.css`

**Interfaces:**
- Consumes: existing routing, `LiveSnapshot`, and live action callbacks.
- Produces: a light product shell, compact status row, and an accessible `role="group"` landmark named `Primary session metric` around repetitions.

- [x] **Step 1: Add failing shell and live hierarchy assertions**

Add to the application-shell test:

```ts
expect(screen.getByText("Live workspace")).toBeVisible()
expect(screen.getByText("Stored on this computer")).toBeVisible()
```

Add to the first LivePage test:

```ts
expect(screen.getByRole("group", { name: "Primary session metric" })).toHaveTextContent(
  "Completed repetitions0",
)
```

- [x] **Step 2: Run focused tests and verify the new labels/landmark fail**

Run: `cd web && npm test -- --run src/app/App.test.tsx src/features/live/LivePage.test.tsx`
Expected: FAIL because the new shell copy and metric landmark do not exist.

- [x] **Step 3: Implement the shell copy and semantic metric landmark**

Change the brand subtitle to `Live workspace`, the local note title to `Stored on this computer`, and wrap the repetition block as:

```tsx
<div className="repetition-metric" role="group" aria-label="Primary session metric">
  <span>Completed repetitions</span>
  <strong>{snapshot.repetitions}</strong>
</div>
```

Rewrite the shell/live CSS using the shared tokens: 208 px light sidebar, graphite brand mark, neutral active row with teal indicator, 40 px controls, 12–14 px labels, bordered cards, and a 1280 × 720-compatible live grid.

- [x] **Step 4: Run focused tests**

Run: `cd web && npm test -- --run src/app/App.test.tsx src/features/live/LivePage.test.tsx`
Expected: PASS.

- [x] **Step 5: Commit shell and live refresh**

```bash
git add web/src/app/App.test.tsx web/src/app/AppShell.tsx web/src/features/live/LivePage.test.tsx web/src/features/live/LivePage.tsx web/src/styles.css
git commit -m "style: refine live dashboard hierarchy"
```

### Task 3: History and report consistency

**Files:**
- Modify: `web/src/features/history/HistoryPage.test.tsx`
- Modify: `web/src/features/history/HistoryPage.tsx`
- Modify: `web/src/features/report/ReportPage.test.tsx`
- Modify: `web/src/features/report/ReportPage.tsx`
- Modify: `web/src/features/report/ReportCharts.tsx`
- Modify: `web/src/styles.css`

**Interfaces:**
- Consumes: unchanged `SessionSummary`, `SessionReport`, and chart series.
- Produces: `Session overview` and `Session measurements` labelled regions, consistent chart tokens, normal-density table styling, and unchanged print behavior.

- [x] **Step 1: Add failing page-region assertions**

Add to `HistoryPage.test.tsx`:

```ts
expect(screen.getByRole("region", { name: "Session overview" })).toBeVisible()
```

Add to `ReportPage.test.tsx`:

```ts
expect(screen.getByRole("region", { name: "Session measurements" })).toBeVisible()
```

- [x] **Step 2: Run focused tests and verify the missing regions fail**

Run: `cd web && npm test -- --run src/features/history/HistoryPage.test.tsx src/features/report/ReportPage.test.tsx`
Expected: FAIL because the summary containers are not labelled regions.

- [x] **Step 3: Add the landmarks and align visual patterns**

Apply these attributes:

```tsx
<div className="history-summary" role="region" aria-label="Session overview">
```

```tsx
<div className="report-metrics" role="region" aria-label="Session measurements">
```

Update history/report CSS to use the shared metric strip, 13 px table cells, 12 px sentence-case headers, mono session IDs, consistent 36–40 px filters, tokenized chart/card colors, and existing A4 print rules. Replace raw chart colors with the refreshed semantic palette while retaining series meaning.

- [x] **Step 4: Run focused tests**

Run: `cd web && npm test -- --run src/features/history/HistoryPage.test.tsx src/features/report/ReportPage.test.tsx`
Expected: PASS.

- [x] **Step 5: Commit records and report refresh**

```bash
git add web/src/features/history/HistoryPage.test.tsx web/src/features/history/HistoryPage.tsx web/src/features/report/ReportPage.test.tsx web/src/features/report/ReportPage.tsx web/src/features/report/ReportCharts.tsx web/src/styles.css
git commit -m "style: unify records and report views"
```

### Task 4: Complete validation

**Files:**
- Modify: `docs/superpowers/plans/2026-07-17-dashboard-visual-refresh.md` (mark completed steps)

**Interfaces:**
- Consumes: the complete visual refresh.
- Produces: verification evidence for behavior, production compilation, local serving, and scope containment.

- [x] **Step 1: Run the complete frontend suite and build**

Run: `cd web && npm test -- --run && npm run build`
Expected: all test files pass and Vite exits 0.

- [x] **Step 2: Run the local built-frontend smoke test**

Run: `./scripts/start_web_demo.sh --fixture --headless-smoke-test --no-browser`
Expected: `LiteRehab web dashboard smoke test: PASS`.

- [x] **Step 3: Check scope and whitespace**

Run: `git diff --check main...HEAD && git diff --stat main...HEAD`
Expected: no whitespace errors; changes limited to the visual-refresh spec/plan and `web/` frontend files.

- [x] **Step 4: Mark plan complete and commit**

```bash
git add docs/superpowers/plans/2026-07-17-dashboard-visual-refresh.md
git commit -m "docs: complete dashboard visual refresh plan"
```
