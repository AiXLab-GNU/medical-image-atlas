"""Optic disc, cup and rim measurements from 2D masks (fundus photograph or OCT en-face).

Disc and cup boundaries drawn on a photograph and the OCT Bruch's-membrane-opening (BMO)
definition are different; record which one the masks follow. Vertical means image rows.
"""
from __future__ import annotations

import math

import numpy as np
from skimage import measure

from ._common import Measurement, Spacing, area_value, as_mask, length_value, not_evaluable

SECTORS = {'superior': 90.0, 'nasal': 0.0, 'inferior': 270.0, 'temporal': 180.0}


def _props(mask):
    labels = measure.label(as_mask(mask, ndim=2))
    props = measure.regionprops(labels)
    return max(props, key=lambda p: p.area) if props else None


def disc_area(disc_mask, *, spacing: Spacing | None = None, feature_id='ft_disc_area') -> Measurement:
    p = _props(disc_mask)
    if p is None:
        return not_evaluable(feature_id, 'area', 'empty disc mask')
    value, unit = area_value(p.area, spacing)
    return Measurement(feature_id, value, unit)


def disc_diameter(disc_mask, *, spacing=None, feature_id='ft_disc_diameter') -> Measurement:
    p = _props(disc_mask)
    if p is None:
        return not_evaluable(feature_id, 'length', 'empty disc mask')
    r0, c0, r1, c1 = p.bbox
    scale, unit = length_value(1.0, spacing)
    return Measurement(feature_id, {'vertical': (r1 - r0) * scale, 'horizontal': (c1 - c0) * scale}, unit)


def cup_area(cup_mask, *, spacing=None, feature_id='ft_cup_area') -> Measurement:
    p = _props(cup_mask)
    if p is None:
        return Measurement(feature_id, None, 'area', 'not_observed')
    value, unit = area_value(p.area, spacing)
    return Measurement(feature_id, value, unit)


def cup_disc_ratio(disc_mask, cup_mask, *, feature_id='ft_cdr_vertical') -> Measurement:
    d, c = _props(disc_mask), _props(cup_mask)
    if d is None:
        return not_evaluable(feature_id, 'ratio', 'empty disc mask')
    if c is None:
        return Measurement(feature_id, 0.0, 'ratio', note='no cup segmented')
    vertical = (c.bbox[2] - c.bbox[0]) / (d.bbox[2] - d.bbox[0])
    return Measurement(feature_id, float(vertical), 'ratio', detail={'area_ratio': float(c.area / d.area)})


def rim_area(disc_mask, cup_mask, *, spacing=None, feature_id='ft_rim_area') -> Measurement:
    disc, cup = as_mask(disc_mask, ndim=2), as_mask(cup_mask, ndim=2)
    if not disc.any():
        return not_evaluable(feature_id, 'area', 'empty disc mask')
    value, unit = area_value(int((disc & ~cup).sum()), spacing)
    return Measurement(feature_id, value, unit)


def rim_width_profile(disc_mask, cup_mask, *, eye='OD', step_deg=5.0) -> dict[float, float]:
    """Radial rim width (disc edge − cup edge, px) by angle; 0° = nasal, 90° = superior."""
    disc, cup = as_mask(disc_mask, ndim=2), as_mask(cup_mask, ndim=2)
    centre = np.argwhere(disc).mean(0)
    out = {}
    max_r = max(disc.shape)
    for deg in np.arange(0, 360, step_deg):
        image_deg = deg if eye == 'OS' else 180 - deg   # OD: nasal is image-right
        rad = math.radians(image_deg)
        rs = np.arange(0, max_r)
        rr = np.clip((centre[0] - rs * math.sin(rad)).round().astype(int), 0, disc.shape[0] - 1)
        cc = np.clip((centre[1] + rs * math.cos(rad)).round().astype(int), 0, disc.shape[1] - 1)
        in_disc, in_cup = disc[rr, cc], cup[rr, cc]
        disc_edge = rs[in_disc].max() if in_disc.any() else 0
        cup_edge = rs[in_cup].max() if in_cup.any() else 0
        out[float(deg)] = float(max(disc_edge - cup_edge, 0))
    return out


def isnt_pattern(disc_mask, cup_mask, *, eye='OD', feature_id='ft_isnt_pattern') -> Measurement:
    """Whether mean rim width follows inferior ≥ superior ≥ nasal ≥ temporal."""
    profile = rim_width_profile(disc_mask, cup_mask, eye=eye)
    widths = {}
    for name, centre in SECTORS.items():
        widths[name] = float(np.mean([w for a, w in profile.items() if abs((a - centre + 180) % 360 - 180) <= 45]))
    ok = widths['inferior'] >= widths['superior'] >= widths['nasal'] >= widths['temporal']
    return Measurement(feature_id, 'follows' if ok else 'violated', 'category', detail=widths)


def rim_notch(disc_mask, cup_mask, *, eye='OD', fraction=0.5, feature_id='ft_cupping_notch') -> Measurement:
    """Focal rim thinning: angles where rim width falls below ``fraction`` × median."""
    profile = rim_width_profile(disc_mask, cup_mask, eye=eye)
    median = float(np.median(list(profile.values())))
    thin = [a for a, w in profile.items() if median and w < fraction * median]
    return Measurement(feature_id, bool(thin), 'presence', 'ok' if thin else 'not_observed',
                       detail={'angles_deg': thin, 'median_rim_px': median})


def disc_shape(disc_mask, *, feature_id='ft_disc_shape') -> Measurement:
    p = _props(disc_mask)
    if p is None:
        return not_evaluable(feature_id, 'ratio', 'empty disc mask')
    ratio = p.major_axis_length / p.minor_axis_length if p.minor_axis_length else None
    return Measurement(feature_id, {'axis_ratio': ratio, 'orientation_deg': math.degrees(p.orientation),
                                    'circularity': 4 * math.pi * p.area / p.perimeter ** 2,
                                    'eccentricity': p.eccentricity}, 'ratio')


def tilt_ratio(disc_mask, *, feature_id='ft_disc_tilt_ratio') -> Measurement:
    shape = disc_shape(disc_mask)
    if shape.status != 'ok':
        return Measurement(feature_id, None, 'ratio', shape.status)
    return Measurement(feature_id, shape.value['axis_ratio'], 'ratio', detail={'orientation_deg': shape.value['orientation_deg']})


def disc_fovea_geometry(disc_centre, fovea_centre, *, disc_diameter_px=None, spacing=None) -> tuple[Measurement, Measurement]:
    """Distance (DD, mm or px) and angle below the horizontal (deg, positive = fovea lower)."""
    if disc_centre is None or fovea_centre is None:
        return (not_evaluable('ft_disc_fovea_distance', 'length', 'landmark missing'),
                not_evaluable('ft_disc_fovea_angle', 'deg', 'landmark missing'))
    dr, dc = fovea_centre[0] - disc_centre[0], fovea_centre[1] - disc_centre[1]
    dist = math.hypot(dr, dc)
    if disc_diameter_px:
        distance = Measurement('ft_disc_fovea_distance', dist / disc_diameter_px, 'DD')
    else:
        value, unit = length_value(dist, spacing)
        distance = Measurement('ft_disc_fovea_distance', value, unit)
    angle = Measurement('ft_disc_fovea_angle', math.degrees(math.atan2(dr, abs(dc))), 'deg')
    return distance, angle


def ppa_area(ppa_mask, *, spacing=None, feature_id='ft_ppa_area') -> Measurement:
    pixels = int(as_mask(ppa_mask, ndim=2).sum())
    value, unit = area_value(pixels, spacing)
    return Measurement(feature_id, value, unit, 'ok' if pixels else 'not_observed')


def rnfl_defect_angle(profile_um, *, normal_um, fraction=0.7, feature_id='ft_rnfl_defect_angle') -> Measurement:
    """Widest contiguous arc (deg) where circumpapillary RNFL < ``fraction`` × the normal value.

    ``profile_um`` is the thickness along a peripapillary circle (equally spaced, 360° total);
    ``normal_um`` is a scalar or same-length reference profile.
    """
    profile = np.asarray(profile_um, dtype=float)
    reference = np.broadcast_to(np.asarray(normal_um, dtype=float), profile.shape)
    low = profile < fraction * reference
    if not low.any():
        return Measurement(feature_id, 0.0, 'deg', 'not_observed')
    doubled = np.concatenate([low, low])
    best = run = 0
    for flag in doubled:
        run = run + 1 if flag else 0
        best = max(best, run)
    best = min(best, len(profile))
    return Measurement(feature_id, best * 360.0 / len(profile), 'deg')


def bmo_mrw(bmo_points, ilm_points, *, spacing=None, feature_id='ft_bmo_mrw') -> Measurement:
    """BMO minimum rim width: shortest distance from each BMO point to the ILM on its radial B-scan.

    ``bmo_points``: list of (row_um, col_um) per radial scan; ``ilm_points``: list of arrays of
    ILM (row_um, col_um) on the same scans (physical units so axial and lateral are comparable).
    """
    if not bmo_points:
        return not_evaluable(feature_id, 'um', 'BMO points required')
    widths = []
    for bmo, ilm in zip(bmo_points, ilm_points):
        ilm = np.asarray(ilm, float)
        widths.append(float(np.min(np.hypot(ilm[:, 0] - bmo[0], ilm[:, 1] - bmo[1]))))
    return Measurement(feature_id, float(np.mean(widths)), 'um',
                       detail={'min': min(widths), 'per_point': widths})
