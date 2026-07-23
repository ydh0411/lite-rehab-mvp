import Combine
import Foundation
import LiteRehabCore

enum LiveConnectionState: Equatable {
    case idle
    case connecting
    case connected
    case reconnecting(attempt: Int)
    case failed(NetworkError)
}

@MainActor
protocol LiveStreaming: AnyObject {
    var state: LiveConnectionState { get }
    func start(
        onState: @escaping @MainActor @Sendable (LiveConnectionState) -> Void,
        onSnapshot: @escaping @MainActor @Sendable (LiveSnapshot) -> Void
    )
    func stop()
}

@MainActor
final class LiveWebSocketClient: ObservableObject, LiveStreaming {
    @Published private(set) var state: LiveConnectionState = .idle
    private let connection: ServerConnection
    private let session: URLSession
    private var socket: URLSessionWebSocketTask?
    private var receiveTask: Task<Void, Never>?
    private var requestedStop = false
    private var consecutiveDecodeFailures = 0
    private var stateHandler: (@MainActor @Sendable (LiveConnectionState) -> Void)?

    init(connection: ServerConnection, session: URLSession = .shared) {
        self.connection = connection
        self.session = session
    }

    func start(
        onState: @escaping @MainActor @Sendable (LiveConnectionState) -> Void,
        onSnapshot: @escaping @MainActor @Sendable (LiveSnapshot) -> Void
    ) {
        stop()
        stateHandler = onState
        requestedStop = false
        publish(.connecting)
        receiveTask = Task { [weak self] in
            await self?.run(onSnapshot: onSnapshot)
        }
    }

    func stop() {
        requestedStop = true
        receiveTask?.cancel()
        receiveTask = nil
        socket?.cancel(with: .normalClosure, reason: nil)
        socket = nil
        publish(.idle)
        stateHandler = nil
    }

    private func run(onSnapshot: @escaping @MainActor @Sendable (LiveSnapshot) -> Void) async {
        var attempt = 0
        while !Task.isCancelled && !requestedStop {
            do {
                let request = try RequestFactory(connection: connection).request(for: .live)
                let task = session.webSocketTask(with: request)
                socket = task
                task.resume()
                publish(.connected)
                consecutiveDecodeFailures = 0
                while !Task.isCancelled && !requestedStop {
                    let message = try await task.receive()
                    let data: Data
                    switch message {
                    case let .data(value):
                        data = value
                    case let .string(value):
                        data = Data(value.utf8)
                    @unknown default:
                        continue
                    }
                    do {
                        let snapshot = try JSONDecoder.liteRehab.decode(LiveSnapshot.self, from: data)
                        attempt = 0
                        consecutiveDecodeFailures = 0
                        onSnapshot(snapshot)
                    } catch {
                        consecutiveDecodeFailures += 1
                        if consecutiveDecodeFailures >= 3 {
                            throw NetworkError.incompatibleData
                        }
                    }
                }
            } catch let error as NetworkError where error == .incompatibleData {
                publish(.failed(error))
                return
            } catch {
                if requestedStop || Task.isCancelled {
                    return
                }
                if socket?.closeCode.rawValue == 4401 {
                    publish(.failed(.pairingExpired))
                    return
                }
                attempt += 1
                publish(.reconnecting(attempt: attempt))
                let delay = min(8, 1 << min(attempt - 1, 3))
                try? await Task.sleep(for: .seconds(delay))
            }
        }
    }

    private func publish(_ newState: LiveConnectionState) {
        state = newState
        stateHandler?(newState)
    }
}
