import Foundation
import Testing

@testable import LiteRehabCore


@Suite("FastAPI model contracts")
struct APIModelsTests {
    @Test("decodes a live snapshot from the FastAPI shape")
    func decodesLiveSnapshot() throws {
        let data = #"{"timestamp_s":1.5,"recording":false,"subject":"","exercise":"idle","repetitions":0,"feedback":"Ready","mode":"IMU-only","source":"rule fallback","side":"right","serial_status":"connected","camera_status":"connected: fixture","rom_deg":null,"confidence_text":"Model unavailable","model_confidence":null,"ecg_bpm":72.0,"ecg_connected":true,"ecg_samples":[101,102],"camera_frame_age_s":0.05}"#.data(using: .utf8)!

        let snapshot = try JSONDecoder.liteRehab.decode(
            LiveSnapshot.self,
            from: data
        )

        #expect(snapshot.timestampS == 1.5)
        #expect(snapshot.romDeg == nil)
        #expect(snapshot.ecgSamples == [101, 102])
        #expect(snapshot.cameraFrameAgeS == 0.05)
    }

    @Test("decodes session summary arrays and nullable measurements")
    func decodesSessionSummary() throws {
        let data = #"{"session_id":"demo-session","subject":"Demo-01","started_at":"2026-07-20T10:00:00+00:00","duration_s":42.5,"repetitions":3,"exercises":["elbow_flexion"],"good_form_percent":66.7,"max_rom_deg":81.2,"serial_completeness_percent":100.0,"pose_completeness_percent":95.0,"ecg_completeness_percent":null,"warnings":["ECG file not recorded"]}"#.data(using: .utf8)!

        let summary = try JSONDecoder.liteRehab.decode(
            SessionSummary.self,
            from: data
        )

        #expect(summary.sessionID == "demo-session")
        #expect(summary.exercises == ["elbow_flexion"])
        #expect(summary.ecgCompletenessPercent == nil)
        #expect(summary.warnings == ["ECG file not recorded"])
    }

    @Test("decodes report quality and time series")
    func decodesSessionReport() throws {
        let data = #"{"session_id":"demo-session","subject":"Demo-01","started_at":"2026-07-20T10:00:00+00:00","duration_s":42.5,"repetitions":3,"exercises":["elbow_flexion"],"quality_counts":{"ok":2,"too_fast":1},"good_form_percent":66.7,"max_rom_deg":81.2,"average_bpm":72.0,"serial_completeness_percent":100.0,"pose_completeness_percent":95.0,"ecg_completeness_percent":90.0,"warnings":[],"repetition_series":[{"t_s":1.0,"value":1.0}],"rom_series":[{"t_s":1.0,"value":35.0}],"bpm_series":[{"t_s":1.0,"value":72.0}]}"#.data(using: .utf8)!

        let report = try JSONDecoder.liteRehab.decode(
            SessionReport.self,
            from: data
        )

        #expect(report.qualityCounts["ok"] == 2)
        #expect(report.repetitionSeries == [SeriesPoint(tS: 1, value: 1)])
        #expect(report.averageBPM == 72)
    }
}
