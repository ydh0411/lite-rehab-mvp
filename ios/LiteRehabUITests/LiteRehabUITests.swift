import XCTest

@MainActor
final class LiteRehabUITests: XCTestCase {
    func testAppLaunches() {
        let app = XCUIApplication()
        app.launchArguments = ["-ui-testing", "-fixture-unpaired"]
        app.launch()
        XCTAssertTrue(
            app.staticTexts["Guided rehabilitation, connected to your Mac"]
                .waitForExistence(timeout: 5)
        )
        XCTAssertTrue(app.buttons["Pair with Mac"].exists)
    }
}
