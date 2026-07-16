from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LiveSnapshot:
    timestamp_s: float
    recording: bool
    subject: str
    exercise: str
    repetitions: int
    feedback: str
    mode: str
    source: str
    side: str
    serial_status: str
    camera_status: str
    rom_deg: float | None
    confidence_text: str
    model_confidence: float | None
    ecg_bpm: float | None
    ecg_connected: bool
    ecg_samples: tuple[float, ...]
    camera_frame_age_s: float | None

    @classmethod
    def initial(cls) -> "LiveSnapshot":
        return cls(
            timestamp_s=0.0,
            recording=False,
            subject="",
            exercise="idle",
            repetitions=0,
            feedback="Ready",
            mode="IMU-only",
            source="rule fallback",
            side="right",
            serial_status="unavailable",
            camera_status="unavailable",
            rom_deg=None,
            confidence_text="Model unavailable",
            model_confidence=None,
            ecg_bpm=None,
            ecg_connected=False,
            ecg_samples=(),
            camera_frame_age_s=None,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
