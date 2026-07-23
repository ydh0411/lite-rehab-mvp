import SwiftUI

struct SessionCompletionView: View {
    let summary: SessionCompletion
    let onViewHistory: () -> Void
    let onDone: () -> Void

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                VStack(spacing: 12) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 68))
                        .foregroundStyle(LiteRehabStyle.success)
                        .accessibilityHidden(true)
                    Text("Session complete")
                        .font(.largeTitle.bold())
                        .accessibilityIdentifier("session-complete")
                    Text("Your movement summary is ready.")
                        .foregroundStyle(.secondary)
                }

                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    MetricCard(title: "Duration", value: durationText, systemImage: "clock")
                    MetricCard(title: "Repetitions", value: "\(summary.repetitions)", systemImage: "repeat")
                    MetricCard(title: "Maximum ROM", value: romText, systemImage: "angle")
                    MetricCard(title: "Latest heart rate", value: bpmText, systemImage: "heart.fill", tint: .red)
                }

                HStack(alignment: .top, spacing: 14) {
                    Image(systemName: summary.finalFeedback.symbolName)
                        .font(.title2)
                        .foregroundStyle(LiteRehabStyle.accent)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(summary.finalFeedback.title).font(.headline)
                        Text(summary.finalFeedback.guidance)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .liteRehabCard()

                Text("The full report is generated and stored by LiteRehab on your Mac.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)

                VStack(spacing: 12) {
                    Button("View in History", action: onViewHistory)
                        .buttonStyle(.borderedProminent)
                        .frame(maxWidth: .infinity)
                    Button("Done", action: onDone)
                        .buttonStyle(.bordered)
                        .frame(maxWidth: .infinity)
                        .accessibilityIdentifier("session-done")
                }
                .controlSize(.large)
            }
            .padding()
        }
    }

    private var durationText: String {
        let seconds = max(0, Int(summary.duration.rounded()))
        return String(format: "%d:%02d", seconds / 60, seconds % 60)
    }

    private var romText: String {
        summary.maximumROM.map { "\(Int($0.rounded()))°" } ?? "—"
    }

    private var bpmText: String {
        summary.latestBPM.map { "\(Int($0.rounded())) BPM" } ?? "—"
    }
}
