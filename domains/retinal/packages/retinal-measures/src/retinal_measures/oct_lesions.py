"""OCT lesion measurements from 3D lesion masks ``(n_bscans, depth, n_ascans)`` or one B-scan.

A single B-scan mask may be passed as ``(depth, n_ascans)``; it is treated as one slice.
Height is axial extent per A-scan; diameter is lateral extent; volume integrates voxels.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from ._common import Measurement, Spacing, as_mask, not_evaluable


def _volume(mask):
    m = np.asarray(mask, bool)
    return m[None] if m.ndim == 2 else m


def _z(spacing):
    return (spacing.z_um, 'um') if spacing and spacing.z_um else (1.0, 'px')


def _x(spacing):
    return (spacing.x_mm * 1000, 'um') if spacing and spacing.x_mm else (1.0, 'px')


def presence(mask, *, feature_id='ft_lesion_generic_presence') -> Measurement:
    found = bool(_volume(mask).any())
    return Measurement(feature_id, found, 'presence', 'ok' if found else 'not_observed')


def volume(mask, *, spacing: Spacing | None = None, feature_id='ft_lesion_generic_volume') -> Measurement:
    m = _volume(mask)
    voxels = int(m.sum())
    if spacing and spacing.z_um and spacing.area_mm2:
        return Measurement(feature_id, voxels * spacing.area_mm2 * spacing.z_um / 1000.0, 'mm3',
                           'ok' if voxels else 'not_observed')
    return Measurement(feature_id, float(voxels), 'voxel', 'ok' if voxels else 'not_observed')


def bscan_area(mask, *, spacing=None, feature_id='ft_lesion_generic_area') -> Measurement:
    """Largest cross-sectional area on any B-scan."""
    m = _volume(mask)
    per_slice = m.sum(axis=(1, 2))
    z, _ = _z(spacing)
    x, _ = _x(spacing)
    unit = 'mm2' if spacing and spacing.z_um and spacing.x_mm else 'px2'
    scale = z * x / 1e6 if unit == 'mm2' else 1.0
    best = int(per_slice.argmax())
    return Measurement(feature_id, float(per_slice[best] * scale), unit, 'ok' if per_slice.any() else 'not_observed',
                       detail={'bscan_index': best})


def height(mask, *, spacing=None, feature_id='ft_lesion_generic_height') -> Measurement:
    """Maximal axial extent across A-scans (e.g. SRF height, PED height, SHRM thickness)."""
    m = _volume(mask)
    if not m.any():
        return Measurement(feature_id, 0.0, _z(spacing)[1], 'not_observed')
    rows = np.arange(m.shape[1])[None, :, None]
    top = np.where(m, rows, np.inf).min(axis=1)
    bottom = np.where(m, rows, -np.inf).max(axis=1)
    extent = np.where(np.isfinite(top), bottom - top + 1, 0)
    z, unit = _z(spacing)
    idx = np.unravel_index(extent.argmax(), extent.shape)
    return Measurement(feature_id, float(extent.max() * z), unit,
                       detail={'bscan_index': int(idx[0]), 'ascan_index': int(idx[1])})


def column_thickness(mask, *, spacing=None):
    """Per-A-scan count of lesion voxels × axial step (en-face thickness map)."""
    z, _ = _z(spacing)
    return _volume(mask).sum(axis=1) * z


def lateral_diameter(mask, *, spacing=None, feature_id='ft_lesion_generic_extent') -> Measurement:
    """Widest lateral extent on any B-scan (e.g. PED base diameter, DRIL horizontal extent)."""
    m = _volume(mask)
    cols = m.any(axis=1)
    widths = []
    for row in cols:
        idx = np.where(row)[0]
        widths.append(idx[-1] - idx[0] + 1 if idx.size else 0)
    x, unit = _x(spacing)
    best = int(np.argmax(widths))
    return Measurement(feature_id, float(widths[best] * x), unit, 'ok' if widths[best] else 'not_observed',
                       detail={'bscan_index': best})


def enface_area(mask, *, spacing=None, feature_id='ft_lesion_generic_area') -> Measurement:
    """Area of the lesion's en-face projection (union over depth)."""
    projected = _volume(mask).any(axis=1)
    pixels = int(projected.sum())
    if spacing and spacing.area_mm2:
        return Measurement(feature_id, pixels * spacing.area_mm2, 'mm2', 'ok' if pixels else 'not_observed')
    return Measurement(feature_id, float(pixels), 'px2', 'ok' if pixels else 'not_observed')


def center_involvement(mask, centre, *, spacing: Spacing, radius_mm=0.5,
                       feature_id='ft_irf_center_involvement') -> Measurement:
    """Lesion within the central 1 mm (ETDRS centre subfield) on the en-face projection."""
    projected = _volume(mask).any(axis=1)
    rows, cols = np.mgrid[0:projected.shape[0], 0:projected.shape[1]]
    y_mm = spacing.y_mm if spacing.y_mm is not None else spacing.x_mm
    inside = np.hypot((rows - centre[0]) * y_mm, (cols - centre[1]) * spacing.x_mm) <= radius_mm
    hit = bool((projected & inside).any())
    return Measurement(feature_id, hit, 'presence', 'ok' if hit else 'not_observed')


def layer_location(mask, surfaces, *, feature_id='ft_irf_layer') -> Measurement:
    """Fraction of lesion voxels lying between each pair of adjacent segmented surfaces."""
    m = _volume(mask)
    order = [n for n in ['ILM', 'RNFL_GCL', 'GCL_IPL', 'IPL_INL', 'INL_OPL', 'OPL_ONL', 'ELM', 'EZ', 'RPE', 'BM', 'CSI']
             if n in surfaces]
    if len(order) < 2 or not m.any():
        return not_evaluable(feature_id, 'category', 'need surfaces and a non-empty mask')
    rows = np.arange(m.shape[1])[None, :, None]
    total = m.sum()
    shares = {}
    for upper, lower in zip(order, order[1:]):
        top = np.asarray(surfaces[upper], float)[:, None, :]
        bottom = np.asarray(surfaces[lower], float)[:, None, :]
        shares[f'{upper}-{lower}'] = float((m & (rows >= top) & (rows < bottom)).sum() / total)
    main = max(shares, key=shares.get)
    return Measurement(feature_id, main, 'category', detail=shares)


def lesion_count(mask, *, min_voxels=1, feature_id='ft_hrf_count') -> Measurement:
    """Connected components in 3D (or 2D for a B-scan), e.g. hyperreflective foci."""
    labels, n = ndimage.label(_volume(mask))
    if n and min_voxels > 1:
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
        n = int((sizes >= min_voxels).sum())
    return Measurement(feature_id, int(n), 'count', 'ok' if n else 'not_observed')


def hole_diameters(hole_mask_bscan, *, spacing=None) -> tuple[Measurement, Measurement]:
    """Macular hole minimum linear diameter (narrowest width) and base diameter (widest row near RPE)."""
    m = as_mask(hole_mask_bscan, ndim=2)
    widths = m.sum(axis=1)
    rows = np.where(widths > 0)[0]
    x, unit = _x(spacing)
    if rows.size == 0:
        return (Measurement('ft_mh_min_diameter', None, unit, 'not_observed'),
                Measurement('ft_mh_base_diameter', None, unit, 'not_observed'))
    return (Measurement('ft_mh_min_diameter', float(widths[rows].min() * x), unit),
            Measurement('ft_mh_base_diameter', float(widths[rows[-1]] * x), unit))


def attachment_width(vitreous_surface, ilm_surface, *, tolerance_px=1.0, spacing=None,
                     feature_id='ft_vmt_attachment_width') -> Measurement:
    """Lateral width where the posterior hyaloid touches the ILM on one B-scan."""
    v, ilm = np.asarray(vitreous_surface, float), np.asarray(ilm_surface, float)
    touching = np.abs(ilm - v) <= tolerance_px
    x, unit = _x(spacing)
    if not touching.any():
        return Measurement(feature_id, 0.0, unit, 'not_observed')
    labels, n = ndimage.label(touching)
    sizes = ndimage.sum(touching, labels, range(1, n + 1))
    return Measurement(feature_id, float(sizes.max() * x), unit, detail={'segments': int(n)})


def depth_category(mask, surfaces, *, feature_id='ft_mnv_type') -> Measurement:
    """Lesion depth relative to RPE/BM: below RPE (type 1), above RPE (type 2), intraretinal (type 3)."""
    loc = layer_location(mask, surfaces, feature_id=feature_id)
    if loc.status != 'ok':
        return loc
    shares = loc.detail
    below = sum(v for k, v in shares.items() if k.startswith(('RPE-', 'BM-')))
    subretinal = sum(v for k, v in shares.items() if k.startswith(('EZ-', 'ELM-')))
    intraretinal = 1.0 - below - subretinal
    parts = {'sub_rpe': below, 'subretinal': subretinal, 'intraretinal': intraretinal}
    return Measurement(feature_id, max(parts, key=parts.get), 'category', detail=parts)


def internal_reflectivity(bscan, mask_bscan, *, reference=None, feature_id='ft_ped_internal_reflectivity') -> Measurement:
    """Mean intensity inside the lesion; ``reference`` (e.g. RPE mean) gives a ratio and category."""
    image, m = np.asarray(bscan, float), as_mask(mask_bscan, ndim=2)
    if not m.any():
        return not_evaluable(feature_id, 'category', 'empty mask')
    mean = float(image[m].mean())
    if reference is None:
        return Measurement(feature_id, mean, 'intensity')
    ratio = mean / reference
    category = 'hyporeflective' if ratio < 0.33 else 'mixed' if ratio < 0.66 else 'hyperreflective'
    return Measurement(feature_id, category, 'category', detail={'mean': mean, 'ratio_to_reference': ratio})


def transmission_width(enface_hypertd, *, spacing=None, feature_id='ft_hypertd_width') -> Measurement:
    """Greatest linear dimension of a hypertransmission defect on the en-face sub-RPE slab mask."""
    m = as_mask(enface_hypertd, ndim=2)
    if not m.any():
        x, unit = _x(spacing)
        return Measurement(feature_id, 0.0, unit, 'not_observed')
    labels, n = ndimage.label(m)
    best = 0.0
    for i in range(1, n + 1):
        pts = np.argwhere(labels == i)
        if len(pts) > 400:
            pts = pts[np.linspace(0, len(pts) - 1, 400).astype(int)]
        d = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1)).max() + 1
        best = max(best, d)
    x, unit = _x(spacing)
    return Measurement(feature_id, float(best * x), unit)


SHORTCUTS = {  # feature_id: (function, keyword overrides)
    'ft_irf_presence': presence, 'ft_srf_presence': presence,
    'ft_irf_volume': volume, 'ft_srf_volume': volume, 'ft_ped_volume': volume, 'ft_drusen_volume': volume,
    'ft_irf_bscan_area': bscan_area,
    'ft_srf_height': height, 'ft_ped_height': height, 'ft_drusen_height': height, 'ft_shrm_thickness': height,
    'ft_ped_diameter': lateral_diameter, 'ft_dril_extent': lateral_diameter,
    'ft_ez_loss_area': enface_area, 'ft_erm_extent': enface_area, 'ft_mnv_lesion_area': enface_area,
    'ft_polyp_count': lesion_count,
}


def measure(feature_id, mask, **kwargs) -> Measurement:
    """Run the generic function behind a lesion-specific feature ID."""
    return SHORTCUTS[feature_id](mask, feature_id=feature_id, **kwargs)
