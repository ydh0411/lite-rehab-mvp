import Combine
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

@MainActor
final class LiveStore: ObservableObject {
    @Published private(set) var snapshot: LiveSnapshot?
    @Published private(set) var cameraImage: UIImage?
    @Published private(set) var cameraError: String?
    @Published private(set) var commandInProgress = false
    @Published var errorMessage: String?

    let stream: any LiveStreaming
    private let api: any APIClientProtocol
    private let camera: any CameraFrameLoading

    init(
        api: any APIClientProtocol,
        stream: any LiveStreaming,
        camera: any CameraFrameLoading
    ) {
        self.api = api
        self.stream = stream
        self.camera = camera
    }

    func appear() {
        stream.start { [weak self] snapshot in
            self?.snapshot = snapshot
        }
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

    func startSession(participantID: String) async throws {
        let subject = participantID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !subject.isEmpty else { throw ParticipantIDError.empty }
        guard subject.count <= 64 else { throw ParticipantIDError.tooLong }
        try await command {
            _ = try await api.startSession(subject: subject)
        }
    }

    func stopSession() async {
        await runCommand { _ = try await api.stopSession() }
    }

    func recaptureBaseline() async {
        await runCommand { try await api.recaptureBaseline() }
    }

    func resetRange() async {
        await runCommand { try await api.resetRange() }
    }

    private func runCommand(_ operation: () async throws -> Void) async {
        do {
            try await command(operation)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func command(_ operation: () async throws -> Void) async throws {
        guard !commandInProgress else { return }
        commandInProgress = true
        defer { commandInProgress = false }
        try await operation()
    }
}
