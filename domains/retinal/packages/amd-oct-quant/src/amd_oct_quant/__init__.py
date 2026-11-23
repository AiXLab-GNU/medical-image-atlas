"""Public API for reusable AMD OCT quantification."""

from .agreement import agreement_statistics, concordance_correlation_coefficient, icc_a1
from .classification_metrics import classification_summary

from .metrics2d import METRIC_VERSION, extract_2d_metrics, metric_dictionary
from .palette import (
    CLASS_ID_TO_NAME,
    CLASS_NAME_TO_ID,
    DEFAULT_PALETTE_RGB,
    decode_rgb_mask,
    load_amd_sd_combined_png,
    split_combined_image,
)
from .pipeline import extract_amd_sd_manifest
from .qc import validate_metric_record, validate_metric_table
from .segmentation_metrics import confusion_matrix, metrics_from_confusion

__all__ = [
    "CLASS_ID_TO_NAME",
    "CLASS_NAME_TO_ID",
    "DEFAULT_PALETTE_RGB",
    "METRIC_VERSION",
    "decode_rgb_mask",
    "extract_2d_metrics",
    "extract_amd_sd_manifest",
    "load_amd_sd_combined_png",
    "metric_dictionary",
    "split_combined_image",
    "validate_metric_record",
    "validate_metric_table",
    "agreement_statistics",
    "concordance_correlation_coefficient",
    "icc_a1",
    "confusion_matrix",
    "metrics_from_confusion",
    "classification_summary",
]

__version__ = "0.2.1"
