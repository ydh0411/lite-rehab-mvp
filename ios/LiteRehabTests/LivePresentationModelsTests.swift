import Foundation
import LiteRehabCore
@testable import LiteRehab
import XCTest

final class LivePresentationModelsTests: XCTestCase {
    func testReadinessBlocksWithoutMacConnection() {
        let readiness = HardwareReadiness.make(snapshot: .fixture(), macConnected: false)

        XCTAssertEqual(readiness.blockingChecks.map(\.id), ["mac"])
        XCTAssertFalse(readiness.canStartNormally)
        XCTAssertFalse(readiness.canStartDegraded)
    }

    func testReadinessBlocksWithoutSerialConnection() {
        let readiness = HardwareReadiness.make(
            snapshot: .fixture(serialStatus: "disconnected"),
            macConnected: true
        )

        XCTAssertEqual(readiness.blockingChecks.map(\.id), ["serial"])
    }

    func testReadinessAllowsExplicitDegradedModeForOptionalHardware() {
        let readiness = HardwareReadiness.make(
            snapshot: .fixture(
                cameraStatus: "unavailable",
                modelConfidence: nil,
                ecgConnected: false
            ),
            macConnected: true
        )

        XCTAssertTrue(readiness.blockingChecks.isEmpty)
        XCTAssertEqual(
            Set(readiness.unavailableOptionalChecks.map(\.id)),
            Set(["camera", "ecg", "model"])
        )
        XCTAssertFalse(readiness.canStartNormally)
        XCTAssertTrue(readiness.canStartDegraded)
    }

    func testReadinessRecognizesNormalizedReadyStatuses() {
        let readiness = HardwareReadiness.make(
            snapshot: .fixture(serialStatus: " READY ", cameraStatus: "Streaming"),
            macConnected: true
        )

        XCTAssertTrue(readiness.canStartNormally)
        XCTAssertTrue(readiness.checks.allSatisfy { $0.state == .ready })
    }

    func testReadinessRecognizesConnectedStatusWithSourceDetail() {
        let readiness = HardwareReadiness.make(
            snapshot: .fixture(cameraStatus: "connected: rtsp://192.168.1.8:8554/live"),
            macConnected: true
        )

        let camera = try? XCTUnwrap(readiness.checks.first { $0.id == "camera" })
        XCTAssertEqual(camera?.state, .ready)
    }

    func testFeedbackNormalizationMapsBackendPhrasesToStableCategories() {
        XCTAssertEqual(FeedbackPresentation.make(raw: "Good form").category, .good)
        XCTAssertEqual(FeedbackPresentation.make(raw: "Please slow down").category, .slowDown)
        XCTAssertEqual(FeedbackPresentation.make(raw: "Increase your range").category, .increaseRange)
        XCTAssertEqual(FeedbackPresentation.make(raw: "Reduce trunk compensation").category, .reduceCompensation)
        XCTAssertEqual(FeedbackPresentation.make(raw: "  ").category, .neutral)
    }

    func testAccumulatorBuildsCompletionFromObservedSnapshots() {
        var accumulator = SessionAccumulator()
        accumulator.start(at: Date(timeIntervalSince1970: 100))
        accumulator.observe(.fixture(repetitions: 3, feedback: "Good form", romDeg: 42, ecgBPM: 71))
        accumulator.observe(.fixture(repetitions: 5, feedback: "Slow down", romDeg: 56, ecgBPM: nil))

        let result = accumulator.completion(at: Date(timeIntervalSince1970: 112))

        XCTAssertEqual(result.duration, 12)
        XCTAssertEqual(result.repetitions, 5)
        XCTAssertEqual(result.maximumROM, 56)
        XCTAssertEqual(result.latestBPM, 71)
        XCTAssertEqual(result.finalFeedback.category, .slowDown)
    }

    func testAccumulatorIgnoresInvalidMeasurementsAndCounterRegression() {
        var accumulator = SessionAccumulator()
        accumulator.start(at: Date(timeIntervalSince1970: 100))
        accumulator.observe(.fixture(repetitions: 7, romDeg: 48, ecgBPM: 68))
        accumulator.observe(.fixture(repetitions: 2, romDeg: .infinity, ecgBPM: -1))

        let result = accumulator.completion(at: Date(timeIntervalSince1970: 99))

        XCTAssertEqual(result.duration, 0)
        XCTAssertEqual(result.repetitions, 7)
        XCTAssertEqual(result.maximumROM, 48)
        XCTAssertEqual(result.latestBPM, 68)
    }

    func testHapticGateRequiresChangedCategoryAndThrottleInterval() {
        var gate = FeedbackHapticGate()
        let start = Date(timeIntervalSince1970: 100)

        XCTAssertTrue(gate.shouldEmit(category: .good, at: start))
        XCTAssertFalse(gate.shouldEmit(category: .good, at: start.addingTimeInterval(2)))
        XCTAssertFalse(gate.shouldEmit(category: .slowDown, at: start.addingTimeInterval(1)))
        XCTAssertTrue(gate.shouldEmit(category: .slowDown, at: start.addingTimeInterval(2)))
    }
}

private extension LiveSnapshot {
    static func fixture(
        recording: Bool = false,
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
            subject: "P-001",
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
