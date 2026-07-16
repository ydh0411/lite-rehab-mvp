export const API_BASE = "/api"

export type ApiError = {
  detail: string
}

export type LiveSnapshot = {
  timestamp_s: number
  recording: boolean
  subject: string
  exercise: string
  repetitions: number
  feedback: string
  mode: string
  source: string
  side: string
  serial_status: string
  camera_status: string
  rom_deg: number | null
  confidence_text: string
  model_confidence: number | null
  ecg_bpm: number | null
  ecg_connected: boolean
  ecg_samples: readonly number[]
  camera_frame_age_s: number | null
}

export type SeriesPoint = {
  t_s: number
  value: number
}

export type SessionSummary = {
  session_id: string
  subject: string
  started_at: string
  duration_s: number | null
  repetitions: number
  exercises: readonly string[]
  good_form_percent: number | null
  max_rom_deg: number | null
  serial_completeness_percent: number
  pose_completeness_percent: number
  ecg_completeness_percent: number | null
  warnings: readonly string[]
}

export type SessionReport = SessionSummary & {
  quality_counts: Record<string, number>
  average_bpm: number | null
  repetition_series: readonly SeriesPoint[]
  rom_series: readonly SeriesPoint[]
  bpm_series: readonly SeriesPoint[]
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({
      detail: `Request failed (${response.status})`,
    }))) as ApiError
    throw new Error(payload.detail)
  }
  return response.json() as Promise<T>
}
