import SwiftUI

struct HistoryView: View {
    @ObservedObject var store: HistoryStore
    let api: any APIClientProtocol

    var body: some View {
        List {
            overviewSection
            sessionsSection
        }
        .listStyle(.insetGrouped)
        .navigationTitle("History")
        .searchable(text: $store.query, prompt: "Participant or Session ID")
        .refreshable { await store.load() }
        .task {
            if case .idle = store.state { await store.load() }
        }
    }

    private var overviewSection: some View {
        Section("Overview") {
            HStack(spacing: 0) {
                overviewMetric(title: "Sessions", value: "\(store.sessions.count)")
                Divider().frame(height: 36)
                overviewMetric(title: "Total reps", value: "\(store.totalRepetitions)")
                Divider().frame(height: 36)
                overviewMetric(
                    title: "Minutes",
                    value: "\(Int((store.totalDuration / 60).rounded()))"
                )
            }

            Picker("Exercise", selection: $store.exercise) {
                Text("All exercises").tag(String?.none)
                ForEach(store.exercises, id: \.self) { exercise in
                    Text(exercise.capitalized).tag(Optional(exercise))
                }
            }
        }
    }

    @ViewBuilder
    private var sessionsSection: some View {
        Section("Sessions") {
            switch store.state {
            case .idle, .loading where store.sessions.isEmpty:
                HStack {
                    Spacer()
                    ProgressView("Loading sessions…")
                    Spacer()
                }
                .padding(.vertical, 36)
            case let .failed(message) where store.sessions.isEmpty:
                ContentUnavailableView {
                    Label("Could not load history", systemImage: "wifi.exclamationmark")
                } description: {
                    Text(message)
                } actions: {
                    Button("Try Again") { Task { await store.load() } }
                }
                .listRowBackground(Color.clear)
            default:
                if store.sessions.isEmpty {
                    ContentUnavailableView(
                        "No sessions yet",
                        systemImage: "clock.arrow.circlepath",
                        description: Text("Completed sessions will appear here.")
                    )
                    .listRowBackground(Color.clear)
                } else if store.filteredSessions.isEmpty {
                    ContentUnavailableView.search(text: store.query)
                        .listRowBackground(Color.clear)
                } else {
                    ForEach(store.filteredSessions) { session in
                        NavigationLink {
                            ReportView(store: ReportStore(api: api, sessionID: session.sessionID))
                        } label: {
                            SessionCard(session: session)
                        }
                    }
                }
            }
        }
    }

    private func overviewMetric(title: String, value: String) -> some View {
        VStack(spacing: 3) {
            Text(value)
                .font(.headline.monospacedDigit())
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .accessibilityElement(children: .combine)
    }
}
