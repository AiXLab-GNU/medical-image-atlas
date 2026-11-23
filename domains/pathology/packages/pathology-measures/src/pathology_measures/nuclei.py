"""Haematoxylin separation and nucleus candidates on H&E (Ruifrok & Johnston 2001 colour deconvolution).

Nuclei are candidates: the darkest of three multi-Otsu haematoxylin levels inside the region, split by distance-transform
peaks, kept within a size window. They are not validated segmentations; touching or faint nuclei are missed.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi
from skimage import color, feature, filters, measure, segmentation

from ._common import Measurement, area_mm2, area_um2, rgb_u8


def hematoxylin(rgb) -> np.ndarray:
    """Haematoxylin optical density (skimage HED separation)."""
    return np.clip(color.rgb2hed(rgb_u8(rgb))[..., 0], 0, None)


@dataclass
class Nuclei:
    labels: np.ndarray
    props: list
    region: np.ndarray
    mpp: float | None


def detect(rgb, region, mpp=None, min_um2=12.0, max_um2=180.0, smooth=1.0) -> Nuclei:
    h = filters.gaussian(hematoxylin(rgb), smooth)
    region = np.asarray(region, bool)
    if region.sum() < 50:
        return Nuclei(np.zeros(region.shape, int), [], region, mpp)
    vals = h[region]
    try:
        thr = filters.threshold_multiotsu(vals, classes=3)[1]    # darkest of three haematoxylin levels
    except ValueError:
        thr = filters.threshold_otsu(vals)
    fg = (h > thr) & region
    fg = ndi.binary_opening(fg, iterations=1)
    dist = ndi.distance_transform_edt(fg)
    r_px = (np.sqrt(min_um2 / np.pi) / mpp) if mpp else 2.0
    peaks = feature.peak_local_max(dist, min_distance=max(2, int(r_px)), labels=measure.label(fg), exclude_border=False)
    markers = np.zeros(fg.shape, int)
    markers[tuple(peaks.T)] = np.arange(1, len(peaks) + 1)
    labels = segmentation.watershed(-dist, markers, mask=fg)
    px_min = min_um2 / (mpp * mpp) if mpp else 10
    px_max = max_um2 / (mpp * mpp) if mpp else 600
    props = [p for p in measure.regionprops(labels) if px_min <= p.area <= px_max]
    keep = np.zeros(labels.max() + 1, bool)
    keep[[p.label for p in props]] = True
    return Nuclei(np.where(keep[labels], labels, 0), props, region, mpp)


def density(n: Nuclei) -> Measurement:
    a, unit = area_mm2(n.region.sum(), n.mpp)
    per = 'count/mm2' if n.mpp else 'count/10^4 px2'
    scale = 1.0 if n.mpp else 1e4
    if a <= 0:
        return Measurement('ft_nuclear_density', None, per, 'not_evaluable')
    return Measurement('ft_nuclear_density', round(len(n.props) / a * scale, 0 if n.mpp else 2), per,
                       detail={'nuclei': len(n.props)})


def mean_area(n: Nuclei) -> Measurement:
    if not n.props:
        return Measurement('ft_nuclear_area', None, 'um2', 'not_observed')
    v, unit = area_um2(np.mean([p.area for p in n.props]), n.mpp)
    return Measurement('ft_nuclear_area', round(v, 1), unit)


def area_variation(n: Nuclei) -> Measurement:
    if len(n.props) < 5:
        return Measurement('ft_nuclear_area_variation', None, 'ratio', 'not_evaluable', '핵 5개 미만')
    a = np.array([p.area for p in n.props], float)
    return Measurement('ft_nuclear_area_variation', round(float(a.std() / a.mean()), 3), 'ratio')


def hematoxylin_od(rgb, region) -> Measurement:
    region = np.asarray(region, bool)
    if region.sum() == 0:
        return Measurement('ft_hematoxylin_od', None, 'OD', 'not_evaluable')
    return Measurement('ft_hematoxylin_od', round(float(hematoxylin(rgb)[region].mean()), 4), 'OD',
                       note='skimage HED 분리 · 염색·스캐너 보정 없음')



def nucleolus_prominence(rgb, region, mpp=None, ratio=0.8, min_nucleus_um2=15.0, max_nucleus_um2=200.0) -> Measurement:
    """EXPERIMENTAL — share of nuclei whose darkest point (total OD smoothed over 0.35 µm) exceeds the nucleus median
    chromatin by ``ratio`` (relative contrast), on 40× pixels.

    Not in the registry: on PRECISE it did not separate tumour from benign glands (see ``data/validation.json``,
    check ``nucleoli``), because the nucleus mask is not accurate enough at this level.
    """
    if mpp and mpp > 0.35:
        return Measurement('ft_nucleolus_prominence', None, '%', 'not_evaluable', '40× 화소(약 0.25 µm) 필요')
    scale = mpp or 0.25
    region = np.asarray(region, bool)
    if region.sum() < 100:
        return Measurement('ft_nucleolus_prominence', None, '%', 'not_evaluable')
    h = filters.gaussian(hematoxylin(rgb), 0.5 / scale)
    fg = ndi.binary_fill_holes(ndi.binary_opening((h > filters.threshold_otsu(h[region])) & region, iterations=2))
    dist = ndi.distance_transform_edt(fg)
    peaks = feature.peak_local_max(dist, min_distance=max(2, int(2.0 / scale)), labels=measure.label(fg), exclude_border=False)
    markers = np.zeros(fg.shape, int)
    markers[tuple(peaks.T)] = np.arange(1, len(peaks) + 1)
    labels = segmentation.watershed(-dist, markers, mask=fg)
    x = rgb_u8(rgb).astype(np.float32)
    od = filters.gaussian(-np.log((x + 1) / 256).sum(2), 0.35 / scale)
    lo, hi = min_nucleus_um2 / scale ** 2, max_nucleus_um2 / scale ** 2
    n = hit = 0
    for p in measure.regionprops(labels):
        if not lo <= p.area <= hi:
            continue
        inner = ndi.binary_erosion(p.image, iterations=2)
        if inner.sum() < 20:
            continue
        v = od[p.slice][inner]
        med = float(np.median(v))
        n += 1
        hit += (v.max() - med) / max(med, 1e-3) > ratio
    if n < 20:
        return Measurement('ft_nucleolus_prominence', None, '%', 'not_evaluable', '핵 20개 미만')
    return Measurement('ft_nucleolus_prominence', round(100 * hit / n, 1), '%', note='실험용 · 검증 미통과',
                       detail={'nuclei': n, 'with_nucleolus': hit})
