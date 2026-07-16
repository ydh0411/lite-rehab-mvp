import { describe, expect, it } from "vitest"

import type { SessionSummary } from "../../app/api"
import { filterSessions } from "./filterSessions"


const fixtures: SessionSummary[] = [
  {
    session_id: "session-a",
    subject: "Demo-01",
    started_at: "2026-07-15T08:00:00+00:00",
    duration_s: 90,
    repetitions: 4,
    exercises: ["forearm_rotation"],
    good_form_percent: 75,
    max_rom_deg: null,
    serial_completeness_percent: 100,
    pose_completeness_percent: 0,
    ecg_completeness_percent: null,
    warnings: ["No valid pose samples"],
  },
  {
    session_id: "session-b",
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
  },
]


describe("filterSessions", () => {
  it("filters by participant and exercise", () => {
    const result = filterSessions(fixtures, {
      query: "demo-02",
      exercise: "elbow_flexion",
    })

    expect(result.map((session) => session.session_id)).toEqual(["session-b"])
  })

  it("keeps newest sessions first", () => {
    const result = filterSessions(fixtures, { query: "", exercise: "all" })

    expect(result.map((session) => session.session_id)).toEqual([
      "session-b",
      "session-a",
    ])
  })
})
