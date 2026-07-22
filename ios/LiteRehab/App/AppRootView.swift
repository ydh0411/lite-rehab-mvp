import SwiftUI

struct AppRootView: View {
    @StateObject private var pairing = PairingCoordinator()

    var body: some View {
        Group {
            if let connection = pairing.connection {
                ConnectedAppView(
                    connection: connection,
                    pairing: pairing,
                    dependencies: AppDependencies.make(
                        connection: connection,
                        arguments: ProcessInfo.processInfo.arguments
                    )
                )
            } else {
                PairingView(coordinator: pairing)
            }
        }
    }
}
