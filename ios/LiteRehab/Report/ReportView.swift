import LiteRehabCore
import SwiftUI

struct ReportView: View {
    @StateObject var store: ReportStore
    @State private var pdfURL: URL?
    @State private var pdfError: String?

    var body: some View {
        Group {
            if let report = store.report {
                reportContent(report)
            } else {
                loadingContent
            }
        }
        .background(Color(uiColor: .secondarySystemBackground))
        .navigationTitle("Session Report")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if let pdfURL {
                ShareLink(item: pdfURL, preview: SharePreview("LiteRehab Session Report")) {
                    Label("Share PDF", systemImage: "square.and.arrow.up")
                }
            } else if store.report != nil {
                Button {
                    createPDF()
                } label: {
                    Label("Create PDF", systemImage: "doc.richtext")
                }
            }
        }
        .task {
            if case .idle = store.state { await store.load() }
        }
        .alert("Could Not Create PDF", isPresented: Binding(
            get: { pdfError != nil },
            set: { if !$0 { pdfError = nil } }
        )) { Button("OK", role: .cancel) {} } message: { Text(pdfError ?? "") }
        .onDisappear { removePDF() }
    }

    private func reportContent(_ report: SessionReport) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                header(report)
                metrics(report)
                ReportChartsView(report: report)
                quality(report)
                completeness(report)
                warnings(report)
                Text("Engineering prototype for demonstration only. Not a medical device and not for diagnosis, monitoring, or treatment.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
                    .padding()
            }
            .padding()
        }
    }

    private func header(_ report: SessionReport) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(report.subject.isEmpty ? "Unnamed participant" : report.subject)
                .font(.title2.bold())
            Text(formattedDate(report.startedAt)).foregroundStyle(.secondary)
            Text(report.exercises.map { $0.capitalized }.joined(separator: " · "))
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.indigo)
            Text("Session \(report.sessionID)")
                .font(.caption.monospaced())
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .liteRehabCard()
    }

    private func metrics(_ report: SessionReport) -> some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            MetricCard(title: "Duration", value: ReportFormatting.duration(report.durationS), systemImage: "clock")
            MetricCard(title: "Repetitions", value: "\(report.repetitions)", systemImage: "repeat")
            MetricCard(title: "Good form", value: ReportFormatting.percent(report.goodFormPercent), systemImage: "checkmark.seal")
            MetricCard(title: "Max ROM", value: ReportFormatting.degrees(report.maxRomDeg), systemImage: "angle")
        }
    }

    private func quality(_ report: SessionReport) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Movement Quality").font(.headline)
            ForEach(report.qualityCounts.keys.sorted(), id: \.self) { key in
                HStack {
                    Text(key.replacingOccurrences(of: "_", with: " ").capitalized)
                    Spacer()
                    Text("\(report.qualityCounts[key] ?? 0)").bold().monospacedDigit()
                }
            }
        }
        .liteRehabCard()
    }

    private func completeness(_ report: SessionReport) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Data Completeness").font(.headline)
            HStack {
                StatusBadge(title: "IMU \(ReportFormatting.percent(report.serialCompletenessPercent))", systemImage: "gyroscope", color: .indigo)
                StatusBadge(title: "Pose \(ReportFormatting.percent(report.poseCompletenessPercent))", systemImage: "figure.walk", color: .cyan)
            }
            StatusBadge(title: "ECG \(ReportFormatting.ecgCompleteness(report.ecgCompletenessPercent))", systemImage: "heart", color: .red)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .liteRehabCard()
    }

    @ViewBuilder
    private func warnings(_ report: SessionReport) -> some View {
        if !report.warnings.isEmpty {
            VStack(alignment: .leading, spacing: 10) {
                Label("Data Warnings", systemImage: "exclamationmark.triangle.fill")
                    .font(.headline)
                    .foregroundStyle(.orange)
                ForEach(report.warnings, id: \.self) { warning in
                    Text("• \(warning)")
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .liteRehabCard()
        }
    }

    @ViewBuilder
    private var loadingContent: some View {
        switch store.state {
        case .idle, .loading:
            ProgressView("Loading report…")
        case let .failed(message):
            ContentUnavailableView {
                Label("Could Not Load Report", systemImage: "exclamationmark.triangle")
            } description: {
                Text(message)
            } actions: {
                Button("Try Again") { Task { await store.load() } }
            }
        case .loaded:
            ContentUnavailableView("Report Unavailable", systemImage: "doc.text.magnifyingglass")
        }
    }

    private func createPDF() {
        guard let report = store.report else { return }
        do {
            let data = try ReportPDFRenderer().render(report: report)
            let url = FileManager.default.temporaryDirectory
                .appendingPathComponent("LiteRehab-\(report.sessionID).pdf")
            try data.write(to: url, options: .atomic)
            pdfURL = url
        } catch {
            pdfError = error.localizedDescription
        }
    }

    private func removePDF() {
        if let pdfURL { try? FileManager.default.removeItem(at: pdfURL) }
        pdfURL = nil
    }
}
