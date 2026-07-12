from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections import deque

import numpy as np


ARCHITECTURE_VERSION = 1
POSE_FEATURE_NAMES = (
    "elbow_angle_deg",
    "shoulder_angle_deg",
    "trunk_displacement",
    "wrist_x",
    "wrist_y",
    "elbow_velocity_dps",
    "shoulder_velocity_dps",
    "visibility",
    "vision_valid",
)


def build_multimodal_model(
    num_exercises: int,
    num_qualities: int,
    imu_channels: int = 6,
    pose_channels: int = len(POSE_FEATURE_NAMES),
):
    import torch
    import torch.nn as nn

    if num_exercises <= 0 or num_qualities <= 0:
        raise ValueError("output class counts must be positive")

    class TemporalBranch(nn.Module):
        def __init__(self, channels: int) -> None:
            super().__init__()
            self.convolution = nn.Sequential(
                nn.Conv1d(channels, 32, kernel_size=5, padding=2),
                nn.BatchNorm1d(32),
                nn.ReLU(),
                nn.MaxPool1d(2),
                nn.Conv1d(32, 64, kernel_size=3, padding=1),
                nn.BatchNorm1d(64),
                nn.ReLU(),
                nn.MaxPool1d(2),
            )
            self.recurrent = nn.GRU(64, 64, batch_first=True,
                                    bidirectional=True)

        def forward(self, values):
            values = self.convolution(values).permute(0, 2, 1)
            values, _ = self.recurrent(values)
            return values.mean(dim=1)

    class MultimodalCNNBiGRU(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.imu_branch = TemporalBranch(imu_channels)
            self.pose_branch = TemporalBranch(pose_channels)
            self.fusion = nn.Sequential(
                nn.Linear(256, 128),
                nn.ReLU(),
                nn.Dropout(0.3),
            )
            self.exercise_head = nn.Linear(128, num_exercises)
            self.quality_head = nn.Linear(128, num_qualities)

        def forward(self, imu, pose, visual_confidence):
            confidence = torch.clamp(visual_confidence, 0.0, 1.0)
            imu_embedding = self.imu_branch(imu)
            pose_embedding = self.pose_branch(pose) * confidence
            fused = self.fusion(torch.cat((imu_embedding, pose_embedding), dim=1))
            return (self.exercise_head(fused), self.quality_head(fused),
                    confidence)

    return MultimodalCNNBiGRU()


@dataclass(frozen=True)
class LoadedMultimodalCheckpoint:
    model: object
    exercise_labels: tuple[str, ...]
    quality_labels: tuple[str, ...]
    imu_mean: np.ndarray
    imu_std: np.ndarray
    pose_mean: np.ndarray
    pose_std: np.ndarray
    window_size: int
    held_out_subject: str
    exercise_accuracy: float
    quality_accuracy: float


@dataclass(frozen=True)
class MultimodalPrediction:
    exercise: str
    quality: str
    confidence: float
    visual_confidence: float


class MultimodalPredictor:
    def __init__(self, checkpoint: LoadedMultimodalCheckpoint) -> None:
        self.checkpoint = checkpoint
        self.imu = deque(maxlen=checkpoint.window_size)
        self.pose = deque(maxlen=checkpoint.window_size)

    def update(self, imu_values, pose_values) -> MultimodalPrediction | None:
        import torch

        imu_array = np.asarray(imu_values, dtype=np.float32)
        pose_array = np.asarray(pose_values, dtype=np.float32)
        if imu_array.shape != (6,) or pose_array.shape != (len(POSE_FEATURE_NAMES),):
            raise ValueError("unexpected multimodal sample shape")
        self.imu.append(imu_array)
        self.pose.append(pose_array)
        if len(self.imu) < self.imu.maxlen:
            return None

        imu_window = np.asarray(self.imu, dtype=np.float32)
        pose_window = np.asarray(self.pose, dtype=np.float32)
        visual_confidence = float(np.mean(
            pose_window[:, POSE_FEATURE_NAMES.index("visibility")] *
            pose_window[:, POSE_FEATURE_NAMES.index("vision_valid")]
        ))
        imu_window = (imu_window - self.checkpoint.imu_mean) / self.checkpoint.imu_std
        pose_window = (pose_window - self.checkpoint.pose_mean) / self.checkpoint.pose_std
        imu_tensor = torch.tensor(imu_window).T.unsqueeze(0)
        pose_tensor = torch.tensor(pose_window).T.unsqueeze(0)
        confidence_tensor = torch.tensor([[visual_confidence]], dtype=torch.float32)
        with torch.no_grad():
            exercise_logits, quality_logits, _ = self.checkpoint.model(
                imu_tensor, pose_tensor, confidence_tensor)
            exercise_probability = torch.softmax(exercise_logits, dim=1)
            quality_probability = torch.softmax(quality_logits, dim=1)
        exercise_index = int(exercise_probability.argmax(dim=1).item())
        quality_index = int(quality_probability.argmax(dim=1).item())
        confidence = min(float(exercise_probability[0, exercise_index]),
                         float(quality_probability[0, quality_index]))
        return MultimodalPrediction(
            exercise=self.checkpoint.exercise_labels[exercise_index],
            quality=self.checkpoint.quality_labels[quality_index],
            confidence=confidence,
            visual_confidence=visual_confidence,
        )


def load_multimodal_checkpoint(path: str | Path) -> LoadedMultimodalCheckpoint:
    import torch

    checkpoint = torch.load(Path(path), map_location="cpu", weights_only=True)
    if checkpoint.get("architecture_version") != ARCHITECTURE_VERSION:
        raise ValueError("unsupported multimodal architecture version")
    if tuple(checkpoint.get("pose_feature_names", ())) != POSE_FEATURE_NAMES:
        raise ValueError("multimodal pose feature schema mismatch")

    required = (
        "state_dict", "exercise_labels", "quality_labels", "imu_mean",
        "imu_std", "pose_mean", "pose_std", "window_size",
        "held_out_subject", "exercise_accuracy", "quality_accuracy",
    )
    missing = [name for name in required if name not in checkpoint]
    if missing:
        raise ValueError(f"multimodal checkpoint missing: {', '.join(missing)}")

    exercise_labels = tuple(checkpoint["exercise_labels"])
    quality_labels = tuple(checkpoint["quality_labels"])
    model = build_multimodal_model(len(exercise_labels), len(quality_labels))
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    return LoadedMultimodalCheckpoint(
        model=model,
        exercise_labels=exercise_labels,
        quality_labels=quality_labels,
        imu_mean=np.asarray(checkpoint["imu_mean"], dtype=np.float32),
        imu_std=np.asarray(checkpoint["imu_std"], dtype=np.float32),
        pose_mean=np.asarray(checkpoint["pose_mean"], dtype=np.float32),
        pose_std=np.asarray(checkpoint["pose_std"], dtype=np.float32),
        window_size=int(checkpoint["window_size"]),
        held_out_subject=str(checkpoint["held_out_subject"]),
        exercise_accuracy=float(checkpoint["exercise_accuracy"]),
        quality_accuracy=float(checkpoint["quality_accuracy"]),
    )
