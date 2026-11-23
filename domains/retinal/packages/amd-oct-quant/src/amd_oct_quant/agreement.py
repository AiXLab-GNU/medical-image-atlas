"""Reusable quantitative agreement statistics for paired phenotype measurements."""

from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr


def _paired(reference: np.ndarray, estimate: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(reference, dtype=np.float64).reshape(-1)
    y = np.asarray(estimate, dtype=np.float64).reshape(-1)
    if x.shape != y.shape:
        raise ValueError(f"Paired arrays must have the same shape, got {x.shape} and {y.shape}")
    if len(x) == 0:
        raise ValueError("At least one paired observation is required")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Paired arrays must be finite")
    return x, y


def concordance_correlation_coefficient(reference: np.ndarray, estimate: np.ndarray) -> float:
    """Lin's CCC using population variance and covariance."""

    x, y = _paired(reference, estimate)
    mean_x, mean_y = float(x.mean()), float(y.mean())
    var_x, var_y = float(x.var(ddof=0)), float(y.var(ddof=0))
    covariance = float(np.mean((x - mean_x) * (y - mean_y)))
    denominator = var_x + var_y + (mean_x - mean_y) ** 2
    if denominator == 0.0:
        return 1.0 if np.array_equal(x, y) else 0.0
    return float(2.0 * covariance / denominator)


def icc_a1(reference: np.ndarray, estimate: np.ndarray) -> float:
    """Two-way random-effects, absolute-agreement, single-measure ICC(A,1)."""

    x, y = _paired(reference, estimate)
    if len(x) < 2:
        return float("nan")
    values = np.column_stack((x, y))
    n, k = values.shape
    grand = float(values.mean())
    subject_means = values.mean(axis=1)
    rater_means = values.mean(axis=0)
    ms_subject = float(k * np.square(subject_means - grand).sum() / (n - 1))
    ms_rater = float(n * np.square(rater_means - grand).sum() / (k - 1))
    residual = values - subject_means[:, None] - rater_means[None, :] + grand
    ms_error = float(np.square(residual).sum() / ((n - 1) * (k - 1)))
    denominator = ms_subject + (k - 1) * ms_error + k * (ms_rater - ms_error) / n
    if denominator == 0.0:
        return 1.0 if np.array_equal(x, y) else float("nan")
    return float((ms_subject - ms_error) / denominator)


def agreement_statistics(reference: np.ndarray, estimate: np.ndarray) -> dict[str, float | int]:
    """Return CCC, ICC(A,1), MAE, Spearman and Bland-Altman statistics."""

    x, y = _paired(reference, estimate)
    differences = y - x
    bias = float(differences.mean())
    difference_sd = float(differences.std(ddof=1)) if len(differences) > 1 else 0.0
    if np.array_equal(x, y):
        rho = 1.0
    elif np.unique(x).size < 2 or np.unique(y).size < 2:
        rho = 0.0
    else:
        rho = float(spearmanr(x, y).statistic)
    return {
        "n": int(len(x)),
        "ccc": concordance_correlation_coefficient(x, y),
        "icc_a1": icc_a1(x, y),
        "mae": float(np.abs(differences).mean()),
        "spearman": rho,
        "bland_altman_bias": bias,
        "bland_altman_lower_loa": float(bias - 1.96 * difference_sd),
        "bland_altman_upper_loa": float(bias + 1.96 * difference_sd),
    }
