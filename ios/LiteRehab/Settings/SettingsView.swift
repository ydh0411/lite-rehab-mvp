import LiteRehabCore
import SwiftUI

struct SettingsView: View {
    let connection: ServerConnection
    @ObservedObject var pairing: PairingCoordinator
    @State private var confirmingDisconnect = false
    @State private var errorMessage: String?

    var body: some View {
        Form {
            Section("Paired Mac") {
                LabeledContent("Status") {
                    Label("Connected", systemImage: "checkmark.circle.fill")
                        .foregroundStyle(LiteRehabStyle.success)
                }
                LabeledContent("Name", value: connection.name)
                LabeledContent("Local address", value: connection.baseURL.host ?? connection.baseURL.absoluteString)
                    .font(.caption)

                Button {
                    disconnect()
                } label: {
                    Label("Repair Connection", systemImage: "qrcode.viewfinder")
                }

                Button("Disconnect Mac", role: .destructive) {
                    confirmingDisconnect = true
                }
                .accessibilityIdentifier("disconnect-mac")
                .accessibilityHint("Removes the saved Mac address and secure access token")
            }

            Section("About LiteRehab") {
                LabeledContent("Version", value: appVersion)
                NavigationLink {
                    AcknowledgementsView()
                } label: {
                    Label("Open Source Acknowledgements", systemImage: "doc.text")
                }
            }

            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Label("Engineering prototype — not a medical device", systemImage: "exclamationmark.shield.fill")
                        .font(.headline)
                        .foregroundStyle(LiteRehabStyle.warning)
                    Text("For teaching and demonstration only. Do not use LiteRehab for diagnosis, monitoring, or treatment.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 4)
                .accessibilityElement(children: .contain)
            }
        }
        .navigationTitle("Settings")
        .confirmationDialog(
            "Disconnect from this Mac?",
            isPresented: $confirmingDisconnect,
            titleVisibility: .visible
        ) {
            Button("Disconnect Mac", role: .destructive) { disconnect() }
        } message: {
            Text("You will need to scan the Mac QR code again.")
        }
        .alert("Could Not Disconnect", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private var appVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "0.1.0"
    }

    private func disconnect() {
        do { try pairing.disconnect() }
        catch { errorMessage = error.localizedDescription }
    }
}
