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
                       detail={'max': int(max(counts)), 'glands': len(props),
                               'glands_3plus': int(sum(c >= 3 for c in counts))})


def nearest_neighbour(gland_mask, mpp=None, min_px=50):
    _, props = components(gland_mask, min_px)
    if len(props) < 3:
        return None
    cen = np.array([p.centroid for p in props])
    d, _ = cKDTree(cen).query(cen, k=2)
    return float(d[:, 1].mean() * (mpp or 1))


def segment_glands(rgb, region, mpp=None, sigma_um=6.0, min_gland_um2=150.0, reference=None):
    """Service estimate of individual glands inside a region (for example a tumour annotation).

    Epithelium is where haematoxylin density smoothed over ~6 µm is above its Otsu level over the whole tissue in the
    image (``reference``, default: tissue mask), so stroma sets the level and a solid sheet stays one piece; enclosed lumina are
    filled in, so each connected component is one gland (a cribriform gland stays one component with many lumina,
    pattern-5 cords become small lumen-less pieces). Without a calibration ``sigma_um`` and ``min_gland_um2`` are
    read as 6 px and 150 px.
    """
    from skimage import color, filters
    region = np.asarray(region, bool)
    sigma = (sigma_um / mpp) if mpp else sigma_um
    min_px = (min_gland_um2 / (mpp * mpp)) if mpp else 150
    h = filters.gaussian(np.clip(color.rgb2hed(rgb_u8(rgb))[..., 0], 0, None), sigma)
    if region.sum() < 100:
        return np.zeros(region.shape, bool)
    if reference is None:
        from .tissue import tissue_mask
        reference = tissue_mask(rgb)
    reference = np.asarray(reference, bool) if np.asarray(reference, bool).sum() > 100 else region
    epi = ndi.binary_closing((h > filters.threshold_otsu(h[reference])) & region, iterations=2)
    lum = lumen_mask(rgb, ndi.binary_dilation(region, iterations=3), min_px=20 if not mpp else None, mpp=mpp,
                     min_um2=5.0)
    g = ndi.binary_fill_holes(epi | lum) & (region | lum)
    return morphology.remove_small_objects(ndi.binary_opening(g, iterations=2), max(int(min_px), 2))


def fill_tumor_glands(rgb, region, close_px=3):
    """Service estimate of gland-like epithelial islands inside a tumour region (not stroma, not lumen)."""
    x = rgb_u8(rgb).astype(np.float32) / 255.0
    from skimage import color
    h = color.rgb2hed(rgb_u8(rgb))[..., 0]
    epi = (h > np.percentile(h[np.asarray(region, bool)], 45)) & np.asarray(region, bool)
    epi = ndi.binary_closing(epi, iterations=close_px)
    return ndi.binary_fill_holes(epi) & np.asarray(region, bool)
