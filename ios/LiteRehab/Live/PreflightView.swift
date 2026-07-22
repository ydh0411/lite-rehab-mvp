import SwiftUI

struct PreflightView: View {
    @ObservedObject var store: LiveStore
    @State private var showingDegradedConfirmation = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Ready for your session?")
                        .font(.largeTitle.bold())
                    Text("Confirm the participant and connected equipment before training begins.")
                        .font(.body)
                        .foregroundStyle(.secondary)
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text("Participant")
                        .font(.headline)
                    TextField("Participant ID", text: $store.participantID)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                        .submitLabel(.done)
                        .padding(14)
                        .background(.background, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                        .overlay {
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .stroke(.quaternary)
                        }
                        .accessibilityIdentifier("participant-id")
                }

                HardwareStatusSection(readiness: store.readiness)

                if !isConnected {
                    Button {
                        store.appear()
                    } label: {
                        Label("Try Mac Connection Again", systemImage: "arrow.clockwise")
                    }
                    .buttonStyle(.bordered)
                }

                Text("Required equipment must be connected. Camera, ECG, and form feedback can be skipped after confirmation.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
            .padding()
            .padding(.bottom, 84)
        }
        .safeAreaInset(edge: .bottom) {
            Button {
                startTapped()
            } label: {
                Label("Start Session", systemImage: "play.fill")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .frame(minHeight: 48)
            }
            .buttonStyle(.borderedProminent)
            .disabled(store.commandInProgress || !store.readiness.blockingChecks.isEmpty)
            .accessibilityIdentifier("start-session")
            .padding(.horizontal)
            .padding(.vertical, 10)
            .background(.ultraThinMaterial)
        }
        .alert("Some features are unavailable", isPresented: $showingDegradedConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Start Anyway") {
                Task { await store.beginSession(allowDegraded: true) }
            }
            .accessibilityIdentifier("start-anyway")
        } message: {
            Text(optionalUnavailableDescription)
        }
    }

    private var isConnected: Bool {
        if case .connected = store.connectionState { return true }
        return false
    }

    private var optionalUnavailableDescription: String {
        let names = store.readiness.unavailableOptionalChecks.map(\.title)
        return "Continue without \(names.joined(separator: ", "))? Core motion tracking will remain available."
    }

    private func startTapped() {
        if store.readiness.canStartDegraded {
            showingDegradedConfirmation = true
        } else {
            Task { await store.beginSession() }
        }
    }
}
