import XCTest

@MainActor
final class SessionFlowTests: XCTestCase {
    func testCompleteGuidedSessionFlow() {
        let app = XCUIApplication()
        app.launchArguments = ["-fixture-paired", "-fixture-live", "-ui-testing"]
        app.launch()

        let field = app.textFields["Participant ID"]
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        field.tap()
        field.typeText("P-001")
        app.buttons["Start Session"].tap()

        XCTAssertTrue(app.staticTexts["Session in progress"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["Repetitions"].exists)
        app.buttons["Finish Session"].tap()
        XCTAssertTrue(app.sheets.buttons["Finish Session"].waitForExistence(timeout: 2))
        app.sheets.buttons["Finish Session"].tap()
        XCTAssertTrue(app.staticTexts["Session complete"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.buttons["Done"].exists)
    }

    func testOptionalHardwareRequiresExplicitStartAnyway() {
        let app = XCUIApplication()
        app.launchArguments = ["-fixture-paired", "-fixture-degraded", "-ui-testing"]
        app.launch()

        let field = app.textFields["Participant ID"]
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        field.tap()
        field.typeText("P-002")
        app.buttons["Start Session"].tap()

        XCTAssertTrue(app.alerts["Some features are unavailable"].waitForExistence(timeout: 2))
        XCTAssertTrue(app.alerts.buttons["Start Anyway"].exists)
    }

    func testReconnectAndCameraLossPreserveActiveTraining() {
        let app = XCUIApplication()
        app.launchArguments = [
            "-fixture-paired",
            "-fixture-reconnecting",
            "-fixture-active-camera-unavailable",
            "-ui-testing"
        ]
        app.launch()

        XCTAssertTrue(app.staticTexts["Session in progress"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Reconnecting to Mac…"].exists)
        XCTAssertTrue(app.staticTexts["Camera temporarily unavailable"].exists)
        XCTAssertTrue(app.buttons["Finish Session"].isHittable)
    }
}
