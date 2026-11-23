"""Shared result type and calibration helpers (microns per pixel)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import ndimage as ndi

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


def area_mm2(px: float, mpp: float | None) -> tuple[float, str]:
    """Pixel count → (value, unit): mm² with a calibration, otherwise px²."""
    return (float(px) * mpp * mpp / 1e6, 'mm2') if mpp else (float(px), 'px2')


def area_um2(px: float, mpp: float | None) -> tuple[float, str]:
    return (float(px) * mpp * mpp, 'um2') if mpp else (float(px), 'px2')


def length_mm(px: float, mpp: float | None) -> tuple[float, str]:
    return (float(px) * mpp / 1000.0, 'mm') if mpp else (float(px), 'px')


def largest_component(mask: np.ndarray) -> np.ndarray:
    labels, n = ndi.label(mask)
    if n == 0:
        return np.zeros_like(mask, dtype=bool)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(np.argmax(sizes))


def max_feret(mask: np.ndarray) -> float:
    """Largest distance between two pixels of a mask (pixels)."""
    from scipy.spatial import ConvexHull
    pts = np.argwhere(mask)
    if len(pts) < 3:
        return float(len(pts) > 0)
    try:
        pts = pts[ConvexHull(pts).vertices]
    except Exception:  # collinear points
        pass
    d = np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1))
    return float(d.max()) + 1.0


def rgb_u8(image: np.ndarray) -> np.ndarray:
    img = np.asarray(image)
    if img.ndim != 3 or img.shape[2] < 3:
        raise ValueError('expected an RGB image')
    img = img[..., :3]
    if img.dtype != np.uint8:
        img = np.clip(img * (255 if img.max() <= 1 else 1), 0, 255).astype(np.uint8)
    return img
