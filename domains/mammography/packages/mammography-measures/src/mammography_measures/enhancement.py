"""Contrast-enhanced mammography (CEM) measurements on the recombined (iodine) image."""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage import filters

from ._common import Measurement, as_float, length, max_feret


def intensity_ratio(recombined, mask, ring=(0.5, 1.5), background_min=0.03) -> Measurement:
    """Mean lesion signal ÷ mean signal of a surrounding ring (inner/outer offsets in lesion radii).

    Ring pixels darker than ``background_min`` (air outside the breast) are excluded.
    """
    img = filters.gaussian(as_float(recombined), 1)
    m = np.asarray(mask, bool)
    if not m.any():
        return Measurement('ft_enh_intensity_ratio', None, 'ratio', 'not_evaluable', '병변 범위 없음')
    radius = np.sqrt(m.sum() / np.pi)
    outer = ndi.binary_dilation(m, iterations=max(int(ring[1] * radius), 2))
    inner = ndi.binary_dilation(m, iterations=max(int(ring[0] * radius), 1))
    band = outer & ~inner & (img > background_min)
    if band.sum() < 20:
        return Measurement('ft_enh_intensity_ratio', None, 'ratio', 'not_evaluable', '주변 실질 띠가 너무 작음')
    ratio = float(img[m].mean() / max(img[band].mean(), 1e-6))
    return Measurement('ft_enh_intensity_ratio', round(ratio, 2), 'ratio', note='병변 평균 ÷ 둘레 띠 평균',
                       detail={'lesion_mean': round(float(img[m].mean()), 3), 'ring_mean': round(float(img[band].mean()), 3)})


def nme_extent(mask, pixel_mm=None) -> Measurement:
    value, unit = length(max_feret(np.asarray(mask, bool)), pixel_mm)
    return Measurement('ft_nme_extent', round(value, 1), unit, note='증강 범위의 최대 지름')


def enhancing_region(recombined, centre, radius, quantile=0.75):
    """Service estimate of an enhancing region inside a reader circle: bright pixels (above the given quantile of the
    circle) connected to the brightest blob nearest the centre, holes filled."""
    img = filters.gaussian(as_float(recombined), 2)
    h, w = img.shape
    yy, xx = np.mgrid[0:h, 0:w]
    circle = np.hypot(yy - centre[0], xx - centre[1]) < radius
    thr = np.quantile(img[circle], quantile)
    labels, n = ndi.label(circle & (img > thr))
    if n == 0:
        return np.zeros_like(circle)
    dist = [np.hypot(*(np.array(ndi.center_of_mass(labels == k)) - np.array(centre))) - np.sqrt((labels == k).sum())
            for k in range(1, n + 1)]
    return ndi.binary_fill_holes(labels == (int(np.argmin(dist)) + 1))
