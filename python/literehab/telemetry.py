from __future__ import annotations

from dataclasses import dataclass
import math


VALID_STATES = {"idle", "forearm_rotation", "elbow_flexion"}
VALID_QUALITIES = {"none", "ok", "too_fast", "insufficient_range"}


@dataclass(frozen=True)
class TelemetrySample:
    timestamp_ms: int
    accel_g: tuple[float, float, float]
    gyro_dps: tuple[float, float, float]
    state: str
    rep_count: int
    quality: str


@dataclass(frozen=True)
class EcgTelemetrySample:
    timestamp_ms: int
    raw_adc: int
    bpm: float
    leads_connected: bool
    beat: bool
    high_bpm_alert: bool

    @property
    def rapid_change(self) -> bool:
        """Compatibility alias for callers using the previous event name."""
        return self.high_bpm_alert


def parse_telemetry_line(line: str) -> TelemetrySample | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    fields = line.split(",")
    if len(fields) != 11 or fields[0] != "IMU":
        return None
    try:
        timestamp = int(fields[1])
        accel = tuple(float(value) for value in fields[2:5])
        gyro = tuple(float(value) for value in fields[5:8])
        state = fields[8]
        reps = int(fields[9])
        quality = fields[10]
    except (TypeError, ValueError):
        return None
    if state not in VALID_STATES or quality not in VALID_QUALITIES:
        return None
    if timestamp < 0 or reps < 0:
        return None
    return TelemetrySample(timestamp, accel, gyro, state, reps, quality)


def parse_ecg_line(line: str) -> EcgTelemetrySample | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    fields = line.split(",")
    if len(fields) != 7 or fields[0] != "ECG":
        return None
    try:
        timestamp = int(fields[1])
        raw_adc = int(fields[2])
        bpm = float(fields[3])
        flags = tuple(int(value) for value in fields[4:7])
    except (TypeError, ValueError):
        return None
    if timestamp < 0 or not 0 <= raw_adc <= 4095:
        return None
    if not math.isfinite(bpm) or bpm < 0.0:
        return None
    if any(value not in (0, 1) for value in flags):
        return None
    return EcgTelemetrySample(
        timestamp,
        raw_adc,
        bpm,
        bool(flags[0]),
        bool(flags[1]),
        bool(flags[2]),
    )
