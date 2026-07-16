from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .web_models import LiveSnapshot


class RuntimeProtocol(Protocol):
    recording: bool

    def snapshot(self) -> LiveSnapshot: ...
    def start_session(self, subject: str) -> None: ...
    def stop_session(self) -> None: ...
    def recapture_baseline(self) -> None: ...
    def reset_range(self) -> None: ...
    def jpeg_frame(self) -> bytes | None: ...


class FixtureRuntime:
    def __init__(self) -> None:
        self.recording = False
        self.subject = ""
        self.baseline_resets = 0
        self.range_resets = 0
        self._snapshot = LiveSnapshot.initial()

    def snapshot(self) -> LiveSnapshot:
        return self._snapshot

    def start_session(self, subject: str) -> None:
        normalized = subject.strip()
        if not normalized:
            raise ValueError("Participant ID is required")
        if self.recording:
            raise RuntimeError("Session is already recording")
        self.recording = True
        self.subject = normalized
        self._snapshot = replace(
            self._snapshot,
            recording=True,
            subject=normalized,
        )

    def stop_session(self) -> None:
        if not self.recording:
            raise RuntimeError("Session is not recording")
        self.recording = False
        self._snapshot = replace(self._snapshot, recording=False)

    def recapture_baseline(self) -> None:
        self.baseline_resets += 1

    def reset_range(self) -> None:
        self.range_resets += 1

    def jpeg_frame(self) -> bytes | None:
        return None

    def set_snapshot(self, snapshot: LiveSnapshot) -> None:
        self._snapshot = snapshot
        self.recording = snapshot.recording
        self.subject = snapshot.subject

