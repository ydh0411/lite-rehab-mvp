import Foundation
import LiteRehabCore

protocol APIClientProtocol: AnyObject, Sendable {
    func health() async throws -> MobileHealth
    func status() async throws -> LiveSnapshot
    func sessions() async throws -> [SessionSummary]
    func report(sessionID: String) async throws -> SessionReport
    func startSession(subject: String) async throws -> SessionCommandResponse
    func stopSession() async throws -> SessionCommandResponse
    func recaptureBaseline() async throws
    func resetRange() async throws
}

actor APIClient: APIClientProtocol {
    let connection: ServerConnection
    private let session: URLSession

    init(connection: ServerConnection, session: URLSession = .shared) {
        self.connection = connection
        self.session = session
    }

    func health() async throws -> MobileHealth {
        try await send(.mobileHealth, as: MobileHealth.self)
    }

    func status() async throws -> LiveSnapshot {
        try await send(.status, as: LiveSnapshot.self)
    }

    func sessions() async throws -> [SessionSummary] {
        try await send(.sessions, as: [SessionSummary].self)
    }

    func report(sessionID: String) async throws -> SessionReport {
        try await send(.report(sessionID), as: SessionReport.self)
    }

    func startSession(subject: String) async throws -> SessionCommandResponse {
        try await send(.startSession(subject: subject), as: SessionCommandResponse.self)
    }

    func stopSession() async throws -> SessionCommandResponse {
        try await send(.stopSession, as: SessionCommandResponse.self)
    }

    func recaptureBaseline() async throws {
        _ = try await send(.recaptureBaseline, as: OKResponse.self)
    }

    func resetRange() async throws {
        _ = try await send(.resetRange, as: OKResponse.self)
    }

    private func send<Value: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        as type: Value.Type
    ) async throws -> Value {
        let request = try RequestFactory(connection: connection).request(for: endpoint)
        do {
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw NetworkError.invalidResponse
            }
            if httpResponse.statusCode == 401 {
                throw NetworkError.pairingExpired
            }
            guard (200..<300).contains(httpResponse.statusCode) else {
                let detail = (try? JSONDecoder.liteRehab.decode(APIErrorPayload.self, from: data).detail)
                    ?? "The Mac returned error \(httpResponse.statusCode)."
                throw NetworkError.server(detail)
            }
            do {
                return try JSONDecoder.liteRehab.decode(type, from: data)
            } catch {
                throw NetworkError.incompatibleData
            }
        } catch let error as NetworkError {
            throw error
        } catch {
            throw NetworkError.transport(error.localizedDescription)
        }
    }
}
