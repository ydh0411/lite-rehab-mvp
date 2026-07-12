from pathlib import Path

import pytest
import torch

from literehab.multimodal import (
    ARCHITECTURE_VERSION,
    POSE_FEATURE_NAMES,
    MultimodalPredictor,
    build_multimodal_model,
    load_multimodal_checkpoint,
)


def test_multimodal_model_shapes_and_zero_confidence_gate():
    torch.manual_seed(4)
    model = build_multimodal_model(3, 4)
    model.eval()
    imu = torch.randn(2, 6, 100)
    pose_a = torch.randn(2, len(POSE_FEATURE_NAMES), 100)
    pose_b = torch.randn(2, len(POSE_FEATURE_NAMES), 100) * 20.0
    confidence = torch.zeros(2, 1)

    with torch.no_grad():
        exercise_a, quality_a, effective = model(imu, pose_a, confidence)
        exercise_b, quality_b, _ = model(imu, pose_b, confidence)

    assert exercise_a.shape == (2, 3)
    assert quality_a.shape == (2, 4)
    assert effective.shape == (2, 1)
    torch.testing.assert_close(exercise_a, exercise_b)
    torch.testing.assert_close(quality_a, quality_b)


def test_loader_rejects_unsupported_architecture_version(tmp_path: Path):
    path = tmp_path / "bad.pt"
    torch.save({"architecture_version": 99}, path)

    with pytest.raises(ValueError, match="architecture version"):
        load_multimodal_checkpoint(path)


def test_loader_rejects_pose_feature_mismatch(tmp_path: Path):
    path = tmp_path / "bad_features.pt"
    torch.save({
        "architecture_version": 1,
        "pose_feature_names": ["wrong"],
    }, path)

    with pytest.raises(ValueError, match="pose feature"):
        load_multimodal_checkpoint(path)


def test_valid_checkpoint_runs_windowed_prediction(tmp_path: Path):
    path = tmp_path / "model.pt"
    model = build_multimodal_model(3, 4)
    torch.save({
        "architecture_version": ARCHITECTURE_VERSION,
        "pose_feature_names": list(POSE_FEATURE_NAMES),
        "state_dict": model.state_dict(),
        "exercise_labels": ["idle", "rotation", "elbow"],
        "quality_labels": ["none", "ok", "fast", "range"],
        "imu_mean": torch.zeros(6),
        "imu_std": torch.ones(6),
        "pose_mean": torch.zeros(len(POSE_FEATURE_NAMES)),
        "pose_std": torch.ones(len(POSE_FEATURE_NAMES)),
        "window_size": 4,
        "held_out_subject": "S03",
        "exercise_accuracy": 0.5,
        "quality_accuracy": 0.5,
    }, path)
    predictor = MultimodalPredictor(load_multimodal_checkpoint(path))
    imu = [0.0] * 6
    pose = [0.0] * len(POSE_FEATURE_NAMES)
    pose[-2:] = [0.9, 1.0]

    assert predictor.update(imu, pose) is None
    assert predictor.update(imu, pose) is None
    assert predictor.update(imu, pose) is None
    prediction = predictor.update(imu, pose)

    assert prediction is not None
    assert prediction.exercise in {"idle", "rotation", "elbow"}
    assert 0.0 <= prediction.confidence <= 1.0
    assert prediction.visual_confidence == pytest.approx(0.9)
