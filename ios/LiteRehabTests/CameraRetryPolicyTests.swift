import Foundation
import LiteRehabCore
@testable import LiteRehab
import UIKit
import XCTest

@MainActor
final class CameraRetryPolicyTests: XCTestCase {
    func testFailuresBackOffAndReportOnlyTheFirstStableError() {
        var policy = CameraRetryPolicy()

        let first = policy.recordFailure()
        let second = policy.recordFailure()
        let third = policy.recordFailure()
        let fourth = policy.recordFailure()
        let fifth = policy.recordFailure()

        XCTAssertEqual(
            [first.delay, second.delay, third.delay, fourth.delay, fifth.delay],
            [.milliseconds(500), .seconds(1), .seconds(2), .seconds(4), .seconds(4)]
        )
        XCTAssertTrue(first.shouldReport)
        XCTAssertFalse(second.shouldReport)
        XCTAssertFalse(third.shouldReport)
    }

    func testSuccessRestoresResponsivePolling() {
        var policy = CameraRetryPolicy()
        _ = policy.recordFailure()
        _ = policy.recordFailure()

        let delay = policy.recordSuccess()

        XCTAssertEqual(delay, .milliseconds(125))
        XCTAssertEqual(policy.consecutiveFailures, 0)
        XCTAssertTrue(policy.recordFailure().shouldReport)
    }

    func testClientSuppressesRepeatedErrorsAndResetsAfterFrameRecovery() async throws {
        let connection = ServerConnection(
            name: "Test Mac",
            baseURL: URL(string: "http://192.168.1.8:8000")!,
            token: "secret"
        )
        let imageData = UIGraphicsImageRenderer(size: CGSize(width: 2, height: 2)).pngData { context in
            UIColor.systemIndigo.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 2, height: 2))
        }
        let sequence = CameraFrameSequence(imageData: imageData)
        let delays = CameraDelayRecorder(cancelAfter: 3)
        let recovered = expectation(description: "Recovered camera frame")
        var errorCount = 0
        var frameCount = 0
        let client = CameraFrameClient(
            connection: connection,
            fetch: { request in try await sequence.next(request: request) },
            sleep: { delay in try await delays.sleep(for: delay) }
        )

        client.start(
            onFrame: { _ in
                frameCount += 1
                recovered.fulfill()
            },
            onError: { _ in
                errorCount += 1
            }
        )

        await fulfillment(of: [recovered], timeout: 2)
        client.stop()

        let recordedDelays = await delays.values()
        XCTAssertEqual(recordedDelays, [.milliseconds(500), .seconds(1), .milliseconds(125)])
        XCTAssertEqual(errorCount, 1)
        XCTAssertEqual(frameCount, 1)
    }
}

private actor CameraFrameSequence {
    private let imageData: Data
    private var attempt = 0

    init(imageData: Data) {
        self.imageData = imageData
    }

    func next(request: URLRequest) throws -> (Data, URLResponse) {
        defer { attempt += 1 }
        if attempt < 2 {
            throw URLError(.timedOut)
        }
        guard attempt == 2 else {
            throw CancellationError()
        }
        let response = HTTPURLResponse(
            url: request.url!,
            statusCode: 200,
            httpVersion: "HTTP/1.1",
            headerFields: ["Content-Type": "image/png"]
        )!
        return (imageData, response)
    }
}

private actor CameraDelayRecorder {
    private var delays: [Duration] = []
    private let cancelAfter: Int

    init(cancelAfter: Int) {
        self.cancelAfter = cancelAfter
    }

    func sleep(for delay: Duration) throws {
        delays.append(delay)
        if delays.count >= cancelAfter {
            throw CancellationError()
        }
    }

    func values() -> [Duration] { delays }
}
