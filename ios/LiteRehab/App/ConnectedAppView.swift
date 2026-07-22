import LiteRehabCore
import SwiftUI

private enum AppTab: Hashable {
    case live
    case history
}

struct ConnectedAppView: View {
    let connection: ServerConnection
    @ObservedObject var pairing: PairingCoordinator
    private let api: any APIClientProtocol
    @StateObject private var liveStore: LiveStore
    @StateObject private var historyStore: HistoryStore
    @State private var selectedTab: AppTab = .live
    @State private var showingSettings = false

    init(
        connection: ServerConnection,
        pairing: PairingCoordinator,
        dependencies: AppDependencies
    ) {
        self.connection = connection
        self.pairing = pairing
        self.api = dependencies.api
        _liveStore = StateObject(wrappedValue: LiveStore(
            api: dependencies.api,
            stream: dependencies.stream,
            camera: dependencies.camera,
            clock: dependencies.clock,
            haptics: dependencies.haptics
        ))
        _historyStore = StateObject(wrappedValue: HistoryStore(api: dependencies.api))
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            NavigationStack {
                LiveView(store: liveStore)
                    .toolbar { settingsToolbar }
            }
            .tabItem { Label("Live", systemImage: "waveform.path.ecg") }
            .tag(AppTab.live)

            NavigationStack {
                HistoryView(store: historyStore, api: api)
                    .toolbar { settingsToolbar }
            }
            .tabItem { Label("History", systemImage: "clock.arrow.circlepath") }
            .tag(AppTab.history)
        }
        .tint(.indigo)
        .sheet(isPresented: $showingSettings) {
            NavigationStack {
                SettingsView(connection: connection, pairing: pairing)
                    .toolbar {
                        ToolbarItem(placement: .confirmationAction) {
                            Button("Done") { showingSettings = false }
                        }
                    }
            }
        }
    }

    @ToolbarContentBuilder
    private var settingsToolbar: some ToolbarContent {
        ToolbarItem(placement: .topBarTrailing) {
            Button {
                showingSettings = true
            } label: {
                Image(systemName: "gearshape")
            }
            .accessibilityLabel("Open Settings")
            .accessibilityIdentifier("open-settings")
        }
    }
}
