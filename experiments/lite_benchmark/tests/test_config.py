import json
from pathlib import Path

import pytest

from literehab_benchmark.config import BenchmarkConfig, load_config


def test_rtx5060_preset_is_a_small_course_project_benchmark():
    preset = Path(__file__).parents[1] / "configs" / "rtx5060_laptop.json"

    config = load_config(preset)

    assert config.models == (
        "imu_cnn",
        "imu_cnn_bigru",
        "pose_cnn_bigru",
        "early_fusion",
        "gated_fusion",
    )
    assert config.epochs <= 10
    assert config.seeds == (7,)
    assert config.max_train_windows <= 6000
    assert config.batch_size <= 128
    assert config.mixed_precision is True


def test_config_rejects_unknown_model(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"models": ["imaginary_net"]}))

    with pytest.raises(ValueError, match="unknown benchmark model"):
        load_config(path)


def test_config_requires_positive_training_budget():
    with pytest.raises(ValueError, match="epochs"):
        BenchmarkConfig(epochs=0).validate()
