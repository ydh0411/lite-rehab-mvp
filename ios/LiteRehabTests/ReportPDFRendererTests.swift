import LiteRehabCore
@testable import LiteRehab
import XCTest

@MainActor
final class ReportPDFRendererTests: XCTestCase {
    func testRendererProducesPDFData() throws {
        let report = SessionReport(
            sessionID: "session-01",
            subject: "demo-01",
            startedAt: "2026-07-20T10:00:00Z",
            durationS: 75,
            repetitions: 8,
            exercises: ["curl"],
            qualityCounts: ["good": 7, "compensation": 1],
            goodFormPercent: 87.5,
            maxRomDeg: 98,
            averageBPM: nil,
            serialCompletenessPercent: 100,
            poseCompletenessPercent: 92,
            ecgCompletenessPercent: nil,
            warnings: ["ECG was not recorded"],
            repetitionSeries: [],
            romSeries: [],
            bpmSeries: []
        )

        let data = try ReportPDFRenderer().render(report: report)

        XCTAssertTrue(data.starts(with: Data("%PDF".utf8)))
        XCTAssertGreaterThan(data.count, 1_000)
    }
}
