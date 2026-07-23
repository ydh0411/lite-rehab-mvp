import Foundation
import LiteRehabCore
@testable import LiteRehab
import UIKit

enum RecordedAPICommand: Equatable, Sendable {
    case recaptureBaseline
    case start(String)
    case stop
    case resetRange
}

enum TestAPIError: LocalizedError {
    case rejected

    var errorDescription: String? { "Test command rejected" }
}

actor RecordingAPIClient: APIClientProtocol {
    private var recordedCommands: [RecordedAPICommand] = []
    private var failingCommand: RecordedAPICommand?
    private var suspendStart = false
    private var startContinuation: CheckedContinuation<Void, Never>?
    private var startCalls = 0
    private let statusSnapshot: LiveSnapshot

    init(
        failingCommand: RecordedAPICommand? = nil,
        suspendStart: Bool = false,
        statusSnapshot: LiveSnapshot = .testFixture()
    ) {
        self.failingCommand = failingCommand
        self.suspendStart = suspendStart
        self.statusSnapshot = statusSnapshot
    }

    func commands() -> [RecordedAPICommand] { recordedCommands }
    func startCount() -> Int { startCalls }

    func waitUntilStartIsSuspended() async {
        while startCalls == 0 || startContinuation == nil {
            await Task.yield()
        }
    }

    func releaseStart() {
        suspendStart = false
        startContinuation?.resume()
        startContinuation = nil
    }

    func health() async throws -> MobileHealth {
        MobileHealth(service: "literehab", apiVersion: 1)
    }

    func status() async throws -> LiveSnapshot { statusSnapshot }
    func sessions() async throws -> [SessionSummary] { [] }

    func report(sessionID: String) async throws -> SessionReport {
        SessionReport(
            sessionID: sessionID,
            subject: "P-001",
            startedAt: "2026-07-22T00:00:00Z",
            durationS: 10,
            repetitions: 1,
            exercises: ["elbow_flexion"],
            qualityCounts: [:],
            goodFormPercent: nil,
            maxRomDeg: nil,
            averageBPM: nil,
            serialCompletenessPercent: 100,
            poseCompletenessPercent: 100,
            ecgCompletenessPercent: nil,
            warnings: [],
            repetitionSeries: [],
            romSeries: [],
            bpmSeries: []
        )
    }

    func startSession(subject: String) async throws -> SessionCommandResponse {
        let command = RecordedAPICommand.start(subject)
        recordedCommands.append(command)
        startCalls += 1
        if suspendStart {
            await withCheckedContinuation { continuation in
                startContinuation = continuation
            }
        }
        try rejectIfNeeded(command)
        return SessionCommandResponse(recording: true, subject: subject)
    }

    func stopSession() async throws -> SessionCommandResponse {
        recordedCommands.append(.stop)
        try rejectIfNeeded(.stop)
        return SessionCommandResponse(recording: false, subject: "P-001")
    }

    func recaptureBaseline() async throws {
        recordedCommands.append(.recaptureBaseline)
        try rejectIfNeeded(.recaptureBaseline)
    }

    func resetRange() async throws {
        recordedCommands.append(.resetRange)
        try rejectIfNeeded(.resetRange)
    }

    private func rejectIfNeeded(_ command: RecordedAPICommand) throws {
        if failingCommand == command {
            throw TestAPIError.rejected
        }
    }
}

@MainActor
final class TestLiveStream: LiveStreaming {
    private(set) var state: LiveConnectionState = .idle
    private var stateHandler: ((LiveConnectionState) -> Void)?
    private var snapshotHandler: ((LiveSnapshot) -> Void)?

    func start(
        onState: @escaping @MainActor (LiveConnectionState) -> Void,
        onSnapshot: @escaping @MainActor (LiveSnapshot) -> Void
    ) {
        stateHandler = onState
        snapshotHandler = onSnapshot
    }

    func stop() {
        state = .idle
        stateHandler?(.idle)
    }

    func emit(state: LiveConnectionState) {
        self.state = state
        stateHandler?(state)
    }

    func emit(snapshot: LiveSnapshot) {
        snapshotHandler?(snapshot)
    }
}

@MainActor
final class TestCameraClient: CameraFrameLoading {
    private(set) var isRunning = false

    func start(
        onFrame: @escaping @MainActor (UIImage) -> Void,
        onError: @escaping @MainActor (Error) -> Void
    ) {
        isRunning = true
    }

    func stop() {
        isRunning = false
    }
}

final class TestSessionClock: SessionClock, @unchecked Sendable {
    var currentDate: Date
    private(set) var waitCount = 0

    init(currentDate: Date = Date(timeIntervalSince1970: 100)) {
        self.currentDate = currentDate
    }

    func now() -> Date { currentDate }

    func waitOneSecond() async throws {
        waitCount += 1
    }
}

@MainActor
final class RecordingHaptics: FeedbackHapticEmitting {
    private(set) var categories: [FeedbackCategory] = []

    func emit(for category: FeedbackCategory) {
        categories.append(category)
    }
}

extension LiveSnapshot {
    static func testFixture(
        recording: Bool = false,
        subject: String = "P-001",
        repetitions: Int = 0,
        feedback: String = "Ready",
        serialStatus: String = "connected",
        cameraStatus: String = "streaming",
        romDeg: Double? = 30,
        modelConfidence: Double? = 0.92,
        ecgBPM: Double? = 70,
        ecgConnected: Bool = true
    ) -> LiveSnapshot {
        LiveSnapshot(
            timestampS: 100,
            recording: recording,
            subject: subject,
            exercise: "elbow_flexion",
            repetitions: repetitions,
            feedback: feedback,
            mode: "hardware",
            source: "serial",
            side: "right",
            serialStatus: serialStatus,
            cameraStatus: cameraStatus,
            romDeg: romDeg,
            confidenceText: modelConfidence == nil ? "Unavailable" : "High",
            modelConfidence: modelConfidence,
            ecgBPM: ecgBPM,
            ecgConnected: ecgConnected,
            ecgSamples: [],
            cameraFrameAgeS: 0.1
        )
    }
}
