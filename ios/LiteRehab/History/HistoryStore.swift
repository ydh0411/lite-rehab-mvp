import Combine
import LiteRehabCore

@MainActor
final class HistoryStore: ObservableObject {
    enum State: Equatable {
        case idle
        case loading
        case loaded
        case failed(String)
    }

    @Published private(set) var sessions: [SessionSummary] = []
    @Published private(set) var state: State = .idle
    @Published var query = ""
    @Published var exercise: String?
    private let api: any APIClientProtocol

    init(api: any APIClientProtocol) {
        self.api = api
    }

    var filteredSessions: [SessionSummary] {
        filterSessions(sessions, query: query, exercise: exercise)
    }

    var exercises: [String] {
        Array(Set(sessions.flatMap(\.exercises))).sorted()
    }

    var totalRepetitions: Int {
        sessions.reduce(0) { $0 + $1.repetitions }
    }

    var totalDuration: Double {
        sessions.compactMap(\.durationS).reduce(0, +)
    }

    func load() async {
        guard state != .loading else { return }
        state = .loading
        do {
            sessions = try await api.sessions()
            state = .loaded
        } catch {
            state = .failed(error.localizedDescription)
        }
    }
}
