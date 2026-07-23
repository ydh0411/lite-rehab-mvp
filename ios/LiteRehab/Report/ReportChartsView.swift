import Charts
import LiteRehabCore
import SwiftUI

struct ReportChartsView: View {
    let report: SessionReport

    var body: some View {
        VStack(spacing: 16) {
            chart(title: "Repetitions", points: report.repetitionSeries, color: .indigo, unit: "reps")
            chart(title: "Range of Motion", points: report.romSeries, color: .cyan, unit: "degrees")
            chart(title: "Heart Rate", points: report.bpmSeries, color: .red, unit: "BPM")
        }
    }

    private func chart(title: String, points: [SeriesPoint], color: Color, unit: String) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title).font(.headline)
            if points.isEmpty {
                ContentUnavailableView(
                    "No \(title) Data",
                    systemImage: "chart.xyaxis.line",
                    description: Text("This metric was not recorded for the session.")
                )
                .frame(height: 160)
            } else {
                Chart(points) { point in
                    LineMark(
                        x: .value("Time", point.tS),
                        y: .value(unit, point.value)
                    )
                    .foregroundStyle(color)
                    .interpolationMethod(.catmullRom)
                }
                .chartXAxisLabel("Time (s)")
                .frame(height: 190)
                .accessibilityLabel("\(title) chart")
                .accessibilityValue("\(points.count) recorded points")
            }
        }
        .liteRehabCard()
    }
}
