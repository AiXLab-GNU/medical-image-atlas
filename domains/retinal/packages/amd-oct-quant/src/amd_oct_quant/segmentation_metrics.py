"""Reusable label-map segmentation metrics with explicit empty-class behavior."""

from __future__ import annotations

import numpy as np


def confusion_matrix(reference: np.ndarray, estimate: np.ndarray, *, num_classes: int) -> np.ndarray:
    truth = np.asarray(reference)
    prediction = np.asarray(estimate)
    if truth.shape != prediction.shape:
        raise ValueError(f"Label maps must match, got {truth.shape} and {prediction.shape}")
    if not np.issubdtype(truth.dtype, np.integer) or not np.issubdtype(prediction.dtype, np.integer):
        raise TypeError("Label maps must use integer dtype")
    if num_classes < 2:
        raise ValueError("num_classes must be at least 2")
    if truth.size and (truth.min() < 0 or truth.max() >= num_classes):
        raise ValueError("Reference label outside class range")
    if prediction.size and (prediction.min() < 0 or prediction.max() >= num_classes):
        raise ValueError("Estimated label outside class range")
    encoded = truth.reshape(-1).astype(np.int64) * num_classes + prediction.reshape(-1)
    return np.bincount(encoded, minlength=num_classes * num_classes).reshape(num_classes, num_classes)


def metrics_from_confusion(matrix: np.ndarray) -> dict[int, dict[str, float | int]]:
    confusion = np.asarray(matrix, dtype=np.int64)
    if confusion.ndim != 2 or confusion.shape[0] != confusion.shape[1]:
        raise ValueError("Confusion matrix must be square")
    output: dict[int, dict[str, float | int]] = {}
    for class_id in range(confusion.shape[0]):
        true_positive = int(confusion[class_id, class_id])
        false_negative = int(confusion[class_id, :].sum() - true_positive)
        false_positive = int(confusion[:, class_id].sum() - true_positive)
        denominator_dice = 2 * true_positive + false_positive + false_negative
        denominator_iou = true_positive + false_positive + false_negative
        output[class_id] = {
            "true_positive_px": true_positive,
            "false_positive_px": false_positive,
            "false_negative_px": false_negative,
            "dice": float(2 * true_positive / denominator_dice) if denominator_dice else float("nan"),
            "iou": float(true_positive / denominator_iou) if denominator_iou else float("nan"),
            "precision": float(true_positive / (true_positive + false_positive))
            if true_positive + false_positive else float("nan"),
            "recall": float(true_positive / (true_positive + false_negative))
            if true_positive + false_negative else float("nan"),
        }
    return output
