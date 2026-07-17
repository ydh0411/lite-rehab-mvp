import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"

import { App } from "./App"

describe("application shell", () => {
  it("renders the focused product destinations without marketing noise", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByRole("link", { name: /live training/i })).toBeVisible()
    expect(screen.getByRole("link", { name: /session history/i })).toBeVisible()
    expect(screen.getByText("Live workspace")).toBeVisible()
    expect(screen.getByText("Stored on this computer")).toBeVisible()
    expect(screen.queryByText(/upgrade plan/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/unlock insights/i)).not.toBeInTheDocument()
  })
})
