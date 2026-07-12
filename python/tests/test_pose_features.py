from dataclasses import dataclass

import pytest

from literehab.pose_features import (
    RepetitionRangeTracker,
    extract_pose_features,
)


@dataclass
class Landmark:
    x: float = 0.0
    y: float = 0.0
    visibility: float = 0.9


def make_landmarks(side: str):
    landmarks = [Landmark() for _ in range(33)]
    indices = ((11, 13, 15, 23) if side == "left" else (12, 14, 16, 24))
    points = [(0.4, 0.3), (0.3, 0.5), (0.2, 0.7), (0.4, 0.7)]
    if side == "right":
        points = [(1.0 - x, y) for x, y in points]
    for index, (x, y) in zip(indices, points):
        landmarks[index] = Landmark(x, y)
    return landmarks


def test_left_and_right_features_are_mirror_symmetric():
    left = extract_pose_features(make_landmarks("left"), "left", 1.0)
    right = extract_pose_features(make_landmarks("right"), "right", 1.0)

    assert left.valid and right.valid
    assert left.elbow_angle_deg == pytest.approx(right.elbow_angle_deg)
    assert left.shoulder_angle_deg == pytest.approx(right.shoulder_angle_deg)
    assert left.wrist_x == pytest.approx(-right.wrist_x)


def test_low_visibility_returns_explicit_invalid_features():
    landmarks = make_landmarks("left")
    landmarks[15].visibility = 0.2

    features = extract_pose_features(landmarks, "left", 1.0)

    assert not features.valid
    assert features.to_vector()[-1] == 0.0


def test_repetition_range_resets_when_next_motion_starts():
    tracker = RepetitionRangeTracker()
    assert tracker.update("elbow_flexion", 0, 150.0) == 0.0
    assert tracker.update("elbow_flexion", 0, 90.0) == 60.0
    assert tracker.update("idle", 1, 90.0) == 60.0

    assert tracker.update("elbow_flexion", 1, 120.0) == 0.0
    assert tracker.update("elbow_flexion", 1, 100.0) == 20.0


def test_side_must_be_supported():
    with pytest.raises(ValueError, match="side"):
        extract_pose_features(make_landmarks("left"), "centre", 1.0)
