import Combine
import Foundation
import LiteRehabCore

enum PairingError: LocalizedError {
    case invalidCode
    case incompatibleServer
    case rejected

    var errorDescription: String? {
        switch self {
        case .invalidCode:
            "Invalid pairing code"
        case .incompatibleServer:
            "This Mac is running an incompatible LiteRehab API."
        case .rejected:
            "The Mac rejected this pairing code. Start the mobile dashboard again and scan the new code."
        }
    }
}

@MainActor
final class PairingCoordinator: ObservableObject {
    @Published private(set) var connection: ServerConnection?
    private let vault: ConnectionVault
    private let session: URLSession

    init(
        vault: ConnectionVault = ConnectionVault(),
        session: URLSession = .shared
    ) {
        self.vault = vault
        self.session = session
        if ProcessInfo.processInfo.arguments.contains("-fixture-paired") {
            self.connection = ServerConnection(
                name: "Fixture Mac",
                baseURL: URL(string: "http://127.0.0.1:8000")!,
                token: "fixture-token"
            )
        } else {
            self.connection = try? vault.load()
        }
    }

    func pair(using code: String) async throws {
        guard let data = code.data(using: .utf8) else {
            throw PairingError.invalidCode
        }
        let payload: PairingPayload
        do {
            payload = try JSONDecoder.liteRehab.decode(PairingPayload.self, from: data)
        } catch {
            throw PairingError.invalidCode
        }
        let candidate = try payload.validated()
        let request = try RequestFactory(connection: candidate).request(for: .mobileHealth)
        let (responseData, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw PairingError.rejected
        }
        guard httpResponse.statusCode == 200 else {
            throw PairingError.rejected
        }
        let health = try JSONDecoder.liteRehab.decode(MobileHealth.self, from: responseData)
        guard health.apiVersion == 1 else {
            throw PairingError.incompatibleServer
        }
        try vault.save(candidate)
        connection = candidate
    }

    func disconnect() throws {
        try vault.clear()
        connection = nil
    }
}
