import LiteRehabCore
import SwiftUI

struct AppRootView: View {
    @StateObject private var pairing = PairingCoordinator()

    var body: some View {
        Group {
            if let connection = pairing.connection {
                DashboardTabView(connection: connection, pairing: pairing)
            } else {
                PairingView(coordinator: pairing)
            }
        }
    }
}

private struct DashboardTabView: View {
    let connection: LiteRehabCore.ServerConnection
    @ObservedObject var pairing: PairingCoordinator
    private let api: APIClient
    @StateObject private var liveStore: LiveStore
    @StateObject private var historyStore: HistoryStore

    init(connection: LiteRehabCore.ServerConnection, pairing: PairingCoordinator) {
        self.connection = connection
        self.pairing = pairing
        let api = APIClient(connection: connection)
        self.api = api
        _liveStore = StateObject(wrappedValue: LiveStore(
            api: api,
            stream: LiveWebSocketClient(connection: connection),
            camera: CameraFrameClient(connection: connection)
        ))
        _historyStore = StateObject(wrappedValue: HistoryStore(api: api))
    }

    var body: some View {
        TabView {
            NavigationStack {
                LiveView(store: liveStore)
            }
            .tabItem {
                Label("Live", systemImage: "waveform.path.ecg")
            }

            NavigationStack {
                HistoryView(store: historyStore, api: api)
            }
            .tabItem {
                Label("History", systemImage: "clock.arrow.circlepath")
            }

            NavigationStack {
                SettingsView(connection: connection, pairing: pairing)
            }
            .tabItem {
                Label("Settings", systemImage: "gearshape")
            }
        }
        .tint(.indigo)
    }
}
