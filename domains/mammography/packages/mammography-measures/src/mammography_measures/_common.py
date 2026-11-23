"""Shared result type and calibration helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

STATUSES = {'ok', 'not_observed', 'not_evaluable'}


@dataclass
class Measurement:
    """One computed atlas feature. ``value`` is None when the status is not ``ok``."""
    feature_id: str
    value: Any
    unit: str
    status: str = 'ok'
    note: str = ''
    detail: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f'invalid status {self.status}')


def length(px: float, pixel_mm: float | None) -> tuple[float, str]:
    """Pixel length → (value, unit); millimetres only when the pixel size is known."""
    return (float(px) * pixel_mm, 'mm') if pixel_mm else (float(px), 'px')


def area(px2: float, pixel_mm: float | None) -> tuple[float, str]:
    return (float(px2) * pixel_mm ** 2, 'mm2') if pixel_mm else (float(px2), 'px2')


def as_float(image: np.ndarray) -> np.ndarray:
    """Grey image as float in [0, 1] (RGB is averaged; 8- and 16-bit are rescaled by their range)."""
    img = np.asarray(image)
    if img.ndim == 3:
        img = img[..., :3].mean(axis=2)
    img = img.astype(np.float64)
    top = img.max()
    return img / top if top > 0 else img


def largest_component(mask: np.ndarray) -> np.ndarray:
    from scipy import ndimage as ndi
    labels, n = ndi.label(mask)
    if n == 0:
        return np.zeros_like(mask, dtype=bool)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(np.argmax(sizes))


def max_feret(mask: np.ndarray) -> float:
    """Largest distance between two boundary pixels of a mask (pixels)."""
    from scipy.spatial import ConvexHull
    pts = np.argwhere(mask)
    if len(pts) < 3:
        return float(len(pts) > 0)
    try:
        hull = pts[ConvexHull(pts).vertices]
    except Exception:  # collinear points
        hull = pts
    d = np.sqrt(((hull[:, None, :] - hull[None, :, :]) ** 2).sum(-1))
    return float(d.max()) + 1.0
