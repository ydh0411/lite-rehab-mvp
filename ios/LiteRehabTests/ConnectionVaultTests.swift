import LiteRehabCore
@testable import LiteRehab
import XCTest

final class ConnectionVaultTests: XCTestCase {
    func testSaveAndLoadKeepTokenOutOfDefaults() throws {
        let defaults = try makeDefaults()
        let tokens = MemoryTokenStore()
        let vault = ConnectionVault(defaults: defaults, tokenStore: tokens)
        let connection = ServerConnection(
            name: "Lab Mac",
            baseURL: URL(string: "http://192.168.1.8:8000")!,
            token: "secret-token"
        )

        try vault.save(connection)

        XCTAssertEqual(try vault.load(), connection)
        XCTAssertEqual(tokens.token, "secret-token")
        XCTAssertFalse(defaults.dictionaryRepresentation().values.contains { value in
            String(describing: value).contains("secret-token")
        })
    }

    func testClearRemovesMetadataAndToken() throws {
        let defaults = try makeDefaults()
        let tokens = MemoryTokenStore()
        let vault = ConnectionVault(defaults: defaults, tokenStore: tokens)
        try vault.save(ServerConnection(
            name: "Lab Mac",
            baseURL: URL(string: "http://192.168.1.8:8000")!,
            token: "secret-token"
        ))

        try vault.clear()

        XCTAssertNil(try vault.load())
        XCTAssertNil(tokens.token)
    }

    private func makeDefaults() throws -> UserDefaults {
        let suite = "ConnectionVaultTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defaults.removePersistentDomain(forName: suite)
        return defaults
    }
}

private final class MemoryTokenStore: TokenStoring {
    var token: String?

    func loadToken() throws -> String? {
        token
    }

    func saveToken(_ token: String) throws {
        self.token = token
    }

    func deleteToken() throws {
        token = nil
    }
}
