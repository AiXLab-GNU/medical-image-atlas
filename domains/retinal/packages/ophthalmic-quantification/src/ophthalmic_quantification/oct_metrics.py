"""Adapter for the validated ``amd-oct-quant`` 25-metric contract."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


try:
    from amd_oct_quant.metrics2d import extract_2d_metrics, metric_dictionary
except ModuleNotFoundError:
    repository_root = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "PROJECT_STRUCTURE_CODEX.md").is_file()
    )
    dependency_source = repository_root / "projects/P002_amd_oct/packages/amd-oct-quant/src"
    sys.path.insert(0, str(dependency_source))
    from amd_oct_quant.metrics2d import extract_2d_metrics, metric_dictionary


OCT_METRIC_IDS = tuple(metric_dictionary()["metric_name"].tolist())


def extract_oct_metrics(label_mask: np.ndarray) -> dict[str, int | float]:
    result = extract_2d_metrics(label_mask)
    return {metric_id: result[metric_id] for metric_id in OCT_METRIC_IDS}


def oct_metric_catalog() -> tuple[dict[str, object], ...]:
    return tuple(metric_dictionary().to_dict(orient="records"))
