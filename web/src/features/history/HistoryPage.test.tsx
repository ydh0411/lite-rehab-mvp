import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"

import type { SessionSummary } from "../../app/api"
import { HistoryPage } from "./HistoryPage"


const session: SessionSummary = {
  session_id: "demo-session",
  subject: "Demo-02",
  started_at: "2026-07-16T08:00:00+00:00",
  duration_s: 120,
  repetitions: 6,
  exercises: ["elbow_flexion"],
  good_form_percent: 83.3,
  max_rom_deg: 72,
  serial_completeness_percent: 100,
  pose_completeness_percent: 92,
  ecg_completeness_percent: 88,
  warnings: [],
}


describe("HistoryPage", () => {
  it("links a real session to its report", () => {
    render(
      <MemoryRouter>
        <HistoryPage sessions={[session]} loading={false} error="" />
      </MemoryRouter>,
    )

    expect(screen.getByText("Demo-02")).toBeVisible()
    expect(screen.getByRole("link", { name: /view report/i })).toHaveAttribute(
      "href",
      "/reports/demo-session",
    )
  })

  it("shows an honest empty state", () => {
    render(
      <MemoryRouter>
        <HistoryPage sessions={[]} loading={false} error="" />
      </MemoryRouter>,
    )

    expect(screen.getByText("No recorded sessions yet")).toBeVisible()
  })
})
