import type { SessionSummary } from "../../app/api"


export type SessionFilters = {
  query: string
  exercise: string
}


export function filterSessions(
  sessions: readonly SessionSummary[],
  filters: SessionFilters,
): SessionSummary[] {
  const query = filters.query.trim().toLowerCase()
  return sessions
    .filter((session) => {
      const matchesQuery = !query || [session.subject, session.session_id]
        .some((value) => value.toLowerCase().includes(query))
      const matchesExercise = filters.exercise === "all"
        || session.exercises.includes(filters.exercise)
      return matchesQuery && matchesExercise
    })
    .sort((left, right) => right.started_at.localeCompare(left.started_at))
}
