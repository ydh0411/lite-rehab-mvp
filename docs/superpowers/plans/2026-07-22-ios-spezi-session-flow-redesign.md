# LiteRehab iPhone Spezi Session Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace only the native iPhone interface with a polished Stanford Spezi-style rehabilitation flow that pairs to the Mac, verifies hardware, guides the user through countdown/training/completion, and stays synchronized with the existing Mac backend.

**Architecture:** Keep the Mac/FastAPI runtime as the single source of truth and retain the existing REST, WebSocket, and camera-frame clients. Add pure presentation/state models around the current `LiveSnapshot`, make `LiveStore` the session-flow coordinator, compose the iPhone screens from Spezi onboarding and SwiftUI task-flow patterns, and expose deterministic fixture dependencies for unit/UI testing. The desktop web dashboard and backend API remain unchanged.

**Tech Stack:** Swift 6, SwiftUI, iOS 17+, Stanford Spezi 1.10.2, SpeziViews 1.12.14, SpeziOnboarding 2.0.4, XCTest/XCUITest, XcodeGen, existing FastAPI/WebSocket backend.

## Global Constraints

- Change only files under `ios/` plus iPhone-facing documentation and third-party notices. Do not change the desktop web UI or backend API contract.
- Preserve portrait orientation, English-only UI, iOS 17 deployment target, and the existing app bundle/signing configuration.
- Use the fixed Spezi Template reference commit `d52014a54cbfe68ef1f1c364e81a97edecf5e4a8`; reuse its page composition and interaction conventions, not its unrelated Firebase, HealthKit, scheduling, contacts, or cloud features.
- Treat Mac connection and serial sensor connection as hard preflight requirements. Treat camera, ECG, and ML feedback as soft requirements that require explicit degraded-mode confirmation.
- Never display `.active` until both baseline capture and `startSession` succeed. Prevent duplicate start/stop requests while commands are in flight.
- Keep full report generation on the Mac. The phone completion screen is a locally accumulated summary only.
- Keep camera polling active only while the Live surface is visible, use adaptive retry after failures, and reset immediately after recovery.
- Keep the engineering-prototype/non-medical disclaimer visible in onboarding and settings.
- Follow red-green-refactor for each task and commit only the files named by that task; never stage Xcode `xcuserdata` or `.swiftpm` output.

---

## Task 1: Add Spezi onboarding dependency and pure session presentation models

**Files:**

- Modify: `ios/project.yml`
- Modify: `ios/LiteRehab/Resources/THIRD_PARTY_NOTICES.md`
- Create: `ios/LiteRehab/Live/SessionFlowState.swift`
- Create: `ios/LiteRehab/Live/HardwareReadiness.swift`
- Create: `ios/LiteRehab/Live/FeedbackPresentation.swift`
- Test: `ios/LiteRehabTests/LivePresentationModelsTests.swift`

**Interfaces:**

- Consumes: `LiveSnapshot`, Boolean Mac connectivity, raw backend feedback text, and `Date` timestamps.
- Produces:

```swift
enum SessionFlowState: Equatable {
    case preflight
    case countdown(remaining: Int)
    case active
    case completed(SessionCompletion)
}

struct SessionCompletion: Equatable {
    let duration: TimeInterval
    let repetitions: Int
    let maximumROM: Double?
    let latestBPM: Double?
    let finalFeedback: FeedbackPresentation
}

struct SessionAccumulator: Equatable {
    private(set) var startedAt: Date?
    mutating func start(at date: Date)
    mutating func observe(_ snapshot: LiveSnapshot)
    func completion(at date: Date) -> SessionCompletion
}

struct HardwareReadiness: Equatable {
    struct Check: Identifiable, Equatable {
        enum Requirement: Equatable { case required, optional }
        enum State: Equatable { case ready, unavailable }
        let id: String
        let title: String
        let detail: String
        let requirement: Requirement
        let state: State
    }

    let checks: [Check]
    var blockingChecks: [Check] { get }
    var unavailableOptionalChecks: [Check] { get }
    var canStartNormally: Bool { get }
    var canStartDegraded: Bool { get }

    static func make(snapshot: LiveSnapshot?, macConnected: Bool) -> HardwareReadiness
}

enum FeedbackCategory: Equatable {
    case neutral, good, slowDown, increaseRange, reduceCompensation
}

struct FeedbackPresentation: Equatable {
    let category: FeedbackCategory
    let title: String
    let guidance: String
    let symbolName: String
    static func make(raw: String?) -> FeedbackPresentation
}

struct FeedbackHapticGate {
    mutating func shouldEmit(
        category: FeedbackCategory,
        at date: Date,
        minimumInterval: TimeInterval = 1.5
    ) -> Bool
}
```

- [ ] Write failing unit tests for hardware requirements, feedback normalization, session accumulation, and haptic throttling.

```swift
func testReadinessBlocksWithoutMacOrSerialButAllowsExplicitDegradedMode() {
    let snapshot = LiveSnapshot.fixture(
        serialStatus: "connected",
        cameraStatus: "unavailable",
        ecgConnected: false,
        modelConfidence: nil
    )

    let disconnected = HardwareReadiness.make(snapshot: snapshot, macConnected: false)
    XCTAssertEqual(disconnected.blockingChecks.map(\.id), ["mac"])

    let connected = HardwareReadiness.make(snapshot: snapshot, macConnected: true)
    XCTAssertTrue(connected.blockingChecks.isEmpty)
    XCTAssertEqual(Set(connected.unavailableOptionalChecks.map(\.id)), ["camera", "ecg", "model"])
    XCTAssertTrue(connected.canStartDegraded)
    XCTAssertFalse(connected.canStartNormally)
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

func testHapticGateRequiresChangedCategoryAndThrottleInterval() {
    var gate = FeedbackHapticGate()
    let start = Date(timeIntervalSince1970: 100)
    XCTAssertTrue(gate.shouldEmit(category: .good, at: start))
    XCTAssertFalse(gate.shouldEmit(category: .good, at: start.addingTimeInterval(2)))
    XCTAssertFalse(gate.shouldEmit(category: .slowDown, at: start.addingTimeInterval(1)))
    XCTAssertTrue(gate.shouldEmit(category: .slowDown, at: start.addingTimeInterval(2)))
}
```

- [ ] Run the focused tests and confirm they fail because the new types do not exist.

```bash
cd /Users/yuedonghan/Desktop/BMEG3920_project/lite_rehab_mvp/.worktrees/codex-ios-native-app/ios
xcodegen generate
xcodebuild test \
  -project LiteRehab.xcodeproj \
  -scheme LiteRehab \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:LiteRehabTests/LivePresentationModelsTests
```

Expected: build fails with `cannot find 'HardwareReadiness' in scope` and related missing-type errors.

- [ ] Add SpeziOnboarding 2.0.4 to `ios/project.yml` and attach the product to the `LiteRehab` application target.

```yaml
packages:
  SpeziOnboarding:
    url: https://github.com/StanfordSpezi/SpeziOnboarding.git
    exactVersion: 2.0.4

targets:
  LiteRehab:
    dependencies:
      - package: SpeziOnboarding
        product: SpeziOnboarding
```

- [ ] Record both reused projects in `ios/LiteRehab/Resources/THIRD_PARTY_NOTICES.md`, including repository URL, fixed version/commit, MIT license, and a short statement that LiteRehab reuses visual/interaction composition rather than source-domain features.

- [ ] Implement the three pure model files. `HardwareReadiness.make` must use normalized lowercase status strings, recognize `connected`, `ready`, and `streaming` as ready, and never infer Mac connectivity from the snapshot. `SessionAccumulator` must retain the latest valid BPM and maximum finite ROM.

- [ ] Add a test-only `LiveSnapshot.fixture(...)` factory at the bottom of the test file so production code does not gain fixture-only APIs.

- [ ] Re-run the focused tests.

Expected: `** TEST SUCCEEDED **` with all `LivePresentationModelsTests` passing.

- [ ] Commit the dependency, notices, models, and tests.

```bash
git add ios/project.yml ios/LiteRehab/Resources/THIRD_PARTY_NOTICES.md \
  ios/LiteRehab/Live/SessionFlowState.swift \
  ios/LiteRehab/Live/HardwareReadiness.swift \
  ios/LiteRehab/Live/FeedbackPresentation.swift \
  ios/LiteRehabTests/LivePresentationModelsTests.swift
git commit -m "feat(ios): add Spezi session presentation models"
```

---

## Task 2: Turn LiveStore into a deterministic session-flow coordinator

**Files:**

- Modify: `ios/LiteRehab/Live/LiveStore.swift`
- Create: `ios/LiteRehab/Live/SessionClock.swift`
- Create: `ios/LiteRehab/Live/FeedbackHaptics.swift`
- Modify: `ios/LiteRehab/Networking/LiveWebSocketClient.swift`
- Create: `ios/LiteRehabTests/Support/LiveTestDoubles.swift`
- Create: `ios/LiteRehabTests/LiveStoreTests.swift`

**Interfaces:**

- Consumes: existing `APIClientProtocol`, `LiveStreaming`, `CameraFrameLoading`, `LiveSnapshot`, and connection changes.
- Produces:

```swift
protocol SessionClock: Sendable {
    func now() -> Date
    func waitOneSecond() async throws
}

struct SystemSessionClock: SessionClock { /* ContinuousClock-backed */ }

@MainActor
protocol FeedbackHapticEmitting {
    func emit(for category: FeedbackCategory)
}

@MainActor
final class LiveStore: ObservableObject {
    @Published private(set) var flowState: SessionFlowState
    @Published var participantID: String
    @Published private(set) var readiness: HardwareReadiness
    @Published private(set) var commandInProgress: Bool
    @Published private(set) var connectionState: LiveConnectionState
    @Published private(set) var sessionMessage: String?

    func beginSession(allowDegraded: Bool = false) async
    func stopSession() async
    func returnToPreflight()
}

@MainActor
protocol LiveStreaming: AnyObject {
    var state: LiveConnectionState { get }
    func start(
        onState: @escaping @MainActor (LiveConnectionState) -> Void,
        onSnapshot: @escaping @MainActor (LiveSnapshot) -> Void
    )
    func stop()
}
```

- [ ] Write failing tests using actor/class fakes that record the exact order and number of API calls. Include separate baseline-failure and stop-failure cases in addition to the examples below.

```swift
func testStartCapturesBaselineBeforeStartAndEntersActive() async {
    let api = RecordingAPIClient()
    let store = makeStore(api: api, snapshots: [.readyFixture])
    store.participantID = "P-001"

    await store.beginSession()

    XCTAssertEqual(await api.commands, [.recaptureBaseline, .start("P-001")])
    XCTAssertEqual(store.flowState, .active)
}

func testStartFailureReturnsToPreflight() async {
    let api = RecordingAPIClient(failingCommand: .start("P-001"))
    let store = makeStore(api: api, snapshots: [.readyFixture])
    store.participantID = "P-001"

    await store.beginSession()

    XCTAssertEqual(store.flowState, .preflight)
    XCTAssertNotNil(store.sessionMessage)
}

func testDuplicateStartIsIgnoredWhileCommandIsInFlight() async {
    let api = SuspendedRecordingAPIClient()
    let store = makeStore(api: api, snapshots: [.readyFixture])
    store.participantID = "P-001"

    async let first: Void = store.beginSession()
    async let second: Void = store.beginSession()
    await api.release()
    _ = await (first, second)

    XCTAssertEqual(await api.startCount, 1)
}

func testExternalRecordingSnapshotReconcilesFlowState() {
    let store = makeStore(snapshots: [.readyFixture])
    store.receive(.readyFixture(recording: true))
    XCTAssertEqual(store.flowState, .active)

    store.receive(.readyFixture(recording: false))
    guard case .completed = store.flowState else {
        return XCTFail("Expected externally stopped recording to complete the session")
    }
}

func testReconnectDoesNotCompleteAnActiveSession() {
    let store = makeStore(snapshots: [.readyFixture(recording: true)])
    store.receiveConnectionState(.reconnecting(attempt: 1))
    XCTAssertEqual(store.flowState, .active)
}
```

- [ ] Run the focused tests and confirm failure because `LiveStore` has no session-flow API.

```bash
cd /Users/yuedonghan/Desktop/BMEG3920_project/lite_rehab_mvp/.worktrees/codex-ios-native-app/ios
xcodebuild test \
  -project LiteRehab.xcodeproj \
  -scheme LiteRehab \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:LiteRehabTests/LiveStoreTests
```

Expected: compilation failures for `flowState`, `participantID`, and `beginSession`.

- [ ] Implement `SessionClock`, using `ContinuousClock().sleep(for: .seconds(1))` and `Date()` in production; use an immediate controllable fake in tests.

- [ ] Implement a UIKit-backed haptic emitter with category mapping and no-op behavior when Reduce Motion is enabled or the app is not active.

```swift
@MainActor
struct SystemFeedbackHaptics: FeedbackHapticEmitting {
    func emit(for category: FeedbackCategory) {
        guard UIApplication.shared.applicationState == .active,
              !UIAccessibility.isReduceMotionEnabled else { return }
        switch category {
        case .good:
            UINotificationFeedbackGenerator().notificationOccurred(.success)
        case .slowDown, .increaseRange, .reduceCompensation:
            UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        case .neutral:
            break
        }
    }
}
```

- [ ] Refactor `LiveStore` initialization to accept `clock: any SessionClock` and `haptics: any FeedbackHapticEmitting`, with production defaults. Preserve existing API/stream/camera injection points and the existing `commandInProgress`, `recaptureBaseline`, and `resetRange` surface so the pre-redesign `LiveView` continues compiling until Task 5. Keep `startSession(participantID:)` as a temporary compatibility adapter to the new coordinator, then remove that adapter with `StartSessionSheet` in Task 5.

- [ ] Extend `LiveStreaming.start` with the state callback shown above. Route every `LiveWebSocketClient` state transition through a small `setState(_:notify:)` helper so `LiveStore.connectionState` and readiness update immediately even when no snapshot arrives.

- [ ] Implement `beginSession` in this exact order: trim/freeze participant ID, reject empty ID, validate hard requirements, require `allowDegraded` when optional checks are missing, set in-flight, run `.countdown(3...1)`, call `recaptureBaseline`, call `startSession(subject:)`, initialize accumulator, then enter `.active`. On cancellation or error, return to `.preflight` and expose a stable user-facing message.

- [ ] Implement snapshot reconciliation:

  - recompute readiness after every snapshot/connection event;
  - observe metrics only while active;
  - emit haptics only when `FeedbackHapticGate` accepts a changed category;
  - if the Mac begins recording externally, enter active and seed the accumulator;
  - if a recording previously observed as active stops externally, create `.completed` exactly once;
  - do not turn a transient reconnect into a completed session.

- [ ] Implement `stopSession`: guard active/in-flight state, call the Mac once, and build `SessionCompletion` from the accumulator. Keep `.active` and show an error if stopping fails.

- [ ] Run both model and store test suites.

Expected: `** TEST SUCCEEDED **`; command-order, degraded-mode, duplicate-command, haptic, and external-reconciliation tests all pass.

- [ ] Commit the coordinator and tests.

```bash
git add ios/LiteRehab/Live/LiveStore.swift \
  ios/LiteRehab/Live/SessionClock.swift \
  ios/LiteRehab/Live/FeedbackHaptics.swift \
  ios/LiteRehab/Networking/LiveWebSocketClient.swift \
  ios/LiteRehabTests/Support/LiveTestDoubles.swift \
  ios/LiteRehabTests/LiveStoreTests.swift
git commit -m "feat(ios): coordinate guided rehabilitation sessions"
```

---

## Task 3: Add adaptive camera retry without changing the backend

**Files:**

- Create: `ios/LiteRehab/Networking/CameraRetryPolicy.swift`
- Modify: `ios/LiteRehab/Networking/CameraFrameClient.swift`
- Create: `ios/LiteRehabTests/CameraRetryPolicyTests.swift`

**Interfaces:**

- Consumes: frame success/failure events from the existing `/api/camera/frame` request.
- Produces:

```swift
struct CameraRetryPolicy: Equatable {
    private(set) var consecutiveFailures = 0

    mutating func recordSuccess() -> Duration
    mutating func recordFailure() -> (delay: Duration, shouldReport: Bool)
}
```

- [ ] Write the failing policy tests.

```swift
func testFailuresBackOffAndReportOnlyTheFirstStableError() {
    var policy = CameraRetryPolicy()
    let first = policy.recordFailure()
    let second = policy.recordFailure()
    let third = policy.recordFailure()
    let fourth = policy.recordFailure()
    let fifth = policy.recordFailure()

    XCTAssertEqual([first.delay, second.delay, third.delay, fourth.delay, fifth.delay], [
        .milliseconds(500), .seconds(1), .seconds(2), .seconds(4), .seconds(4)
    ])
    XCTAssertTrue(first.shouldReport)
    XCTAssertFalse(second.shouldReport)
}

func testSuccessRestoresResponsivePolling() {
    var policy = CameraRetryPolicy()
    _ = policy.recordFailure()
    _ = policy.recordFailure()
    XCTAssertEqual(policy.recordSuccess(), .milliseconds(125))
    XCTAssertEqual(policy.consecutiveFailures, 0)
}
```

- [ ] Run the test and confirm the missing-type failure.

```bash
cd /Users/yuedonghan/Desktop/BMEG3920_project/lite_rehab_mvp/.worktrees/codex-ios-native-app/ios
xcodebuild test \
  -project LiteRehab.xcodeproj \
  -scheme LiteRehab \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:LiteRehabTests/CameraRetryPolicyTests
```

Expected: build fails with `cannot find 'CameraRetryPolicy' in scope`.

- [ ] Implement the pure policy with a 125 ms success interval and capped failure sequence 500 ms, 1 s, 2 s, 4 s.

- [ ] Replace the fixed sleep in `CameraFrameClient` with the policy result. Publish the first error in a failure streak, suppress identical repeated errors, clear the visible error on the first recovered frame, and keep `stop()` cancellation immediate.

- [ ] Add a URLProtocol-backed client test or injected frame-fetch closure that proves retry delay selection and recovery reset without wall-clock sleeping.

- [ ] Run camera tests, then the complete unit-test target.

Expected: `** TEST SUCCEEDED **`, and no camera test waits for real time or network access.

- [ ] Commit the camera reliability change.

```bash
git add ios/LiteRehab/Networking/CameraRetryPolicy.swift \
  ios/LiteRehab/Networking/CameraFrameClient.swift \
  ios/LiteRehabTests/CameraRetryPolicyTests.swift
git commit -m "fix(ios): adapt camera polling to wireless failures"
```

---

## Task 4: Replace pairing and the app shell with Spezi-style composition

**Files:**

- Modify: `ios/LiteRehab/Pairing/PairingView.swift`
- Modify: `ios/LiteRehab/Pairing/PairingCoordinator.swift`
- Modify: `ios/LiteRehab/App/AppRootView.swift`
- Create: `ios/LiteRehab/App/ConnectedAppView.swift`
- Create: `ios/LiteRehab/App/AppDependencyFactory.swift`
- Modify: `ios/LiteRehab/Settings/SettingsView.swift`
- Modify: `ios/LiteRehabUITests/PairingFlowTests.swift`
- Modify: `ios/LiteRehabUITests/NavigationTests.swift`

**Interfaces:**

- Consumes: existing `PairingCoordinator`, `ConnectionVault`, production API clients, and process launch arguments.
- Produces:

```swift
struct AppDependencies {
    let apiClient: any APIClientProtocol
    let liveStream: any LiveStreaming
    let cameraClient: any CameraFrameLoading
    let sessionClock: any SessionClock
    let haptics: any FeedbackHapticEmitting

    static func production(connection: ServerConnection) -> AppDependencies
    static func fixture(arguments: [String]) -> AppDependencies?
}

struct ConnectedAppView: View {
    let connection: ServerConnection
    let dependencies: AppDependencies
    @ObservedObject var pairing: PairingCoordinator
}

enum AppTab: Hashable {
    case live, history
}
```

- [ ] Update UI tests first to require the new accessibility contract.

```swift
func testPairedAppHasTwoPrimaryTabsAndSettingsToolbarButton() {
    app.launchArguments = ["-fixture-paired", "-fixture-live"]
    app.launch()

    XCTAssertTrue(app.tabBars.buttons["Live"].exists)
    XCTAssertTrue(app.tabBars.buttons["History"].exists)
    XCTAssertFalse(app.tabBars.buttons["Settings"].exists)
    XCTAssertTrue(app.buttons["Open Settings"].exists)
}

func testUnpairedAppShowsSpeziWelcomeAndPairingAction() {
    app.launchArguments = ["-fixture-unpaired"]
    app.launch()

    XCTAssertTrue(app.staticTexts["Guided rehabilitation, connected to your Mac"].exists)
    XCTAssertTrue(app.buttons["Pair with Mac"].exists)
    XCTAssertTrue(app.staticTexts["Engineering prototype — not a medical device"].exists)
}
```

- [ ] Run the UI tests and confirm they fail against the old three-tab/custom pairing UI.

```bash
cd /Users/yuedonghan/Desktop/BMEG3920_project/lite_rehab_mvp/.worktrees/codex-ios-native-app/ios
xcodebuild test \
  -project LiteRehab.xcodeproj \
  -scheme LiteRehab \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:LiteRehabUITests/PairingFlowTests \
  -only-testing:LiteRehabUITests/NavigationTests
```

Expected: assertion failures for the onboarding title, two-tab shell, or settings toolbar control.

- [ ] Rebuild `PairingView` with `import SpeziOnboarding`, `OnboardingView`, and `OnboardingInformationView.Area`. Use these exact user-facing areas:

```swift
OnboardingInformationView.Area(
    icon: { Image(systemName: "iphone.and.arrow.forward") },
    title: "Pair once",
    description: "Scan the QR code shown by LiteRehab on your Mac."
)
OnboardingInformationView.Area(
    icon: { Image(systemName: "wave.3.right") },
    title: "Stay synchronized",
    description: "Your iPhone and Mac show the same live session state."
)
OnboardingInformationView.Area(
    icon: { Image(systemName: "lock.shield") },
    title: "Local network only",
    description: "Session data stays on your trusted local network."
)
```

- [ ] Construct the onboarding header with title `Guided rehabilitation, connected to your Mac`, subtitle `Follow a clear setup, training, and review flow on your iPhone`, and action text `Pair with Mac`. Keep the existing QR scanner, manual URL/token entry, validation, and Keychain-backed save behavior beneath the Spezi onboarding surface. Do not change the QR payload or authentication scheme.

- [ ] Implement `ConnectedAppView` as an iOS 17-compatible selection-bound `TabView` with only `Live` and `History`. Add `Open Settings` as a navigation toolbar button that presents a settings sheet; do not use iOS 18-only tab APIs from the current upstream template. Pass `LiveView` an `onOpenHistory` closure that assigns `.history` so the completion screen can switch tabs without owning navigation state.

- [ ] Make `PairingCoordinator` treat `-fixture-unpaired` as an explicit empty vault and `-fixture-paired` as the existing fixture connection. Implement deterministic `AppDependencyFactory.fixture(arguments:)` fakes for `-fixture-live`, `-fixture-degraded`, `-fixture-reconnecting`, and `-fixture-active-camera-unavailable`, including ready/degraded/active snapshots and immediate successful commands. When `-ui-testing` is present, inject an immediate session clock and no-op haptics; production always receives `SystemSessionClock` and `SystemFeedbackHaptics`. These fakes must live in the application target behind launch-argument selection so XCUITest can drive the real SwiftUI flow without a backend.

- [ ] Update `AppRootView` to choose dependencies once per saved connection and preserve the existing disconnect/repair behavior.

- [ ] Add accessibility identifiers: `pair-with-mac`, `open-settings`, `live-tab`, `history-tab`, and `disconnect-mac`.

- [ ] Re-run the UI tests.

Expected: `** TEST SUCCEEDED **`; the app has two primary tabs and settings opens from the toolbar.

- [ ] Commit the Spezi shell and pairing changes.

```bash
git add ios/LiteRehab/Pairing/PairingView.swift \
  ios/LiteRehab/Pairing/PairingCoordinator.swift \
  ios/LiteRehab/App/AppRootView.swift \
  ios/LiteRehab/App/ConnectedAppView.swift \
  ios/LiteRehab/App/AppDependencyFactory.swift \
  ios/LiteRehab/Settings/SettingsView.swift \
  ios/LiteRehabUITests/PairingFlowTests.swift \
  ios/LiteRehabUITests/NavigationTests.swift
git commit -m "feat(ios): adopt Spezi onboarding and app shell"
```

---

## Task 5: Build the guided preflight, countdown, active, and completion screens

**Files:**

- Modify: `ios/LiteRehab/Live/LiveView.swift`
- Create: `ios/LiteRehab/Live/PreflightView.swift`
- Create: `ios/LiteRehab/Live/HardwareStatusSection.swift`
- Create: `ios/LiteRehab/Live/SessionCountdownView.swift`
- Create: `ios/LiteRehab/Live/ActiveTrainingView.swift`
- Create: `ios/LiteRehab/Live/SessionCompletionView.swift`
- Modify: `ios/LiteRehab/Live/StartSessionSheet.swift`
- Modify: `ios/LiteRehab/DesignSystem/LiteRehabStyle.swift`
- Modify: `ios/LiteRehab/DesignSystem/MetricCard.swift`
- Modify: `ios/LiteRehab/DesignSystem/StatusBadge.swift`
- Create: `ios/LiteRehabUITests/SessionFlowTests.swift`

**Interfaces:**

- Consumes: `LiveStore.flowState`, `readiness`, `snapshot`, `cameraImage`, `participantID`, and command methods.
- Produces a single state-switched Live surface:

```swift
switch store.flowState {
case .preflight:
    PreflightView(store: store)
case .countdown(let remaining):
    SessionCountdownView(remaining: remaining)
case .active:
    ActiveTrainingView(store: store)
case .completed(let summary):
    SessionCompletionView(summary: summary) {
        store.returnToPreflight()
    }
}
```

- [ ] Write failing XCUITests for the happy path and degraded confirmation using fixture dependencies.

```swift
func testCompleteGuidedSessionFlow() {
    app.launchArguments = ["-fixture-paired", "-fixture-live", "-ui-testing"]
    app.launch()

    let field = app.textFields["Participant ID"]
    field.tap()
    field.typeText("P-001")
    app.buttons["Start Session"].tap()

    XCTAssertTrue(app.staticTexts["Session in progress"].waitForExistence(timeout: 2))
    XCTAssertTrue(app.staticTexts["Repetitions"].exists)
    app.buttons["Finish Session"].tap()
    XCTAssertTrue(app.staticTexts["Session complete"].waitForExistence(timeout: 2))
    XCTAssertTrue(app.buttons["Done"].exists)
}

func testOptionalHardwareRequiresExplicitStartAnyway() {
    app.launchArguments = ["-fixture-paired", "-fixture-degraded", "-ui-testing"]
    app.launch()
    app.textFields["Participant ID"].tap()
    app.textFields["Participant ID"].typeText("P-002")
    app.buttons["Start Session"].tap()

    XCTAssertTrue(app.alerts["Some features are unavailable"].exists)
    XCTAssertTrue(app.alerts.buttons["Start Anyway"].exists)
}

func testReconnectAndCameraLossPreserveActiveTraining() {
    app.launchArguments = [
        "-fixture-paired", "-fixture-reconnecting",
        "-fixture-active-camera-unavailable", "-ui-testing"
    ]
    app.launch()

    XCTAssertTrue(app.staticTexts["Session in progress"].waitForExistence(timeout: 2))
    XCTAssertTrue(app.staticTexts["Reconnecting to Mac…"].exists)
    XCTAssertTrue(app.staticTexts["Camera temporarily unavailable"].exists)
    XCTAssertTrue(app.buttons["Finish Session"].isHittable)
}
```

- [ ] Run the new UI tests and confirm they fail because the guided screens and identifiers do not exist.

- [ ] Implement `PreflightView` with a large Spezi-style title, participant field, hardware readiness list, connection retry action, and one primary `Start Session` button. Required failures disable start; optional failures present a confirmation alert with `Cancel` and `Start Anyway`.

- [ ] Implement `HardwareStatusSection` as a semantic list with green checkmark, amber optional warning, and red required error. Include text labels so status is not color-only. Keep technical URLs/tokens out of this surface.

- [ ] Implement `SessionCountdownView` with a large monospaced 3/2/1 numeral, `Preparing your baseline` copy, VoiceOver announcements, and Reduce Motion-aware animation.

- [ ] Implement `ActiveTrainingView` in this visual order:

  1. `Session in progress` status and participant ID;
  2. prominent repetitions and normalized feedback guidance;
  3. ROM and BPM metrics;
  4. wireless camera frame or stable recovery state;
  5. collapsed `Technical status` disclosure for confidence/source/serial/camera details;
  6. destructive-but-confirmed `Finish Session` action.

- [ ] Implement `SessionCompletionView` with duration, repetitions, maximum ROM, latest BPM, final feedback, `View in History`, and `Done`. State clearly that the full report is generated by the Mac.

- [ ] Retire the old modal start-sheet behavior. Keep `StartSessionSheet.swift` only if it becomes the optional-hardware confirmation content; otherwise delete it in this task and remove references from the XcodeGen project.

- [ ] Simplify the design system to system background/grouped background, semantic tint, 16–20 pt corner radii, system typography, and minimal shadow. Remove ornamental gradients that are not present in the Spezi reference language.

- [ ] Add accessibility identifiers: `participant-id`, `start-session`, `start-anyway`, `finish-session`, `session-complete`, `session-done`, and `technical-status`.

- [ ] Re-run `LivePresentationModelsTests`, `LiveStoreTests`, and `SessionFlowTests`.

Expected: `** TEST SUCCEEDED **`; both normal and degraded fixture flows reach active and completion states.

- [ ] Commit the complete guided interface.

```bash
git add ios/LiteRehab/Live ios/LiteRehab/DesignSystem \
  ios/LiteRehabUITests/SessionFlowTests.swift
git commit -m "feat(ios): build guided Spezi rehabilitation flow"
```

---

## Task 6: Restyle History, report, and settings without changing data ownership

**Files:**

- Modify: `ios/LiteRehab/History/HistoryView.swift`
- Modify: `ios/LiteRehab/History/SessionCard.swift`
- Modify: `ios/LiteRehab/Report/ReportView.swift`
- Modify: `ios/LiteRehab/Settings/SettingsView.swift`
- Modify: `ios/LiteRehab/Settings/AcknowledgementsView.swift`
- Modify: `ios/LiteRehabUITests/NavigationTests.swift`
- Create: `ios/LiteRehabUITests/AccessibilityTests.swift`

**Interfaces:**

- Consumes: existing sessions endpoint, report endpoint/PDF renderer, saved connection, and acknowledgements.
- Produces: visually consistent Spezi-style secondary surfaces; no new backend calls or report fields.

- [ ] Add failing UI tests that verify History empty/error/content states, report navigation, Settings presentation, disclaimer text, and Dynamic Type launch.

```swift
func testSettingsKeepsPrototypeDisclaimerAndAcknowledgements() {
    app.launchArguments = ["-fixture-paired", "-fixture-live"]
    app.launch()
    app.buttons["Open Settings"].tap()

    XCTAssertTrue(app.staticTexts["Engineering prototype — not a medical device"].exists)
    XCTAssertTrue(app.buttons["Open Source Acknowledgements"].exists)
}

func testLiveScreenRemainsUsableAtAccessibilityTextSize() {
    app.launchArguments = [
        "-fixture-paired", "-fixture-live",
        "-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityExtraExtraExtraLarge"
    ]
    app.launch()
    XCTAssertTrue(app.buttons["Start Session"].isHittable)
}
```

- [ ] Run the tests and confirm failures against the old layouts/accessibility labels.

- [ ] Replace custom history cards with an inset grouped list inspired by Spezi task tiles: clear subject/date hierarchy, compact exercise/side metadata, and a single obvious disclosure affordance.

- [ ] Keep report retrieval and PDF rendering unchanged. Restyle loading, error, and unavailable states with `ProgressView`, `ContentUnavailableView`, and retry actions appropriate to iOS 17.

- [ ] Present connection identity, repair/disconnect, acknowledgements, and prototype disclaimer as native Settings `Form` sections. Never display the stored bearer token.

- [ ] Ensure every icon-only control has an accessibility label, all semantic status includes text, scrolling works at AX5 text size, and essential actions meet a 44×44 pt hit target.

- [ ] Run the History/Settings accessibility UI tests.

Expected: `** TEST SUCCEEDED **` in standard and accessibility text-size launches.

- [ ] Commit the secondary-screen restyle.

```bash
git add ios/LiteRehab/History ios/LiteRehab/Report ios/LiteRehab/Settings \
  ios/LiteRehabUITests/NavigationTests.swift \
  ios/LiteRehabUITests/AccessibilityTests.swift
git commit -m "style(ios): align secondary screens with Spezi"
```

---

## Task 7: Verify on simulator and physical iPhone, then update demo documentation

**Files:**

- Modify: `README.md`
- Modify: `README_zh.md`
- Modify: `DEMO_GUIDE.md`
- Modify only if test discovery requires it: `ios/project.yml`

**Interfaces:**

- Consumes: the completed iPhone flow, existing backend command, Mac IP `172.20.10.14`, and MaixCAM RTSP source.
- Produces: reproducible simulator/physical-device demo instructions and evidence that no desktop/backend regression was introduced.

- [ ] Regenerate the Xcode project and confirm the package graph resolves SpeziOnboarding 2.0.4.

```bash
cd /Users/yuedonghan/Desktop/BMEG3920_project/lite_rehab_mvp/.worktrees/codex-ios-native-app/ios
xcodegen generate
xcodebuild -resolvePackageDependencies \
  -project LiteRehab.xcodeproj \
  -scheme LiteRehab
```

Expected: resolution lists `SpeziOnboarding @ 2.0.4` and exits 0.

- [ ] Run the complete automated suite.

```bash
cd /Users/yuedonghan/Desktop/BMEG3920_project/lite_rehab_mvp/.worktrees/codex-ios-native-app
./scripts/test_all.sh

cd ios
xcodebuild test \
  -project LiteRehab.xcodeproj \
  -scheme LiteRehab \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
```

Expected: backend/core tests pass and Xcode reports `** TEST SUCCEEDED **` for unit and UI tests.

- [ ] Run light, dark, and AX5 fixture launches and capture screenshots for pairing, preflight, active, completion, history, and settings. Visually inspect for clipping, contrast, stale camera errors, and controls hidden by the keyboard or safe areas.

- [ ] Launch the unchanged final hardware backend from the repository worktree using the wireless MaixCAM stream:

```bash
LITEREHAB_DIR="/Users/yuedonghan/Desktop/BMEG3920_project/lite_rehab_mvp/.worktrees/codex-ios-native-app"
MAC_IP="172.20.10.14"
CAMERA_RTSP="rtsp://172.20.10.5:8554/live"

cd "$LITEREHAB_DIR" || exit 1
conda activate literehab
python -m pip install -r python/requirements.txt

PYTHONPATH="$LITEREHAB_DIR/python" \
python "$LITEREHAB_DIR/python/run_web_dashboard.py" \
  --host 0.0.0.0 \
  --web-port 8000 \
  --mobile \
  --advertised-host "$MAC_IP" \
  --no-browser \
  --port auto \
  --camera-source "$CAMERA_RTSP" \
  --side right \
  --sessions-dir "$LITEREHAB_DIR/python/sessions" \
  --model "$LITEREHAB_DIR/python/models/imu_cnnbigru.pt"
```

Expected: terminal prints `Mobile server: http://172.20.10.14:8000`; the Mac web dashboard loads and the iPhone remains paired on the same trusted network.

- [ ] On the physical iPhone, verify: QR pairing; Local Network permission; ready/degraded preflight; 3-2-1 baseline; start/stop synchronization with the Mac dashboard; feedback haptic category changes; camera backoff/recovery by briefly interrupting Wi-Fi; completion summary; History report; Settings disconnect/repair.

- [ ] Update `README.md`, `README_zh.md`, and `DEMO_GUIDE.md` with the two-tab phone flow, Settings toolbar location, hard/soft preflight behavior, wireless-camera recovery behavior, and the exact final hardware command above.

- [ ] Check the scope and generated-file hygiene.

```bash
git status --short
git diff --check
git diff --stat HEAD~6
```

Expected: no changes to desktop web/backend implementation; no staged `xcuserdata`, `.swiftpm`, DerivedData, screenshots, tokens, or session data; `git diff --check` exits 0.

- [ ] Commit documentation after every verification item is complete.

```bash
git add README.md README_zh.md DEMO_GUIDE.md ios/project.yml
git commit -m "docs: update final iPhone hardware demo workflow"
```

- [ ] Push only after reviewing all seven task commits and confirming the physical-device demo.

```bash
git push origin codex/ios-native-app
```

Expected: remote branch advances successfully and GitHub contains the Spezi redesign plus its tests and documentation.
