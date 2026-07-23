import Foundation
import LiteRehabCore
@testable import LiteRehab
import XCTest

final class APIClientTests: XCTestCase {
    override func tearDown() {
        StubURLProtocol.handler = nil
        super.tearDown()
    }

    func testSessionsDecodeAndCarryBearerAuthorization() async throws {
        StubURLProtocol.handler = { request in
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer secret")
            XCTAssertEqual(request.url?.path, "/api/sessions")
            let json = #"[{"session_id":"s-1","subject":"demo-01","started_at":"2026-07-20T10:00:00Z","duration_s":60,"repetitions":4,"exercises":["curl"],"good_form_percent":75,"max_rom_deg":92,"serial_completeness_percent":100,"pose_completeness_percent":90,"ecg_completeness_percent":null,"warnings":[]}]"#
            return (200, Data(json.utf8))
        }

        let sessions = try await makeClient().sessions()

        XCTAssertEqual(sessions.first?.sessionID, "s-1")
        XCTAssertEqual(sessions.first?.ecgCompletenessPercent, nil)
    }

    func testUnauthorizedResponseMapsToPairingExpired() async {
        StubURLProtocol.handler = { _ in (401, Data()) }
        do {
            _ = try await makeClient().health()
            XCTFail("Expected pairingExpired")
        } catch {
            XCTAssertEqual(error as? NetworkError, .pairingExpired)
        }
    }

    func testConflictPreservesBackendDetail() async {
        StubURLProtocol.handler = { _ in
            (409, Data(#"{"detail":"A session is already recording"}"#.utf8))
        }
        do {
            _ = try await makeClient().startSession(subject: "demo")
            XCTFail("Expected server error")
        } catch {
            XCTAssertEqual(error as? NetworkError, .server("A session is already recording"))
        }
    }

    private func makeClient() -> APIClient {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubURLProtocol.self]
        return APIClient(
            connection: ServerConnection(
                name: "Test Mac",
                baseURL: URL(string: "http://192.168.1.8:8000")!,
                token: "secret"
            ),
            session: URLSession(configuration: configuration)
        )
    }
}

private final class StubURLProtocol: URLProtocol {
    nonisolated(unsafe) static var handler: ((URLRequest) throws -> (Int, Data))?

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        do {
            let (status, data) = try XCTUnwrap(Self.handler)(request)
            let response = HTTPURLResponse(
                url: try XCTUnwrap(request.url),
                statusCode: status,
                httpVersion: "HTTP/1.1",
                headerFields: ["Content-Type": "application/json"]
            )!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}
