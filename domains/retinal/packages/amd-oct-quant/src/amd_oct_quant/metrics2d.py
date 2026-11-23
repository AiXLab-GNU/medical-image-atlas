"""Outcome-independent pixel-based 2D AMD OCT mask metrics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import ndimage

from .palette import CLASS_NAME_TO_ID


METRIC_VERSION = "amd_oct_quant.metrics2d.v0.1.0"
AREA_LESIONS = ("IRF", "SRF", "PED", "SHRM")
CONNECTIVITY_8 = np.ones((3, 3), dtype=np.uint8)


def _component_metrics(binary: np.ndarray) -> tuple[int, float]:
    area = int(binary.sum())
    if area == 0:
        return 0, 0.0
    components, count = ndimage.label(binary, structure=CONNECTIVITY_8)
    sizes = np.bincount(components.reshape(-1))[1:]
    largest_fraction = float(sizes.max(initial=0) / area)
    return int(count), largest_fraction


def _largest_false_run(values: np.ndarray) -> int:
    present = np.asarray(values, dtype=bool)
    absent = ~present
    if absent.size == 0 or not absent.any():
        return 0
    padded = np.concatenate(([False], absent, [False])).astype(np.int8)
    changes = np.diff(padded)
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1)
    return int((ends - starts).max(initial=0))


def extract_2d_metrics(
    label_mask: np.ndarray,
    *,
    central_band_fraction: float = 0.20,
) -> dict[str, int | float]:
    """Calculate the locked minimal metric set from one integer label mask."""

    labels = np.asarray(label_mask)
    if labels.ndim != 2:
        raise ValueError(f"Expected a 2D label mask, got shape {labels.shape}")
    if not np.issubdtype(labels.dtype, np.integer):
        raise TypeError(f"Label mask must have integer dtype, got {labels.dtype}")
    unique = np.unique(labels)
    invalid = unique[(unique < 0) | (unique > 5)]
    if len(invalid):
        raise ValueError(f"Unknown class IDs: {invalid.tolist()}")
    if not (0 < central_band_fraction <= 1):
        raise ValueError("central_band_fraction must be in (0, 1]")

    height, width = labels.shape
    image_area = int(height * width)
    result: dict[str, int | float] = {}
    for lesion in AREA_LESIONS:
        key = lesion.lower()
        binary = labels == CLASS_NAME_TO_ID[lesion]
        area = int(binary.sum())
        component_count, largest_fraction = _component_metrics(binary)
        result[f"{key}_presence"] = int(area > 0)
        result[f"{key}_area_px"] = area
        result[f"{key}_area_fraction"] = float(area / image_area) if image_area else 0.0
        result[f"{key}_component_count"] = component_count
        result[f"{key}_largest_component_fraction"] = largest_fraction

    is_os = labels == CLASS_NAME_TO_ID["IS_OS"]
    column_presence = is_os.any(axis=0) if height else np.zeros(width, dtype=bool)
    band_width = max(1, int(round(width * central_band_fraction))) if width else 0
    start = max(0, (width - band_width) // 2)
    end = min(width, start + band_width)
    central_fraction = float(column_presence[start:end].mean()) if end > start else 0.0
    result["is_os_presence"] = int(column_presence.any())
    result["is_os_preserved_fraction"] = float(column_presence.mean()) if width else 0.0
    result["is_os_central_preserved_fraction"] = central_fraction
    result["is_os_central_preserved"] = int(central_fraction > 0.0)
    result["is_os_largest_gap_px"] = _largest_false_run(column_presence)
    return result


def metric_dictionary() -> pd.DataFrame:
    """Return the outcome-independent metric dictionary distributed with the package."""

    rows: list[dict[str, Any]] = []
    for lesion in AREA_LESIONS:
        key = lesion.lower()
        definitions = [
            ("presence", "1(area_px > 0)", "binary", "0", "lesion presence"),
            ("area_px", "count(mask == class_id)", "px", "0", "lesion pixel burden"),
            ("area_fraction", "area_px / (height*width)", "fraction", "0.0", "size-normalized burden"),
            ("component_count", "8-connected component count", "count", "0", "fragmentation count"),
            ("largest_component_fraction", "largest component area / area_px", "fraction_of_lesion_area", "0.0", "dominant-lesion share"),
        ]
        for suffix, formula, unit, zero_rule, meaning in definitions:
            rows.append(
                {
                    "metric_name": f"{key}_{suffix}",
                    "lesion": lesion,
                    "formula": formula,
                    "unit": unit,
                    "zero_rule": zero_rule,
                    "input": "integer 2D mask",
                    "clinical_meaning": meaning,
                    "failure_condition": "invalid mask shape/class ID",
                    "algorithm_version": METRIC_VERSION,
                    "outcome_dependent": False,
                }
            )
    rows.extend(
        [
            {
                "metric_name": "is_os_presence",
                "lesion": "IS_OS",
                "formula": "1(any image column contains IS/OS)",
                "unit": "binary",
                "zero_rule": "0",
                "input": "integer 2D mask",
                "clinical_meaning": "any annotated ellipsoid-zone preservation",
                "failure_condition": "invalid mask shape/class ID",
                "algorithm_version": METRIC_VERSION,
                "outcome_dependent": False,
            },
            {
                "metric_name": "is_os_preserved_fraction",
                "lesion": "IS_OS",
                "formula": "columns containing IS/OS / image width",
                "unit": "fraction_of_image_columns",
                "zero_rule": "0.0",
                "input": "integer 2D mask",
                "clinical_meaning": "total horizontal preservation ratio",
                "failure_condition": "invalid mask shape/class ID",
                "algorithm_version": METRIC_VERSION,
                "outcome_dependent": False,
            },
            {
                "metric_name": "is_os_central_preserved_fraction",
                "lesion": "IS_OS",
                "formula": "central 20% columns containing IS/OS / central-band width",
                "unit": "fraction_of_central_columns",
                "zero_rule": "0.0",
                "input": "integer 2D mask",
                "clinical_meaning": "central ellipsoid-zone preservation",
                "failure_condition": "invalid mask shape/class ID",
                "algorithm_version": METRIC_VERSION,
                "outcome_dependent": False,
            },
            {
                "metric_name": "is_os_central_preserved",
                "lesion": "IS_OS",
                "formula": "1(is_os_central_preserved_fraction > 0)",
                "unit": "binary",
                "zero_rule": "0",
                "input": "integer 2D mask",
                "clinical_meaning": "any central-band preservation",
                "failure_condition": "invalid mask shape/class ID",
                "algorithm_version": METRIC_VERSION,
                "outcome_dependent": False,
            },
            {
                "metric_name": "is_os_largest_gap_px",
                "lesion": "IS_OS",
                "formula": "longest consecutive run of columns without IS/OS",
                "unit": "px",
                "zero_rule": "image width when IS/OS fully absent",
                "input": "integer 2D mask",
                "clinical_meaning": "largest horizontal disruption",
                "failure_condition": "invalid mask shape/class ID",
                "algorithm_version": METRIC_VERSION,
                "outcome_dependent": False,
            },
        ]
    )
    return pd.DataFrame(rows)
