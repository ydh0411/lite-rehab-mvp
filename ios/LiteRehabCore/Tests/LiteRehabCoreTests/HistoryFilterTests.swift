import Testing

@testable import LiteRehabCore


@Suite("Session history filtering")
struct HistoryFilterTests {
    @Test("searches subject and session ID case-insensitively")
    func searchesSubjectAndID() {
        let sessions = [
            session(id: "session-a", subject: "Demo-01", startedAt: "2026-07-19"),
            session(id: "session-b", subject: "Participant B", startedAt: "2026-07-20"),
        ]

        #expect(filterSessions(sessions, query: "DEMO-01", exercise: nil).map(\.sessionID) == ["session-a"])
        #expect(filterSessions(sessions, query: "SESSION-B", exercise: nil).map(\.sessionID) == ["session-b"])
    }

    @Test("filters exact exercise values")
    func filtersExercise() {
        let sessions = [
            session(
                id: "rotation",
                subject: "A",
                startedAt: "2026-07-19",
                exercises: ["forearm_rotation"]
            ),
            session(
                id: "elbow",
                subject: "B",
                startedAt: "2026-07-20",
                exercises: ["elbow_flexion"]
            ),
        ]

        let filtered = filterSessions(
            sessions,
            query: "",
            exercise: "elbow_flexion"
        )

        #expect(filtered.map(\.sessionID) == ["elbow"])
    }

    @Test("sorts newest sessions first")
    func sortsNewestFirst() {
        let sessions = [
            session(id: "older", subject: "A", startedAt: "2026-07-19T10:00:00Z"),
            session(id: "newer", subject: "B", startedAt: "2026-07-20T10:00:00Z"),
        ]

        #expect(filterSessions(sessions, query: "", exercise: nil).map(\.sessionID) == ["newer", "older"])
    }

    private func session(
        id: String,
        subject: String,
        startedAt: String,
        exercises: [String] = []
    ) -> SessionSummary {
        SessionSummary(
            sessionID: id,
            subject: subject,
            startedAt: startedAt,
            durationS: 10,
            repetitions: 2,
            exercises: exercises,
            goodFormPercent: 100,
            maxRomDeg: 80,
            serialCompletenessPercent: 100,
            poseCompletenessPercent: 100,
            ecgCompletenessPercent: 100,
            warnings: []
        )
    }
}
