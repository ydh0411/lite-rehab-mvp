import Testing

@testable import LiteRehabCore


@Suite("Report value formatting")
struct ReportFormattingTests {
    @Test("uses explicit missing-value labels")
    func missingValues() {
        #expect(ReportFormatting.percent(nil) == "Not available")
        #expect(ReportFormatting.ecgCompleteness(nil) == "Not recorded")
        #expect(ReportFormatting.degrees(nil) == "Not available")
        #expect(ReportFormatting.bpm(nil) == "Not available")
        #expect(ReportFormatting.duration(nil) == "Not available")
    }

    @Test("formats measurements consistently")
    func measurements() {
        #expect(ReportFormatting.percent(66.66) == "66.7%")
        #expect(ReportFormatting.ecgCompleteness(90.2) == "90%")
        #expect(ReportFormatting.degrees(81.24) == "81.2°")
        #expect(ReportFormatting.bpm(72.4) == "72")
        #expect(ReportFormatting.duration(125) == "2m 05s")
    }
}
