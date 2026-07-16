import { Navigate, Route, Routes } from "react-router-dom"

import { AppShell } from "./AppShell"

function LiveTrainingPlaceholder() {
  return (
    <section className="page placeholder-page" aria-labelledby="live-heading">
      <header className="page-header">
        <div>
          <p className="eyebrow">Current session</p>
          <h1 id="live-heading">Live training</h1>
          <p>Camera, movement quality, and ECG will appear when the local runtime connects.</p>
        </div>
      </header>
      <div className="placeholder-panel">
        <span className="placeholder-mark" aria-hidden="true">LR</span>
        <div>
          <strong>Waiting for LiteRehab hardware</strong>
          <p>The interface remains available while serial and camera sources reconnect.</p>
        </div>
      </div>
    </section>
  )
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
        <Route index element={<LiveTrainingPlaceholder />} />
        <Route path="history" element={<HistoryPlaceholder />} />
        <Route path="reports/:sessionId" element={<HistoryPlaceholder />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
