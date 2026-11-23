"""Where a finding lies relative to the nipple on one view (BI-RADS location descriptors).

Quadrant and clock position need the same lesion matched on the CC and MLO views of one breast
(``quadrant`` / ``clock_position``); a single view gives only one half (``view_half``).
Display convention assumed: CC with the lateral side at the top, MLO with the cranial side at the top.
"""
from __future__ import annotations

import numpy as np

from ._common import Measurement, length


def centroid(mask: np.ndarray) -> tuple[float, float]:
    r, c = np.argwhere(mask).mean(axis=0)
    return float(r), float(c)


def distance_from_nipple(point, nipple, pixel_mm: float | None = None) -> Measurement:
    value, unit = length(np.hypot(point[0] - nipple[0], point[1] - nipple[1]), pixel_mm)
    return Measurement('ft_lesion_distance_nipple', round(value, 1), unit)


def depth_third(point, nipple, pnl_foot) -> Measurement:
    """Anterior / middle / posterior third by projection on the posterior nipple line."""
    axis = np.array([pnl_foot[0] - nipple[0], pnl_foot[1] - nipple[1]], float)
    total = np.linalg.norm(axis)
    if total == 0:
        return Measurement('ft_lesion_depth_third', None, 'category', 'not_evaluable', '후유두선 길이 0')
    t = float(np.dot([point[0] - nipple[0], point[1] - nipple[1]], axis) / total ** 2)
    label = 'anterior' if t < 1 / 3 else ('middle' if t < 2 / 3 else 'posterior')
    return Measurement('ft_lesion_depth_third', label, 'category', detail={'fraction_of_pnl': round(t, 2)})


def view_half(point, nipple, pnl_foot, view: str) -> Measurement:
    """CC: lateral (top) or medial (bottom) of the nipple line; MLO: upper or lower."""
    axis = np.array([pnl_foot[0] - nipple[0], pnl_foot[1] - nipple[1]], float)
    v = np.array([point[0] - nipple[0], point[1] - nipple[1]], float)
    t = float(v @ axis / max(axis @ axis, 1e-9))
    on_line = np.array(nipple, float) + t * axis          # nearest point of the nipple→chest line
    upper = point[0] < on_line[0]                         # smaller row = toward the top of the image
    if view.upper() == 'CC':
        label = 'lateral' if upper else 'medial'
    else:
        label = 'upper' if upper else 'lower'
    return Measurement('ft_lesion_view_half', label, 'category', note=f'{view.upper()} 한 영상 기준')


def quadrant(cc_half: str, mlo_half: str) -> Measurement:
    """Combine the CC half (lateral/medial) and the MLO half (upper/lower) of one matched lesion."""
    names = {('upper', 'lateral'): 'UOQ', ('upper', 'medial'): 'UIQ', ('lower', 'lateral'): 'LOQ',
             ('lower', 'medial'): 'LIQ'}
    q = names.get((mlo_half, cc_half))
    if q is None:
        return Measurement('ft_lesion_quadrant', None, 'category', 'not_evaluable', 'CC·MLO 위치 필요')
    return Measurement('ft_lesion_quadrant', q, 'category')


def clock_position(cc_offset: float, mlo_offset: float, laterality: str) -> Measurement:
    """Clock hour from signed offsets: CC lateral(+)/medial(−) and MLO upper(+)/lower(−), any common unit."""
    if cc_offset == 0 and mlo_offset == 0:
        return Measurement('ft_lesion_clock_position', 'subareolar', 'category')
    ang = np.degrees(np.arctan2(mlo_offset, cc_offset))           # 0° = lateral, 90° = up
    # facing the patient: right breast lateral = 9 o'clock, left breast lateral = 3 o'clock
    hour = (3 - ang / 30) if laterality.upper().startswith('L') else (9 + ang / 30)
    hour = int(round(hour)) % 12 or 12
    return Measurement('ft_lesion_clock_position', f'{hour}:00', 'category')
