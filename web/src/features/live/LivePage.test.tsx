import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { LivePage } from "./LivePage"


const initialSnapshot = {
  timestamp_s: 0,
  recording: false,
  subject: "",
  exercise: "idle",
  repetitions: 0,
  feedback: "Ready",
  mode: "IMU-only",
  source: "rule fallback",
  side: "right",
  serial_status: "unavailable",
  camera_status: "unavailable",
  rom_deg: null,
  confidence_text: "Model unavailable",
  model_confidence: null,
  ecg_bpm: null,
  ecg_connected: false,
  ecg_samples: [],
  camera_frame_age_s: null,
} as const


function handlers() {
  return {
    onStart: vi.fn().mockResolvedValue(undefined),
    onStop: vi.fn().mockResolvedValue(undefined),
    onBaseline: vi.fn().mockResolvedValue(undefined),
    onResetRange: vi.fn().mockResolvedValue(undefined),
  }
}


describe("LivePage", () => {
  it("shows unavailable ECG without inventing zero BPM", () => {
    render(
      <LivePage
        snapshot={initialSnapshot}
        connectionState="connected"
        {...handlers()}
      />,
    )

    expect(screen.getByText("Leads off")).toBeVisible()
    expect(screen.queryByText("0 BPM")).not.toBeInTheDocument()
    expect(screen.getByText("Camera unavailable")).toBeVisible()
  })

  it("keeps the camera placeholder visible while the device is retrying", () => {
    render(
      <LivePage
        snapshot={{
          ...initialSnapshot,
          camera_status: "no local camera found; retrying",
        }}
        connectionState="connected"
        {...handlers()}
      />,
    )

    expect(screen.getByText("Camera unavailable")).toBeVisible()
    expect(
      screen.queryByAltText("Annotated rehabilitation camera feed"),
    ).not.toBeInTheDocument()
  })

  it("labels safety feedback with direct coaching copy", () => {
    render(
      <LivePage
        snapshot={{ ...initialSnapshot, feedback: "Avoid trunk compensation" }}
        connectionState="connected"
        {...handlers()}
      />,
    )

    expect(screen.getByRole("status", { name: "Movement feedback" })).toHaveTextContent(
      "Avoid trunk compensation",
    )
  })

  it("starts a session with the entered participant ID", async () => {
    const actions = handlers()
    const user = userEvent.setup()
    render(
      <LivePage
        snapshot={initialSnapshot}
        connectionState="connected"
        {...actions}
      />,
    )

    await user.type(screen.getByLabelText("Participant ID"), "Demo-07")
    await user.click(screen.getByRole("button", { name: "Start session" }))

    expect(actions.onStart).toHaveBeenCalledWith("Demo-07")
  })
})
