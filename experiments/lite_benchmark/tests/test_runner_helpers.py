import csv
from pathlib import Path

import numpy as np

from literehab_benchmark.runner import (
    apply_missing_samples,
    augment_actionmae_modalities,
    write_summary,
)


def test_missing_sample_corruption_is_seeded_and_preserves_original():
    values = np.ones((4, 3, 20), dtype=np.float32)

    first, available_first = apply_missing_samples(values, missing_rate=0.25, seed=9)
    second, available_second = apply_missing_samples(values, missing_rate=0.25, seed=9)

    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(available_first, available_second)
    assert np.count_nonzero(first == 0) == 4 * 3 * 5
    assert np.all(values == 1)
    assert available_first.shape == (4,)
    assert np.all((available_first >= 0) & (available_first <= 1))


def test_summary_writer_uses_stable_columns(tmp_path: Path):
    rows = [{
        "model": "gated_fusion",
        "condition": "clean",
        "accuracy": 0.8,
        "macro_f1": 0.79,
        "balanced_accuracy": 0.78,
        "latency_ms": 2.5,
        "parameters": 50000,
        "seed": 7,
    }]

    path = write_summary(rows, tmp_path / "summary.csv")

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(rows[0])
        assert list(reader)[0]["model"] == "gated_fusion"


def test_actionmae_augmentation_is_seeded_and_never_drops_both_modalities():
    torch = __import__("torch")
    imu = torch.ones((8, 6, 20))
    pose = torch.ones((8, 9, 20))

    torch.manual_seed(13)
    first = augment_actionmae_modalities(imu, pose)
    torch.manual_seed(13)
    second = augment_actionmae_modalities(imu, pose)

    for left, right in zip(first, second):
        torch.testing.assert_close(left, right)
    augmented_imu, augmented_pose, availability = first
    assert augmented_imu.shape == imu.shape
    assert augmented_pose.shape == pose.shape
    assert availability.shape == (8, 2)
    assert torch.all((availability >= 0) & (availability <= 1))
    assert torch.all(availability.sum(dim=1) > 0)
    assert torch.all(imu == 1)
    assert torch.all(pose == 1)
