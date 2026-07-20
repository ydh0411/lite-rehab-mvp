from __future__ import annotations

import csv
import json
from pathlib import Path
import random
import time

import numpy as np

from .config import BenchmarkConfig
from .data import capped_indices, load_dataset, subject_disjoint_split
from .metrics import classification_metrics, confusion_matrix
from .models import build_model, count_parameters


SUMMARY_FIELDS = (
    "model",
    "condition",
    "accuracy",
    "macro_f1",
    "balanced_accuracy",
    "latency_ms",
    "parameters",
    "seed",
)


def apply_missing_samples(values, missing_rate: float, seed: int):
    values = np.asarray(values, dtype=np.float32)
    if values.ndim != 3:
        raise ValueError("modality values must use [window, channel, time]")
    if not 0 <= missing_rate <= 1:
        raise ValueError("missing_rate must be between zero and one")
    output = values.copy()
    missing_per_window = round(values.shape[2] * missing_rate)
    generator = np.random.default_rng(seed)
    for index in range(len(output)):
        if missing_per_window:
            missing = generator.choice(
                values.shape[2], size=missing_per_window, replace=False
            )
            output[index, :, missing] = 0.0
    availability = np.full(len(output), 1.0 - missing_per_window / values.shape[2])
    return output, availability.astype(np.float32)


def write_summary(rows: list[dict[str, object]], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for row in rows:
        if tuple(row) != SUMMARY_FIELDS:
            raise ValueError("summary rows must use the stable benchmark schema")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _select_device(device_name: str):
    import torch

    if device_name != "auto":
        return torch.device(device_name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _normalization(values: np.ndarray, train_indices: np.ndarray):
    mean = values[train_indices].mean(axis=(0, 2), keepdims=True)
    std = values[train_indices].std(axis=(0, 2), keepdims=True) + 1e-6
    return mean.astype(np.float32), std.astype(np.float32)


def _make_loader(imu, pose, labels, batch_size, shuffle, num_workers):
    import torch
    from torch.utils.data import DataLoader, TensorDataset

    dataset = TensorDataset(
        torch.from_numpy(np.ascontiguousarray(imu)),
        torch.from_numpy(np.ascontiguousarray(pose)),
        torch.from_numpy(np.asarray(labels, dtype=np.int64)),
    )
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )


def _availability(batch_size: int, device, model_name: str, training: bool):
    import torch

    availability = torch.ones((batch_size, 2), device=device)
    if training and model_name == "gated_fusion":
        keep = (torch.rand((batch_size, 2), device=device) > 0.15).float()
        missing_both = keep.sum(dim=1) == 0
        keep[missing_both, 0] = 1.0
        availability = keep
    return availability


def _predict(model, loader, device, availability_values=None):
    import torch

    predictions: list[int] = []
    truth: list[int] = []
    model.eval()
    offset = 0
    with torch.no_grad():
        for imu, pose, labels in loader:
            imu = imu.to(device, non_blocking=True)
            pose = pose.to(device, non_blocking=True)
            if availability_values is None:
                available = torch.ones((len(labels), 2), device=device)
            else:
                available = torch.from_numpy(
                    availability_values[offset : offset + len(labels)]
                ).to(device)
            logits, _ = model(imu, pose, available)
            predictions.extend(logits.argmax(dim=1).cpu().tolist())
            truth.extend(labels.tolist())
            offset += len(labels)
    return np.asarray(truth), np.asarray(predictions)


def _measure_latency(model, loader, device, warmup_batches: int, latency_batches: int):
    import torch

    imu, pose, _ = next(iter(loader))
    imu = imu.to(device)
    pose = pose.to(device)
    available = torch.ones((len(imu), 2), device=device)
    model.eval()
    with torch.no_grad():
        for _ in range(warmup_batches):
            model(imu, pose, available)
        if device.type == "cuda":
            torch.cuda.synchronize()
        start = time.perf_counter()
        for _ in range(latency_batches):
            model(imu, pose, available)
        if device.type == "cuda":
            torch.cuda.synchronize()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return elapsed_ms / max(1, latency_batches) / len(imu)


def _metric_row(model_name, condition, metrics, latency_ms, parameters, seed):
    return {
        "model": model_name,
        "condition": condition,
        "accuracy": metrics["accuracy"],
        "macro_f1": metrics["macro_f1"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "latency_ms": latency_ms,
        "parameters": parameters,
        "seed": seed,
    }


def run_benchmark(
    dataset_path: str | Path,
    config: BenchmarkConfig,
    output_dir: str | Path,
    holdout_subjects: tuple[str, ...] | None = None,
    device_name: str = "auto",
) -> Path:
    import torch

    config.validate()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = load_dataset(dataset_path)
    split = subject_disjoint_split(dataset, holdout_subjects)
    device = _select_device(device_name)
    holdout = sorted(set(dataset.subjects[split.test_indices].tolist()))
    imu_mean, imu_std = _normalization(dataset.imu, split.train_indices)
    pose_mean, pose_std = _normalization(dataset.pose, split.train_indices)
    normalized_imu = (dataset.imu - imu_mean) / imu_std
    normalized_pose = (dataset.pose - pose_mean) / pose_std
    all_rows: list[dict[str, object]] = []

    for seed in config.seeds:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        train_indices = capped_indices(split.train_indices, config.max_train_windows, seed)
        test_indices = capped_indices(split.test_indices, config.max_test_windows, seed)
        train_loader = _make_loader(
            normalized_imu[train_indices], normalized_pose[train_indices],
            dataset.labels[train_indices], config.batch_size, True, config.num_workers,
        )
        test_loader = _make_loader(
            normalized_imu[test_indices], normalized_pose[test_indices],
            dataset.labels[test_indices], config.batch_size, False, config.num_workers,
        )

        for model_name in config.models:
            torch.manual_seed(seed)
            model = build_model(
                model_name,
                num_classes=len(dataset.class_names),
                imu_channels=dataset.imu.shape[1],
                pose_channels=dataset.pose.shape[1],
            ).to(device)
            optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
            criterion = torch.nn.CrossEntropyLoss()
            use_amp = bool(config.mixed_precision and device.type == "cuda")
            scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
            history = {"epoch": [], "train_loss": [], "test_macro_f1": []}
            for epoch in range(config.epochs):
                model.train()
                total_loss = 0.0
                sample_count = 0
                for imu, pose, labels in train_loader:
                    imu = imu.to(device, non_blocking=True)
                    pose = pose.to(device, non_blocking=True)
                    labels = labels.to(device, non_blocking=True)
                    available = _availability(len(labels), device, model_name, training=True)
                    optimizer.zero_grad(set_to_none=True)
                    with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                        logits, _ = model(imu, pose, available)
                        loss = criterion(logits, labels)
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                    total_loss += float(loss.detach()) * len(labels)
                    sample_count += len(labels)
                epoch_truth, epoch_prediction = _predict(model, test_loader, device)
                epoch_metrics = classification_metrics(
                    epoch_truth, epoch_prediction, len(dataset.class_names)
                )
                history["epoch"].append(epoch + 1)
                history["train_loss"].append(total_loss / max(1, sample_count))
                history["test_macro_f1"].append(epoch_metrics["macro_f1"])
                print(
                    f"model={model_name} seed={seed} epoch={epoch + 1}/{config.epochs} "
                    f"loss={history['train_loss'][-1]:.4f} "
                    f"test_macro_f1={epoch_metrics['macro_f1']:.4f}",
                    flush=True,
                )

            truth, prediction = _predict(model, test_loader, device)
            clean_metrics = classification_metrics(
                truth, prediction, len(dataset.class_names)
            )
            latency_ms = _measure_latency(
                model, test_loader, device,
                config.warmup_batches, config.latency_batches,
            )
            parameters = count_parameters(model)
            all_rows.append(_metric_row(
                model_name, "clean", clean_metrics, latency_ms, parameters, seed
            ))
            print(
                f"model={model_name} condition=clean "
                f"accuracy={clean_metrics['accuracy']:.4f} "
                f"macro_f1={clean_metrics['macro_f1']:.4f} "
                f"latency_ms={latency_ms:.3f}",
                flush=True,
            )

            if model_name == "gated_fusion":
                (output_dir / "confusion_gated_fusion.json").write_text(json.dumps({
                    "class_names": list(dataset.class_names),
                    "matrix": confusion_matrix(
                        truth, prediction, len(dataset.class_names)
                    ).tolist(),
                }, indent=2))
                (output_dir / "history_gated_fusion.json").write_text(
                    json.dumps(history, indent=2)
                )
                test_imu = normalized_imu[test_indices]
                test_pose = normalized_pose[test_indices]
                test_labels = dataset.labels[test_indices]
                for rate in config.robustness_missing_rates:
                    corrupt_pose, pose_available = apply_missing_samples(
                        test_pose, rate, seed + 101
                    )
                    pose_loader = _make_loader(
                        test_imu, corrupt_pose, test_labels,
                        config.batch_size, False, config.num_workers,
                    )
                    availability = np.column_stack((
                        np.ones(len(test_labels), dtype=np.float32), pose_available
                    )).astype(np.float32)
                    robust_truth, robust_prediction = _predict(
                        model, pose_loader, device, availability
                    )
                    metrics = classification_metrics(
                        robust_truth, robust_prediction, len(dataset.class_names)
                    )
                    all_rows.append(_metric_row(
                        model_name, f"pose_missing_{rate:.2f}", metrics,
                        latency_ms, parameters, seed,
                    ))

                    corrupt_imu, imu_available = apply_missing_samples(
                        test_imu, rate, seed + 202
                    )
                    imu_loader = _make_loader(
                        corrupt_imu, test_pose, test_labels,
                        config.batch_size, False, config.num_workers,
                    )
                    availability = np.column_stack((
                        imu_available, np.ones(len(test_labels), dtype=np.float32)
                    )).astype(np.float32)
                    robust_truth, robust_prediction = _predict(
                        model, imu_loader, device, availability
                    )
                    metrics = classification_metrics(
                        robust_truth, robust_prediction, len(dataset.class_names)
                    )
                    all_rows.append(_metric_row(
                        model_name, f"imu_missing_{rate:.2f}", metrics,
                        latency_ms, parameters, seed,
                    ))

    manifest = {
        "dataset": str(Path(dataset_path).resolve()),
        "device": str(device),
        "holdout_subjects": holdout,
        "class_names": list(dataset.class_names),
        "config": config.to_dict(),
        "note": "Metrics are valid only for this dataset, split, and lightweight budget.",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return write_summary(all_rows, output_dir / "summary.csv")
