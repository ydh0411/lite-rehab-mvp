import Foundation
import Testing

@testable import LiteRehabCore


@Suite("Pairing payload validation")
struct PairingTests {
    @Test("decodes the compact Mac QR payload")
    func decodesPairingPayload() throws {
        let data = #"{"version":1,"name":"LiteRehab Mac","base_url":"http://192.168.1.8:8000","pairing_token":"secret-token"}"#.data(using: .utf8)!

        let payload = try JSONDecoder().decode(PairingPayload.self, from: data)
        let connection = try payload.validated()

        #expect(connection.name == "LiteRehab Mac")
        #expect(connection.baseURL.absoluteString == "http://192.168.1.8:8000")
        #expect(connection.token == "secret-token")
    }

    @Test("accepts common private and local hosts", arguments: [
        "http://10.0.0.2:8000",
        "http://172.16.4.2:8000",
        "http://192.168.10.2:8000",
        "http://localhost:8000",
        "http://literehab.local:8000",
        "http://[fe80::1]:8000",
    ])
    func acceptsLocalHosts(address: String) throws {
        let payload = PairingPayload(
            version: 1,
            name: "LiteRehab Mac",
            baseURL: URL(string: address)!,
            pairingToken: "secret-token"
        )

        #expect(throws: Never.self) {
            _ = try payload.validated()
        }
    }

    @Test("rejects an unsupported pairing version")
    func rejectsUnsupportedVersion() {
        #expect(throws: PairingValidationError.unsupportedVersion) {
            _ = try payload(version: 2).validated()
        }
    }

    @Test("rejects a public internet host")
    func rejectsPublicHost() {
        #expect(throws: PairingValidationError.nonLocalHost) {
            _ = try payload(baseURL: URL(string: "https://example.com")!).validated()
        }
    }

    @Test("rejects a missing token")
    func rejectsMissingToken() {
        #expect(throws: PairingValidationError.missingToken) {
            _ = try payload(pairingToken: "   ").validated()
        }
    }

    @Test("rejects unsupported URL schemes")
    func rejectsUnsupportedScheme() {
        #expect(throws: PairingValidationError.unsupportedScheme) {
            _ = try payload(baseURL: URL(string: "ftp://192.168.1.8")!).validated()
        }
    }

    private func payload(
        version: Int = 1,
        baseURL: URL = URL(string: "http://192.168.1.8:8000")!,
        pairingToken: String = "secret-token"
    ) -> PairingPayload {
        PairingPayload(
            version: version,
            name: "LiteRehab Mac",
            baseURL: baseURL,
            pairingToken: pairingToken
        )
    }
}
