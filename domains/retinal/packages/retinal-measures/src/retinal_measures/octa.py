"""OCT angiography en-face measurements.

Inputs are 2D en-face slabs (flow intensity) or binary vessel / FAZ / non-perfusion masks.
Binarisation is part of the measurement definition: always report which method was used.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage
from skimage import filters, measure, morphology

from ._common import Measurement, Spacing, area_value, as_mask, not_evaluable
from . import vessels


def binarize(slab, *, method='otsu', window=15):
    image = np.asarray(slab, dtype=float)
    if method == 'otsu':
        return image > filters.threshold_otsu(image)
    if method == 'phansalkar':
        return image > phansalkar_threshold(image, window=window)
    if method == 'mean':
        return image > image.mean()
    raise ValueError(method)


def phansalkar_threshold(image, *, window=15, k=0.25, r=0.5, p=2.0, q=10.0):
    """Phansalkar local threshold on an image scaled to [0, 1]."""
    img = np.asarray(image, float)
    span = img.max() - img.min()
    img = (img - img.min()) / span if span else img * 0
    mean = ndimage.uniform_filter(img, window)
    sq = ndimage.uniform_filter(img ** 2, window)
    std = np.sqrt(np.clip(sq - mean ** 2, 0, None))
    t = mean * (1 + p * np.exp(-q * mean) + k * (std / r - 1))
    return t * (span if span else 1) + np.asarray(image, float).min()


def vessel_density(vessel_mask, *, fov=None, feature_id='ft_octa_vessel_density_scp') -> Measurement:
    """Perfusion (area) density; skeleton density is in ``detail``."""
    area = vessels.area_density(vessel_mask, fov=fov, feature_id=feature_id)
    skel = morphology.skeletonize(as_mask(vessel_mask, ndim=2))
    region = as_mask(fov, ndim=2) if fov is not None else np.ones_like(skel)
    return Measurement(feature_id, area.value, 'ratio',
                       detail={'skeleton_density': float((skel & region).sum() / region.sum())})


def rpc_density(vessel_mask, disc_mask, *, outer_px, feature_id='ft_rpc_density') -> Measurement:
    """Density in an annulus from the disc margin to ``outer_px`` beyond it (large vessels removed upstream)."""
    disc = as_mask(disc_mask, ndim=2)
    dist = ndimage.distance_transform_edt(~disc)
    ring = (dist > 0) & (dist <= outer_px)
    return vessels.area_density(vessel_mask, fov=ring, feature_id=feature_id)


def _largest(mask):
    labels = measure.label(as_mask(mask, ndim=2))
    props = measure.regionprops(labels)
    return max(props, key=lambda p: p.area) if props else None


def faz_area(faz_mask, *, spacing: Spacing | None = None, feature_id='ft_faz_area') -> Measurement:
    p = _largest(faz_mask)
    if p is None:
        return not_evaluable(feature_id, 'area', 'empty FAZ mask')
    value, unit = area_value(p.area, spacing)
    return Measurement(feature_id, value, unit)


def faz_shape(faz_mask, *, spacing=None, feature_id='ft_faz_circularity') -> Measurement:
    """Circularity 4πA/P², perimeter and acircularity (P / circle perimeter of equal area)."""
    p = _largest(faz_mask)
    if p is None:
        return not_evaluable(feature_id, 'index', 'empty FAZ mask')
    perim = measure.perimeter_crofton(p.image, 4)
    circ = 4 * math.pi * p.area / perim ** 2 if perim else math.nan
    scale = spacing.x_mm if spacing and spacing.x_mm else 1.0
    return Measurement(feature_id, min(circ, 1.0), 'index',
                       detail={'perimeter': perim * scale, 'perimeter_unit': 'mm' if scale != 1.0 else 'px',
                               'acircularity': perim / (2 * math.sqrt(math.pi * p.area)), 'axis_ratio':
                               p.major_axis_length / p.minor_axis_length if p.minor_axis_length else math.nan})


def faz_detect(slab, centre, *, max_radius_px=None):
    """Simple FAZ estimate: dark region connected to ``centre`` after Otsu binarisation and closing."""
    flow = binarize(slab)
    void = ~morphology.binary_closing(flow, morphology.disk(2))
    labels = measure.label(void)
    label = labels[int(centre[0]), int(centre[1])]
    faz = labels == label if label else np.zeros_like(void)
    if max_radius_px:
        rr, cc = np.mgrid[0:faz.shape[0], 0:faz.shape[1]]
        faz &= np.hypot(rr - centre[0], cc - centre[1]) <= max_radius_px
    return ndimage.binary_fill_holes(faz)


def faz_enlargement(faz_before, faz_after, *, spacing=None, interval_years=None,
                    feature_id='ft_faz_enlargement') -> Measurement:
    a0, a1 = faz_area(faz_before, spacing=spacing), faz_area(faz_after, spacing=spacing)
    if a0.status != 'ok' or a1.status != 'ok':
        return not_evaluable(feature_id, 'rate', 'FAZ missing at a visit')
    change = a1.value - a0.value
    if interval_years:
        return Measurement(feature_id, change / interval_years, f'{a0.unit}/year')
    return Measurement(feature_id, change, a0.unit, note='absolute change; interval not given')


def flow_deficit(cc_slab, *, fov=None, window=15, min_area_px=1, spacing=None,
                 feature_id='ft_cc_flow_deficit') -> Measurement:
    """Choriocapillaris flow-deficit percentage (Phansalkar local thresholding) with FD count and mean size."""
    image = np.asarray(cc_slab, float)
    deficit = image <= phansalkar_threshold(image, window=window)
    region = as_mask(fov, ndim=2) if fov is not None else np.ones_like(deficit)
    deficit &= region
    labels = measure.label(deficit)
    sizes = np.bincount(labels.ravel())[1:]
    sizes = sizes[sizes >= min_area_px]
    mean_size, unit = area_value(float(sizes.mean()) if sizes.size else 0.0, spacing)
    return Measurement(feature_id, float(deficit.sum() / region.sum()), 'ratio',
                       detail={'fd_count': int(sizes.size), 'mean_fd_size': mean_size, 'size_unit': unit})


def nonperfusion(np_mask, *, fov=None, spacing=None) -> tuple[Measurement, Measurement]:
    """Non-perfusion area and ischemic index (non-perfused / gradable field)."""
    m = as_mask(np_mask, ndim=2)
    region = as_mask(fov, ndim=2) if fov is not None else np.ones_like(m)
    value, unit = area_value(int((m & region).sum()), spacing)
    status = 'ok' if value else 'not_observed'
    return (Measurement('ft_nonperfusion_area', value, unit, status),
            Measurement('ft_ischemic_index', float((m & region).sum() / region.sum()), 'ratio', status))


def nonperfusion_from_vessels(vessel_mask, *, min_gap_px=10):
    """Candidate non-perfusion: pixels farther than ``min_gap_px`` from any flow pixel."""
    dist = ndimage.distance_transform_edt(~as_mask(vessel_mask, ndim=2))
    return dist > min_gap_px
