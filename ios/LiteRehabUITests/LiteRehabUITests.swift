import XCTest

@MainActor
final class LiteRehabUITests: XCTestCase {
    func testAppLaunches() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.staticTexts["LiteRehab"].waitForExistence(timeout: 3))
    }
}
