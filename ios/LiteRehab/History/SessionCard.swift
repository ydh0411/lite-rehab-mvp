import LiteRehabCore
import SwiftUI

struct SessionCard: View {
    let session: SessionSummary

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(session.subject.isEmpty ? "Unnamed participant" : session.subject)
                    .font(.headline)
                Text(formattedDate(session.startedAt))
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            if !session.exercises.isEmpty {
                Label(
                    session.exercises.map { $0.capitalized }.joined(separator: " · "),
                    systemImage: "figure.strengthtraining.traditional"
                )
                .font(.subheadline)
                .foregroundStyle(LiteRehabStyle.accent)
            }

            HStack(spacing: 12) {
                Label("\(session.repetitions) reps", systemImage: "repeat")
                Label(durationText(session.durationS), systemImage: "clock")
                if let goodForm = session.goodFormPercent {
                    Label("\(Int(goodForm.rounded()))%", systemImage: "checkmark.seal")
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if !session.warnings.isEmpty {
                Label(
                    "\(session.warnings.count) data warning\(session.warnings.count == 1 ? "" : "s")",
                    systemImage: "exclamationmark.triangle.fill"
                )
                .font(.caption)
                .foregroundStyle(LiteRehabStyle.warning)
            }
        }
        .padding(.vertical, 5)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(
            "Session for \(session.subject), \(session.repetitions) repetitions, \(durationText(session.durationS))"
        )
        .accessibilityHint("Opens the session report")
    }
}

func durationText(_ seconds: Double?) -> String {
    guard let seconds else { return "Not available" }
    let total = Int(seconds.rounded())
    return String(format: "%d:%02d", total / 60, total % 60)
}

func formattedDate(_ value: String) -> String {
    let formatter = ISO8601DateFormatter()
    guard let date = formatter.date(from: value) else { return value }
    return date.formatted(date: .abbreviated, time: .shortened)
}
