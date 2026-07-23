import Foundation
import LiteRehabCore

enum SessionFlowState: Equatable, Sendable {
    case preflight
    case countdown(remaining: Int)
    case active
    case completed(SessionCompletion)
}

struct SessionCompletion: Equatable, Sendable {
    let duration: TimeInterval
    let repetitions: Int
    let maximumROM: Double?
    let latestBPM: Double?
    let finalFeedback: FeedbackPresentation
}

struct SessionAccumulator: Equatable, Sendable {
    private var startedAt: Date?
    private var repetitions = 0
    private var maximumROM: Double?
    private var latestBPM: Double?
    private var finalFeedback = FeedbackPresentation.make(raw: nil)

    mutating func start(at date: Date) {
        startedAt = date
        repetitions = 0
        maximumROM = nil
        latestBPM = nil
        finalFeedback = .make(raw: nil)
    }

    mutating func observe(_ snapshot: LiveSnapshot) {
        repetitions = max(repetitions, snapshot.repetitions)
        if let rom = snapshot.romDeg, rom.isFinite, rom >= 0 {
            maximumROM = max(maximumROM ?? rom, rom)
        }
        if let bpm = snapshot.ecgBPM, bpm.isFinite, bpm > 0 {
            latestBPM = bpm
        }
        finalFeedback = .make(raw: snapshot.feedback)
    }

    func completion(at date: Date) -> SessionCompletion {
        SessionCompletion(
            duration: max(0, date.timeIntervalSince(startedAt ?? date)),
            repetitions: repetitions,
            maximumROM: maximumROM,
            latestBPM: latestBPM,
            finalFeedback: finalFeedback
        )
    }
}
