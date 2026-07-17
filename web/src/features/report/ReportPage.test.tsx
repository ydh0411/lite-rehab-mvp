import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"

import type { SessionReport } from "../../app/api"
import { ReportPage } from "./ReportPage"


const report: SessionReport = {
  session_id: "demo-session",
  subject: "Demo-02",
  started_at: "2026-07-16T08:00:00+00:00",
  duration_s: 120,
  repetitions: 6,
  exercises: ["elbow_flexion"],
  quality_counts: { ok: 5, too_fast: 1 },
  good_form_percent: 83.3,
  max_rom_deg: 72,
  average_bpm: null,
  serial_completeness_percent: 100,
  pose_completeness_percent: 92,
  ecg_completeness_percent: 0,
  warnings: ["No connected ECG samples"],
  repetition_series: [{ t_s: 12, value: 1 }],
  rom_series: [{ t_s: 12, value: 72 }],
  bpm_series: [],
}


describe("ReportPage", () => {
  it("prints the prototype disclaimer and unavailable values", () => {
    render(
      <MemoryRouter>
        <ReportPage report={report} loading={false} error="" />
      </MemoryRouter>,
    )

    expect(screen.getByRole("region", { name: "Session measurements" })).toBeVisible()
    expect(screen.getByText(/not a medical device/i)).toBeVisible()
    expect(screen.getByText("Not available")).toBeVisible()
    expect(screen.queryByText("0 BPM")).not.toBeInTheDocument()
  })
})
