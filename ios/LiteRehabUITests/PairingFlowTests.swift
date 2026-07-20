import XCTest

@MainActor
final class PairingFlowTests: XCTestCase {
    func testScannerCanBeOpenedAndCancelled() {
        let app = XCUIApplication()
        app.launchArguments = ["-ui-testing"]
        app.launch()

        let scan = app.buttons["Scan Mac QR Code"]
        XCTAssertTrue(scan.waitForExistence(timeout: 5))
        scan.tap()
        XCTAssertTrue(app.navigationBars["Scan QR Code"].waitForExistence(timeout: 3))
        app.buttons["Cancel"].tap()
        XCTAssertTrue(scan.waitForExistence(timeout: 3))
    }
}
