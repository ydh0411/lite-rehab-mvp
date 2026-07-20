import LiteRehabCore
import SwiftUI

struct LiveView: View {
    @StateObject var store: LiveStore
    @State private var showingStart = false
    @State private var confirmingStop = false

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                statusRow
                camera
                feedback
                repetitionCard
                metrics
                ecg
                secondaryActions
                Text("Engineering prototype · Demonstration only · Not for diagnosis or treatment.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }
            .padding()
            .padding(.bottom, 84)
        }
        .background(Color(uiColor: .secondarySystemBackground))
        .navigationTitle("Live Training")
        .safeAreaInset(edge: .bottom) {
            primaryAction
                .padding(.horizontal)
                .padding(.vertical, 10)
                .background(.ultraThinMaterial)
        }
        .sheet(isPresented: $showingStart) {
            StartSessionSheet { participantID in
                try await store.startSession(participantID: participantID)
            }
        }
        .confirmationDialog(
            "Stop this rehabilitation session?",
            isPresented: $confirmingStop,
            titleVisibility: .visible
        ) {
            Button("Stop Session", role: .destructive) {
                Task { await store.stopSession() }
            }
        }
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

    private var statusRow: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack {
                StatusBadge(
                    title: connectionLabel,
                    systemImage: connectionIcon,
                    color: connectionColor
                )
                StatusBadge(
                    title: "IMU: \(store.snapshot?.serialStatus.capitalized ?? "Waiting")",
                    systemImage: "gyroscope",
                    color: store.snapshot?.serialStatus == "connected" ? .green : .orange
                )
                StatusBadge(
                    title: "Camera: \(store.snapshot?.cameraStatus.capitalized ?? "Waiting")",
                    systemImage: "camera",
                    color: store.cameraImage == nil ? .orange : .green
                )
            }
        }
    }

    private var camera: some View {
        ZStack {
            Color.black
            if let image = store.cameraImage {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
            } else {
                VStack(spacing: 10) {
                    Image(systemName: "video.slash")
                        .font(.largeTitle)
                    Text(store.cameraError ?? "Waiting for camera")
                        .font(.callout)
                        .multilineTextAlignment(.center)
                }
                .foregroundStyle(.white.opacity(0.82))
                .padding()
            }
        }
        .aspectRatio(16 / 9, contentMode: .fit)
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .accessibilityLabel("Live rehabilitation camera")
    }

    private var feedback: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "waveform.path.ecg.rectangle")
                .foregroundStyle(.indigo)
            Text(store.snapshot?.feedback ?? "Waiting for live feedback from the Mac…")
                .font(.headline)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .liteRehabCard()
    }

    private var repetitionCard: some View {
        VStack(spacing: 5) {
            Text("REPETITIONS")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            Text("\(store.snapshot?.repetitions ?? 0)")
                .font(.system(size: 62, weight: .bold, design: .rounded))
                .foregroundStyle(.indigo)
        }
        .frame(maxWidth: .infinity)
        .liteRehabCard()
    }

    private var metrics: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            MetricCard(title: "Range of motion", value: romText, systemImage: "angle")
            MetricCard(title: "Exercise", value: store.snapshot?.exercise.capitalized ?? "—", systemImage: "figure.walk")
            MetricCard(title: "Side", value: store.snapshot?.side.capitalized ?? "—", systemImage: "arrow.left.and.right")
            MetricCard(title: "Model", value: store.snapshot?.confidenceText ?? "—", systemImage: "brain.head.profile")
        }
    }

    private var ecg: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("ECG", systemImage: "heart.fill")
                    .font(.headline)
                    .foregroundStyle(.red)
                Spacer()
                Text(store.snapshot?.ecgBPM.map { "\(Int($0.rounded())) BPM" } ?? "Not available")
                    .font(.headline.monospacedDigit())
            }
            ECGTraceView(samples: store.snapshot?.ecgSamples ?? [])
            Text("Demonstration only")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .liteRehabCard()
    }

    private var secondaryActions: some View {
        HStack {
            Button {
                Task { await store.recaptureBaseline() }
            } label: {
                Label("Baseline", systemImage: "scope")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            Button {
                Task { await store.resetRange() }
            } label: {
                Label("Reset Range", systemImage: "arrow.counterclockwise")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
        }
        .disabled(store.commandInProgress || !isConnected)
    }

    private var primaryAction: some View {
        Button {
            if store.snapshot?.recording == true { confirmingStop = true }
            else { showingStart = true }
        } label: {
            Label(
                store.snapshot?.recording == true ? "Stop Session" : "Start Session",
                systemImage: store.snapshot?.recording == true ? "stop.fill" : "play.fill"
            )
            .font(.headline)
            .frame(maxWidth: .infinity)
            .frame(minHeight: 48)
        }
        .buttonStyle(.borderedProminent)
        .tint(store.snapshot?.recording == true ? .red : .indigo)
        .disabled(store.commandInProgress || !isConnected)
    }

    private var isConnected: Bool {
        if case .connected = store.stream.state { return true }
        return false
    }

    private var connectionLabel: String {
        switch store.stream.state {
        case .idle: "Offline"
        case .connecting: "Connecting"
        case .connected: "Connected"
        case .reconnecting: "Reconnecting"
        case .failed: "Connection failed"
        }
    }

    private var connectionIcon: String {
        isConnected ? "wifi" : "wifi.exclamationmark"
    }

    private var connectionColor: Color {
        isConnected ? .green : .orange
    }

    private var romText: String {
        guard let rom = store.snapshot?.romDeg else { return "—" }
        return "\(Int(rom.rounded()))°"
    }
}
