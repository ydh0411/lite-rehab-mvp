import Foundation

enum FeedbackCategory: Equatable, Sendable {
    case neutral
    case good
    case slowDown
    case increaseRange
    case reduceCompensation
}

struct FeedbackPresentation: Equatable, Sendable {
    let category: FeedbackCategory
    let title: String
    let guidance: String
    let symbolName: String

    static func make(raw: String?) -> FeedbackPresentation {
        let normalized = raw?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() ?? ""

        if normalized.contains("compensation") || normalized.contains("trunk") {
            return FeedbackPresentation(
                category: .reduceCompensation,
                title: "Keep your body steady",
                guidance: "Reduce trunk and shoulder compensation.",
                symbolName: "figure.mind.and.body"
            )
        }
        if normalized.contains("slow") {
            return FeedbackPresentation(
                category: .slowDown,
                title: "Slow down",
                guidance: "Use a smooth, controlled movement.",
                symbolName: "tortoise.fill"
            )
        }
        if normalized.contains("range") || normalized.contains("extend") || normalized.contains("further") {
            return FeedbackPresentation(
                category: .increaseRange,
                title: "Increase your range",
                guidance: "Move a little further if it remains comfortable.",
                symbolName: "arrow.up.right.and.arrow.down.left"
            )
        }
        if normalized.contains("good") || normalized.contains("excellent") || normalized.contains("keep it up") {
            return FeedbackPresentation(
                category: .good,
                title: "Good form",
                guidance: "Keep the same controlled movement.",
                symbolName: "checkmark.circle.fill"
            )
        }
        return FeedbackPresentation(
            category: .neutral,
            title: "Ready for feedback",
            guidance: normalized.isEmpty ? "Feedback will appear during movement." : raw ?? "",
            symbolName: "waveform.path.ecg"
        )
    }
}

struct FeedbackHapticGate: Sendable {
    private var lastCategory: FeedbackCategory?
    private var lastEmissionDate: Date?

    mutating func shouldEmit(
        category: FeedbackCategory,
        at date: Date,
        minimumInterval: TimeInterval = 1.5
    ) -> Bool {
        guard category != .neutral else {
            lastCategory = category
            return false
        }
        guard category != lastCategory else { return false }
        if let lastEmissionDate,
           date.timeIntervalSince(lastEmissionDate) < minimumInterval {
            return false
        }
        lastCategory = category
        lastEmissionDate = date
        return true
    }
}
