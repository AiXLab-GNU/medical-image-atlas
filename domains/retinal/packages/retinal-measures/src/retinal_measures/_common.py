"""Shared result type, spacing and input checks.

Every measurement returns a :class:`Measurement`. Missing evidence is never turned into 0:
``status`` is ``ok``, ``not_observed`` (evaluated, nothing found) or ``not_evaluable``
(input insufficient), and ``value`` is ``None`` unless the status is ``ok`` or the
quantity is a genuine zero/count of an evaluated field.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Measurement:
    feature_id: str
    value: Any
    unit: str
    status: str = 'ok'
    note: str = ''
    detail: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.status not in {'ok', 'not_observed', 'not_evaluable'}:
            raise ValueError(f'invalid status {self.status}')


@dataclass(frozen=True)
class Spacing:
    """Physical size of one pixel/voxel. Leave a field as None when it is not calibrated."""
    x_mm: float | None = None      # lateral (fundus column / OCT A-scan step)
    y_mm: float | None = None      # fundus row / OCT B-scan step (slow axis)
    z_um: float | None = None      # OCT axial step

    @property
    def area_mm2(self) -> float | None:
        if self.x_mm is None or self.y_mm is None:
            return None
        return self.x_mm * self.y_mm


def as_mask(mask, name: str = 'mask', ndim: int | None = None) -> np.ndarray:
    array = np.asarray(mask)
    if ndim is not None and array.ndim != ndim:
        raise ValueError(f'{name} must be {ndim}D, got shape {array.shape}')
    return array.astype(bool)


def not_evaluable(feature_id: str, unit: str, note: str) -> Measurement:
    return Measurement(feature_id, None, unit, 'not_evaluable', note)


def area_value(pixels: float, spacing: Spacing | None) -> tuple[float, str]:
    if spacing is not None and spacing.area_mm2 is not None:
        return pixels * spacing.area_mm2, 'mm2'
    return float(pixels), 'px2'


def length_value(pixels: float, spacing: Spacing | None) -> tuple[float, str]:
    if spacing is not None and spacing.x_mm is not None and spacing.y_mm in (None, spacing.x_mm):
        return pixels * spacing.x_mm, 'mm'
    return float(pixels), 'px'
