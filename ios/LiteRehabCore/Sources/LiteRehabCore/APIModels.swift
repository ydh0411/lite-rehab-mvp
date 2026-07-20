import Foundation


public extension JSONDecoder {
    static var liteRehab: JSONDecoder {
        JSONDecoder()
    }
}


public struct LiveSnapshot: Codable, Equatable, Sendable {
    public let timestampS: Double
    public let recording: Bool
    public let subject: String
    public let exercise: String
    public let repetitions: Int
    public let feedback: String
    public let mode: String
    public let source: String
    public let side: String
    public let serialStatus: String
    public let cameraStatus: String
    public let romDeg: Double?
    public let confidenceText: String
    public let modelConfidence: Double?
    public let ecgBPM: Double?
    public let ecgConnected: Bool
    public let ecgSamples: [Double]
    public let cameraFrameAgeS: Double?

    public init(
        timestampS: Double,
        recording: Bool,
        subject: String,
        exercise: String,
        repetitions: Int,
        feedback: String,
        mode: String,
        source: String,
        side: String,
        serialStatus: String,
        cameraStatus: String,
        romDeg: Double?,
        confidenceText: String,
        modelConfidence: Double?,
        ecgBPM: Double?,
        ecgConnected: Bool,
        ecgSamples: [Double],
        cameraFrameAgeS: Double?
    ) {
        self.timestampS = timestampS
        self.recording = recording
        self.subject = subject
        self.exercise = exercise
        self.repetitions = repetitions
        self.feedback = feedback
        self.mode = mode
        self.source = source
        self.side = side
        self.serialStatus = serialStatus
        self.cameraStatus = cameraStatus
        self.romDeg = romDeg
        self.confidenceText = confidenceText
        self.modelConfidence = modelConfidence
        self.ecgBPM = ecgBPM
        self.ecgConnected = ecgConnected
        self.ecgSamples = ecgSamples
        self.cameraFrameAgeS = cameraFrameAgeS
    }

    private enum CodingKeys: String, CodingKey {
        case timestampS = "timestamp_s"
        case recording
        case subject
        case exercise
        case repetitions
        case feedback
        case mode
        case source
        case side
        case serialStatus = "serial_status"
        case cameraStatus = "camera_status"
        case romDeg = "rom_deg"
        case confidenceText = "confidence_text"
        case modelConfidence = "model_confidence"
        case ecgBPM = "ecg_bpm"
        case ecgConnected = "ecg_connected"
        case ecgSamples = "ecg_samples"
        case cameraFrameAgeS = "camera_frame_age_s"
    }
}


public struct SeriesPoint: Codable, Equatable, Sendable, Identifiable {
    public let tS: Double
    public let value: Double

    public var id: Double { tS }

    public init(tS: Double, value: Double) {
        self.tS = tS
        self.value = value
    }

    private enum CodingKeys: String, CodingKey {
        case tS = "t_s"
        case value
    }
}


public struct SessionSummary: Codable, Equatable, Sendable, Identifiable {
    public let sessionID: String
    public let subject: String
    public let startedAt: String
    public let durationS: Double?
    public let repetitions: Int
    public let exercises: [String]
    public let goodFormPercent: Double?
    public let maxRomDeg: Double?
    public let serialCompletenessPercent: Double
    public let poseCompletenessPercent: Double
    public let ecgCompletenessPercent: Double?
    public let warnings: [String]

    public var id: String { sessionID }

    public init(
        sessionID: String,
        subject: String,
        startedAt: String,
        durationS: Double?,
        repetitions: Int,
        exercises: [String],
        goodFormPercent: Double?,
        maxRomDeg: Double?,
        serialCompletenessPercent: Double,
        poseCompletenessPercent: Double,
        ecgCompletenessPercent: Double?,
        warnings: [String]
    ) {
        self.sessionID = sessionID
        self.subject = subject
        self.startedAt = startedAt
        self.durationS = durationS
        self.repetitions = repetitions
        self.exercises = exercises
        self.goodFormPercent = goodFormPercent
        self.maxRomDeg = maxRomDeg
        self.serialCompletenessPercent = serialCompletenessPercent
        self.poseCompletenessPercent = poseCompletenessPercent
        self.ecgCompletenessPercent = ecgCompletenessPercent
        self.warnings = warnings
    }

    private enum CodingKeys: String, CodingKey {
        case sessionID = "session_id"
        case subject
        case startedAt = "started_at"
        case durationS = "duration_s"
        case repetitions
        case exercises
        case goodFormPercent = "good_form_percent"
        case maxRomDeg = "max_rom_deg"
        case serialCompletenessPercent = "serial_completeness_percent"
        case poseCompletenessPercent = "pose_completeness_percent"
        case ecgCompletenessPercent = "ecg_completeness_percent"
        case warnings
    }
}


public struct SessionReport: Codable, Equatable, Sendable, Identifiable {
    public let sessionID: String
    public let subject: String
    public let startedAt: String
    public let durationS: Double?
    public let repetitions: Int
    public let exercises: [String]
    public let qualityCounts: [String: Int]
    public let goodFormPercent: Double?
    public let maxRomDeg: Double?
    public let averageBPM: Double?
    public let serialCompletenessPercent: Double
    public let poseCompletenessPercent: Double
    public let ecgCompletenessPercent: Double?
    public let warnings: [String]
    public let repetitionSeries: [SeriesPoint]
    public let romSeries: [SeriesPoint]
    public let bpmSeries: [SeriesPoint]

    public var id: String { sessionID }

    public init(
        sessionID: String,
        subject: String,
        startedAt: String,
        durationS: Double?,
        repetitions: Int,
        exercises: [String],
        qualityCounts: [String: Int],
        goodFormPercent: Double?,
        maxRomDeg: Double?,
        averageBPM: Double?,
        serialCompletenessPercent: Double,
        poseCompletenessPercent: Double,
        ecgCompletenessPercent: Double?,
        warnings: [String],
        repetitionSeries: [SeriesPoint],
        romSeries: [SeriesPoint],
        bpmSeries: [SeriesPoint]
    ) {
        self.sessionID = sessionID
        self.subject = subject
        self.startedAt = startedAt
        self.durationS = durationS
        self.repetitions = repetitions
        self.exercises = exercises
        self.qualityCounts = qualityCounts
        self.goodFormPercent = goodFormPercent
        self.maxRomDeg = maxRomDeg
        self.averageBPM = averageBPM
        self.serialCompletenessPercent = serialCompletenessPercent
        self.poseCompletenessPercent = poseCompletenessPercent
        self.ecgCompletenessPercent = ecgCompletenessPercent
        self.warnings = warnings
        self.repetitionSeries = repetitionSeries
        self.romSeries = romSeries
        self.bpmSeries = bpmSeries
    }

    private enum CodingKeys: String, CodingKey {
        case sessionID = "session_id"
        case subject
        case startedAt = "started_at"
        case durationS = "duration_s"
        case repetitions
        case exercises
        case qualityCounts = "quality_counts"
        case goodFormPercent = "good_form_percent"
        case maxRomDeg = "max_rom_deg"
        case averageBPM = "average_bpm"
        case serialCompletenessPercent = "serial_completeness_percent"
        case poseCompletenessPercent = "pose_completeness_percent"
        case ecgCompletenessPercent = "ecg_completeness_percent"
        case warnings
        case repetitionSeries = "repetition_series"
        case romSeries = "rom_series"
        case bpmSeries = "bpm_series"
    }
}


public struct MobileHealth: Codable, Equatable, Sendable {
    public let service: String
    public let apiVersion: Int

    public init(service: String, apiVersion: Int) {
        self.service = service
        self.apiVersion = apiVersion
    }

    private enum CodingKeys: String, CodingKey {
        case service
        case apiVersion = "api_version"
    }
}


public struct APIErrorPayload: Codable, Equatable, Sendable {
    public let detail: String

    public init(detail: String) {
        self.detail = detail
    }
}


public struct SessionCommandResponse: Codable, Equatable, Sendable {
    public let recording: Bool
    public let subject: String

    public init(recording: Bool, subject: String) {
        self.recording = recording
        self.subject = subject
    }
}


public struct OKResponse: Codable, Equatable, Sendable {
    public let ok: Bool

    public init(ok: Bool) {
        self.ok = ok
    }
}
