"""HMWCK–AMACR dual immunohistochemistry: brown basal cells (DAB) and red AMACR chromogen.

Brown is the DAB channel of the scikit-image HED separation. Red is a hue rule (red well above green, blue above green —
the magenta tint that separates it from brown), because the red chromogen has no fixed stain vector in HED. Both are service estimates; staining
batches and scanners shift the thresholds.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage import color, filters  # noqa: F401

from ._common import Measurement, rgb_u8


def brown_mask(rgb, threshold=0.03) -> np.ndarray:
    """DAB optical density above a fixed threshold (Otsu over-selects only the darkest brown when much is present)."""
    dab = filters.gaussian(np.clip(color.rgb2hed(rgb_u8(rgb))[..., 2], 0, None), 1)
    thr = threshold
    x = rgb_u8(rgb).astype(np.int16)
    not_pink = x[..., 2] <= x[..., 1] + 10                       # brown: blue at or below green (pink-red: blue above green)
    return (dab > thr) & not_pink


def red_mask(rgb, min_margin=45) -> np.ndarray:
    """Pink-red AMACR chromogen: red well above green, blue above green (magenta tint, unlike brown), bright."""
    x = rgb_u8(rgb).astype(np.int16)
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    m = (r - g > min_margin) & (b - g > 10) & (r > 150)
    return ndi.binary_opening(m, iterations=1)


def basal_coverage(rgb, gland_mask, band_px=30, min_gland_px=200) -> Measurement:
    """Share of the outer rim of each gland that is brown (HMWCK) — basal cells retained (high) or lost (≈0)."""
    from skimage import measure
    g = np.asarray(gland_mask, bool)
    labels = measure.label(g)
    brown = brown_mask(rgb)
    per = []
    rim_all = np.zeros(g.shape, bool)
    for p in measure.regionprops(labels):
        if p.area < min_gland_px:
            continue
        one = labels == p.label
        rim = ndi.binary_dilation(one, iterations=band_px // 2) & ~ndi.binary_erosion(one, iterations=band_px)
        rim_all |= rim
        per.append(float((brown & rim).sum() / max(rim.sum(), 1)))
    if not per:
        return Measurement('ft_basal_cell_coverage', None, '%', 'not_observed', '샘 없음')
    return Measurement('ft_basal_cell_coverage', round(100 * float(np.median(per)), 1), '%',
                       note='샘 둘레 띠 중 갈색(HMWCK) 화소 비율의 샘별 중앙값',
                       detail={'glands': len(per), 'rim': rim_all})


def basal_cell_presence(coverage: Measurement, cutoff=5.0) -> Measurement:
    if coverage.status != 'ok':
        return Measurement('ft_basal_cell_presence', None, 'presence', coverage.status)
    return Measurement('ft_basal_cell_presence', bool(coverage.value >= cutoff), 'presence',
                       note=f'둘레의 {cutoff:.0f}% 이상이 갈색이면 기저세포 있음(서비스 기준)')


def amacr_fraction(rgb, region) -> Measurement:
    region = np.asarray(region, bool)
    if region.sum() == 0:
        return Measurement('ft_amacr_fraction', None, '%', 'not_evaluable')
    red = red_mask(rgb) & region
    return Measurement('ft_amacr_fraction', round(100 * float(red.sum() / region.sum()), 1), '%',
                       note='영역 중 적색(AMACR) 화소 비율')


def amacr_positivity(fraction: Measurement, cutoff=5.0) -> Measurement:
    if fraction.status != 'ok':
        return Measurement('ft_amacr_positivity', None, 'presence', fraction.status)
    return Measurement('ft_amacr_positivity', bool(fraction.value >= cutoff), 'presence',
                       note=f'적색 화소가 {cutoff:.0f}% 이상이면 양성(서비스 기준)')
