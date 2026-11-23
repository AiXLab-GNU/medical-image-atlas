"""Retinal vessel measurements from a binary vessel mask (fundus photograph or OCTA slab).

Inputs: a boolean vessel mask, optionally artery/vein masks, a field-of-view mask, pixel
spacing and landmarks. Widths come from the Euclidean distance transform sampled on the
skeleton (2 × distance − 1 px). These are mask-based geometric measures; they describe the
segmented vessel column, not the true lumen.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize

from ._common import Measurement, Spacing, as_mask, length_value, not_evaluable

_NEIGHBOURS = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])


def _skeleton(mask):
    return skeletonize(as_mask(mask, ndim=2))


def _neighbour_count(skel):
    return ndimage.convolve(skel.astype(int), _NEIGHBOURS, mode='constant') * skel


def _skeleton_length_px(skel) -> float:
    """Centreline length with diagonal steps weighted √2 (each link counted once)."""
    s = skel.astype(np.int8)
    orth = (s[:, :-1] & s[:, 1:]).sum() + (s[:-1, :] & s[1:, :]).sum()
    diag = (s[:-1, :-1] & s[1:, 1:]).sum() + (s[:-1, 1:] & s[1:, :-1]).sum()
    return float(orth + math.sqrt(2) * diag)


def _region_area(mask, fov):
    return float(as_mask(fov).sum()) if fov is not None else float(np.asarray(mask).size)


def area_density(mask, *, fov=None, feature_id='ft_vessel_area_density') -> Measurement:
    mask = as_mask(mask, ndim=2)
    region = _region_area(mask, fov)
    inside = mask & as_mask(fov) if fov is not None else mask
    return Measurement(feature_id, float(inside.sum() / region), 'ratio')


def pixel_count(mask, *, feature_id='ft_vessel_pixel_count') -> Measurement:
    mask = as_mask(mask, ndim=2)
    return Measurement(feature_id, {'vessel': int(mask.sum()), 'skeleton': int(_skeleton(mask).sum())}, 'px')


def length_density(mask, *, fov=None, spacing: Spacing | None = None, feature_id='ft_vessel_length_density') -> Measurement:
    mask = as_mask(mask, ndim=2)
    skel = _skeleton(mask & as_mask(fov) if fov is not None else mask)
    length = _skeleton_length_px(skel)
    region = _region_area(mask, fov)
    if spacing is not None and spacing.x_mm and spacing.x_mm == spacing.y_mm:
        return Measurement(feature_id, length * spacing.x_mm / (region * spacing.x_mm ** 2), 'mm/mm2')
    return Measurement(feature_id, length / region, 'px/px2')


def caliber(mask, *, spacing=None, feature_id='ft_vessel_caliber') -> Measurement:
    mask = as_mask(mask, ndim=2)
    skel = _skeleton(mask)
    if not skel.any():
        return Measurement(feature_id, None, 'px', 'not_observed')
    widths = 2 * ndimage.distance_transform_edt(mask)[skel] - 1
    scale, unit = length_value(1.0, spacing)
    summary = {k: float(v * scale) for k, v in (('mean', widths.mean()), ('median', np.median(widths)),
                                                ('p90', np.percentile(widths, 90)), ('std', widths.std()))}
    return Measurement(feature_id, summary, unit)


def caliber_variability(mask, *, feature_id='ft_vessel_caliber_variability') -> Measurement:
    result = caliber(mask)
    if result.status != 'ok':
        return Measurement(feature_id, None, 'ratio', result.status)
    return Measurement(feature_id, result.value['std'] / result.value['mean'], 'ratio')


def _segments(skel):
    """Split the skeleton at branch points; return pixel coordinate arrays of each segment."""
    nb = _neighbour_count(skel)
    branch = skel & (nb >= 3)
    pieces = skel & ~ndimage.binary_dilation(branch, structure=np.ones((3, 3)))
    labels, n = ndimage.label(pieces, structure=np.ones((3, 3)))
    return [np.argwhere(labels == i) for i in range(1, n + 1)], branch, skel & (nb == 1)


def _ordered_path(points):
    """Order the pixels of a simple path by walking from one end."""
    pts = {tuple(p) for p in points}
    ends = [p for p in pts if sum((p[0] + dr, p[1] + dc) in pts for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                                   if (dr, dc) != (0, 0)) <= 1]
    start = ends[0] if ends else next(iter(pts))
    path, seen = [start], {start}
    while True:
        r, c = path[-1]
        nxt = [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)
               if (dr, dc) != (0, 0) and (r + dr, c + dc) in pts and (r + dr, c + dc) not in seen]
        if not nxt:
            return np.array(path)
        nxt.sort(key=lambda q: abs(q[0] - r) + abs(q[1] - c))
        path.append(nxt[0])
        seen.add(nxt[0])


def tortuosity(mask, *, min_length_px=20, feature_id='ft_vessel_tortuosity') -> Measurement:
    """Length-weighted mean of segment arc length / chord length (1 = straight)."""
    segments, _, _ = _segments(_skeleton(mask))
    values, weights = [], []
    for seg in segments:
        if len(seg) < min_length_px:
            continue
        path = _ordered_path(seg)
        steps = np.hypot(*np.diff(path, axis=0).T)
        arc = steps.sum()
        chord = math.hypot(*(path[-1] - path[0]))
        if chord > 0:
            values.append(arc / chord)
            weights.append(arc)
    if not values:
        return Measurement(feature_id, None, 'ratio', 'not_observed')
    return Measurement(feature_id, float(np.average(values, weights=weights)), 'ratio', detail={'segments': len(values)})


def path_length(mask, *, spacing=None, min_length_px=5, feature_id='ft_vessel_path_length') -> Measurement:
    segments, _, _ = _segments(_skeleton(mask))
    lengths = [np.hypot(*np.diff(_ordered_path(s), axis=0).T).sum() for s in segments if len(s) >= min_length_px]
    if not lengths:
        return Measurement(feature_id, None, 'px', 'not_observed')
    scale, unit = length_value(1.0, spacing)
    return Measurement(feature_id, {'mean': float(np.mean(lengths) * scale), 'total': float(np.sum(lengths) * scale),
                                    'segments': len(lengths)}, unit)


def topology(mask, *, fov=None, feature_id='ft_vessel_topology') -> Measurement:
    """Branch and end points per 10,000 px of field, from the skeleton."""
    skel = _skeleton(mask)
    nb = _neighbour_count(skel)
    region = _region_area(mask, fov)
    branch_labels = ndimage.label(skel & (nb >= 3), structure=np.ones((3, 3)))[1]
    ends = int((skel & (nb == 1)).sum())
    return Measurement(feature_id, {'branch_points': branch_labels * 1e4 / region, 'end_points': ends * 1e4 / region},
                       'count/10k px', detail={'branch_points': branch_labels, 'end_points': ends})


def connectivity(mask, *, feature_id='ft_vessel_connectivity') -> Measurement:
    mask = as_mask(mask, ndim=2)
    labels, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if not n:
        return Measurement(feature_id, None, 'ratio', 'not_observed')
    sizes = np.bincount(labels.ravel())[1:]
    topo = topology(mask).detail
    ratio = topo['branch_points'] / topo['end_points'] if topo['end_points'] else None
    return Measurement(feature_id, {'largest_component_fraction': float(sizes.max() / sizes.sum()),
                                    'components': int(n), 'branch_end_ratio': ratio}, 'ratio')


def branching_angle(mask, *, arm_px=8, feature_id='ft_branching_angle') -> Measurement:
    """Mean angle between the two most divergent daughter arms at each branch point."""
    skel = _skeleton(mask)
    nb = _neighbour_count(skel)
    branch_points = np.argwhere(skel & (nb >= 3))
    pts = np.argwhere(skel)
    angles = []
    for r, c in branch_points:
        d = np.hypot(pts[:, 0] - r, pts[:, 1] - c)
        ring = pts[(d >= arm_px - 1) & (d <= arm_px + 1)]
        if len(ring) < 3:
            continue
        vecs = ring - np.array([r, c])
        theta = np.degrees(np.arctan2(vecs[:, 0], vecs[:, 1]))
        # cluster directions into arms (≥25° apart), keep up to three arms
        arms = []
        for t in sorted(theta):
            if not arms or min(abs((t - a + 180) % 360 - 180) for a in arms) > 25:
                arms.append(t)
        if len(arms) < 3:
            continue
        gaps = [abs((a - b + 180) % 360 - 180) for i, a in enumerate(arms) for b in arms[i + 1:]]
        angles.append(sorted(gaps)[0])  # daughters are usually the closest pair of arms
    if not angles:
        return Measurement(feature_id, None, 'deg', 'not_observed')
    return Measurement(feature_id, float(np.mean(angles)), 'deg', detail={'junctions': len(angles)},
                       note='geometric approximation from skeleton arms; parent/daughter roles not identified')


def fractal_dimension(mask, *, feature_id='ft_fractal_dimension') -> Measurement:
    """Box-counting dimension of the vessel mask over dyadic box sizes."""
    mask = as_mask(mask, ndim=2)
    if mask.sum() < 10:
        return Measurement(feature_id, None, 'dimensionless', 'not_observed')
    size = 2 ** int(math.ceil(math.log2(max(mask.shape))))
    padded = np.zeros((size, size), bool)
    padded[:mask.shape[0], :mask.shape[1]] = mask
    sizes, counts = [], []
    box = size // 2
    while box >= 2:
        view = padded.reshape(size // box, box, size // box, box).any(axis=(1, 3))
        sizes.append(box)
        counts.append(view.sum())
        box //= 2
    slope = np.polyfit(np.log(1 / np.array(sizes)), np.log(counts), 1)[0]
    return Measurement(feature_id, float(slope), 'dimensionless', note='box counting')


def orientation(mask, *, bins=12, feature_id='ft_vessel_orientation') -> Measurement:
    """Normalised entropy and dominance of centreline orientation (axial, 0–180°)."""
    skel = _skeleton(mask).astype(float)
    gr = ndimage.sobel(ndimage.gaussian_filter(skel, 1.5), 0)
    gc = ndimage.sobel(ndimage.gaussian_filter(skel, 1.5), 1)
    on = skel > 0
    if not on.any():
        return Measurement(feature_id, None, 'dimensionless', 'not_observed')
    theta = (np.degrees(np.arctan2(gr[on], gc[on])) + 90) % 180  # tangent = gradient + 90°
    hist = np.histogram(theta, bins=bins, range=(0, 180))[0].astype(float)
    p = hist / hist.sum()
    nz = p[p > 0]
    entropy = float(-(nz * np.log(nz)).sum() / math.log(bins))
    return Measurement(feature_id, {'entropy': entropy, 'dominance': float(p.max())}, 'dimensionless')


def regional_density(mask, centre, *, rings=(0.33, 0.66, 1.0), feature_id='ft_vessel_regional_density') -> Measurement:
    """Vessel area fraction in quadrants (up/down/left/right of centre) and concentric rings."""
    mask = as_mask(mask, ndim=2)
    rows, cols = np.indices(mask.shape)
    dr, dc = rows - centre[0], cols - centre[1]
    radius = np.hypot(dr, dc)
    rmax = radius.max()
    out = {'upper': float(mask[dr < 0].mean()), 'lower': float(mask[dr >= 0].mean()),
           'left': float(mask[dc < 0].mean()), 'right': float(mask[dc >= 0].mean())}
    lo = 0.0
    for k, hi in enumerate(rings):
        ring = (radius >= lo * rmax) & (radius < hi * rmax)
        out[f'ring{k + 1}'] = float(mask[ring].mean()) if ring.any() else None
        lo = hi
    return Measurement(feature_id, out, 'ratio')


def knudtson_equivalent(widths, *, kind: str) -> float:
    """Revised Knudtson (2003) big-6 summary: iteratively pair largest with smallest.

    Arterioles: w = 0.88·√(w1² + w2²); venules: w = 0.95·√(w1² + w2²).
    """
    k = {'artery': 0.88, 'vein': 0.95}[kind]
    values = sorted(float(w) for w in widths)[-6:]
    while len(values) > 1:
        values.sort()
        merged = []
        while len(values) > 1:
            small, large = values.pop(0), values.pop(-1)
            merged.append(k * math.sqrt(small ** 2 + large ** 2))
        merged.extend(values)
        values = merged
    return values[0]


def zone_widths(mask, disc, disc_radius_px, *, inner_dd=0.5, outer_dd=1.0) -> list[float]:
    """Width of each vessel crossing the zone ``inner_dd``–``outer_dd`` disc diameters from the disc margin."""
    mask = as_mask(mask, ndim=2)
    skel = _skeleton(mask)
    rows, cols = np.indices(mask.shape)
    radius = np.hypot(rows - disc[0], cols - disc[1]) / disc_radius_px   # in disc radii from the centre
    zone = skel & (radius >= 1 + 2 * inner_dd) & (radius <= 1 + 2 * outer_dd)
    labels, n = ndimage.label(zone, structure=np.ones((3, 3)))
    dist = ndimage.distance_transform_edt(mask)
    return [float(np.median(2 * dist[labels == i] - 1)) for i in range(1, n + 1)]


def crae(artery_mask, disc, disc_radius_px, *, spacing=None, feature_id='ft_crae') -> Measurement:
    widths = zone_widths(artery_mask, disc, disc_radius_px)
    if len(widths) < 2:
        return not_evaluable(feature_id, 'px', 'fewer than two arterioles in the measurement zone')
    scale, unit = length_value(1.0, spacing)
    return Measurement(feature_id, knudtson_equivalent(widths, kind='artery') * scale, unit,
                       detail={'vessels': len(widths)}, note='zone 0.5–1 DD from the disc margin; revised Knudtson big-6')


def crve(vein_mask, disc, disc_radius_px, *, spacing=None, feature_id='ft_crve') -> Measurement:
    widths = zone_widths(vein_mask, disc, disc_radius_px)
    if len(widths) < 2:
        return not_evaluable(feature_id, 'px', 'fewer than two venules in the measurement zone')
    scale, unit = length_value(1.0, spacing)
    return Measurement(feature_id, knudtson_equivalent(widths, kind='vein') * scale, unit,
                       detail={'vessels': len(widths)}, note='zone 0.5–1 DD from the disc margin; revised Knudtson big-6')


def avr(artery_mask, vein_mask, disc, disc_radius_px, *, feature_id='ft_avr') -> Measurement:
    a, v = crae(artery_mask, disc, disc_radius_px), crve(vein_mask, disc, disc_radius_px)
    if a.status != 'ok' or v.status != 'ok':
        return not_evaluable(feature_id, 'ratio', 'CRAE or CRVE not evaluable')
    return Measurement(feature_id, a.value / v.value, 'ratio')


def caliber_variation(vessel_mask, *, min_length_px=30, feature_id='ft_vb_caliber_variation') -> Measurement:
    """Per-segment width variation along the centreline (max/min and CV); high values suggest beading."""
    mask = as_mask(vessel_mask, ndim=2)
    segments, _, _ = _segments(_skeleton(mask))
    dist = ndimage.distance_transform_edt(mask)
    stats = []
    for seg in segments:
        if len(seg) < min_length_px:
            continue
        w = 2 * dist[tuple(_ordered_path(seg).T)] - 1
        w = ndimage.uniform_filter1d(w, 3)
        if w.min() > 0:
            stats.append((w.max() / w.min(), w.std() / w.mean()))
    if not stats:
        return Measurement(feature_id, None, 'ratio', 'not_observed')
    arr = np.array(stats)
    return Measurement(feature_id, {'max_min_ratio': float(arr[:, 0].max()), 'mean_cv': float(arr[:, 1].mean())},
                       'ratio', detail={'segments': len(stats)})
