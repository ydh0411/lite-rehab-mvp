import SwiftUI

struct HistoryView: View {
    @StateObject var store: HistoryStore
    let api: any APIClientProtocol

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 14) {
                overview
                exerciseFilter
                content
            }
            .padding()
        }
        .background(Color(uiColor: .secondarySystemBackground))
        .navigationTitle("History")
        .searchable(text: $store.query, prompt: "Participant or Session ID")
        .refreshable { await store.load() }
        .task {
            if case .idle = store.state { await store.load() }
        }
    }

    private var overview: some View {
        HStack(spacing: 10) {
            MetricCard(title: "Sessions", value: "\(store.sessions.count)", systemImage: "calendar")
            MetricCard(title: "Total reps", value: "\(store.totalRepetitions)", systemImage: "repeat")
            MetricCard(title: "Minutes", value: "\(Int((store.totalDuration / 60).rounded()))", systemImage: "clock")
        }
    }

    private var exerciseFilter: some View {
        Picker("Exercise", selection: $store.exercise) {
            Text("All exercises").tag(String?.none)
            ForEach(store.exercises, id: \.self) { exercise in
                Text(exercise.capitalized).tag(Optional(exercise))
            }
        }
        .pickerStyle(.menu)
        .frame(maxWidth: .infinity, alignment: .leading)
        .liteRehabCard()
    }

    @ViewBuilder
    private var content: some View {
        switch store.state {
        case .idle:
            ProgressView("Loading sessions…")
                .frame(maxWidth: .infinity)
                .padding(.vertical, 50)
        case .loading where store.sessions.isEmpty:
            ProgressView("Loading sessions…")
                .frame(maxWidth: .infinity)
                .padding(.vertical, 50)
        case let .failed(message) where store.sessions.isEmpty:
            ContentUnavailableView {
                Label("Could Not Load History", systemImage: "wifi.exclamationmark")
            } description: {
                Text(message)
            } actions: {
                Button("Try Again") { Task { await store.load() } }
            }
        default:
            if store.sessions.isEmpty {
                ContentUnavailableView(
                    "No Sessions Yet",
                    systemImage: "clock.arrow.circlepath",
                    description: Text("Completed sessions will appear here.")
                )
            } else if store.filteredSessions.isEmpty {
                ContentUnavailableView.search(text: store.query)
            } else {
                ForEach(store.filteredSessions) { session in
                    NavigationLink {
                        ReportView(store: ReportStore(api: api, sessionID: session.sessionID))
                    } label: {
                        SessionCard(session: session)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}
