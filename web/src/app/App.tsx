import { lazy, Suspense, useEffect, useState } from "react"
import { Navigate, Route, Routes, useParams } from "react-router-dom"

import { AppShell } from "./AppShell"
import { requestJson, type SessionReport, type SessionSummary } from "./api"
import { useLiveSnapshot } from "./useLiveSnapshot"
import { LivePage } from "../features/live/LivePage"


const HistoryPage = lazy(() => import("../features/history/HistoryPage").then(
  (module) => ({ default: module.HistoryPage }),
))
const ReportPage = lazy(() => import("../features/report/ReportPage").then(
  (module) => ({ default: module.ReportPage }),
))

function ConnectedLivePage() {
  const live = useLiveSnapshot()
  return <LivePage
    snapshot={live.snapshot}
    connectionState={live.connectionState}
    onStart={live.start}
    onStop={live.stop}
    onBaseline={live.baseline}
    onResetRange={live.resetRange}
  />
}

function HistoryRoute() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    requestJson<SessionSummary[]>("/sessions")
      .then(setSessions)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Could not load sessions"))
      .finally(() => setLoading(false))
  }, [])

  return <HistoryPage sessions={sessions} loading={loading} error={error} />
}


function ReportRoute() {
  const { sessionId = "" } = useParams()
  const [report, setReport] = useState<SessionReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    requestJson<SessionReport>(`/sessions/${encodeURIComponent(sessionId)}`)
      .then(setReport)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Could not load report"))
      .finally(() => setLoading(false))
  }, [sessionId])

  return <ReportPage report={report} loading={loading} error={error} />
}

export function App() {
  return (
    <Suspense fallback={<div className="route-loading">Loading local view…</div>}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<ConnectedLivePage />} />
          <Route path="history" element={<HistoryRoute />} />
          <Route path="reports/:sessionId" element={<ReportRoute />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
