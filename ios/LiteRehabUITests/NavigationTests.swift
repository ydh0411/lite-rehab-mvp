import XCTest

@MainActor
final class NavigationTests: XCTestCase {
    func testPairedAppHasTwoPrimaryTabsAndSettingsToolbarButton() {
        let app = XCUIApplication()
        app.launchArguments = ["-ui-testing", "-fixture-paired", "-fixture-live"]
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["Live"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.tabBars.buttons["History"].exists)
        XCTAssertFalse(app.tabBars.buttons["Settings"].exists)

        let settings = app.buttons["Open Settings"]
        XCTAssertTrue(settings.exists)
        settings.tap()
        XCTAssertTrue(app.navigationBars["Settings"].waitForExistence(timeout: 3))
        app.buttons["Done"].tap()

        app.tabBars.buttons["History"].tap()
        XCTAssertTrue(app.navigationBars["History"].exists)
    }
}
