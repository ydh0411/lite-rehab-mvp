import SwiftUI

struct LiveView: View {
    @ObservedObject var store: LiveStore
    let onOpenHistory: () -> Void

    init(store: LiveStore, onOpenHistory: @escaping () -> Void = {}) {
        self.store = store
        self.onOpenHistory = onOpenHistory
    }

    var body: some View {
        Group {
            switch store.flowState {
            case .preflight:
                PreflightView(store: store)
            case let .countdown(remaining):
                SessionCountdownView(remaining: remaining)
            case .active:
                ActiveTrainingView(store: store)
            case let .completed(summary):
                SessionCompletionView(
                    summary: summary,
                    onViewHistory: {
                        store.returnToPreflight()
                        onOpenHistory()
                    },
                    onDone: store.returnToPreflight
                )
            }
        }
        .background(Color(uiColor: .systemGroupedBackground))
        .navigationTitle("Live")
        .navigationBarTitleDisplayMode(.inline)
        .alert("LiteRehab", isPresented: Binding(
            get: { store.errorMessage != nil },
            set: { if !$0 { store.errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(store.errorMessage ?? "")
        }
        .onAppear { store.appear() }
        .onDisappear { store.disappear() }
    }
}
