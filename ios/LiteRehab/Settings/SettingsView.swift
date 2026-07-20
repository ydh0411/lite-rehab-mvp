import LiteRehabCore
import SwiftUI

struct SettingsView: View {
    let connection: ServerConnection
    @ObservedObject var pairing: PairingCoordinator
    @State private var confirmingClear = false
    @State private var errorMessage: String?

    var body: some View {
        Form {
            Section("Connection") {
                LabeledContent("Status") {
                    Label("Connected", systemImage: "checkmark.circle.fill")
                        .foregroundStyle(.green)
                }
                LabeledContent("Service", value: connection.name)
                LabeledContent("Address", value: connection.baseURL.absoluteString)
                    .font(.caption)
                LabeledContent("API version", value: "1")
                Button("Rescan QR Code") {
                    clearConnection()
                }
                Button("Clear Connection", role: .destructive) {
                    confirmingClear = true
                }
                .accessibilityHint("Removes the saved Mac address and secure access token")
            }

            Section("About") {
                LabeledContent("Version", value: appVersion)
                NavigationLink("Acknowledgements") {
                    AcknowledgementsView()
                }
            }

            Section("Important") {
                Label {
                    Text("LiteRehab is an engineering prototype for teaching and demonstration only. It is not a medical device and must not be used for diagnosis, monitoring, or treatment.")
                } icon: {
                    Image(systemName: "exclamationmark.shield.fill")
                        .foregroundStyle(.orange)
                }
            }
        }
        .navigationTitle("Settings")
        .confirmationDialog(
            "Clear the saved Mac connection?",
            isPresented: $confirmingClear,
            titleVisibility: .visible
        ) {
            Button("Clear Connection", role: .destructive) { clearConnection() }
        } message: {
            Text("You will need to scan the Mac QR code again.")
        }
        .alert("Could Not Clear Connection", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) { Button("OK", role: .cancel) {} } message: { Text(errorMessage ?? "") }
    }

    private var appVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "0.1.0"
    }

    private func clearConnection() {
        do { try pairing.disconnect() }
        catch { errorMessage = error.localizedDescription }
    }
}
