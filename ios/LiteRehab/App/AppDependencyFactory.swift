import Foundation
import LiteRehabCore
import UIKit

@MainActor
struct AppDependencies {
    let api: any APIClientProtocol
    let stream: any LiveStreaming
    let camera: any CameraFrameLoading
    let clock: any SessionClock
    let haptics: any FeedbackHapticEmitting

    static func make(connection: ServerConnection, arguments: [String]) -> AppDependencies {
        guard arguments.contains("-ui-testing") else {
            let api = APIClient(connection: connection)
            return AppDependencies(
                api: api,
                stream: LiveWebSocketClient(connection: connection),
                camera: CameraFrameClient(connection: connection),
                clock: SystemSessionClock(),
                haptics: SystemFeedbackHaptics()
            )
        }

        let recording = arguments.contains("-fixture-reconnecting")
            || arguments.contains("-fixture-active-camera-unavailable")
        let cameraUnavailable = arguments.contains("-fixture-degraded")
            || arguments.contains("-fixture-active-camera-unavailable")
        let snapshot = LiveSnapshot.fixture(
            recording: recording,
            cameraReady: !cameraUnavailable
        )
        let state: LiveConnectionState = arguments.contains("-fixture-reconnecting")
            ? .reconnecting(attempt: 2)
            : .connected
        let historyMode: FixtureAPIClient.HistoryMode
        if arguments.contains("-fixture-history-empty") {
            historyMode = .empty
        } else if arguments.contains("-fixture-history-error") {
            historyMode = .error
        } else {
            historyMode = .content
        }
        let api = FixtureAPIClient(snapshot: snapshot, historyMode: historyMode)
        return AppDependencies(
            api: api,
            stream: FixtureLiveStream(state: state, snapshot: snapshot),
            camera: FixtureCameraClient(unavailable: cameraUnavailable),
            clock: ImmediateSessionClock(),
            haptics: NoopFeedbackHaptics()
        )
    }
}

private struct ImmediateSessionClock: SessionClock {
    func now() -> Date { Date(timeIntervalSince1970: 1_720_000_000) }
    func waitOneSecond() async throws {}
}

@MainActor
private final class NoopFeedbackHaptics: FeedbackHapticEmitting {
    func emit(for category: FeedbackCategory) {}
}

@MainActor
private final class FixtureCameraClient: CameraFrameLoading {
    private let unavailable: Bool

    init(unavailable: Bool) {
        self.unavailable = unavailable
    }

    func start(
        onFrame: @escaping @MainActor (UIImage) -> Void,
        onError: @escaping @MainActor (Error) -> Void
    ) {
        if unavailable {
            onError(NetworkError.transport("Wireless camera is unavailable."))
        }
    }

    func stop() {}
}

@MainActor
private final class FixtureLiveStream: LiveStreaming {
    private(set) var state: LiveConnectionState
    private let snapshot: LiveSnapshot

    init(state: LiveConnectionState, snapshot: LiveSnapshot) {
        self.state = state
        self.snapshot = snapshot
    }

    func start(
        onState: @escaping @MainActor @Sendable (LiveConnectionState) -> Void,
        onSnapshot: @escaping @MainActor @Sendable (LiveSnapshot) -> Void
    ) {
        onState(state)
        onSnapshot(snapshot)
    }

    func stop() {}
}

private actor FixtureAPIClient: APIClientProtocol {
    enum HistoryMode: Equatable {
        case content
        case empty
        case error
    }

    private var snapshot: LiveSnapshot
    private let historyMode: HistoryMode

    init(snapshot: LiveSnapshot, historyMode: HistoryMode) {
        self.snapshot = snapshot
        self.historyMode = historyMode
    }

    func health() async throws -> MobileHealth {
        MobileHealth(service: "LiteRehab fixture", apiVersion: 1)
    }

    func status() async throws -> LiveSnapshot { snapshot }

    func sessions() async throws -> [SessionSummary] {
        if historyMode == .error {
            throw NetworkError.transport("Fixture history server is unavailable.")
        }
        if historyMode == .empty {
            return []
        }
        return [
            SessionSummary(
                sessionID: "DEMO-2026-07-22",
                subject: "Participant 01",
                startedAt: "2026-07-22T10:30:00Z",
                durationS: 284,
                repetitions: 12,
                exercises: ["elbow flexion"],
                goodFormPercent: 83,
                maxRomDeg: 118,
                serialCompletenessPercent: 99,
                poseCompletenessPercent: 94,
                ecgCompletenessPercent: 91,
                warnings: []
            )
        ]
    }

    func report(sessionID: String) async throws -> SessionReport {
        SessionReport(
            sessionID: sessionID,
            subject: "Participant 01",
            startedAt: "2026-07-22T10:30:00Z",
            durationS: 284,
            repetitions: 12,
            exercises: ["elbow flexion"],
            qualityCounts: ["good": 10, "adjust": 2],
            goodFormPercent: 83,
            maxRomDeg: 118,
            averageBPM: 76,
            serialCompletenessPercent: 99,
            poseCompletenessPercent: 94,
            ecgCompletenessPercent: 91,
            warnings: [],
            repetitionSeries: [SeriesPoint(tS: 0, value: 0), SeriesPoint(tS: 284, value: 12)],
            romSeries: [SeriesPoint(tS: 0, value: 82), SeriesPoint(tS: 284, value: 118)],
            bpmSeries: [SeriesPoint(tS: 0, value: 72), SeriesPoint(tS: 284, value: 79)]
        )
    }

    func startSession(subject: String) async throws -> SessionCommandResponse {
        snapshot = snapshot.withRecording(true, subject: subject)
        return SessionCommandResponse(recording: true, subject: subject)
    }

    func stopSession() async throws -> SessionCommandResponse {
        snapshot = snapshot.withRecording(false, subject: snapshot.subject)
        return SessionCommandResponse(recording: false, subject: snapshot.subject)
    }

    func recaptureBaseline() async throws {}
    func resetRange() async throws {}
}

private extension LiveSnapshot {
    static func fixture(recording: Bool, cameraReady: Bool) -> LiveSnapshot {
        LiveSnapshot(
            timestampS: 12,
            recording: recording,
            subject: recording ? "Participant 01" : "",
            exercise: "elbow flexion",
            repetitions: recording ? 7 : 0,
            feedback: recording ? "Good form" : "Ready to begin",
            mode: "model",
            source: "imu",
            side: "right",
            serialStatus: "connected",
            cameraStatus: cameraReady ? "streaming" : "unavailable",
            romDeg: recording ? 104 : 0,
            confidenceText: "High confidence",
            modelConfidence: 0.94,
            ecgBPM: 76,
            ecgConnected: true,
            ecgSamples: [0.1, 0.2, 0.15, 0.8, 0.12, 0.2],
            cameraFrameAgeS: cameraReady ? 0.1 : nil
        )
    }

    func withRecording(_ recording: Bool, subject: String) -> LiveSnapshot {
        LiveSnapshot(
            timestampS: timestampS,
            recording: recording,
            subject: subject,
            exercise: exercise,
            repetitions: repetitions,
            feedback: feedback,
            mode: mode,
            source: source,
            side: side,
            serialStatus: serialStatus,
            cameraStatus: cameraStatus,
            romDeg: romDeg,
            confidenceText: confidenceText,
            modelConfidence: modelConfidence,
            ecgBPM: ecgBPM,
            ecgConnected: ecgConnected,
            ecgSamples: ecgSamples,
            cameraFrameAgeS: cameraFrameAgeS
        )
    }
}
