"""Reusable manifest-to-metric-table extraction pipelines."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .metrics2d import METRIC_VERSION, extract_2d_metrics
from .palette import load_amd_sd_combined_png
from .qc import validate_metric_record


def extract_amd_sd_manifest(
    manifest: str | Path | pd.DataFrame,
    *,
    project_root: str | Path,
) -> pd.DataFrame:
    """Extract ground-truth metrics for included AMD-SD manifest rows."""

    source = pd.read_csv(manifest) if not isinstance(manifest, pd.DataFrame) else manifest.copy()
    included = source[source["included"].astype(str).str.lower().isin({"true", "1"})].copy()
    included = included.sort_values("sample_uid").reset_index(drop=True)
    project = Path(project_root).resolve()
    records = []
    for row in included.to_dict("records"):
        record = {
            "dataset": "AMD-SD",
            "analysis_split": row["analysis_split"],
            "sample_uid": row["sample_uid"],
            "patient_key": f"amd_sd_patient_{int(row['patient_id']):03d}",
            "eye_key": f"amd_sd_eye_{int(row['eye_id']):03d}",
            "eye_side": row["eye_side"],
            "relative_source_path": row["relative_source_path"],
            "source_sha256": row["source_sha256"],
            "width_px": 570,
            "height_px": 380,
            "spacing_x": None,
            "spacing_y": None,
            "spacing_source": "unavailable",
            "physical_unit_verified": False,
            "mask_source": "ground_truth",
            "segmentation_model": None,
            "checkpoint_sha256": None,
            "metric_version": METRIC_VERSION,
            "extraction_failure": False,
            "exclusion_reason": "",
        }
        try:
            _, labels, decoder = load_amd_sd_combined_png(project / row["relative_source_path"])
            metrics = extract_2d_metrics(labels)
            errors = validate_metric_record(metrics, width_px=labels.shape[1])
            if errors:
                raise ValueError("metric_qc:" + ";".join(errors))
            record.update(metrics)
            record.update(
                decoder_rule=decoder.rule,
                decoder_tie_pixels=decoder.tie_pixels,
                decoder_maximum_distance=decoder.maximum_distance,
                decoder_within_64_fraction=decoder.within_64_fraction,
                qc_status="PASS",
            )
        except Exception as error:
            record.update(
                extraction_failure=True,
                exclusion_reason=f"{type(error).__name__}:{error}",
                qc_status="FAIL",
            )
        records.append(record)
    return pd.DataFrame(records).sort_values("sample_uid").reset_index(drop=True)
