import {
  AlertTriangle,
  CalendarDays,
  ChevronRight,
  ClipboardList,
  Clock3,
  Dumbbell,
  Search,
} from "lucide-react"
import { useMemo, useState } from "react"
import { Link } from "react-router-dom"

import type { SessionSummary } from "../../app/api"
import { filterSessions } from "./filterSessions"


type HistoryPageProps = {
  sessions: readonly SessionSummary[]
  loading: boolean
  error: string
}


function formatDuration(seconds: number | null): string {
  if (seconds === null) return "Not available"
  const minutes = Math.floor(seconds / 60)
  const remainder = Math.round(seconds % 60)
  return `${minutes}:${remainder.toString().padStart(2, "0")}`
}


function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "Unknown date"
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}


function displayExercise(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
}


export function HistoryPage({ sessions, loading, error }: HistoryPageProps) {
  const [query, setQuery] = useState("")
  const [exercise, setExercise] = useState("all")
  const filtered = useMemo(
    () => filterSessions(sessions, { query, exercise }),
    [exercise, query, sessions],
  )
  const exercises = useMemo(
    () => [...new Set(sessions.flatMap((session) => session.exercises))].sort(),
    [sessions],
  )
  const totalRepetitions = sessions.reduce((sum, session) => sum + session.repetitions, 0)
  const durations = sessions.flatMap((session) => session.duration_s === null ? [] : [session.duration_s])
  const averageDuration = durations.length
    ? durations.reduce((sum, duration) => sum + duration, 0) / durations.length
    : null

  return (
    <section className="page history-page" aria-labelledby="history-heading">
      <header className="page-header history-header">
        <div>
          <p className="eyebrow">Local records</p>
          <h1 id="history-heading">Session history</h1>
          <p>Review locally recorded training sessions and open a traceable summary report.</p>
        </div>
      </header>

      <div className="history-summary" role="region" aria-label="Session overview">
        <div><ClipboardList size={18} /><span>Recorded sessions</span><strong>{sessions.length}</strong></div>
        <div><Dumbbell size={18} /><span>Valid repetitions</span><strong>{totalRepetitions}</strong></div>
        <div><Clock3 size={18} /><span>Average duration</span><strong>{formatDuration(averageDuration)}</strong></div>
        <div><CalendarDays size={18} /><span>Most recent</span><strong>{sessions[0] ? formatDate(sessions[0].started_at).split(",")[0] : "—"}</strong></div>
      </div>

      <article className="session-table-card">
        <header className="table-toolbar">
          <div>
            <strong>Recorded sessions</strong>
            <span>{filtered.length} shown</span>
          </div>
          <div className="table-filters">
            <label className="search-field">
              <Search size={15} />
              <span className="sr-only">Search sessions</span>
              <input
                aria-label="Search sessions"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search participant"
                value={query}
              />
            </label>
            <label>
              <span className="sr-only">Filter exercise</span>
              <select
                aria-label="Filter exercise"
                onChange={(event) => setExercise(event.target.value)}
                value={exercise}
              >
                <option value="all">All exercises</option>
                {exercises.map((item) => <option key={item} value={item}>{displayExercise(item)}</option>)}
              </select>
            </label>
          </div>
        </header>

        {loading ? <div className="table-state">Loading local sessions…</div> : null}
        {error ? <div className="table-state error" role="alert">{error}</div> : null}
        {!loading && !error && sessions.length === 0 ? (
          <div className="table-state empty">
            <ClipboardList size={24} />
            <strong>No recorded sessions yet</strong>
            <p>Start and stop a live training session to create the first local record.</p>
          </div>
        ) : null}
        {!loading && !error && sessions.length > 0 && filtered.length === 0 ? (
          <div className="table-state empty">
            <Search size={24} />
            <strong>No sessions match these filters</strong>
            <p>Try another participant ID or exercise.</p>
          </div>
        ) : null}
        {filtered.length > 0 ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Participant</th>
                  <th>Date</th>
                  <th>Exercise</th>
                  <th>Duration</th>
                  <th>Reps</th>
                  <th>Good form</th>
                  <th>Data quality</th>
                  <th><span className="sr-only">Report</span></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((session) => (
                  <tr key={session.session_id}>
                    <td><strong>{session.subject}</strong><small>{session.session_id}</small></td>
                    <td>{formatDate(session.started_at)}</td>
                    <td>{session.exercises.length ? session.exercises.map(displayExercise).join(", ") : "No exercise"}</td>
                    <td className="numeric">{formatDuration(session.duration_s)}</td>
                    <td className="numeric strong">{session.repetitions}</td>
                    <td className="numeric">{session.good_form_percent === null ? "—" : `${session.good_form_percent.toFixed(1)}%`}</td>
                    <td>
                      <span className={`quality-label${session.warnings.length ? " attention" : " good"}`}>
                        {session.warnings.length ? <AlertTriangle size={13} /> : null}
                        {session.warnings.length ? `${session.warnings.length} note${session.warnings.length > 1 ? "s" : ""}` : "Complete"}
                      </span>
                    </td>
                    <td>
                      <Link className="report-link" to={`/reports/${session.session_id}`}>
                        View report <ChevronRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </article>
    </section>
  )
}
