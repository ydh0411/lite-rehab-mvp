import Foundation


public struct PairingPayload: Codable, Equatable, Sendable {
    public let version: Int
    public let name: String
    public let baseURL: URL
    public let pairingToken: String

    public init(
        version: Int,
        name: String,
        baseURL: URL,
        pairingToken: String
    ) {
        self.version = version
        self.name = name
        self.baseURL = baseURL
        self.pairingToken = pairingToken
    }

    public func validated() throws -> ServerConnection {
        guard version == 1 else {
            throw PairingValidationError.unsupportedVersion
        }
        guard let scheme = baseURL.scheme?.lowercased(),
              scheme == "http" || scheme == "https" else {
            throw PairingValidationError.unsupportedScheme
        }
        guard let host = baseURL.host, Self.isLocalHost(host) else {
            throw PairingValidationError.nonLocalHost
        }
        let token = pairingToken.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !token.isEmpty else {
            throw PairingValidationError.missingToken
        }
        return ServerConnection(
            name: name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                ? "LiteRehab Mac"
                : name.trimmingCharacters(in: .whitespacesAndNewlines),
            baseURL: baseURL,
            token: token
        )
    }

    private static func isLocalHost(_ rawHost: String) -> Bool {
        let host = rawHost.lowercased().trimmingCharacters(
            in: CharacterSet(charactersIn: "[]")
        )
        if host == "localhost" || host.hasSuffix(".local") {
            return true
        }
        if host == "::1" || host.hasPrefix("fe80:")
            || host.hasPrefix("fc") || host.hasPrefix("fd") {
            return true
        }

        let octets = host.split(separator: ".").compactMap { Int($0) }
        guard octets.count == 4, octets.allSatisfy({ 0...255 ~= $0 }) else {
            return false
        }
        return octets[0] == 10
            || octets[0] == 127
            || (octets[0] == 169 && octets[1] == 254)
            || (octets[0] == 172 && 16...31 ~= octets[1])
            || (octets[0] == 192 && octets[1] == 168)
    }

    private enum CodingKeys: String, CodingKey {
        case version
        case name
        case baseURL = "base_url"
        case pairingToken = "pairing_token"
    }
}


public struct ServerConnection: Codable, Equatable, Sendable {
    public let name: String
    public let baseURL: URL
    public let token: String

    public init(name: String, baseURL: URL, token: String) {
        self.name = name
        self.baseURL = baseURL
        self.token = token
    }
}


public enum PairingValidationError: Error, Equatable, LocalizedError, Sendable {
    case unsupportedVersion
    case unsupportedScheme
    case nonLocalHost
    case missingToken

    public var errorDescription: String? {
        switch self {
        case .unsupportedVersion:
            "This QR code uses an unsupported LiteRehab pairing version."
        case .unsupportedScheme:
            "The QR code contains an unsupported server address."
        case .nonLocalHost:
            "LiteRehab only connects to a Mac on the local network."
        case .missingToken:
            "The QR code does not contain a pairing token."
        }
    }
}
