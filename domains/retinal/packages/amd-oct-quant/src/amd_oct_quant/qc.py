"""Range and provenance QC for quantitative metric records."""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd


def validate_metric_record(record: Mapping[str, object], *, width_px: int) -> list[str]:
    errors: list[str] = []
    for key, value in record.items():
        if not isinstance(value, (int, float, np.integer, np.floating)):
            continue
        numeric = float(value)
        if not np.isfinite(numeric):
            errors.append(f"{key}:nonfinite")
        if key.endswith("_area_px") or key.endswith("_component_count"):
            if numeric < 0:
                errors.append(f"{key}:negative")
        if key.endswith("_fraction") and not 0.0 <= numeric <= 1.0:
            errors.append(f"{key}:outside_0_1")
        if key.endswith("_presence") and numeric not in (0.0, 1.0):
            errors.append(f"{key}:not_binary")
        if key == "is_os_largest_gap_px" and not 0 <= numeric <= width_px:
            errors.append(f"{key}:outside_width")
    return errors


def validate_metric_table(frame: pd.DataFrame) -> dict[str, object]:
    failure_rows = frame[frame["extraction_failure"].fillna(True)]
    metric_columns = [
        column
        for column in frame.columns
        if any(token in column for token in ["_area_", "_component_", "_fraction", "_presence", "_gap_px"])
    ]
    nonfinite = {}
    for column in metric_columns:
        numeric = pd.to_numeric(frame[column], errors="coerce")
        bad = (~np.isfinite(numeric)) & (~frame["extraction_failure"].fillna(True))
        if int(bad.sum()):
            nonfinite[column] = int(bad.sum())
    duplicate_samples = int(frame["sample_uid"].duplicated().sum())
    mixed_mask_source = sorted(frame["mask_source"].dropna().astype(str).unique())
    return {
        "rows": len(frame),
        "extraction_failures": len(failure_rows),
        "extraction_failure_fraction": float(len(failure_rows) / len(frame)) if len(frame) else 0.0,
        "nonfinite_metric_counts": nonfinite,
        "duplicate_sample_uids": duplicate_samples,
        "mask_sources": mixed_mask_source,
        "passed": not len(failure_rows) and not nonfinite and not duplicate_samples and mixed_mask_source == ["ground_truth"],
    }
