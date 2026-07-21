from pathlib import Path

import numpy as np
import pytest

from literehab_benchmark.data import load_dataset, subject_disjoint_split


def _write_dataset(path: Path):
    np.savez_compressed(
        path,
        imu=np.zeros((8, 6, 32), dtype=np.float32),
        pose=np.zeros((8, 9, 32), dtype=np.float32),
        labels=np.asarray([0, 1, 0, 1, 0, 1, 0, 1]),
        subjects=np.asarray(["S01", "S01", "S02", "S02", "S03", "S03", "S04", "S04"]),
        class_names=np.asarray(["elbow_flexion", "shoulder_abduction"]),
    )


def test_loader_and_split_never_mix_subjects(tmp_path: Path):
    path = tmp_path / "tiny.npz"
    _write_dataset(path)

    dataset = load_dataset(path)
    split = subject_disjoint_split(dataset, holdout_subjects=("S04",))

    assert dataset.imu.shape == (8, 6, 32)
    assert dataset.pose.shape == (8, 9, 32)
    assert set(dataset.subjects[split.train_indices]).isdisjoint(
        set(dataset.subjects[split.test_indices])
    )
    assert set(dataset.subjects[split.test_indices]) == {"S04"}


def test_loader_rejects_misaligned_modalities(tmp_path: Path):
    path = tmp_path / "bad.npz"
    np.savez(
        path,
        imu=np.zeros((4, 6, 16)),
        pose=np.zeros((3, 9, 16)),
        labels=np.zeros(4),
        subjects=np.asarray(["S01"] * 4),
        class_names=np.asarray(["idle"]),
    )

    with pytest.raises(ValueError, match="same number of windows"):
        load_dataset(path)
