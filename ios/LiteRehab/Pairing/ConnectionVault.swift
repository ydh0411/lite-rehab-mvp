import Foundation
import LiteRehabCore
import Security

protocol TokenStoring {
    func loadToken() throws -> String?
    func saveToken(_ token: String) throws
    func deleteToken() throws
}

struct KeychainTokenStore: TokenStoring {
    private let service = "edu.cuhk.literehab.mobile-access"
    private let account = "dashboard-token"

    func loadToken() throws -> String? {
        var query = baseQuery
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound {
            return nil
        }
        guard status == errSecSuccess,
              let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            throw KeychainError(status: status)
        }
        return token
    }

    func saveToken(_ token: String) throws {
        guard let data = token.data(using: .utf8) else {
            throw KeychainError(status: errSecParam)
        }
        let status: OSStatus
        if try loadToken() == nil {
            var query = baseQuery
            query[kSecValueData as String] = data
            status = SecItemAdd(query as CFDictionary, nil)
        } else {
            status = SecItemUpdate(
                baseQuery as CFDictionary,
                [kSecValueData as String: data] as CFDictionary
            )
        }
        guard status == errSecSuccess else {
            throw KeychainError(status: status)
        }
    }

    func deleteToken() throws {
        let status = SecItemDelete(baseQuery as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError(status: status)
        }
    }

    private var baseQuery: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]
    }
}

struct KeychainError: LocalizedError {
    let status: OSStatus

    var errorDescription: String? {
        SecCopyErrorMessageString(status, nil) as String? ?? "Keychain error \(status)"
    }
}

final class ConnectionVault {
    private enum Keys {
        static let name = "pairedServerName"
        static let baseURL = "pairedServerBaseURL"
    }

    private let defaults: UserDefaults
    private let tokenStore: any TokenStoring

    init(
        defaults: UserDefaults = .standard,
        tokenStore: any TokenStoring = KeychainTokenStore()
    ) {
        self.defaults = defaults
        self.tokenStore = tokenStore
    }

    func save(_ connection: ServerConnection) throws {
        try tokenStore.saveToken(connection.token)
        defaults.set(connection.name, forKey: Keys.name)
        defaults.set(connection.baseURL.absoluteString, forKey: Keys.baseURL)
    }

    func load() throws -> ServerConnection? {
        guard let name = defaults.string(forKey: Keys.name),
              let urlString = defaults.string(forKey: Keys.baseURL),
              let baseURL = URL(string: urlString),
              let token = try tokenStore.loadToken() else {
            return nil
        }
        return ServerConnection(name: name, baseURL: baseURL, token: token)
    }

    func clear() throws {
        try tokenStore.deleteToken()
        defaults.removeObject(forKey: Keys.name)
        defaults.removeObject(forKey: Keys.baseURL)
    }
}
