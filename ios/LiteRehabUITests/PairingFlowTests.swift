import XCTest

@MainActor
final class PairingFlowTests: XCTestCase {
    func testUnpairedAppShowsSpeziWelcomeAndPairingAction() {
        let app = XCUIApplication()
        app.launchArguments = ["-ui-testing", "-fixture-unpaired"]
        app.launch()

        XCTAssertTrue(
            app.staticTexts["Guided rehabilitation, connected to your Mac"]
                .waitForExistence(timeout: 5)
        )
        XCTAssertTrue(app.staticTexts["Engineering prototype — not a medical device"].exists)

        let pair = app.buttons["Pair with Mac"]
        XCTAssertTrue(pair.exists)
        pair.tap()
        XCTAssertTrue(app.navigationBars["Scan QR Code"].waitForExistence(timeout: 3))
        app.buttons["Cancel"].tap()
        XCTAssertTrue(pair.waitForExistence(timeout: 3))
    }
}
