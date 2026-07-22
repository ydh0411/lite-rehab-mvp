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
    private let fetch: @Sendable (URLRequest) async throws -> (Data, URLResponse)
    private let sleep: @Sendable (Duration) async throws -> Void
    private var pollingTask: Task<Void, Never>?

    init(connection: ServerConnection, session: URLSession = .shared) {
        self.connection = connection
        self.fetch = { request in
            try await session.data(for: request)
        }
        self.sleep = { delay in
            try await Task.sleep(for: delay)
        }
    }

    init(
        connection: ServerConnection,
        fetch: @escaping @Sendable (URLRequest) async throws -> (Data, URLResponse),
        sleep: @escaping @Sendable (Duration) async throws -> Void
    ) {
        self.connection = connection
        self.fetch = fetch
        self.sleep = sleep
    }

    func start(
        onFrame: @escaping @MainActor (UIImage) -> Void,
        onError: @escaping @MainActor (Error) -> Void
    ) {
        stop()
        pollingTask = Task { [weak self] in
            guard let self else { return }
            var retryPolicy = CameraRetryPolicy()
            while !Task.isCancelled {
                let delay: Duration
                do {
                    let request = try RequestFactory(connection: connection).request(for: .cameraJPEG)
                    let (data, response) = try await fetch(request)
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
                    delay = retryPolicy.recordSuccess()
                } catch is CancellationError {
                    return
                } catch {
                    let failure = retryPolicy.recordFailure()
                    if failure.shouldReport {
                        onError(error)
                    }
                    delay = failure.delay
                }
                do {
                    try await sleep(delay)
                } catch {
                    return
                }
            }
        }
    }

    func stop() {
        pollingTask?.cancel()
        pollingTask = nil
    }
}
