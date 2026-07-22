import Combine
import Foundation
import LiteRehabCore
import UIKit

enum ParticipantIDError: LocalizedError {
    case empty
    case tooLong

    var errorDescription: String? {
        switch self {
        case .empty: "Enter a Participant ID."
        case .tooLong: "Participant ID must contain 64 characters or fewer."
        }
    }
}

private struct SessionFlowError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

@MainActor
final class LiveStore: ObservableObject {
    @Published private(set) var snapshot: LiveSnapshot?
    @Published private(set) var cameraImage: UIImage?
    @Published private(set) var cameraError: String?
    @Published private(set) var commandInProgress = false
    @Published var errorMessage: String?

    @Published private(set) var flowState: SessionFlowState = .preflight
    @Published var participantID = ""
    @Published private(set) var readiness = HardwareReadiness.make(snapshot: nil, macConnected: false)
    @Published private(set) var connectionState: LiveConnectionState = .idle
    @Published private(set) var sessionMessage: String?
    @Published private(set) var requiresDegradedConfirmation = false

    let stream: any LiveStreaming
    private let api: any APIClientProtocol
    private let camera: any CameraFrameLoading
    private let clock: any SessionClock
    private let haptics: any FeedbackHapticEmitting

    private var accumulator = SessionAccumulator()
    private var hapticGate = FeedbackHapticGate()
    private var hasObservedRecording = false
    private var awaitingStoppedSnapshot = false

    init(
        api: any APIClientProtocol,
        stream: any LiveStreaming,
        camera: any CameraFrameLoading,
        clock: any SessionClock = SystemSessionClock(),
        haptics: any FeedbackHapticEmitting = SystemFeedbackHaptics()
    ) {
        self.api = api
        self.stream = stream
        self.camera = camera
        self.clock = clock
        self.haptics = haptics
    }

    func appear() {
        stream.start(
            onState: { [weak self] state in
                self?.handleConnectionState(state)
            },
            onSnapshot: { [weak self] snapshot in
                self?.handleSnapshot(snapshot)
            }
        )
        camera.start(
            onFrame: { [weak self] image in
                self?.cameraImage = image
                self?.cameraError = nil
            },
            onError: { [weak self] error in
                self?.cameraError = error.localizedDescription
            }
        )
    }

    func disappear() {
        stream.stop()
        camera.stop()
    }

    func beginSession(allowDegraded: Bool = false) async {
        guard !commandInProgress else { return }

        let subject = participantID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !subject.isEmpty else {
            show(ParticipantIDError.empty)
            return
        }
        guard subject.count <= 64 else {
            show(ParticipantIDError.tooLong)
            return
        }
        participantID = subject

        guard readiness.blockingChecks.isEmpty else {
            showMessage(readiness.blockingChecks[0].detail)
            return
        }
        if !readiness.unavailableOptionalChecks.isEmpty && !allowDegraded {
            requiresDegradedConfirmation = true
            sessionMessage = "Some features are unavailable."
            return
        }

        commandInProgress = true
        requiresDegradedConfirmation = false
        clearMessages()
        defer { commandInProgress = false }

        do {
            for remaining in stride(from: 3, through: 1, by: -1) {
                flowState = .countdown(remaining: remaining)
                try await clock.waitOneSecond()
            }
            try Task.checkCancellation()
            try await api.recaptureBaseline()
            _ = try await api.startSession(subject: subject)

            accumulator = SessionAccumulator()
            accumulator.start(at: clock.now())
            if let snapshot {
                accumulator.observe(snapshot)
            }
            hapticGate = FeedbackHapticGate()
            hasObservedRecording = false
            awaitingStoppedSnapshot = false
            flowState = .active
        } catch {
            flowState = .preflight
            show(error)
        }
    }

    func stopSession() async {
        guard !commandInProgress, case .active = flowState else { return }
        commandInProgress = true
        clearMessages()
        defer { commandInProgress = false }

        do {
            _ = try await api.stopSession()
            awaitingStoppedSnapshot = true
            hasObservedRecording = false
            flowState = .completed(accumulator.completion(at: clock.now()))
        } catch {
            show(error)
        }
    }

    func returnToPreflight() {
        flowState = .preflight
        accumulator = SessionAccumulator()
        hapticGate = FeedbackHapticGate()
        hasObservedRecording = false
        requiresDegradedConfirmation = false
        clearMessages()
    }

    // Compatibility adapter for the existing start sheet. Task 5 removes it with the old sheet.
    func startSession(participantID: String) async throws {
        self.participantID = participantID
        await beginSession()
        guard case .active = flowState else {
            throw SessionFlowError(message: sessionMessage ?? "Unable to start the session.")
        }
    }

    func recaptureBaseline() async {
        await runCommand { try await api.recaptureBaseline() }
    }

    func resetRange() async {
        await runCommand { try await api.resetRange() }
    }

    private func handleConnectionState(_ state: LiveConnectionState) {
        connectionState = state
        updateReadiness()
    }

    private func handleSnapshot(_ newSnapshot: LiveSnapshot) {
        snapshot = newSnapshot
        updateReadiness()

        if awaitingStoppedSnapshot {
            if !newSnapshot.recording {
                awaitingStoppedSnapshot = false
            }
            return
        }

        if newSnapshot.recording {
            if case .active = flowState {
                // Keep the current locally or externally started session.
            } else {
                accumulator = SessionAccumulator()
                accumulator.start(at: clock.now())
                hapticGate = FeedbackHapticGate()
                flowState = .active
            }
            hasObservedRecording = true
            observeActiveSnapshot(newSnapshot)
        } else if case .active = flowState {
            accumulator.observe(newSnapshot)
            if hasObservedRecording {
                hasObservedRecording = false
                flowState = .completed(accumulator.completion(at: clock.now()))
            }
        }
    }

    private func observeActiveSnapshot(_ snapshot: LiveSnapshot) {
        accumulator.observe(snapshot)
        let presentation = FeedbackPresentation.make(raw: snapshot.feedback)
        if hapticGate.shouldEmit(category: presentation.category, at: clock.now()) {
            haptics.emit(for: presentation.category)
        }
    }

    private func updateReadiness() {
        let isConnected: Bool
        if case .connected = connectionState {
            isConnected = true
        } else {
            isConnected = false
        }
        readiness = .make(snapshot: snapshot, macConnected: isConnected)
    }

    private func runCommand(_ operation: () async throws -> Void) async {
        guard !commandInProgress else { return }
        commandInProgress = true
        defer { commandInProgress = false }
        do {
            try await operation()
        } catch {
            show(error)
        }
    }

    private func show(_ error: Error) {
        showMessage(error.localizedDescription)
    }

    private func showMessage(_ message: String) {
        sessionMessage = message
        errorMessage = message
    }

    private func clearMessages() {
        sessionMessage = nil
        errorMessage = nil
    }
}
