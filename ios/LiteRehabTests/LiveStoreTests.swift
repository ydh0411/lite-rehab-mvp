import Foundation
import LiteRehabCore
@testable import LiteRehab
import XCTest

@MainActor
final class LiveStoreTests: XCTestCase {
    func testStartCapturesBaselineBeforeStartAndEntersActive() async {
        let api = RecordingAPIClient()
        let clock = TestSessionClock()
        let context = makeStore(api: api, clock: clock)
        context.store.participantID = "  P-001  "

        await context.store.beginSession()

        let commands = await api.commands()
        XCTAssertEqual(commands, [.recaptureBaseline, .start("P-001")])
        XCTAssertEqual(clock.waitCount, 3)
        XCTAssertEqual(context.store.participantID, "P-001")
        XCTAssertEqual(context.store.flowState, .active)
    }

    func testMissingOptionalHardwareRequiresExplicitDegradedStart() async {
        let api = RecordingAPIClient()
        let context = makeStore(
            api: api,
            snapshot: .testFixture(cameraStatus: "unavailable", modelConfidence: nil, ecgConnected: false)
        )
        context.store.participantID = "P-001"

        await context.store.beginSession()
        let commandsBeforeConfirmation = await api.commands()
        XCTAssertTrue(context.store.requiresDegradedConfirmation)
        XCTAssertEqual(commandsBeforeConfirmation, [])

        await context.store.beginSession(allowDegraded: true)
        let commandsAfterConfirmation = await api.commands()
        XCTAssertEqual(commandsAfterConfirmation, [.recaptureBaseline, .start("P-001")])
        XCTAssertEqual(context.store.flowState, .active)
    }

    func testHardRequirementPreventsStart() async {
        let api = RecordingAPIClient()
        let context = makeStore(api: api, snapshot: .testFixture(serialStatus: "disconnected"))
        context.store.participantID = "P-001"

        await context.store.beginSession(allowDegraded: true)

        let commands = await api.commands()
        XCTAssertEqual(commands, [])
        XCTAssertEqual(context.store.flowState, .preflight)
        XCTAssertNotNil(context.store.sessionMessage)
    }

    func testBaselineFailureReturnsToPreflightWithoutStarting() async {
        let api = RecordingAPIClient(failingCommand: .recaptureBaseline)
        let context = makeStore(api: api)
        context.store.participantID = "P-001"

        await context.store.beginSession()

        let commands = await api.commands()
        XCTAssertEqual(commands, [.recaptureBaseline])
        XCTAssertEqual(context.store.flowState, .preflight)
        XCTAssertEqual(context.store.sessionMessage, "Test command rejected")
    }

    func testStartFailureReturnsToPreflight() async {
        let api = RecordingAPIClient(failingCommand: .start("P-001"))
        let context = makeStore(api: api)
        context.store.participantID = "P-001"

        await context.store.beginSession()

        XCTAssertEqual(context.store.flowState, .preflight)
        XCTAssertEqual(context.store.sessionMessage, "Test command rejected")
    }

    func testDuplicateStartIsIgnoredWhileCommandIsInFlight() async {
        let api = RecordingAPIClient(suspendStart: true)
        let context = makeStore(api: api)
        context.store.participantID = "P-001"

        let first = Task { await context.store.beginSession() }
        await api.waitUntilStartIsSuspended()
        await context.store.beginSession()
        await api.releaseStart()
        await first.value

        let startCount = await api.startCount()
        XCTAssertEqual(startCount, 1)
    }

    func testStopBuildsCompletionFromObservedMetrics() async {
        let api = RecordingAPIClient()
        let clock = TestSessionClock()
        let context = makeStore(api: api, clock: clock)
        context.store.participantID = "P-001"
        await context.store.beginSession()
        context.stream.emit(snapshot: .testFixture(
            recording: true,
            repetitions: 6,
            feedback: "Good form",
            romDeg: 58,
            ecgBPM: 73
        ))
        clock.currentDate = Date(timeIntervalSince1970: 112)

        await context.store.stopSession()

        guard case .completed(let completion) = context.store.flowState else {
            return XCTFail("Expected completed session")
        }
        XCTAssertEqual(completion.duration, 12)
        XCTAssertEqual(completion.repetitions, 6)
        XCTAssertEqual(completion.maximumROM, 58)
        XCTAssertEqual(completion.latestBPM, 73)
    }

    func testStopFailureKeepsActiveState() async {
        let api = RecordingAPIClient(failingCommand: .stop)
        let context = makeStore(api: api)
        context.store.participantID = "P-001"
        await context.store.beginSession()

        await context.store.stopSession()

        XCTAssertEqual(context.store.flowState, .active)
        XCTAssertEqual(context.store.sessionMessage, "Test command rejected")
    }

    func testExternalRecordingSnapshotReconcilesFlowState() {
        let context = makeStore()

        context.stream.emit(snapshot: .testFixture(recording: true, repetitions: 2))
        XCTAssertEqual(context.store.flowState, .active)

        context.stream.emit(snapshot: .testFixture(recording: false, repetitions: 4))
        guard case .completed(let completion) = context.store.flowState else {
            return XCTFail("Expected externally stopped recording to complete the session")
        }
        XCTAssertEqual(completion.repetitions, 4)
    }

    func testReconnectDoesNotCompleteAnActiveSession() {
        let context = makeStore(snapshot: .testFixture(recording: true))

        context.stream.emit(state: .reconnecting(attempt: 1))

        XCTAssertEqual(context.store.flowState, .active)
        XCTAssertFalse(context.store.readiness.blockingChecks.isEmpty)
    }

    func testFeedbackHapticsEmitOnlyForAcceptedCategoryChanges() async {
        let haptics = RecordingHaptics()
        let clock = TestSessionClock()
        let context = makeStore(clock: clock, haptics: haptics)
        context.store.participantID = "P-001"
        await context.store.beginSession()

        context.stream.emit(snapshot: .testFixture(recording: true, feedback: "Good form"))
        context.stream.emit(snapshot: .testFixture(recording: true, feedback: "Good form"))
        clock.currentDate = Date(timeIntervalSince1970: 102)
        context.stream.emit(snapshot: .testFixture(recording: true, feedback: "Slow down"))

        XCTAssertEqual(haptics.categories, [.good, .slowDown])
    }

    func testReturnToPreflightResetsCompletion() async {
        let context = makeStore()
        context.store.participantID = "P-001"
        await context.store.beginSession()
        await context.store.stopSession()

        context.store.returnToPreflight()

        XCTAssertEqual(context.store.flowState, .preflight)
        XCTAssertNil(context.store.sessionMessage)
    }

    private func makeStore(
        api: RecordingAPIClient = RecordingAPIClient(),
        snapshot: LiveSnapshot = .testFixture(),
        clock: TestSessionClock = TestSessionClock(),
        haptics: RecordingHaptics = RecordingHaptics()
    ) -> (store: LiveStore, stream: TestLiveStream) {
        let stream = TestLiveStream()
        let store = LiveStore(
            api: api,
            stream: stream,
            camera: TestCameraClient(),
            clock: clock,
            haptics: haptics
        )
        store.appear()
        stream.emit(state: .connected)
        stream.emit(snapshot: snapshot)
        return (store, stream)
    }
}
