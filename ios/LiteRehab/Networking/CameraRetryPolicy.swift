import Foundation

struct CameraRetryPolicy: Equatable, Sendable {
    private(set) var consecutiveFailures = 0

    mutating func recordSuccess() -> Duration {
        consecutiveFailures = 0
        return .milliseconds(125)
    }

    mutating func recordFailure() -> (delay: Duration, shouldReport: Bool) {
        consecutiveFailures += 1
        let delay: Duration
        switch consecutiveFailures {
        case 1:
            delay = .milliseconds(500)
        case 2:
            delay = .seconds(1)
        case 3:
            delay = .seconds(2)
        default:
            delay = .seconds(4)
        }
        return (delay, consecutiveFailures == 1)
    }
}
