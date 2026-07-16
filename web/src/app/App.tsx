import { Navigate, Route, Routes } from "react-router-dom"

import { AppShell } from "./AppShell"
import { useLiveSnapshot } from "./useLiveSnapshot"
import { LivePage } from "../features/live/LivePage"

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

function HistoryPlaceholder() {
  return (
    <section className="page placeholder-page" aria-labelledby="history-heading">
      <header className="page-header">
        <div>
          <p className="eyebrow">Local records</p>
          <h1 id="history-heading">Session history</h1>
          <p>Recorded sessions stay on this computer and are summarized from CSV data.</p>
        </div>
      </header>
      <div className="placeholder-panel">
        <span className="placeholder-mark" aria-hidden="true">01</span>
        <div>
          <strong>No session selected</strong>
          <p>Completed sessions will be listed here with data-quality indicators.</p>
        </div>
      </div>
    </section>
  )
}

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<ConnectedLivePage />} />
        <Route path="history" element={<HistoryPlaceholder />} />
        <Route path="reports/:sessionId" element={<HistoryPlaceholder />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
