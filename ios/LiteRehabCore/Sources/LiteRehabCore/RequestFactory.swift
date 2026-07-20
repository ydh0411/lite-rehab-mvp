import Foundation


public enum APIEndpoint: Equatable, Sendable {
    case mobileHealth
    case status
    case sessions
    case report(String)
    case startSession(subject: String)
    case stopSession
    case recaptureBaseline
    case resetRange
    case cameraJPEG
    case live

    fileprivate var pathComponents: [String] {
        switch self {
        case .mobileHealth:
            ["api", "mobile", "health"]
        case .status:
            ["api", "status"]
        case .sessions:
            ["api", "sessions"]
        case let .report(sessionID):
            ["api", "sessions", sessionID]
        case .startSession:
            ["api", "session", "start"]
        case .stopSession:
            ["api", "session", "stop"]
        case .recaptureBaseline:
            ["api", "session", "baseline"]
        case .resetRange:
            ["api", "session", "range", "reset"]
        case .cameraJPEG:
            ["api", "camera.jpg"]
        case .live:
            ["api", "live"]
        }
    }

    fileprivate var method: String {
        switch self {
        case .startSession, .stopSession, .recaptureBaseline, .resetRange:
            "POST"
        default:
            "GET"
        }
    }

    fileprivate var isWebSocket: Bool {
        self == .live
    }
}


public struct RequestFactory: Sendable {
    public let connection: ServerConnection

    public init(connection: ServerConnection) {
        self.connection = connection
    }

    public func request(for endpoint: APIEndpoint) throws -> URLRequest {
        var url = connection.baseURL
        for component in endpoint.pathComponents {
            url.appendPathComponent(component)
        }
        if endpoint.isWebSocket {
            guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
                throw RequestFactoryError.invalidURL
            }
            components.scheme = components.scheme == "https" ? "wss" : "ws"
            guard let websocketURL = components.url else {
                throw RequestFactoryError.invalidURL
            }
            url = websocketURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method
        request.timeoutInterval = endpoint == .live ? 60 : 15
        request.setValue(
            "Bearer \(connection.token)",
            forHTTPHeaderField: "Authorization"
        )

        if case let .startSession(subject) = endpoint {
            request.httpBody = try JSONEncoder().encode(
                StartSessionBody(subject: subject)
            )
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        return request
    }
}


public enum RequestFactoryError: Error, Equatable, Sendable {
    case invalidURL
}


private struct StartSessionBody: Encodable {
    let subject: String
}
