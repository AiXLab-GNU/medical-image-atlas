"""Deterministic binary-mask morphology and agreement metrics."""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage.measure import label, perimeter, regionprops


BINARY_MASK_METRIC_IDS = (
    "presence",
    "area_px",
    "area_fraction",
    "area_physical",
    "component_count",
    "largest_component_fraction",
    "centroid_x_fraction",
    "centroid_y_fraction",
    "bbox_width_fraction",
    "bbox_height_fraction",
    "perimeter_px",
    "circularity",
    "eccentricity",
)
AGREEMENT_METRIC_IDS = (
    "dice",
    "iou",
    "precision",
    "recall",
    "specificity",
    "both_empty",
)


def _as_2d_bool(mask: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(mask)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a 2D mask")
    if not np.issubdtype(array.dtype, np.bool_) and not np.isin(array, [0, 1]).all():
        raise ValueError(f"{name} must be binary")
    return array.astype(bool, copy=False)


def binary_mask_metrics(
    mask: np.ndarray,
    *,
    pixel_spacing: tuple[float, float] | None = None,
) -> dict[str, int | float]:
    binary = _as_2d_bool(mask, "mask")
    area = int(binary.sum())
    image_area = binary.size
    physical_area = float("nan")
    if pixel_spacing is not None:
        if len(pixel_spacing) != 2 or not all(np.isfinite(pixel_spacing)) or not all(value > 0 for value in pixel_spacing):
            raise ValueError("pixel_spacing must contain two positive finite values")
        physical_area = float(area * pixel_spacing[0] * pixel_spacing[1])
    output: dict[str, int | float] = {
        "presence": int(area > 0),
        "area_px": area,
        "area_fraction": float(area / image_area) if image_area else 0.0,
        "area_physical": physical_area,
        "component_count": 0,
        "largest_component_fraction": 0.0,
        "centroid_x_fraction": float("nan"),
        "centroid_y_fraction": float("nan"),
        "bbox_width_fraction": 0.0,
        "bbox_height_fraction": 0.0,
        "perimeter_px": 0.0,
        "circularity": float("nan"),
        "eccentricity": float("nan"),
    }
    if area == 0:
        return output
    components = label(binary, connectivity=2)
    regions = regionprops(components)
    largest = max(regions, key=lambda region: region.area)
    y0, x0, y1, x1 = largest.bbox
    boundary_length = float(perimeter(binary, neighborhood=8))
    output.update(
        {
            "component_count": len(regions),
            "largest_component_fraction": float(largest.area / area),
            "centroid_x_fraction": float(largest.centroid[1] / max(1, binary.shape[1] - 1)),
            "centroid_y_fraction": float(largest.centroid[0] / max(1, binary.shape[0] - 1)),
            "bbox_width_fraction": float((x1 - x0) / binary.shape[1]),
            "bbox_height_fraction": float((y1 - y0) / binary.shape[0]),
            "perimeter_px": boundary_length,
            "circularity": float(4 * np.pi * area / boundary_length**2) if boundary_length else float("nan"),
            "eccentricity": float(largest.eccentricity),
        }
    )
    return output


def segmentation_agreement(predicted: np.ndarray, target: np.ndarray) -> dict[str, int | float]:
    prediction = _as_2d_bool(predicted, "predicted")
    truth = _as_2d_bool(target, "target")
    if prediction.shape != truth.shape:
        raise ValueError("predicted and target masks must have identical shapes")
    tp = int((prediction & truth).sum())
    fp = int((prediction & ~truth).sum())
    fn = int((~prediction & truth).sum())
    tn = int((~prediction & ~truth).sum())
    both_empty = int(not prediction.any() and not truth.any())
    dice_denominator = 2 * tp + fp + fn
    union = tp + fp + fn
    return {
        "dice": 1.0 if both_empty else float(2 * tp / dice_denominator),
        "iou": 1.0 if both_empty else float(tp / union),
        "precision": 1.0 if both_empty else (float(tp / (tp + fp)) if tp + fp else 0.0),
        "recall": 1.0 if both_empty else (float(tp / (tp + fn)) if tp + fn else 0.0),
        "specificity": float(tn / (tn + fp)) if tn + fp else float("nan"),
        "both_empty": both_empty,
    }
