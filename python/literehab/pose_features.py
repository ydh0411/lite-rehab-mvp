from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .pose_math import angle_degrees


SIDE_INDICES = {
    "left": {"shoulder": 11, "elbow": 13, "wrist": 15, "hip": 23},
    "right": {"shoulder": 12, "elbow": 14, "wrist": 16, "hip": 24},
}


@dataclass(frozen=True)
class PoseFeatures:
    timestamp_s: float
    valid: bool
    elbow_angle_deg: float = 0.0
    shoulder_angle_deg: float = 0.0
    trunk_displacement: float = 0.0
    wrist_x: float = 0.0
    wrist_y: float = 0.0
    elbow_velocity_dps: float = 0.0
    shoulder_velocity_dps: float = 0.0
    visibility: float = 0.0

    def to_vector(self) -> tuple[float, ...]:
        return (
            self.elbow_angle_deg,
            self.shoulder_angle_deg,
            self.trunk_displacement,
            self.wrist_x,
            self.wrist_y,
            self.elbow_velocity_dps,
            self.shoulder_velocity_dps,
            self.visibility,
            1.0 if self.valid else 0.0,
        )


def _point(landmark) -> tuple[float, float]:
    return float(landmark.x), float(landmark.y)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def extract_pose_features(
    landmarks: Sequence,
    side: str,
    timestamp_s: float,
    baseline: dict[str, tuple[float, float]] | None = None,
    previous: PoseFeatures | None = None,
    visibility_threshold: float = 0.5,
) -> PoseFeatures:
    if side not in SIDE_INDICES:
        raise ValueError("side must be 'left' or 'right'")
    indices = SIDE_INDICES[side]
    selected = {name: landmarks[index] for name, index in indices.items()}
    visibility = sum(float(item.visibility) for item in selected.values()) / 4.0
    if any(float(item.visibility) < visibility_threshold for item in selected.values()):
        return PoseFeatures(timestamp_s=timestamp_s, valid=False,
                            visibility=visibility)

    shoulder = _point(selected["shoulder"])
    elbow = _point(selected["elbow"])
    wrist = _point(selected["wrist"])
    hip = _point(selected["hip"])
    torso = _distance(shoulder, hip)
    if torso <= 1e-9:
        return PoseFeatures(timestamp_s=timestamp_s, valid=False,
                            visibility=visibility)

    elbow_angle = angle_degrees(shoulder, elbow, wrist)
    shoulder_angle = angle_degrees(elbow, shoulder, hip)
    if elbow_angle is None or shoulder_angle is None:
        return PoseFeatures(timestamp_s=timestamp_s, valid=False,
                            visibility=visibility)

    trunk_displacement = 0.0
    if baseline is not None:
        try:
            base_shoulder = baseline["shoulder"]
            base_hip = baseline["hip"]
            base_relative = (base_shoulder[0] - base_hip[0],
                             base_shoulder[1] - base_hip[1])
            current_relative = (shoulder[0] - hip[0], shoulder[1] - hip[1])
            trunk_displacement = _distance(base_relative, current_relative) / torso
        except (KeyError, TypeError, IndexError):
            trunk_displacement = 0.0

    elbow_velocity = 0.0
    shoulder_velocity = 0.0
    if previous is not None and previous.valid and timestamp_s > previous.timestamp_s:
        dt = timestamp_s - previous.timestamp_s
        elbow_velocity = (elbow_angle - previous.elbow_angle_deg) / dt
        shoulder_velocity = (shoulder_angle - previous.shoulder_angle_deg) / dt

    return PoseFeatures(
        timestamp_s=timestamp_s,
        valid=True,
        elbow_angle_deg=elbow_angle,
        shoulder_angle_deg=shoulder_angle,
        trunk_displacement=trunk_displacement,
        wrist_x=(wrist[0] - shoulder[0]) / torso,
        wrist_y=(wrist[1] - shoulder[1]) / torso,
        elbow_velocity_dps=elbow_velocity,
        shoulder_velocity_dps=shoulder_velocity,
        visibility=visibility,
    )


class RepetitionRangeTracker:
    def __init__(self) -> None:
        self._active = False
        self._angles: list[float] = []
        self._last_range: float | None = None
        self._rep_count = 0

    def reset(self) -> None:
        self._active = False
        self._angles.clear()
        self._last_range = None

    def update(self, state: str, rep_count: int,
               angle: float | None) -> float | None:
        is_active = state != "idle"
        if is_active and not self._active:
            self._angles = []
            self._last_range = None
        if is_active and angle is not None:
            self._angles.append(float(angle))
        if not is_active and self._active and self._angles:
            self._last_range = max(self._angles) - min(self._angles)
        self._active = is_active
        self._rep_count = rep_count
        if self._angles and is_active:
            return max(self._angles) - min(self._angles)
        return self._last_range
