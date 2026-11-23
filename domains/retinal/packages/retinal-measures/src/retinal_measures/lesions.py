"""Lesion measurements on 2D masks (fundus photographs or OCT en-face maps).

Inputs are boolean masks of one lesion type, optional landmarks in (row, col) pixel
coordinates, an optional field-of-view mask and optional pixel spacing. Connected
components are counted as lesions only after removing components smaller than
``min_area_px``; a component count is a segmentation count, not a clinical count,
unless the mask itself is a clinician's point-by-point annotation.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage
from skimage import measure

from ._common import Measurement, Spacing, area_value, as_mask, length_value, not_evaluable

QUADRANTS = ('superotemporal', 'superonasal', 'inferonasal', 'inferotemporal')


def _components(mask: np.ndarray, min_area_px: int):
    labels, _ = ndimage.label(mask)
    props = [p for p in measure.regionprops(labels) if p.area >= min_area_px]
    return labels, props


def presence(mask, *, fov=None, feature_id='ft_lesion_generic_presence', min_area_px=1) -> Measurement:
    mask = as_mask(mask, ndim=2)
    if fov is not None and not as_mask(fov).any():
        return not_evaluable(feature_id, 'presence', 'empty field of view')
    found = any(True for _ in _components(mask, min_area_px)[1])
    return Measurement(feature_id, found, 'presence', 'ok' if found else 'not_observed')


def count(mask, *, min_area_px=1, feature_id='ft_lesion_generic_count') -> Measurement:
    _, props = _components(as_mask(mask, ndim=2), min_area_px)
    return Measurement(feature_id, len(props), 'count', 'ok' if props else 'not_observed',
                       'connected components; equals a clinical count only for point/brush annotations')


def area(mask, *, spacing: Spacing | None = None, feature_id='ft_lesion_generic_area') -> Measurement:
    pixels = int(as_mask(mask, ndim=2).sum())
    value, unit = area_value(pixels, spacing)
    return Measurement(feature_id, value, unit, 'ok' if pixels else 'not_observed', detail={'pixels': pixels})


def size_distribution(mask, *, spacing=None, min_area_px=1, feature_id='ft_lesion_size_distribution') -> Measurement:
    _, props = _components(as_mask(mask, ndim=2), min_area_px)
    if not props:
        return Measurement(feature_id, None, 'area', 'not_observed')
    areas = np.array([area_value(p.area, spacing)[0] for p in props])
    unit = area_value(1, spacing)[1]
    summary = {'mean': float(areas.mean()), 'median': float(np.median(areas)), 'p90': float(np.percentile(areas, 90)),
               'max': float(areas.max()), 'cv': float(areas.std() / areas.mean()) if areas.mean() else 0.0}
    return Measurement(feature_id, summary, unit)


def shape(mask, *, min_area_px=5, feature_id='ft_lesion_generic_shape') -> Measurement:
    """Area-weighted circularity (4πA/P²), eccentricity and solidity of components."""
    _, props = _components(as_mask(mask, ndim=2), min_area_px)
    if not props:
        return Measurement(feature_id, None, 'ratio', 'not_observed')
    weights = np.array([p.area for p in props], dtype=float)
    circ = np.array([min(1.0, 4 * math.pi * p.area / p.perimeter ** 2) if p.perimeter else 1.0 for p in props])
    ecc = np.array([p.eccentricity for p in props])
    sol = np.array([p.solidity for p in props])
    avg = lambda v: float(np.average(v, weights=weights))  # noqa: E731
    return Measurement(feature_id, {'circularity': avg(circ), 'eccentricity': avg(ecc), 'solidity': avg(sol)}, 'ratio')


def extent(mask, *, spacing=None, min_area_px=1, feature_id='ft_lesion_generic_extent') -> Measurement:
    """Largest maximum Feret diameter among components."""
    _, props = _components(as_mask(mask, ndim=2), min_area_px)
    if not props:
        return Measurement(feature_id, None, 'length', 'not_observed')
    value, unit = length_value(max(p.feret_diameter_max for p in props), spacing)
    return Measurement(feature_id, value, unit)


def position(mask, *, feature_id='ft_lesion_generic_position') -> Measurement:
    mask = as_mask(mask, ndim=2)
    if not mask.any():
        return Measurement(feature_id, None, 'ratio', 'not_observed')
    rows, cols = np.nonzero(mask)
    h, w = mask.shape
    return Measurement(feature_id, {'row': float(rows.mean() / h), 'col': float(cols.mean() / w)}, 'ratio',
                       note='mask centroid as fraction of image height/width')


def _distances_to(mask, point):
    rows, cols = np.nonzero(mask)
    return np.hypot(rows - point[0], cols - point[1])


def fovea_distance(mask, fovea, *, disc_diameter_px=None, spacing=None,
                   feature_id='ft_lesion_fovea_distance') -> Measurement:
    """Minimum and median distance of lesion pixels from the foveal centre."""
    mask = as_mask(mask, ndim=2)
    if fovea is None:
        return not_evaluable(feature_id, 'length', 'fovea location missing')
    if not mask.any():
        return Measurement(feature_id, None, 'length', 'not_observed')
    d = _distances_to(mask, fovea)
    if disc_diameter_px:
        return Measurement(feature_id, {'min': float(d.min() / disc_diameter_px), 'median': float(np.median(d) / disc_diameter_px)}, 'DD')
    scale, unit = length_value(1.0, spacing)
    return Measurement(feature_id, {'min': float(d.min() * scale), 'median': float(np.median(d) * scale)}, unit)


def radial_position(mask, centre, *, disc_diameter_px=None, feature_id='ft_lesion_radial_position') -> Measurement:
    mask = as_mask(mask, ndim=2)
    if not mask.any():
        return Measurement(feature_id, None, 'length', 'not_observed')
    d = float(_distances_to(mask, centre).mean())
    return Measurement(feature_id, d / disc_diameter_px if disc_diameter_px else d, 'DD' if disc_diameter_px else 'px')


def regional_fraction(mask, centre, radius_px, *, feature_id='ft_lesion_regional_fraction') -> Measurement:
    """Fraction of lesion area inside a circle (e.g. 1 or 2 DD around the fovea)."""
    mask = as_mask(mask, ndim=2)
    total = mask.sum()
    if not total:
        return Measurement(feature_id, None, 'ratio', 'not_observed')
    inside = (_distances_to(mask, centre) <= radius_px).sum()
    return Measurement(feature_id, float(inside / total), 'ratio')


def quadrant_of(points, fovea, disc, *, eye='OD') -> np.ndarray:
    """Assign (row, col) points to fundus quadrants around the fovea.

    The horizontal axis runs through the fovea toward the disc (nasal); rows above that axis
    are superior. ``eye`` is accepted for documentation; the disc position fixes nasal/temporal.
    """
    points = np.atleast_2d(np.asarray(points, dtype=float))
    axis = np.array([disc[0] - fovea[0], disc[1] - fovea[1]], dtype=float)
    axis /= np.linalg.norm(axis)
    normal = np.array([-axis[1], axis[0]])
    if normal[0] > 0:            # make the normal point up (toward smaller row = superior)
        normal = -normal
    rel = points - np.asarray(fovea, dtype=float)
    nasal = rel @ axis > 0
    superior = rel @ normal > 0
    return np.where(superior, np.where(nasal, 'superonasal', 'superotemporal'),
                    np.where(nasal, 'inferonasal', 'inferotemporal'))


def quadrant_counts(mask, fovea, disc, *, min_area_px=1, feature_id='ft_hem_count_quadrant') -> Measurement:
    """Number of lesion components per fundus quadrant (component centroids)."""
    if fovea is None or disc is None:
        return not_evaluable(feature_id, 'count', 'fovea and disc locations are required')
    _, props = _components(as_mask(mask, ndim=2), min_area_px)
    counts = dict.fromkeys(QUADRANTS, 0)
    if props:
        for q in quadrant_of([p.centroid for p in props], fovea, disc):
            counts[str(q)] += 1
    return Measurement(feature_id, counts, 'count', 'ok' if props else 'not_observed',
                       'component counts per quadrant; not the same as clinician lesion counts')


def quadrant_occupancy(mask, fovea, disc, *, min_area_px=1, feature_id='ft_vascular_change_extent') -> Measurement:
    result = quadrant_counts(mask, fovea, disc, min_area_px=min_area_px, feature_id=feature_id)
    if result.status == 'not_evaluable':
        return result
    return Measurement(feature_id, sum(1 for v in result.value.values() if v), 'count', result.status,
                       detail={'quadrants': result.value})


def spatial_dispersion(mask, fovea, disc, *, min_area_px=1, feature_id='ft_lesion_spatial_dispersion') -> Measurement:
    """Shannon entropy (bits, 0–2) of lesion area across the four quadrants."""
    mask = as_mask(mask, ndim=2)
    if not mask.any():
        return Measurement(feature_id, None, 'bits', 'not_observed')
    names = quadrant_of(np.argwhere(mask), fovea, disc)
    p = np.array([(names == q).mean() for q in QUADRANTS])
    p = p[p > 0]
    return Measurement(feature_id, float(-(p * np.log2(p)).sum()), 'bits')


def distribution_pattern(mask, *, fov=None, min_area_px=1, feature_id='ft_lesion_generic_distribution') -> Measurement:
    """Clark–Evans nearest-neighbour ratio R of component centroids: R<1 clustered, ≈1 random, >1 dispersed."""
    _, props = _components(as_mask(mask, ndim=2), min_area_px)
    if len(props) < 3:
        return Measurement(feature_id, None, 'category', 'not_evaluable' if props else 'not_observed',
                           'at least three lesions are needed')
    pts = np.array([p.centroid for p in props])
    region = as_mask(fov).sum() if fov is not None else np.asarray(mask).size
    d = np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(d, np.inf)
    observed = d.min(1).mean()
    expected = 0.5 / math.sqrt(len(pts) / region)
    r = observed / expected
    category = 'clustered' if r < 0.8 else ('dispersed' if r > 1.2 else 'random')
    return Measurement(feature_id, category, 'category', detail={'clark_evans_R': float(r)})


def vessel_relation(mask, vessel_mask, *, near_px=10, feature_id='ft_lesion_vessel_relation') -> Measurement:
    mask, vessels = as_mask(mask, ndim=2), as_mask(vessel_mask, ndim=2)
    if not mask.any():
        return Measurement(feature_id, None, 'px', 'not_observed')
    if not vessels.any():
        return not_evaluable(feature_id, 'px', 'empty vessel mask')
    dist = ndimage.distance_transform_edt(~vessels)[mask]
    return Measurement(feature_id, {'mean_distance': float(dist.mean()), 'near_fraction': float((dist <= near_px).mean())}, 'px')


def change(mask_before, mask_after, *, spacing=None, interval_years=None, feature_id='ft_lesion_generic_change') -> Measurement:
    """Area change between two registered masks (and per-year rate when the interval is known)."""
    a = area(mask_before, spacing=spacing).value or 0
    b = area(mask_after, spacing=spacing).value or 0
    unit = area_value(1, spacing)[1]
    detail = {'before': a, 'after': b}
    if interval_years:
        detail['rate_per_year'] = (b - a) / interval_years
    return Measurement(feature_id, b - a, unit, detail=detail, note='masks must be registered to the same frame')


def turnover(mask_before, mask_after, *, min_area_px=1, overlap=0.3, feature_id='ft_ma_turnover') -> Measurement:
    """New and disappeared components between two registered masks (e.g. microaneurysm turnover)."""
    la, pa = _components(as_mask(mask_before, ndim=2), min_area_px)
    lb, pb = _components(as_mask(mask_after, ndim=2), min_area_px)

    def matched(labels_src, props_src, mask_other):
        return sum(1 for p in props_src if mask_other[labels_src == p.label].mean() >= overlap)
    disappeared = len(pa) - matched(la, pa, lb > 0)
    new = len(pb) - matched(lb, pb, la > 0)
    return Measurement(feature_id, {'new': new, 'disappeared': disappeared}, 'count')


def clock_hour(mask, disc, *, eye='OD', feature_id='ft_disc_hem_location') -> Measurement:
    """Clock-hour position (1–12) of the lesion centroid around the disc centre, 12 = superior."""
    mask = as_mask(mask, ndim=2)
    if not mask.any():
        return Measurement(feature_id, None, 'clock hour', 'not_observed')
    r, c = np.argwhere(mask).mean(0)
    angle = math.degrees(math.atan2(c - disc[1], -(r - disc[0])))  # 0 = up, clockwise positive
    if eye == 'OS':
        angle = -angle
    hour = int(round((angle % 360) / 30)) % 12 or 12
    return Measurement(feature_id, hour, 'clock hour')


def focality(mask, *, min_area_px=1, feature_id='ft_atrophy_focality') -> Measurement:
    _, props = _components(as_mask(mask, ndim=2), min_area_px)
    if not props:
        return Measurement(feature_id, None, 'category', 'not_observed')
    return Measurement(feature_id, 'unifocal' if len(props) == 1 else 'multifocal', 'category',
                       detail={'foci': len(props)})


def involves_point(mask, point, *, radius_px=0, feature_id='ft_atrophy_foveal_involvement') -> Measurement:
    mask = as_mask(mask, ndim=2)
    if point is None:
        return not_evaluable(feature_id, 'presence', 'reference point missing')
    if not mask.any():
        return Measurement(feature_id, False, 'presence', 'not_observed')
    hit = bool((_distances_to(mask, point) <= radius_px).any()) if radius_px else bool(mask[int(point[0]), int(point[1])])
    return Measurement(feature_id, hit, 'presence')


def field_fraction(mask, *, fov=None, feature_id='ft_rd_extent') -> Measurement:
    """Share of the gradable field covered by the lesion (e.g. detachment extent)."""
    m = as_mask(mask, ndim=2)
    region = as_mask(fov, ndim=2) if fov is not None else np.ones_like(m)
    value = float((m & region).sum() / region.sum())
    return Measurement(feature_id, value, 'ratio', 'ok' if value else 'not_observed')
