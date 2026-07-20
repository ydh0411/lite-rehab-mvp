import Foundation
import LiteRehabCore
import UIKit

@MainActor
protocol CameraFrameLoading: AnyObject {
    func start(
        onFrame: @escaping @MainActor (UIImage) -> Void,
        onError: @escaping @MainActor (Error) -> Void
    )
    func stop()
}

@MainActor
final class CameraFrameClient: CameraFrameLoading {
    private let connection: ServerConnection
    private let session: URLSession
    private var pollingTask: Task<Void, Never>?

    init(connection: ServerConnection, session: URLSession = .shared) {
        self.connection = connection
        self.session = session
    }

    func start(
        onFrame: @escaping @MainActor (UIImage) -> Void,
        onError: @escaping @MainActor (Error) -> Void
    ) {
        stop()
        pollingTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                do {
                    let request = try RequestFactory(connection: connection).request(for: .cameraJPEG)
                    let (data, response) = try await session.data(for: request)
                    guard let httpResponse = response as? HTTPURLResponse else {
                        throw NetworkError.invalidResponse
                    }
                    guard httpResponse.statusCode != 401 else {
                        throw NetworkError.pairingExpired
                    }
                    guard (200..<300).contains(httpResponse.statusCode),
                          httpResponse.mimeType?.hasPrefix("image/") == true,
                          let image = UIImage(data: data) else {
                        throw NetworkError.invalidImage
                    }
                    onFrame(image)
                } catch is CancellationError {
                    return
                } catch {
                    onError(error)
                }
                try? await Task.sleep(for: .milliseconds(125))
            }
        }
    }

    func stop() {
        pollingTask?.cancel()
        pollingTask = nil
    }
}
