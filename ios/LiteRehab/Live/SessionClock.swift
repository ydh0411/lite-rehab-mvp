import Foundation

protocol SessionClock: Sendable {
    func now() -> Date
    func waitOneSecond() async throws
}

struct SystemSessionClock: SessionClock {
    func now() -> Date { Date() }

    func waitOneSecond() async throws {
        try await Task.sleep(for: .seconds(1))
    }
}
