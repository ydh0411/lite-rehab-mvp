import UIKit

@MainActor
protocol FeedbackHapticEmitting: AnyObject {
    func emit(for category: FeedbackCategory)
}

@MainActor
final class SystemFeedbackHaptics: FeedbackHapticEmitting {
    func emit(for category: FeedbackCategory) {
        guard UIApplication.shared.applicationState == .active,
              !UIAccessibility.isReduceMotionEnabled else {
            return
        }

        switch category {
        case .good:
            UINotificationFeedbackGenerator().notificationOccurred(.success)
        case .slowDown, .increaseRange, .reduceCompensation:
            UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        case .neutral:
            break
        }
    }
}
