import Combine
import LiteRehabCore

@MainActor
final class ReportStore: ObservableObject {
    enum State: Equatable {
        case idle
        case loading
        case loaded
        case failed(String)
    }

    @Published private(set) var report: SessionReport?
    @Published private(set) var state: State = .idle
    private let api: any APIClientProtocol
    let sessionID: String

    init(api: any APIClientProtocol, sessionID: String) {
        self.api = api
        self.sessionID = sessionID
    }

    func load() async {
        state = .loading
        do {
            report = try await api.report(sessionID: sessionID)
            state = .loaded
        } catch {
            state = .failed(error.localizedDescription)
        }
    }
}
