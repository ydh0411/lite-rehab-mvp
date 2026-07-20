import SpeziViews
import SwiftUI

struct PairingView: View {
    @ObservedObject var coordinator: PairingCoordinator
    @State private var showingScanner = false
    @State private var manualCode = ""
    @State private var viewState: ViewState = .idle

    var body: some View {
        NavigationStack {
            ZStack {
                LinearGradient(
                    colors: [Color.indigo.opacity(0.18), Color.cyan.opacity(0.08), .clear],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 26) {
                        Spacer(minLength: 44)
                        Image(systemName: "figure.strengthtraining.traditional")
                            .font(.system(size: 66, weight: .semibold))
                            .foregroundStyle(.indigo)
                            .accessibilityHidden(true)
                        VStack(spacing: 10) {
                            Text("LiteRehab")
                                .font(.largeTitle.bold())
                            Text("Your live rehabilitation companion")
                                .font(.headline)
                                .foregroundStyle(.secondary)
                            Text("Start the mobile dashboard on your Mac, then scan the QR code to connect securely over the same Wi-Fi network.")
                                .multilineTextAlignment(.center)
                                .foregroundStyle(.secondary)
                        }

                        Button {
                            showingScanner = true
                        } label: {
                            Label("Scan Mac QR Code", systemImage: "qrcode.viewfinder")
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 7)
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)

                        DisclosureGroup("Enter code manually") {
                            VStack(spacing: 12) {
                                TextEditor(text: $manualCode)
                                    .font(.caption.monospaced())
                                    .frame(minHeight: 100)
                                    .padding(6)
                                    .background(.background, in: RoundedRectangle(cornerRadius: 10))
                                    .overlay {
                                        RoundedRectangle(cornerRadius: 10)
                                            .stroke(.quaternary)
                                    }
                                Button("Connect") {
                                    connect(manualCode)
                                }
                                .buttonStyle(.bordered)
                                .disabled(manualCode.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                            }
                            .padding(.top, 10)
                        }
                        .tint(.primary)
                    }
                    .padding(.horizontal, 28)
                }

                if viewState == .processing {
                    Color.black.opacity(0.12).ignoresSafeArea()
                    ProgressView("Connecting…")
                        .padding(24)
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18))
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .sheet(isPresented: $showingScanner) {
                NavigationStack {
                    ZStack {
                        QRCodeScannerView(
                            onCode: { code in
                                showingScanner = false
                                connect(code)
                            },
                            onError: { error in
                                showingScanner = false
                                viewState = .error(AnyLocalizedError(error: error))
                            }
                        )
                        scannerGuide
                    }
                    .navigationTitle("Scan QR Code")
                    .navigationBarTitleDisplayMode(.inline)
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("Cancel") { showingScanner = false }
                        }
                    }
                }
            }
            .viewStateAlert(state: $viewState)
        }
    }

    private var scannerGuide: some View {
        VStack {
            Spacer()
            Image(systemName: "viewfinder")
                .font(.system(size: 220, weight: .ultraLight))
                .foregroundStyle(.white)
                .shadow(radius: 10)
            Spacer()
            Text("Point your iPhone at the QR code shown in the Mac terminal.")
                .font(.callout.weight(.medium))
                .multilineTextAlignment(.center)
                .foregroundStyle(.white)
                .padding()
                .background(.black.opacity(0.55), in: Capsule())
                .padding(.bottom, 32)
        }
        .padding()
        .allowsHitTesting(false)
    }

    private func connect(_ code: String) {
        viewState = .processing
        Task {
            do {
                try await coordinator.pair(using: code.trimmingCharacters(in: .whitespacesAndNewlines))
                viewState = .idle
            } catch {
                viewState = .error(AnyLocalizedError(error: error))
            }
        }
    }
}
