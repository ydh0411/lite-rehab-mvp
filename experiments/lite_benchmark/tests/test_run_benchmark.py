import json
from pathlib import Path

import numpy as np

from literehab_benchmark.config import BenchmarkConfig
from literehab_benchmark.runner import run_benchmark


def test_one_epoch_smoke_benchmark_writes_real_result_artifacts(tmp_path: Path, capsys):
    rng = np.random.default_rng(5)
    labels = np.asarray([0, 1] * 8)
    signal = labels[:, None, None].astype(np.float32)
    imu = rng.normal(size=(16, 6, 24)).astype(np.float32) * 0.05 + signal
    pose = rng.normal(size=(16, 9, 24)).astype(np.float32) * 0.05 + signal
    dataset_path = tmp_path / "tiny.npz"
    np.savez_compressed(
        dataset_path,
        imu=imu,
        pose=pose,
        labels=labels,
        subjects=np.asarray([f"S{index // 4 + 1:02d}" for index in range(16)]),
        class_names=np.asarray(["class_a", "class_b"]),
    )
    config = BenchmarkConfig(
        models=("imu_cnn", "gated_fusion", "lite_actionmae"),
        epochs=1,
        seeds=(7,),
        batch_size=4,
        max_train_windows=12,
        max_test_windows=4,
        mixed_precision=False,
        num_workers=0,
        robustness_missing_rates=(0.0, 0.5),
        warmup_batches=1,
        latency_batches=2,
    )

    summary_path = run_benchmark(
        dataset_path=dataset_path,
        config=config,
        output_dir=tmp_path / "results",
        holdout_subjects=("S04",),
        device_name="cpu",
    )

    assert summary_path.exists()
    assert (tmp_path / "results" / "confusion_gated_fusion.json").exists()
    assert (tmp_path / "results" / "confusion_gated_fusion_seed7.json").exists()
    assert (tmp_path / "results" / "history_gated_fusion_seed7.json").exists()
    assert (tmp_path / "results" / "confusion_lite_actionmae_seed7.json").exists()
    assert (tmp_path / "results" / "history_lite_actionmae_seed7.json").exists()
    history = json.loads(
        (tmp_path / "results" / "history_gated_fusion.json").read_text()
    )
    assert history["epoch"] == [1]
    manifest = json.loads((tmp_path / "results" / "manifest.json").read_text())
    assert manifest["device"] == "cpu"
    assert manifest["holdout_subjects"] == ["S04"]
    output = capsys.readouterr().out
    assert "model=imu_cnn seed=7 epoch=1/1" in output
    assert "model=gated_fusion condition=clean" in output
