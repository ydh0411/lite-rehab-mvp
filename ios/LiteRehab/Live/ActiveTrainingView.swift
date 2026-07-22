import SwiftUI

struct ActiveTrainingView: View {
    @ObservedObject var store: LiveStore
    @State private var confirmingFinish = false

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                sessionHeader
                if isReconnecting { reconnectingBanner }
                repetitionAndFeedback
                metrics
                camera
                technicalStatus
            }
            .padding()
            .padding(.bottom, 84)
        }
        .safeAreaInset(edge: .bottom) {
            Button(role: .destructive) {
                confirmingFinish = true
            } label: {
                Label("Finish Session", systemImage: "stop.fill")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .frame(minHeight: 48)
            }
            .buttonStyle(.borderedProminent)
            .tint(.red)
            .disabled(store.commandInProgress)
            .accessibilityIdentifier("finish-session")
            .padding(.horizontal)
            .padding(.vertical, 10)
            .background(.ultraThinMaterial)
        }
        .confirmationDialog(
            "Finish this rehabilitation session?",
            isPresented: $confirmingFinish,
            titleVisibility: .visible
        ) {
            Button("Finish Session", role: .destructive) {
                Task { await store.stopSession() }
            }
            Button("Keep Training", role: .cancel) {}
        } message: {
            Text("The Mac will save the full session report.")
        }
    }

    private var sessionHeader: some View {
        HStack(alignment: .center, spacing: 12) {
            ZStack {
                Circle().fill(LiteRehabStyle.success.opacity(0.14))
                Image(systemName: "figure.strengthtraining.traditional")
                    .foregroundStyle(LiteRehabStyle.success)
            }
            .frame(width: 48, height: 48)
            VStack(alignment: .leading, spacing: 3) {
                Text("Session in progress")
                    .font(.title2.bold())
                Text(participantText)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .liteRehabCard()
    }

    private var reconnectingBanner: some View {
        Label("Reconnecting to Mac…", systemImage: "wifi.exclamationmark")
            .font(.callout.weight(.semibold))
            .foregroundStyle(LiteRehabStyle.warning)
            .frame(maxWidth: .infinity, alignment: .leading)
            .liteRehabCard()
    }

    private var repetitionAndFeedback: some View {
        VStack(spacing: 18) {
            VStack(spacing: 2) {
                Text("Repetitions")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
                Text("\(store.snapshot?.repetitions ?? 0)")
                    .font(.system(size: 72, weight: .bold, design: .rounded))
                    .monospacedDigit()
                    .foregroundStyle(LiteRehabStyle.accent)
            }
            Divider()
            let feedback = FeedbackPresentation.make(raw: store.snapshot?.feedback)
            HStack(alignment: .top, spacing: 14) {
                Image(systemName: feedback.symbolName)
                    .font(.title2)
                    .foregroundStyle(feedbackColor(feedback.category))
                    .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 4) {
                    Text(feedback.title).font(.headline)
                    Text(feedback.guidance)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }
        }
        .liteRehabCard()
    }

    private var metrics: some View {
        HStack(spacing: 12) {
            MetricCard(title: "Range of motion", value: romText, systemImage: "angle")
            MetricCard(title: "Heart rate", value: bpmText, systemImage: "heart.fill", tint: .red)
        }
    }

    private var camera: some View {
        ZStack {
            Color.black
            if let image = store.cameraImage {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
            } else if cameraUnavailable {
                cameraPlaceholder(
                    title: "Camera temporarily unavailable",
                    detail: "Training continues while LiteRehab retries the wireless stream.",
                    symbol: "video.slash"
                )
            } else {
                cameraPlaceholder(
                    title: "Wireless camera connected",
                    detail: "Waiting for the next frame from the Mac.",
                    symbol: "video"
                )
            }
        }
        .aspectRatio(16 / 9, contentMode: .fit)
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        .accessibilityElement(children: .combine)
    }

    private var technicalStatus: some View {
        DisclosureGroup {
            VStack(alignment: .leading, spacing: 8) {
                LabeledContent("Motion sensor", value: store.snapshot?.serialStatus.capitalized ?? "Waiting")
                LabeledContent("Camera", value: store.snapshot?.cameraStatus.capitalized ?? "Waiting")
                LabeledContent("Data source", value: store.snapshot?.source.uppercased() ?? "—")
                LabeledContent("Model", value: store.snapshot?.confidenceText ?? "—")
            }
            .font(.footnote)
            .padding(.top, 10)
        } label: {
            Label("Technical status", systemImage: "wrench.and.screwdriver")
                .font(.headline)
        }
        .liteRehabCard()
        .accessibilityIdentifier("technical-status")
    }

    private var participantText: String {
        let subject = store.snapshot?.subject.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return subject.isEmpty ? store.participantID : subject
    }

    private var isReconnecting: Bool {
        if case .reconnecting = store.connectionState { return true }
        return false
    }

    private var cameraUnavailable: Bool {
        store.cameraError != nil || !["connected", "ready", "streaming"].contains(
            store.snapshot?.cameraStatus.lowercased() ?? ""
        )
    }

    private var romText: String {
        guard let value = store.snapshot?.romDeg else { return "—" }
        return "\(Int(value.rounded()))°"
    }

    private var bpmText: String {
        guard let value = store.snapshot?.ecgBPM else { return "—" }
        return "\(Int(value.rounded())) BPM"
    }

    private func cameraPlaceholder(title: String, detail: String, symbol: String) -> some View {
        VStack(spacing: 8) {
            Image(systemName: symbol).font(.title)
            Text(title).font(.headline)
            Text(detail)
                .font(.caption)
                .multilineTextAlignment(.center)
                .foregroundStyle(.white.opacity(0.72))
        }
        .foregroundStyle(.white)
        .padding()
    }

    private func feedbackColor(_ category: FeedbackCategory) -> Color {
        switch category {
        case .good: LiteRehabStyle.success
        case .neutral: LiteRehabStyle.accent
        case .slowDown, .increaseRange, .reduceCompensation: LiteRehabStyle.warning
        }
    }
}
