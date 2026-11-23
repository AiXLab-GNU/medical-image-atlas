"""Architectural distortion and asymmetry measurements.

``convergence_index`` is a simplified form of the stellate-pattern feature of Karssemeijer & te Brake 1996:
in an annulus around a candidate centre, the share of line (ridge) pixels whose direction points to the
centre. Random parenchyma gives about 0.25 (±22.5° of 180°); converging spicules give more.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage import feature, filters

from ._common import Measurement, area, as_float, length, max_feret


def convergence_index(image, centre, radius_px, inner=0.25) -> Measurement:
    img = filters.gaussian(as_float(image), 2)
    h, w = img.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - centre[0], xx - centre[1])
    ring = (r > inner * radius_px) & (r < radius_px)
    if ring.sum() < 50:
        return Measurement('ft_ad_convergence_index', None, 'ratio', 'not_evaluable', '띠가 너무 작음')
    sigma = max(1.5, radius_px / 40)
    ridge = filters.sato(img, sigmas=[sigma, 2 * sigma], black_ridges=False)
    Arr, Arc, Acc = feature.structure_tensor(img, sigma=2 * sigma, order='rc')
    theta = 0.5 * np.arctan2(2 * Arc, Acc - Arr) + np.pi / 2
    sel = ring & (ridge > np.quantile(ridge[ring], 0.85))
    radial = np.arctan2(yy[sel] - centre[0], xx[sel] - centre[1])
    align = np.abs(np.cos(theta[sel] - radial))
    hit = align > np.cos(np.pi / 8)
    pts = np.c_[yy[sel], xx[sel]][hit]
    return Measurement('ft_ad_convergence_index', round(float(hit.mean()), 3), 'ratio',
                       note='무작위 배열이면 약 0.25',
                       detail={'ring_px': [round(inner * radius_px, 1), round(float(radius_px), 1)],
                               'points': pts[:: max(1, len(pts) // 400)].tolist()})


def distortion_extent(mask, pixel_mm=None) -> Measurement:
    value, unit = length(max_feret(np.asarray(mask, bool)), pixel_mm)
    return Measurement('ft_ad_extent', round(value, 1), unit)


def asymmetry_area(mask, pixel_mm=None) -> Measurement:
    value, unit = area(np.asarray(mask, bool).sum(), pixel_mm)
    return Measurement('ft_asym_area', value, unit)


def bilateral_difference(dense_left, breast_left, dense_right, breast_right) -> Measurement:
    """Difference of percent dense area between the left and right images of the same view."""
    pl = 100 * dense_left.sum() / max(breast_left.sum(), 1)
    pr = 100 * dense_right.sum() / max(breast_right.sum(), 1)
    return Measurement('ft_asym_bilateral_difference', round(float(pl - pr), 1), '%p',
                       detail={'left_percent': round(float(pl), 1), 'right_percent': round(float(pr), 1)})


def lesion_size(mask, pixel_mm=None) -> Measurement:
    value, unit = length(max_feret(np.asarray(mask, bool)), pixel_mm)
    return Measurement('ft_lesion_generic_size', round(value, 1), unit)


def presence(mask, min_px=1) -> Measurement:
    n = int(np.asarray(mask, bool).sum())
    return Measurement('ft_lesion_generic_presence', n >= min_px, 'presence')


def lesion_count(mask) -> Measurement:
    _, n = ndi.label(np.asarray(mask, bool))
    return Measurement('ft_lesion_generic_count', int(n), 'count', 'ok' if n else 'not_observed')
