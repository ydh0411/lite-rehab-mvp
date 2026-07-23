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
        XCTAssertTrue(app.staticTexts["Participant 01"].waitForExistence(timeout: 3))
        app.staticTexts["Participant 01"].tap()
        XCTAssertTrue(app.navigationBars["Session Report"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["Movement quality"].exists)
    }

    func testSettingsKeepsPrototypeDisclaimerAndAcknowledgements() {
        let app = XCUIApplication()
        app.launchArguments = ["-ui-testing", "-fixture-paired", "-fixture-live"]
        app.launch()
        app.buttons["Open Settings"].tap()

        XCTAssertTrue(
            app.staticTexts["Engineering prototype — not a medical device"]
                .waitForExistence(timeout: 3)
        )
        XCTAssertTrue(app.buttons["Open Source Acknowledgements"].exists)
    }

    func testHistoryShowsEmptyState() {
        let app = XCUIApplication()
        app.launchArguments = [
            "-ui-testing", "-fixture-paired", "-fixture-live", "-fixture-history-empty"
        ]
        app.launch()
        app.tabBars.buttons["History"].tap()

        XCTAssertTrue(app.staticTexts["No sessions yet"].waitForExistence(timeout: 3))
    }

    func testHistoryShowsRetryForServerError() {
        let app = XCUIApplication()
        app.launchArguments = [
            "-ui-testing", "-fixture-paired", "-fixture-live", "-fixture-history-error"
        ]
        app.launch()
        app.tabBars.buttons["History"].tap()

        XCTAssertTrue(app.staticTexts["Could not load history"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.buttons["Try Again"].exists)
    }
}
