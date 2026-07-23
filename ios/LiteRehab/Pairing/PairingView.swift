import SpeziOnboarding
import SpeziViews
import SwiftUI

struct PairingView: View {
    @ObservedObject var coordinator: PairingCoordinator
    @State private var showingScanner = false
    @State private var manualCode = ""
    @State private var viewState: ViewState = .idle

    var body: some View {
        NavigationStack {
            OnboardingView {
                OnboardingTitleView(
                    title: "Guided rehabilitation, connected to your Mac",
                    subtitle: "Follow a clear setup, training, and review flow on your iPhone"
                )
            } content: {
                VStack(spacing: 24) {
                    OnboardingInformationView(areas: pairingAreas)
                    VStack(spacing: 14) {
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
                        Text("Engineering prototype — not a medical device")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                }
            } footer: {
                OnboardingActionsView("Pair with Mac", viewState: $viewState) {
                    showingScanner = true
                }
            }
            .padding(.top, 16)
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

    private var pairingAreas: [OnboardingInformationView.Area] {
        [
            OnboardingInformationView.Area(
                icon: { Image(systemName: "qrcode.viewfinder").accessibilityHidden(true) },
                title: "Pair once",
                description: "Scan the QR code shown by LiteRehab on your Mac."
            ),
            OnboardingInformationView.Area(
                icon: { Image(systemName: "iphone.and.arrow.forward").accessibilityHidden(true) },
                title: "Stay synchronized",
                description: "Your iPhone and Mac show the same live session state."
            ),
            OnboardingInformationView.Area(
                icon: { Image(systemName: "lock.shield").accessibilityHidden(true) },
                title: "Local network only",
                description: "Session data stays on your trusted local network."
            )
        ]
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
