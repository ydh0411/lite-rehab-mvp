from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .pose_features import PoseFeatures
from .telemetry import TelemetrySample


@dataclass(frozen=True)
class ReceivedTelemetry:
    sample: TelemetrySample
    received_s: float


@dataclass(frozen=True)
class SynchronizedSample:
    telemetry: TelemetrySample
    received_s: float
    pose: PoseFeatures | None


class SampleSynchronizer:
    def __init__(self, tolerance_s: float = 0.05) -> None:
        if tolerance_s <= 0:
            raise ValueError("tolerance_s must be positive")
        self.tolerance_s = tolerance_s
        self._imu: deque[ReceivedTelemetry] = deque()
        self._poses: deque[PoseFeatures] = deque(maxlen=500)

    def add_imu(self, received: ReceivedTelemetry) -> None:
        self._imu.append(received)

    def add_pose(self, features: PoseFeatures) -> None:
        self._poses.append(features)

    def _nearest_pose(self, timestamp_s: float) -> PoseFeatures | None:
        if not self._poses:
            return None
        nearest = min(self._poses,
                      key=lambda item: abs(item.timestamp_s - timestamp_s))
        if abs(nearest.timestamp_s - timestamp_s) > self.tolerance_s:
            return None
        return nearest

    def drain(self, now_s: float, force: bool = False) -> list[SynchronizedSample]:
        ready: list[SynchronizedSample] = []
        cutoff = now_s - self.tolerance_s
        while self._imu and (force or self._imu[0].received_s <= cutoff):
            received = self._imu.popleft()
            ready.append(SynchronizedSample(
                telemetry=received.sample,
                received_s=received.received_s,
                pose=self._nearest_pose(received.received_s),
            ))

        oldest_needed = ((self._imu[0].received_s - self.tolerance_s)
                         if self._imu else cutoff - self.tolerance_s)
        while self._poses and self._poses[0].timestamp_s < oldest_needed:
            self._poses.popleft()
        return ready
