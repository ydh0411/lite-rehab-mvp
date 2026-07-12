#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from literehab.dataset import make_windows
from literehab.multimodal import (
    ARCHITECTURE_VERSION,
    POSE_FEATURE_NAMES,
    build_multimodal_model,
)


IMU_FEATURES = ("ax", "ay", "az", "gx", "gy", "gz")


def load_recording(path: Path):
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return None
    required = (*IMU_FEATURES, *POSE_FEATURE_NAMES,
                "subject", "label_exercise", "label_quality")
    missing = [name for name in required if name not in rows[0]]
    if missing:
        raise ValueError(f"{path} missing columns: {', '.join(missing)}")
    subjects = {row["subject"] for row in rows}
    exercises = {row["label_exercise"] for row in rows}
    qualities = {row["label_quality"] for row in rows}
    if len(subjects) != 1 or len(exercises) != 1 or len(qualities) != 1:
        raise ValueError(f"{path} must contain one subject and one label pair")
    imu = np.asarray([[float(row[name]) for name in IMU_FEATURES]
                      for row in rows], dtype=np.float32)
    pose = np.asarray([[float(row[name]) for name in POSE_FEATURE_NAMES]
                       for row in rows], dtype=np.float32)
    return imu, pose, subjects.pop(), exercises.pop(), qualities.pop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train LiteRehab RGB-IMU fusion")
    parser.add_argument("--data", type=Path, default=Path("multimodal_data"))
    parser.add_argument("--holdout-subject", required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--output", type=Path,
                        default=Path("models/multimodal_cnn_bigru.pt"))
    args = parser.parse_args()

    recordings = [load_recording(path) for path in sorted(args.data.glob("*.csv"))]
    recordings = [item for item in recordings if item is not None]
    if not recordings:
        raise SystemExit("No synchronized labelled CSV recordings found")
    exercise_labels = sorted({item[3] for item in recordings})
    quality_labels = sorted({item[4] for item in recordings})
    exercise_index = {label: index for index, label in enumerate(exercise_labels)}
    quality_index = {label: index for index, label in enumerate(quality_labels)}

    train_imu, train_pose, train_exercise, train_quality = [], [], [], []
    test_imu, test_pose, test_exercise, test_quality = [], [], [], []
    for imu, pose, subject, exercise, quality in recordings:
        imu_windows = make_windows(imu, 100, 50)
        pose_windows = make_windows(pose, 100, 50)
        target = ((test_imu, test_pose, test_exercise, test_quality)
                  if subject == args.holdout_subject
                  else (train_imu, train_pose, train_exercise, train_quality))
        target[0].extend(imu_windows)
        target[1].extend(pose_windows)
        target[2].extend([exercise_index[exercise]] * len(imu_windows))
        target[3].extend([quality_index[quality]] * len(imu_windows))
    if not train_imu or not test_imu:
        raise SystemExit("Training and held-out subjects both need usable windows")

    train_imu_array = np.asarray(train_imu, dtype=np.float32)
    train_pose_array = np.asarray(train_pose, dtype=np.float32)
    imu_mean = train_imu_array.mean(axis=(0, 1))
    imu_std = train_imu_array.std(axis=(0, 1)) + 1e-6
    pose_mean = train_pose_array.mean(axis=(0, 1))
    pose_std = train_pose_array.std(axis=(0, 1)) + 1e-6

    def tensors(imu_values, pose_values):
        imu_values = np.asarray(imu_values, dtype=np.float32)
        pose_values = np.asarray(pose_values, dtype=np.float32)
        visibility_index = POSE_FEATURE_NAMES.index("visibility")
        valid_index = POSE_FEATURE_NAMES.index("vision_valid")
        confidence = (pose_values[:, :, visibility_index] *
                      pose_values[:, :, valid_index]).mean(axis=1, keepdims=True)
        confidence = np.clip(confidence, 0.0, 1.0)
        imu_values = (imu_values - imu_mean) / imu_std
        pose_values = (pose_values - pose_mean) / pose_std
        return (torch.tensor(imu_values).permute(0, 2, 1),
                torch.tensor(pose_values).permute(0, 2, 1),
                torch.tensor(confidence))

    train_tensors = tensors(train_imu_array, train_pose_array)
    loader = DataLoader(TensorDataset(
        *train_tensors, torch.tensor(train_exercise), torch.tensor(train_quality)),
        batch_size=32, shuffle=True)
    model = build_multimodal_model(len(exercise_labels), len(quality_labels))
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = torch.nn.CrossEntropyLoss()
    for epoch in range(args.epochs):
        model.train()
        total = 0.0
        for imu_batch, pose_batch, confidence, exercise_target, quality_target in loader:
            optimizer.zero_grad()
            exercise_logits, quality_logits, _ = model(
                imu_batch, pose_batch, confidence)
            loss = (criterion(exercise_logits, exercise_target) +
                    criterion(quality_logits, quality_target))
            loss.backward()
            optimizer.step()
            total += loss.item() * len(exercise_target)
        print(f"epoch={epoch + 1} loss={total / len(train_imu_array):.4f}")

    model.eval()
    test_tensors = tensors(test_imu, test_pose)
    with torch.no_grad():
        exercise_logits, quality_logits, _ = model(*test_tensors)
    exercise_accuracy = float((exercise_logits.argmax(1) ==
                               torch.tensor(test_exercise)).float().mean())
    quality_accuracy = float((quality_logits.argmax(1) ==
                              torch.tensor(test_quality)).float().mean())
    print(f"held_out_subject={args.holdout_subject} "
          f"exercise_accuracy={exercise_accuracy:.3f} "
          f"quality_accuracy={quality_accuracy:.3f}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "architecture_version": ARCHITECTURE_VERSION,
        "pose_feature_names": list(POSE_FEATURE_NAMES),
        "state_dict": model.state_dict(),
        "exercise_labels": exercise_labels,
        "quality_labels": quality_labels,
        "imu_mean": imu_mean,
        "imu_std": imu_std,
        "pose_mean": pose_mean,
        "pose_std": pose_std,
        "window_size": 100,
        "held_out_subject": args.holdout_subject,
        "exercise_accuracy": exercise_accuracy,
        "quality_accuracy": quality_accuracy,
    }, args.output)
    print(f"saved={args.output}")


if __name__ == "__main__":
    main()
