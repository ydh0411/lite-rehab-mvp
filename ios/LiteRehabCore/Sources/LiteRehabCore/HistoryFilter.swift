import Foundation


public func filterSessions(
    _ sessions: [SessionSummary],
    query: String,
    exercise: String?
) -> [SessionSummary] {
    let normalizedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        .lowercased()
    let normalizedExercise = exercise?.trimmingCharacters(
        in: .whitespacesAndNewlines
    )

    return sessions
        .filter { session in
            let matchesQuery = normalizedQuery.isEmpty
                || session.subject.lowercased().contains(normalizedQuery)
                || session.sessionID.lowercased().contains(normalizedQuery)
            let matchesExercise = normalizedExercise?.isEmpty != false
                || session.exercises.contains(normalizedExercise ?? "")
            return matchesQuery && matchesExercise
        }
        .sorted { lhs, rhs in
            lhs.startedAt > rhs.startedAt
        }
}
