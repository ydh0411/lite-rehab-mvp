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
