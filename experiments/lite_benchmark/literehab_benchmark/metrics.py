from __future__ import annotations

import numpy as np


def confusion_matrix(truth, prediction, num_classes: int) -> np.ndarray:
    truth = np.asarray(truth, dtype=np.int64)
    prediction = np.asarray(prediction, dtype=np.int64)
    if truth.shape != prediction.shape or truth.ndim != 1:
        raise ValueError("truth and prediction must be aligned 1D arrays")
    if num_classes <= 0:
        raise ValueError("num_classes must be positive")
    matrix = np.zeros((num_classes, num_classes), dtype=np.int64)
    for actual, predicted in zip(truth, prediction):
        if not 0 <= actual < num_classes or not 0 <= predicted < num_classes:
            raise ValueError("class index outside configured range")
        matrix[actual, predicted] += 1
    return matrix


def classification_metrics(truth, prediction, num_classes: int) -> dict[str, float]:
    matrix = confusion_matrix(truth, prediction, num_classes)
    support = matrix.sum(axis=1)
    predicted = matrix.sum(axis=0)
    true_positive = np.diag(matrix).astype(np.float64)
    recall = np.divide(
        true_positive, support, out=np.zeros_like(true_positive), where=support != 0
    )
    precision = np.divide(
        true_positive, predicted, out=np.zeros_like(true_positive), where=predicted != 0
    )
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros_like(true_positive),
        where=(precision + recall) != 0,
    )
    total = matrix.sum()
    return {
        "accuracy": float(true_positive.sum() / total) if total else 0.0,
        "macro_f1": float(f1.mean()),
        "balanced_accuracy": float(recall.mean()),
    }
