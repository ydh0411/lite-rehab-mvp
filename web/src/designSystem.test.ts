import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"


const styles = readFileSync(resolve(process.cwd(), "src/styles.css"), "utf8")
const reportCharts = readFileSync(
  resolve(process.cwd(), "src/features/report/ReportCharts.tsx"),
  "utf8",
)
const pkg = JSON.parse(
  readFileSync(resolve(process.cwd(), "package.json"), "utf8"),
) as { dependencies: Record<string, string> }


describe("dashboard design system", () => {
  it("bundles Geist and defines one semantic type scale", () => {
    expect(pkg.dependencies).toHaveProperty("@fontsource-variable/geist")
    expect(pkg.dependencies).toHaveProperty("@fontsource-variable/geist-mono")
    expect(styles).toContain("--font-sans")
    expect(styles).toContain("--font-mono")
    expect(styles).toContain("--text-xs: 0.75rem")
    expect(styles).not.toMatch(/font-size:\s*0\.(?:[0-6]\d|7[0-4])rem/)
    expect(reportCharts).not.toMatch(/fontSize:\s*(?:[0-9]|1[01])\b/)
  })
})
