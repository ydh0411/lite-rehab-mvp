import LiteRehabCore
import UIKit

@MainActor
struct ReportPDFRenderer {
    func render(report: SessionReport) throws -> Data {
        let page = CGRect(x: 0, y: 0, width: 842, height: 595)
        let renderer = UIGraphicsPDFRenderer(bounds: page)
        return renderer.pdfData { context in
            context.beginPage()
            draw(report: report, in: page)
        }
    }

    private func draw(report: SessionReport, in page: CGRect) {
        let margin: CGFloat = 42
        var y = margin
        draw("LiteRehab Session Report", font: .boldSystemFont(ofSize: 25), y: &y, page: page)
        draw("Participant: \(report.subject)", font: .boldSystemFont(ofSize: 15), y: &y, page: page)
        draw("Session: \(report.sessionID) · \(formattedDate(report.startedAt))", font: .systemFont(ofSize: 11), y: &y, page: page)
        y += 10

        let metrics = [
            "Duration: \(ReportFormatting.duration(report.durationS))",
            "Repetitions: \(report.repetitions)",
            "Good form: \(ReportFormatting.percent(report.goodFormPercent))",
            "Max ROM: \(ReportFormatting.degrees(report.maxRomDeg))",
            "Average heart rate: \(ReportFormatting.bpm(report.averageBPM)) BPM",
            "Exercises: \(report.exercises.map { $0.capitalized }.joined(separator: ", "))",
        ]
        for metric in metrics {
            draw(metric, font: .systemFont(ofSize: 13), y: &y, page: page)
        }
        y += 8
        draw("Data availability", font: .boldSystemFont(ofSize: 15), y: &y, page: page)
        draw("Parsed IMU rows \(ReportFormatting.percent(report.serialCompletenessPercent)) · Valid pose \(ReportFormatting.percent(report.poseCompletenessPercent)) · ECG connected \(ReportFormatting.ecgCompleteness(report.ecgCompletenessPercent))", font: .systemFont(ofSize: 12), y: &y, page: page)

        if !report.warnings.isEmpty {
            y += 8
            draw("Warnings", font: .boldSystemFont(ofSize: 15), y: &y, page: page)
            for warning in report.warnings.prefix(8) {
                draw("• \(warning)", font: .systemFont(ofSize: 11), y: &y, page: page)
            }
        }

        let disclaimer = "Engineering prototype for demonstration only. Not a medical device and not for diagnosis, monitoring, or treatment."
        let rect = CGRect(x: margin, y: page.height - 62, width: page.width - margin * 2, height: 30)
        (disclaimer as NSString).draw(in: rect, withAttributes: [
            .font: UIFont.italicSystemFont(ofSize: 9),
            .foregroundColor: UIColor.secondaryLabel,
        ])
    }

    private func draw(_ text: String, font: UIFont, y: inout CGFloat, page: CGRect) {
        let rect = CGRect(x: 42, y: y, width: page.width - 84, height: 26)
        (text as NSString).draw(in: rect, withAttributes: [
            .font: font,
            .foregroundColor: UIColor.label,
        ])
        y += font.lineHeight + 7
    }
}
