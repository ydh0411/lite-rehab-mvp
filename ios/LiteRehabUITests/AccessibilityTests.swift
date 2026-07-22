import XCTest

@MainActor
final class AccessibilityTests: XCTestCase {
    func testLiveScreenRemainsUsableAtAccessibilityTextSize() {
        let app = XCUIApplication()
        app.launchArguments = [
            "-ui-testing",
            "-fixture-paired",
            "-fixture-live",
            "-UIPreferredContentSizeCategoryName",
            "UICTContentSizeCategoryAccessibilityExtraExtraExtraLarge"
        ]
        app.launch()

        XCTAssertTrue(app.textFields["Participant ID"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["Start Session"].isHittable)
        XCTAssertTrue(app.buttons["Open Settings"].isHittable)
    }

    func testEveryPrimaryTabAndSettingsControlHasAReadableLabel() {
        let app = XCUIApplication()
        app.launchArguments = ["-ui-testing", "-fixture-paired", "-fixture-live"]
        app.launch()

        XCTAssertEqual(app.tabBars.buttons["Live"].label, "Live")
        XCTAssertEqual(app.tabBars.buttons["History"].label, "History")
        XCTAssertEqual(app.buttons["Open Settings"].label, "Open Settings")
    }
}
