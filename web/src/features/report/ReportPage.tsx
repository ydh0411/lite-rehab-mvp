import {
  AlertTriangle,
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Dumbbell,
  HeartPulse,
  Printer,
  Ruler,
} from "lucide-react"
import { Link } from "react-router-dom"

import type { SessionReport } from "../../app/api"
import { TrendChart } from "./ReportCharts"


type ReportPageProps = {
  report: SessionReport | null
  loading: boolean
  error: string
}


function formatDuration(seconds: number | null): string {
  if (seconds === null) return "Not available"
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m ${Math.round(seconds % 60)}s`
}


function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "Unknown date"
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date)
}


function displayExercise(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
}


export function ReportPage({ report, loading, error }: ReportPageProps) {
  if (loading) return <div className="page report-state">Loading session report…</div>
  if (error || report === null) {
    return <div className="page report-state error" role="alert">{error || "Session report unavailable"}</div>
  }

  const qualityTotal = Object.values(report.quality_counts).reduce((sum, count) => sum + count, 0)

  return (
    <section className="page report-page" aria-labelledby="report-heading">
      <header className="report-header">
        <div>
          <Link className="back-link no-print" to="/history"><ArrowLeft size={15} /> Session history</Link>
          <p className="eyebrow">Session report</p>
          <h1 id="report-heading">{report.subject}</h1>
          <div className="report-meta">
            <span><CalendarDays size={14} /> {formatDate(report.started_at)}</span>
            <span><Clock3 size={14} /> {formatDuration(report.duration_s)}</span>
            <span><Dumbbell size={14} /> {report.exercises.length ? report.exercises.map(displayExercise).join(", ") : "No exercise detected"}</span>
          </div>
        </div>
        <button className="button secondary no-print" type="button" onClick={() => window.print()}>
          <Printer size={15} /> Print / Save PDF
        </button>
      </header>

      <div className="report-metrics">
        <div><Dumbbell size={19} /><span>Valid repetitions</span><strong>{report.repetitions}</strong></div>
        <div><CheckCircle2 size={19} /><span>Good-form events</span><strong>{report.good_form_percent === null ? "Not available" : `${report.good_form_percent.toFixed(1)}%`}</strong></div>
        <div><Ruler size={19} /><span>Maximum observed ROM</span><strong>{report.max_rom_deg === null ? "Not available" : `${report.max_rom_deg.toFixed(1)}°`}</strong></div>
        <div><HeartPulse size={19} /><span>Average connected BPM</span><strong>{report.average_bpm === null ? "Not available" : report.average_bpm.toFixed(0)}</strong></div>
      </div>

      <div className="report-content-grid">
        <TrendChart title="Repetitions over time" description="Positive counter increments" data={report.repetition_series} unit="" />
        <TrendChart title="Range of motion" description="Peak-to-peak valid pose interval" data={report.rom_series} unit="°" color="#286f9b" />
        <TrendChart title="Connected BPM" description="Positive BPM values with leads connected" data={report.bpm_series} unit="" color="#b13b3b" />

        <article className="quality-distribution">
          <header><strong>Movement quality events</strong><span>{qualityTotal} recognized events</span></header>
          <div className="quality-bars">
            {Object.entries(report.quality_counts).length ? Object.entries(report.quality_counts).map(([quality, count]) => (
              <div key={quality}>
                <span>{displayExercise(quality)}</span>
                <div><i style={{ width: `${qualityTotal ? (count / qualityTotal) * 100 : 0}%` }} /></div>
                <strong>{count}</strong>
              </div>
            )) : <p>No recognized quality events.</p>}
          </div>
        </article>
      </div>

      <aside className="data-quality-note">
        <header><AlertTriangle size={17} /><strong>Data quality and interpretation</strong></header>
        <div className="completeness-row">
          <span>Serial {report.serial_completeness_percent.toFixed(0)}%</span>
          <span>Valid pose {report.pose_completeness_percent.toFixed(0)}%</span>
          <span>ECG connected {report.ecg_completeness_percent === null ? "Not recorded" : `${report.ecg_completeness_percent.toFixed(0)}%`}</span>
        </div>
        {report.warnings.length ? <ul>{report.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : <p>All recorded sources contain usable samples.</p>}
      </aside>

      <footer className="report-disclaimer">
        LiteRehab is an engineering prototype and not a medical device. This report is for classroom demonstration only and does not provide diagnosis, treatment advice, or a validated rehabilitation score.
      </footer>
    </section>
  )
}
