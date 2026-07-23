import Foundation
import LiteRehabCore

struct HardwareReadiness: Equatable, Sendable {
    struct Check: Identifiable, Equatable, Sendable {
        enum Requirement: Equatable, Sendable {
            case required
            case optional
        }

        enum State: Equatable, Sendable {
            case ready
            case unavailable
        }

        let id: String
        let title: String
        let detail: String
        let requirement: Requirement
        let state: State
    }

    let checks: [Check]

    var blockingChecks: [Check] {
        checks.filter { $0.requirement == .required && $0.state == .unavailable }
    }

    var unavailableOptionalChecks: [Check] {
        checks.filter { $0.requirement == .optional && $0.state == .unavailable }
    }

    var canStartNormally: Bool {
        blockingChecks.isEmpty && unavailableOptionalChecks.isEmpty
    }

    var canStartDegraded: Bool {
        blockingChecks.isEmpty && !unavailableOptionalChecks.isEmpty
    }

    static func make(snapshot: LiveSnapshot?, macConnected: Bool) -> HardwareReadiness {
        let serialReady = statusIsReady(snapshot?.serialStatus)
        let cameraReady = statusIsReady(snapshot?.cameraStatus)
        let modelReady = snapshot?.modelConfidence.map { $0.isFinite } == true
        let ecgReady = snapshot?.ecgConnected == true

        return HardwareReadiness(checks: [
            Check(
                id: "mac",
                title: "Mac connection",
                detail: macConnected ? "Live session link is connected." : "Reconnect to the paired Mac.",
                requirement: .required,
                state: macConnected ? .ready : .unavailable
            ),
            Check(
                id: "serial",
                title: "Motion sensor",
                detail: serialReady ? "Motion data is ready." : "Connect the serial motion sensor to the Mac.",
                requirement: .required,
                state: serialReady ? .ready : .unavailable
            ),
            Check(
                id: "camera",
                title: "Wireless camera",
                detail: cameraReady ? "Camera stream is ready." : "Training can continue without video.",
                requirement: .optional,
                state: cameraReady ? .ready : .unavailable
            ),
            Check(
                id: "ecg",
                title: "ECG",
                detail: ecgReady ? "Heart-rate data is ready." : "Training can continue without ECG.",
                requirement: .optional,
                state: ecgReady ? .ready : .unavailable
            ),
            Check(
                id: "model",
                title: "Form feedback",
                detail: modelReady ? "ML feedback is ready." : "Training can continue with basic metrics.",
                requirement: .optional,
                state: modelReady ? .ready : .unavailable
            )
        ])
    }

    private static func statusIsReady(_ status: String?) -> Bool {
        guard let normalized = status?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() else {
            return false
        }
        return ["connected", "ready", "streaming"].contains(normalized)
    }
}
