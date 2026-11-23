"""Reusable MARIO-compatible multiclass performance metrics with valid QWK scope."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    log_loss,
    recall_score,
)


def classification_summary(
    targets: np.ndarray,
    probabilities: np.ndarray,
    *,
    class_names: tuple[str, ...] = ("Reduced", "Stable", "Worsened", "Other_Uninterpretable"),
) -> dict[str, object]:
    """Summarize four-class predictions and 0/1/2-only ordinal sensitivity.

    Class 3 is Other/Uninterpretable and is never placed on the ordinal QWK scale. For the QWK
    sensitivity, rows whose true class is 0/1/2 are retained and probabilities are restricted to
    those three interpretable classes before argmax.
    """

    y = np.asarray(targets, dtype=np.int64).reshape(-1)
    probability = np.asarray(probabilities, dtype=np.float64)
    if probability.shape != (len(y), len(class_names)):
        raise ValueError(f"Expected probability shape {(len(y), len(class_names))}, got {probability.shape}")
    if not np.isfinite(probability).all() or (probability < 0).any():
        raise ValueError("Probabilities must be finite and nonnegative")
    row_sum = probability.sum(axis=1, keepdims=True)
    if (row_sum <= 0).any():
        raise ValueError("Each probability row must have positive mass")
    probability = probability / row_sum
    prediction = probability.argmax(axis=1)
    labels = np.arange(len(class_names))
    recalls = recall_score(y, prediction, labels=labels, average=None, zero_division=0)
    ordinal = y < 3
    ordinal_prediction = probability[ordinal, :3].argmax(axis=1)
    qwk = cohen_kappa_score(y[ordinal], ordinal_prediction, labels=[0, 1, 2], weights="quadratic")
    return {
        "n": int(len(y)),
        "macro_f1": float(f1_score(y, prediction, labels=labels, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "accuracy": float(accuracy_score(y, prediction)),
        "log_loss": float(log_loss(y, probability, labels=labels)),
        "class_recall": {class_names[index]: float(recalls[index]) for index in labels},
        "confusion_matrix": confusion_matrix(y, prediction, labels=labels).astype(int).tolist(),
        "qwk_3class_sensitivity": float(qwk),
        "qwk_rows_true_class_0_1_2": int(ordinal.sum()),
        "qwk_rule": "true class 0/1/2 only; argmax after restricting probabilities to classes 0/1/2",
    }
