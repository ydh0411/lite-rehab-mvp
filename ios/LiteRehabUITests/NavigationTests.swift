import XCTest

@MainActor
final class NavigationTests: XCTestCase {
    func testPairedAppShowsMainTabsAndAcknowledgements() {
        let app = XCUIApplication()
        app.launchArguments = ["-ui-testing", "-fixture-paired"]
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["Live"].waitForExistence(timeout: 5))
        app.tabBars.buttons["History"].tap()
        XCTAssertTrue(app.navigationBars["History"].exists)
        app.tabBars.buttons["Settings"].tap()
        XCTAssertTrue(app.navigationBars["Settings"].exists)
        let acknowledgements = app.buttons["Acknowledgements"]
        if !acknowledgements.exists {
            app.swipeUp()
        }
        XCTAssertTrue(acknowledgements.waitForExistence(timeout: 3))
        acknowledgements.tap()
        XCTAssertTrue(app.navigationBars["Acknowledgements"].exists)
    }
}
