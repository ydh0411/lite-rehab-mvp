import Foundation

enum NetworkError: LocalizedError, Equatable {
    case invalidResponse
    case pairingExpired
    case server(String)
    case incompatibleData
    case invalidImage
    case transport(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            "The Mac returned an invalid response."
        case .pairingExpired:
            "The connection code has expired. Rescan the QR code on your Mac."
        case let .server(detail):
            detail
        case .incompatibleData:
            "The Mac sent data this app version cannot read."
        case .invalidImage:
            "The camera response was not an image."
        case let .transport(message):
            message
        }
    }
}
