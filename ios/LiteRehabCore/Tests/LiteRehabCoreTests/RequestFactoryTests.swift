import Foundation
import Testing

@testable import LiteRehabCore


@Suite("Authenticated request construction")
struct RequestFactoryTests {
    private let connection = ServerConnection(
        name: "LiteRehab Mac",
        baseURL: URL(string: "http://192.168.1.8:8000")!,
        token: "secret-token"
    )

    @Test("constructs an authenticated sessions request")
    func sessionsRequest() throws {
        let request = try RequestFactory(connection: connection).request(for: .sessions)

        #expect(request.url?.absoluteString == "http://192.168.1.8:8000/api/sessions")
        #expect(request.httpMethod == "GET")
        #expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer secret-token")
    }

    @Test("encodes a report session ID as one path component")
    func reportRequest() throws {
        let request = try RequestFactory(connection: connection).request(
            for: .report("session with spaces")
        )

        #expect(request.url?.absoluteString == "http://192.168.1.8:8000/api/sessions/session%20with%20spaces")
    }

    @Test("encodes a start command as JSON")
    func startRequest() throws {
        let request = try RequestFactory(connection: connection).request(
            for: .startSession(subject: "Demo-01")
        )
        let body = try #require(request.httpBody)
        let json = try #require(
            JSONSerialization.jsonObject(with: body) as? [String: String]
        )

        #expect(request.httpMethod == "POST")
        #expect(request.value(forHTTPHeaderField: "Content-Type") == "application/json")
        #expect(json == ["subject": "Demo-01"])
    }

    @Test("converts HTTP to WebSocket without dropping authorization")
    func websocketRequest() throws {
        let request = try RequestFactory(connection: connection).request(for: .live)

        #expect(request.url?.absoluteString == "ws://192.168.1.8:8000/api/live")
        #expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer secret-token")
    }

    @Test("maps every command to the existing FastAPI route", arguments: [
        (APIEndpoint.stopSession, "/api/session/stop"),
        (APIEndpoint.recaptureBaseline, "/api/session/baseline"),
        (APIEndpoint.resetRange, "/api/session/range/reset"),
        (APIEndpoint.cameraJPEG, "/api/camera.jpg"),
        (APIEndpoint.mobileHealth, "/api/mobile/health"),
    ])
    func mapsRoutes(endpoint: APIEndpoint, path: String) throws {
        let request = try RequestFactory(connection: connection).request(for: endpoint)

        #expect(request.url?.path == path)
    }
}
