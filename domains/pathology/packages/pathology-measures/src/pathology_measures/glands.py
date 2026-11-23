"""Gland morphometry from a gland mask (annotation or segmentation) and lumen detection on H&E.

Lumina are bright, low-saturation pixels inside a gland. Glands are connected components of the gland mask.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage import measure, morphology

from ._common import Measurement, area_mm2, area_um2, rgb_u8


def components(gland_mask, min_px=50):
    labels = measure.label(np.asarray(gland_mask, bool))
    props = [p for p in measure.regionprops(labels) if p.area >= min_px]
    return labels, props


def lumen_mask(rgb, gland_mask, luminance_min=0.8, saturation_max=0.12, min_px=None, mpp=None,
               min_um2=40.0) -> np.ndarray:
    """Enclosed bright spaces inside glands. Spaces connected to the slide background (glass reaching the image
    border) are not lumina. Minimum size: ``min_um2`` with a calibration, else ``min_px`` (default 30 px)."""
    x = rgb_u8(rgb).astype(np.float32) / 255.0
    mx, mn = x.max(2), x.min(2)
    sat = (mx - mn) / np.maximum(mx, 1 / 255)
    lum = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    bright = (lum > luminance_min) & (sat < saturation_max)
    labels, _ = ndi.label(bright)
    border = np.unique(np.r_[labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    open_to_glass = np.isin(labels, border[border > 0])
    m = bright & ~open_to_glass & np.asarray(gland_mask, bool)
    limit = (min_um2 / (mpp * mpp)) if mpp else (min_px or 30)
    return morphology.remove_small_objects(m, max(int(limit), 2))


def count(gland_mask, min_px=50) -> Measurement:
    _, props = components(gland_mask, min_px)
    return Measurement('ft_gland_count', len(props), 'count', 'ok' if props else 'not_observed')


def gland_density(gland_mask, tissue, mpp=None, min_px=50) -> Measurement:
    _, props = components(gland_mask, min_px)
    a, unit = area_mm2(np.asarray(tissue, bool).sum(), mpp)
    per = 'count/mm2' if mpp else 'count/10^6 px2'
    if a <= 0:
        return Measurement('ft_gland_density', None, per, 'not_evaluable')
    return Measurement('ft_gland_density', round(len(props) / a * (1 if mpp else 1e6), 1), per)


def mean_area(gland_mask, mpp=None, min_px=50) -> Measurement:
    _, props = components(gland_mask, min_px)
    if not props:
        return Measurement('ft_gland_area', None, 'um2', 'not_observed')
    v, unit = area_um2(np.mean([p.area for p in props]), mpp)
    return Measurement('ft_gland_area', round(v, 0), unit, detail={'glands': len(props)})


def circularity(gland_mask, min_px=50) -> Measurement:
    _, props = components(gland_mask, min_px)
    if not props:
        return Measurement('ft_gland_circularity', None, 'index', 'not_observed')
    c = [min(4 * np.pi * p.area / max(p.perimeter, 1) ** 2, 1.0) for p in props]
    return Measurement('ft_gland_circularity', round(float(np.median(c)), 3), 'index', note='샘별 값의 중앙값')


def lumen_fraction(rgb, gland_mask, mpp=None) -> Measurement:
    g = np.asarray(gland_mask, bool)
    if g.sum() == 0:
        return Measurement('ft_lumen_fraction', None, '%', 'not_observed')
    lum = lumen_mask(rgb, g, mpp=mpp)
    return Measurement('ft_lumen_fraction', round(100.0 * lum.sum() / g.sum(), 1), '%')


def lumina_per_gland(rgb, gland_mask, min_px=50, mpp=None) -> Measurement:
    labels, props = components(gland_mask, min_px)
    if not props:
        return Measurement('ft_lumina_per_gland', None, 'count', 'not_observed')
    lum_labels = measure.label(lumen_mask(rgb, gland_mask, mpp=mpp))
    counts = []
    for p in props:
        inside = np.unique(lum_labels[labels == p.label])
        counts.append(int((inside > 0).sum()))
    return Measurement('ft_lumina_per_gland', round(float(np.mean(counts)), 2), 'count',
                       detail={'max': int(max(counts)), 'glands': len(props)})


def nearest_neighbour(gland_mask, mpp=None, min_px=50):
    _, props = components(gland_mask, min_px)
    if len(props) < 3:
        return None
    cen = np.array([p.centroid for p in props])
    d, _ = cKDTree(cen).query(cen, k=2)
    return float(d[:, 1].mean() * (mpp or 1))


def fill_tumor_glands(rgb, region, close_px=3):
    """Service estimate of gland-like epithelial islands inside a tumour region (not stroma, not lumen)."""
    x = rgb_u8(rgb).astype(np.float32) / 255.0
    from skimage import color
    h = color.rgb2hed(rgb_u8(rgb))[..., 0]
    epi = (h > np.percentile(h[np.asarray(region, bool)], 45)) & np.asarray(region, bool)
    epi = ndi.binary_closing(epi, iterations=close_px)
    return ndi.binary_fill_holes(epi) & np.asarray(region, bool)
