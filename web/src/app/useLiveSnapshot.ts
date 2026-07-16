import { useCallback, useEffect, useRef, useState } from "react"

import { requestJson, type LiveSnapshot } from "./api"
import type { ConnectionState } from "../features/live/LivePage"


export const initialSnapshot: LiveSnapshot = {
  timestamp_s: 0,
  recording: false,
  subject: "",
  exercise: "idle",
  repetitions: 0,
  feedback: "Ready",
  mode: "IMU-only",
  source: "rule fallback",
  side: "right",
  serial_status: "unavailable",
  camera_status: "unavailable",
  rom_deg: null,
  confidence_text: "Model unavailable",
  model_confidence: null,
  ecg_bpm: null,
  ecg_connected: false,
  ecg_samples: [],
  camera_frame_age_s: null,
}


export function useLiveSnapshot() {
  const [snapshot, setSnapshot] = useState<LiveSnapshot>(initialSnapshot)
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting")
  const retryRef = useRef<number | undefined>(undefined)

  useEffect(() => {
    if (typeof WebSocket === "undefined") {
      setConnectionState("reconnecting")
      return
    }
    let active = true
    let socket: WebSocket | undefined

    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
      socket = new WebSocket(`${protocol}//${window.location.host}/api/live`)
      socket.onopen = () => active && setConnectionState("connected")
      socket.onmessage = (event) => {
        if (!active) return
        setSnapshot(JSON.parse(event.data) as LiveSnapshot)
      }
      socket.onerror = () => socket?.close()
      socket.onclose = () => {
        if (!active) return
        setConnectionState("reconnecting")
        retryRef.current = window.setTimeout(connect, 1200)
      }
    }

    connect()
    return () => {
      active = false
      if (retryRef.current !== undefined) window.clearTimeout(retryRef.current)
      socket?.close()
    }
  }, [])

  const command = useCallback(async (path: string, body?: object) => {
    await requestJson(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  }, [])

  return {
    snapshot,
    connectionState,
    start: (subject: string) => command("/session/start", { subject }),
    stop: () => command("/session/stop"),
    baseline: () => command("/session/baseline"),
    resetRange: () => command("/session/range/reset"),
  }
}
