import { describe, expect, it } from "vitest"

import { appendBounded } from "./liveBuffer"


describe("appendBounded", () => {
  it("keeps only the newest live samples", () => {
    expect(appendBounded([1, 2], 3, 2)).toEqual([2, 3])
  })

  it("rejects a non-positive buffer size", () => {
    expect(() => appendBounded([1], 2, 0)).toThrow("limit must be positive")
  })
})
