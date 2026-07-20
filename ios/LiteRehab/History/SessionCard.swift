import LiteRehabCore
import SwiftUI

struct SessionCard: View {
    let session: SessionSummary

    var body: some View {
        VStack(alignment: .leading, spacing: 13) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(session.subject.isEmpty ? "Unnamed participant" : session.subject)
                        .font(.headline)
                    Text(formattedDate(session.startedAt))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundStyle(.tertiary)
            }
            HStack(spacing: 8) {
                ForEach(session.exercises, id: \.self) { exercise in
                    Text(exercise.capitalized)
                        .font(.caption.weight(.medium))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 5)
                        .background(Color.indigo.opacity(0.1), in: Capsule())
                }
            }
            HStack {
                summaryItem("Reps", "\(session.repetitions)")
                Divider()
                summaryItem("Duration", durationText(session.durationS))
                Divider()
                summaryItem("Good form", session.goodFormPercent.map { "\(Int($0.rounded()))%" } ?? "Not available")
            }
            if !session.warnings.isEmpty {
                Label("\(session.warnings.count) data warning\(session.warnings.count == 1 ? "" : "s")", systemImage: "exclamationmark.triangle.fill")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }
        }
        .liteRehabCard()
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Session for \(session.subject), \(session.repetitions) repetitions")
        .accessibilityHint("Opens the session report")
    }

    private func summaryItem(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title).font(.caption2).foregroundStyle(.secondary)
            Text(value).font(.caption.weight(.semibold)).lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
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
