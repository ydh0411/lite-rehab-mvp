from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class BenchmarkDataset:
    imu: np.ndarray
    pose: np.ndarray
    labels: np.ndarray
    subjects: np.ndarray
    class_names: tuple[str, ...]


@dataclass(frozen=True)
class SubjectSplit:
    train_indices: np.ndarray
    test_indices: np.ndarray


def load_dataset(path: str | Path) -> BenchmarkDataset:
    with np.load(Path(path), allow_pickle=False) as archive:
        required = ("imu", "pose", "labels", "subjects", "class_names")
        missing = [name for name in required if name not in archive]
        if missing:
            raise ValueError(f"dataset missing arrays: {', '.join(missing)}")
        imu = np.asarray(archive["imu"], dtype=np.float32)
        pose = np.asarray(archive["pose"], dtype=np.float32)
        labels = np.asarray(archive["labels"], dtype=np.int64)
        subjects = np.asarray(archive["subjects"]).astype(str)
        class_names = tuple(str(item) for item in archive["class_names"])
    if imu.ndim != 3 or pose.ndim != 3:
        raise ValueError("imu and pose must use [window, channel, time]")
    sample_counts = {len(imu), len(pose), len(labels), len(subjects)}
    if len(sample_counts) != 1:
        raise ValueError("modalities, labels, and subjects must have the same number of windows")
    if imu.shape[2] != pose.shape[2]:
        raise ValueError("imu and pose windows must have the same temporal length")
    if not class_names or np.any(labels < 0) or np.any(labels >= len(class_names)):
        raise ValueError("labels must index class_names")
    return BenchmarkDataset(imu, pose, labels, subjects, class_names)


def subject_disjoint_split(
    dataset: BenchmarkDataset,
    holdout_subjects: tuple[str, ...] | None = None,
) -> SubjectSplit:
    unique_subjects = sorted(set(dataset.subjects.tolist()))
    if len(unique_subjects) < 2:
        raise ValueError("subject-disjoint evaluation needs at least two subjects")
    if holdout_subjects is None:
        holdout_count = max(1, round(len(unique_subjects) * 0.2))
        holdout_subjects = tuple(unique_subjects[-holdout_count:])
    unknown = sorted(set(holdout_subjects) - set(unique_subjects))
    if unknown:
        raise ValueError(f"unknown holdout subjects: {', '.join(unknown)}")
    test_mask = np.isin(dataset.subjects, holdout_subjects)
    train_indices = np.flatnonzero(~test_mask)
    test_indices = np.flatnonzero(test_mask)
    if not len(train_indices) or not len(test_indices):
        raise ValueError("training and test splits must both be non-empty")
    return SubjectSplit(train_indices=train_indices, test_indices=test_indices)


def capped_indices(indices: np.ndarray, maximum: int, seed: int) -> np.ndarray:
    indices = np.asarray(indices, dtype=np.int64)
    if len(indices) <= maximum:
        return indices
    generator = np.random.default_rng(seed)
    return np.sort(generator.choice(indices, size=maximum, replace=False))
