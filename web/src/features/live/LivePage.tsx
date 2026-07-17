import {
  Activity,
  CameraOff,
  CheckCircle2,
  CircleGauge,
  Crosshair,
  HeartPulse,
  Radio,
  RefreshCw,
  RotateCcw,
  Square,
} from "lucide-react"
import { FormEvent, useState } from "react"

import type { LiveSnapshot } from "../../app/api"
import { EcgTrace } from "./EcgTrace"


export type ConnectionState = "connecting" | "connected" | "reconnecting"

type LivePageProps = {
  snapshot: LiveSnapshot
  connectionState: ConnectionState
  onStart: (subject: string) => Promise<void>
  onStop: () => Promise<void>
  onBaseline: () => Promise<void>
  onResetRange: () => Promise<void>
}


function displayExercise(value: string): string {
  const labels: Record<string, string> = {
    idle: "Ready",
    elbow_flexion: "Elbow flexion",
    forearm_rotation: "Forearm rotation",
    shoulder_abduction: "Shoulder abduction",
  }
  return labels[value] ?? value.replaceAll("_", " ")
}


function statusTone(value: string): "good" | "attention" | "neutral" {
  const normalized = value.toLowerCase()
  if (normalized.includes("connected") && !normalized.includes("not connected")) {
    return "good"
  }
  if (normalized.includes("reconnect") || normalized.includes("connecting")) {
    return "attention"
  }
  return "neutral"
}


function feedbackTone(feedback: string): string {
  const normalized = feedback.toLowerCase()
  if (normalized.includes("trunk")) return "danger"
  if (normalized.includes("slow") || normalized.includes("range")) return "attention"
  if (normalized.includes("good")) return "good"
  return "neutral"
}


function cameraAvailable(status: string): boolean {
  const normalized = status.toLowerCase()
  return normalized.startsWith("connected:")
}


export function LivePage({
  snapshot,
  connectionState,
  onStart,
  onStop,
  onBaseline,
  onResetRange,
}: LivePageProps) {
  const [subject, setSubject] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  async function start(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError("")
    try {
      await onStart(subject.trim())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start session")
    } finally {
      setBusy(false)
    }
  }

  async function stop() {
    if (!window.confirm("Stop and save this session?")) return
    setBusy(true)
    setError("")
    try {
      await onStop()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not stop session")
    } finally {
      setBusy(false)
    }
  }

  const hasCamera = cameraAvailable(snapshot.camera_status)
  const tone = feedbackTone(snapshot.feedback)

  return (
    <section className="page live-page" aria-labelledby="live-heading">
      <header className="live-header">
        <div>
          <div className="live-title-line">
            <p className="eyebrow">Current session</p>
            <span className={`connection-label ${connectionState}`}>
              <span aria-hidden="true" />
              {connectionState === "connected" ? "Live" : "Reconnecting"}
            </span>
          </div>
          <h1 id="live-heading">Live training</h1>
        </div>

        <div className="device-statuses" aria-label="Device status">
          <span className={`status-pill ${statusTone(snapshot.serial_status)}`}>
            <Radio size={14} /> Serial · {snapshot.serial_status}
          </span>
          <span className={`status-pill ${statusTone(snapshot.camera_status)}`}>
            <Activity size={14} /> Camera · {snapshot.camera_status}
          </span>
          <span className={`status-pill ${snapshot.mode === "Fusion" ? "good" : "attention"}`}>
            <Crosshair size={14} /> {snapshot.mode}
          </span>
        </div>

        <div className="session-actions">
          {snapshot.recording ? (
            <>
              <div className="recording-label">
                <span aria-hidden="true" />
                <div><small>Recording</small><strong>{snapshot.subject}</strong></div>
              </div>
              <button className="button secondary" type="button" onClick={stop} disabled={busy}>
                <Square size={15} fill="currentColor" /> Stop session
              </button>
            </>
          ) : (
            <form className="start-session-form" onSubmit={start}>
              <label>
                <span>Participant ID</span>
                <input
                  aria-label="Participant ID"
                  maxLength={64}
                  onChange={(event) => setSubject(event.target.value)}
                  placeholder="Demo-01"
                  required
                  value={subject}
                />
              </label>
              <button className="button primary" type="submit" disabled={busy || !subject.trim()}>
                <Activity size={16} /> Start session
              </button>
            </form>
          )}
        </div>
      </header>

      {error ? <p className="inline-error" role="alert">{error}</p> : null}

      <div className="live-grid">
        <article className="camera-panel">
          {hasCamera ? (
            <img src="/api/camera.mjpg" alt="Annotated rehabilitation camera feed" />
          ) : (
            <div className="camera-empty">
              <CameraOff size={28} />
              <div>
                <strong>Camera unavailable</strong>
                <p>IMU and ECG continue while the camera reconnects.</p>
              </div>
            </div>
          )}

          <div className={`feedback-banner ${tone}`} role="status" aria-label="Movement feedback">
            {tone === "good" ? <CheckCircle2 size={20} /> : <CircleGauge size={20} />}
            <div>
              <small>Movement feedback</small>
              <strong>{snapshot.feedback}</strong>
            </div>
          </div>
        </article>

        <aside className="metrics-rail" aria-label="Training metrics">
          <div className="exercise-summary">
            <span>Current exercise</span>
            <strong>{displayExercise(snapshot.exercise)}</strong>
            <small>{snapshot.source}</small>
          </div>

          <div className="repetition-metric" role="group" aria-label="Primary session metric">
            <span>Completed repetitions</span>
            <strong>{snapshot.repetitions}</strong>
          </div>

          <div className="metric-row">
            <div>
              <span>Range of motion</span>
              <strong>{snapshot.rom_deg === null ? "—" : `${snapshot.rom_deg.toFixed(1)}°`}</strong>
            </div>
            <div>
              <span>Affected side</span>
              <strong>{snapshot.side[0]?.toUpperCase() + snapshot.side.slice(1)}</strong>
            </div>
          </div>

          <div className="model-note">
            <span>Model status</span>
            <strong>{snapshot.confidence_text}</strong>
          </div>

          <div className="metric-controls">
            <button type="button" onClick={onBaseline}>
              <RefreshCw size={14} /> Recapture baseline
            </button>
            <button type="button" onClick={onResetRange}>
              <RotateCcw size={14} /> Reset range
            </button>
          </div>
        </aside>

        <article className="ecg-panel">
          <header>
            <div className="ecg-heading">
              <HeartPulse size={18} />
              <div><strong>ECG signal</strong><span>Demonstration only</span></div>
            </div>
            <div className={`ecg-reading${snapshot.ecg_connected ? " connected" : ""}`}>
              {snapshot.ecg_connected && snapshot.ecg_bpm !== null ? (
                <><strong>{snapshot.ecg_bpm.toFixed(0)}</strong><span>BPM</span></>
              ) : (
                <><strong>Leads off</strong><span>Check electrodes</span></>
              )}
            </div>
          </header>
          <EcgTrace connected={snapshot.ecg_connected} samples={snapshot.ecg_samples} />
        </article>
      </div>
    </section>
  )
}
