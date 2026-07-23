from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _segment_windows(values: np.ndarray, window_size: int, stride: int):
    for start in range(0, len(values) - window_size + 1, stride):
        yield values[start : start + window_size].T


def prepare_mri_windows(
    feature_dir: str | Path,
    annotation_path: str | Path,
    output_path: str | Path,
    window_size: int = 100,
    stride: int = 50,
    selected_labels: tuple[str, ...] | None = None,
    subsets: tuple[str, ...] = ("training", "validation"),
) -> int:
    """Convert official mRI precomputed RGB/IMU pose features to small windows.

    mRI stores both modalities as ``[time, 17 joints, xyz]`` arrays in one NPZ
    per subject/video.  This converter deliberately uses those precomputed
    features so the course-project benchmark does not decode videos or train a
    large pose estimator.
    """
    feature_dir = Path(feature_dir)
    annotation = json.loads(Path(annotation_path).read_text())
    database = annotation.get("database")
    if not isinstance(database, dict):
        raise ValueError("mRI annotation must contain a database object")
    if window_size <= 0 or stride <= 0:
        raise ValueError("window_size and stride must be positive")

    if selected_labels is None:
        selected_labels = tuple(sorted({
            action["label"]
            for video in database.values()
            for action in video.get("annotations", [])
        }))
    if not selected_labels:
        raise ValueError("at least one action label is required")
    label_index = {label: index for index, label in enumerate(selected_labels)}

    imu_windows: list[np.ndarray] = []
    pose_windows: list[np.ndarray] = []
    labels: list[int] = []
    subjects: list[str] = []
    for video_id, video in database.items():
        if str(video.get("subset", "")).lower() not in subsets:
            continue
        feature_path = feature_dir / f"{video_id}.npz"
        if not feature_path.exists():
            raise FileNotFoundError(f"missing mRI feature file: {feature_path}")
        with np.load(feature_path, allow_pickle=False) as features:
            if "rgb" not in features or "imu" not in features:
                raise ValueError(f"{feature_path} must contain rgb and imu arrays")
            pose = np.asarray(features["rgb"], dtype=np.float32)
            imu = np.asarray(features["imu"], dtype=np.float32)
        if pose.ndim != 3 or imu.ndim != 3 or pose.shape != imu.shape:
            raise ValueError(f"{feature_path} modalities must share [time, joint, xyz]")
        pose = pose.reshape(len(pose), -1)
        imu = imu.reshape(len(imu), -1)
        fps = float(video.get("fps", 50.0))
        for action in video.get("annotations", []):
            label = str(action["label"])
            if label not in label_index:
                continue
            start_s, end_s = action["segment"]
            start = max(0, int(round(float(start_s) * fps)))
            end = min(len(pose), int(round(float(end_s) * fps)))
            pose_segment = pose[start:end]
            imu_segment = imu[start:end]
            pose_parts = list(_segment_windows(pose_segment, window_size, stride))
            imu_parts = list(_segment_windows(imu_segment, window_size, stride))
            for pose_window, imu_window in zip(pose_parts, imu_parts):
                pose_windows.append(pose_window)
                imu_windows.append(imu_window)
                labels.append(label_index[label])
                subjects.append(str(video_id))
    if not labels:
        raise ValueError("no complete windows matched the selected mRI labels")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        imu=np.stack(imu_windows).astype(np.float32),
        pose=np.stack(pose_windows).astype(np.float32),
        labels=np.asarray(labels, dtype=np.int64),
        subjects=np.asarray(subjects),
        class_names=np.asarray(selected_labels),
    )
    return len(labels)
