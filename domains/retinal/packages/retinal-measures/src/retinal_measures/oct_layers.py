"""OCT layer measurements from segmented surfaces.

Surfaces are 2D depth maps ``(n_bscans, n_ascans)`` in axial pixels (row index, increasing
downward), one map per boundary, named after the convention below. A single B-scan is a
``(1, n_ascans)`` map. ``NaN`` marks columns where a surface was not segmented.

Boundary names: ILM, RNFL_GCL, GCL_IPL, IPL_INL, INL_OPL, OPL_ONL, ELM, EZ, OS_RPE (interdigitation
or RPE apex), RPE, BM, CSI (choroid–sclera interface).
"""
from __future__ import annotations

import math

import numpy as np

from ._common import Measurement, Spacing, not_evaluable

LAYERS = {  # name: (top surface, bottom surface)
    'retina': ('ILM', 'BM'),
    'rnfl': ('ILM', 'RNFL_GCL'),
    'gcl': ('RNFL_GCL', 'GCL_IPL'),
    'gcipl': ('RNFL_GCL', 'IPL_INL'),
    'gcc': ('ILM', 'IPL_INL'),
    'inl': ('IPL_INL', 'INL_OPL'),
    'onl': ('OPL_ONL', 'ELM'),
    'os': ('EZ', 'OS_RPE'),
    'rpe_bm': ('RPE', 'BM'),
    'choroid': ('BM', 'CSI'),
}
ETDRS_RINGS_MM = (0.5, 1.5, 3.0)   # radii: centre 1 mm, inner 3 mm, outer 6 mm diameter


def _require(surfaces, *names):
    missing = [n for n in names if n not in surfaces]
    if missing:
        raise KeyError(f'surfaces missing: {missing}')
    return [np.asarray(surfaces[n], dtype=float) for n in names]


def thickness_map(surfaces, layer='retina', *, spacing: Spacing | None = None) -> np.ndarray:
    """Per-A-scan thickness (µm if ``spacing.z_um`` is set, else axial px)."""
    top, bottom = _require(surfaces, *LAYERS[layer])
    out = bottom - top
    out[out < 0] = np.nan
    return out * (spacing.z_um if spacing and spacing.z_um else 1.0)


def _unit(spacing):
    return 'um' if spacing and spacing.z_um else 'px'


def _grid_mm(shape, spacing, centre):
    if spacing is None or spacing.x_mm is None:
        raise ValueError('lateral spacing (x_mm, y_mm) required for ETDRS geometry')
    rows, cols = np.mgrid[0:shape[0], 0:shape[1]]
    y_mm = spacing.y_mm if spacing.y_mm is not None else spacing.x_mm
    return (rows - centre[0]) * y_mm, (cols - centre[1]) * spacing.x_mm


def etdrs_subfields(thickness, centre, *, spacing: Spacing, eye='OD') -> dict[str, float]:
    """Mean thickness in the nine ETDRS subfields (C, S1, N1, I1, T1, S2, N2, I2, T2)."""
    dy, dx = _grid_mm(thickness.shape, spacing, centre)
    r = np.hypot(dy, dx)
    angle = np.degrees(np.arctan2(-dy, dx if eye == 'OS' else -dx)) % 360  # 0 = nasal, 90 = superior
    sectors = {'N': (angle >= 315) | (angle < 45), 'S': (angle >= 45) & (angle < 135),
               'T': (angle >= 135) & (angle < 225), 'I': (angle >= 225) & (angle < 315)}
    rings = {'1': (r > ETDRS_RINGS_MM[0]) & (r <= ETDRS_RINGS_MM[1]),
             '2': (r > ETDRS_RINGS_MM[1]) & (r <= ETDRS_RINGS_MM[2])}
    out = {'C': float(np.nanmean(np.where(r <= ETDRS_RINGS_MM[0], thickness, np.nan)))}
    for ring, ring_mask in rings.items():
        for sector, sector_mask in sectors.items():
            region = ring_mask & sector_mask
            out[sector + ring] = float(np.nanmean(thickness[region])) if region.any() else math.nan
    return out


def central_subfield_thickness(surfaces, centre, *, spacing: Spacing, layer='retina',
                               feature_id='ft_central_subfield_thickness') -> Measurement:
    t = thickness_map(surfaces, layer, spacing=spacing)
    value = etdrs_subfields(t, centre, spacing=spacing)['C']
    if math.isnan(value):
        return not_evaluable(feature_id, _unit(spacing), 'no segmented A-scan inside 1 mm')
    return Measurement(feature_id, value, _unit(spacing))


def etdrs_thickness(surfaces, centre, *, spacing: Spacing, layer='retina', eye='OD',
                    feature_id='ft_etdrs_subfield_thickness') -> Measurement:
    t = thickness_map(surfaces, layer, spacing=spacing)
    return Measurement(feature_id, etdrs_subfields(t, centre, spacing=spacing, eye=eye), _unit(spacing))


def macular_volume(surfaces, centre, *, spacing: Spacing, radius_mm=3.0, layer='retina',
                   feature_id='ft_macular_volume') -> Measurement:
    if spacing is None or spacing.z_um is None or spacing.area_mm2 is None:
        return not_evaluable(feature_id, 'mm3', 'x, y and z spacing required')
    t = thickness_map(surfaces, layer, spacing=spacing) / 1000.0
    dy, dx = _grid_mm(t.shape, spacing, centre)
    inside = np.hypot(dy, dx) <= radius_mm
    return Measurement(feature_id, float(np.nansum(t[inside]) * spacing.area_mm2), 'mm3')


def layer_thickness(surfaces, layer, *, spacing=None, region=None, feature_id=None) -> Measurement:
    """Mean thickness of ``layer`` over an optional boolean ``region`` of A-scans."""
    ids = {'gcipl': 'ft_gcipl_thickness', 'onl': 'ft_onl_thickness', 'os': 'ft_os_length',
           'rpe_bm': 'ft_rpe_bm_thickness', 'rnfl': 'ft_rnfl_thickness_macular',
           'choroid': 'ft_choroid_thickness_map'}
    feature_id = feature_id or ids.get(layer, 'ft_layer_thickness_generic')
    t = thickness_map(surfaces, layer, spacing=spacing)
    values = t[np.asarray(region, bool)] if region is not None else t.ravel()
    if np.isnan(values).all():
        return not_evaluable(feature_id, _unit(spacing), 'layer not segmented in region')
    return Measurement(feature_id, float(np.nanmean(values)), _unit(spacing),
                       detail={'min': float(np.nanmin(values)), 'max': float(np.nanmax(values))})


def subfoveal_choroid_thickness(surfaces, centre, *, spacing=None,
                                feature_id='ft_choroid_thickness_subfoveal') -> Measurement:
    t = thickness_map(surfaces, 'choroid', spacing=spacing)
    value = t[int(round(centre[0])), int(round(centre[1]))]
    if math.isnan(value):
        return not_evaluable(feature_id, _unit(spacing), 'CSI not visible under the fovea')
    return Measurement(feature_id, float(value), _unit(spacing))


def foveal_pit(ilm_bscan, *, fovea_col=None, spacing=None, rim_mm=1.0,
               feature_id='ft_foveal_pit_shape') -> Measurement:
    """Depth, rim-to-rim width and maximal slope of the foveal pit on one B-scan ILM profile."""
    ilm = np.asarray(ilm_bscan, dtype=float)
    if np.isnan(ilm).all():
        return not_evaluable(feature_id, 'index', 'ILM missing')
    if fovea_col is None:   # deepest point within the central half of the scan
        q = len(ilm) // 4
        centre = q + int(np.nanargmax(ilm[q:len(ilm) - q]))
        if np.nanmax(ilm[q:len(ilm) - q]) == ilm[q:len(ilm) - q][0]:
            centre = len(ilm) // 2
    else:
        centre = int(fovea_col)
    x_mm = spacing.x_mm if spacing and spacing.x_mm else None
    z = spacing.z_um if spacing and spacing.z_um else 1.0
    half = int(round(rim_mm / x_mm)) if x_mm else len(ilm) // 4
    left = ilm[max(centre - half, 0):centre + 1]
    right = ilm[centre:centre + half + 1]
    rim_left = centre - half + int(np.nanargmin(left)) if centre - half >= 0 else int(np.nanargmin(left))
    rim_right = centre + int(np.nanargmin(right))
    depth = (ilm[centre] - (ilm[rim_left] + ilm[rim_right]) / 2) * z
    width = (rim_right - rim_left) * (x_mm * 1000 if x_mm else 1.0)
    segment = ilm[rim_left:rim_right + 1]
    steps = np.abs(np.diff(segment)) if segment.size > 1 else np.zeros(1)
    slope = np.nanmax(steps) * z / (x_mm * 1000 if x_mm else 1.0)
    return Measurement(feature_id, {'depth': float(depth), 'width': float(width), 'max_slope': float(slope)},
                       'index', note='depth/width in um when spacing is given, else px')


def foveal_contour(ilm_bscan, *, fovea_col=None, spacing=None, flat_um=10.0,
                   feature_id='ft_foveal_contour') -> Measurement:
    """Category: normal pit / shallow (blunted) / inverted (convex centre)."""
    pit = foveal_pit(ilm_bscan, fovea_col=fovea_col, spacing=spacing)
    if pit.status != 'ok':
        return Measurement(feature_id, None, 'category', pit.status)
    depth = pit.value['depth']
    category = 'inverted' if depth < -flat_um else 'shallow' if depth < flat_um else 'pit'
    return Measurement(feature_id, category, 'category', detail=pit.value)


def surface_contour(surface_bscan, *, spacing=None, window=15, feature_id='ft_rpe_contour') -> Measurement:
    """Irregularity of a boundary: RMS deviation from a moving-average baseline and peak elevation."""
    s = np.asarray(surface_bscan, dtype=float)
    valid = ~np.isnan(s)
    if valid.sum() < window:
        return not_evaluable(feature_id, 'index', 'too few segmented columns')
    x = np.arange(len(s))
    filled = np.interp(x, x[valid], s[valid])
    baseline = np.polyval(np.polyfit(x, filled, 2), x)
    deviation = (baseline - filled) * (spacing.z_um if spacing and spacing.z_um else 1.0)  # positive = elevation
    return Measurement(feature_id, {'rms': float(np.sqrt(np.mean(deviation ** 2))),
                                    'max_elevation': float(deviation.max())}, 'index')


def layer_continuity(visible, *, spacing=None, min_gap_px=1, feature_id='ft_layer_continuity_generic') -> Measurement:
    """From a boolean per-A-scan visibility map: preserved fraction and gaps along each B-scan."""
    v = np.atleast_2d(np.asarray(visible, bool))
    gaps = []
    for row in v:
        run = 0
        for flag in list(row) + [True]:
            if not flag:
                run += 1
            else:
                if run >= min_gap_px:
                    gaps.append(run)
                run = 0
    scale = spacing.x_mm * 1000 if spacing and spacing.x_mm else 1.0
    category = 'continuous' if not gaps else 'disrupted' if v.mean() > 0.5 else 'absent'
    return Measurement(feature_id, category, 'category',
                       detail={'preserved_fraction': float(v.mean()), 'gap_count': len(gaps),
                               'max_gap': max(gaps) * scale if gaps else 0.0})


def ez_preserved(ez_visible, *, spacing=None) -> tuple[Measurement, Measurement, Measurement]:
    """EZ preserved area (en-face), preserved fraction and widest disruption on any B-scan."""
    v = np.atleast_2d(np.asarray(ez_visible, bool))
    cont = layer_continuity(v, spacing=spacing, feature_id='ft_ez_continuity')
    if spacing is not None and spacing.area_mm2 is not None:
        area = Measurement('ft_ez_preserved_area', float(v.sum() * spacing.area_mm2), 'mm2')
    else:
        area = Measurement('ft_ez_preserved_area', float(v.sum()), 'px2')
    unit = 'um' if spacing and spacing.x_mm else 'px'
    return (area, Measurement('ft_ez_preserved_fraction', float(v.mean()), 'ratio'),
            Measurement('ft_ez_disruption_width', cont.detail['max_gap'], unit,
                        'ok' if cont.detail['gap_count'] else 'not_observed'))


def layer_reflectivity(bscan, surfaces_bscan, layer, *, feature_id='ft_layer_reflectivity_generic') -> Measurement:
    """Mean intensity inside ``layer`` on one B-scan, raw and normalised so vitreous = 0, RPE = 1.

    ``surfaces_bscan`` maps boundary names to 1D row positions for this B-scan.
    """
    image = np.asarray(bscan, dtype=float)
    top, bottom = (np.asarray(surfaces_bscan[n], float) for n in LAYERS[layer])
    rows = np.arange(image.shape[0])[:, None]
    inside = (rows >= top[None]) & (rows < bottom[None])
    if not inside.any():
        return not_evaluable(feature_id, 'intensity', 'empty layer')
    raw = float(image[inside].mean())
    norm = math.nan
    if 'ILM' in surfaces_bscan and 'RPE' in surfaces_bscan:
        ilm = np.asarray(surfaces_bscan['ILM'], float)[None]
        rpe = np.asarray(surfaces_bscan['RPE'], float)[None]
        vitreous_px = image[rows < ilm - 5]
        rpe_px = image[np.abs(rows - rpe) <= 2]
        if vitreous_px.size and rpe_px.size and rpe_px.mean() != np.median(vitreous_px):
            v = float(np.median(vitreous_px))
            norm = (raw - v) / (float(rpe_px.mean()) - v)
    return Measurement(feature_id, raw, 'intensity', detail={'normalised': norm})


def layer_order(surfaces, *, tolerance_px=0, feature_id='ft_layer_order') -> Measurement:
    """Fraction of A-scans where all present surfaces keep the anatomical top-to-bottom order."""
    order = ['ILM', 'RNFL_GCL', 'GCL_IPL', 'IPL_INL', 'INL_OPL', 'OPL_ONL', 'ELM', 'EZ', 'OS_RPE', 'RPE', 'BM', 'CSI']
    present = [np.asarray(surfaces[n], float) for n in order if n in surfaces]
    if len(present) < 2:
        return not_evaluable(feature_id, 'category', 'need at least two surfaces')
    stack = np.stack(present)
    diffs = np.diff(stack, axis=0)
    ok = np.all((diffs >= -tolerance_px) | np.isnan(diffs), axis=0)
    fraction = float(ok.mean())
    return Measurement(feature_id, 'preserved' if fraction == 1 else 'disorganised', 'category',
                       detail={'ordered_fraction': fraction})


def peripapillary_profile(thickness, disc_centre, *, radius_mm=1.73, spacing: Spacing, n=256, eye='OD'):
    """Thickness sampled on a circle around the disc (default 3.46 mm diameter), TSNIT order."""
    y_mm = spacing.y_mm if spacing.y_mm is not None else spacing.x_mm
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)            # 0 = temporal, going superior
    sign = 1 if eye == 'OD' else -1
    rows = disc_centre[0] - radius_mm / y_mm * np.sin(angles)
    cols = disc_centre[1] - sign * radius_mm / spacing.x_mm * np.cos(angles)
    rr = np.clip(np.round(rows).astype(int), 0, thickness.shape[0] - 1)
    cc = np.clip(np.round(cols).astype(int), 0, thickness.shape[1] - 1)
    return np.degrees(angles), thickness[rr, cc]


def rnfl_peripapillary(surfaces, disc_centre, *, spacing: Spacing, eye='OD',
                       feature_id='ft_rnfl_thickness_peripapillary') -> Measurement:
    """Global, quadrant and 12 clock-hour mean RNFL on the peripapillary circle (TSNIT)."""
    t = thickness_map(surfaces, 'rnfl', spacing=spacing)
    angles, profile = peripapillary_profile(t, disc_centre, spacing=spacing, eye=eye)
    quadrants = {'T': (angles >= 315) | (angles < 45), 'S': (angles >= 45) & (angles < 135),
                 'N': (angles >= 135) & (angles < 225), 'I': (angles >= 225) & (angles < 315)}
    clock = {f'h{i + 1}': float(np.nanmean(profile[(angles >= i * 30) & (angles < (i + 1) * 30)])) for i in range(12)}
    return Measurement(feature_id, float(np.nanmean(profile)), _unit(spacing),
                       detail={'quadrants': {k: float(np.nanmean(profile[m])) for k, m in quadrants.items()},
                               'clock_hours_from_temporal': clock, 'profile': profile.tolist()})


def staphyloma_depth(bm_bscan, *, spacing=None, feature_id='ft_staphyloma_depth') -> Measurement:
    """Maximal posterior bowing of BM below the chord joining its two ends on one wide B-scan."""
    s = np.asarray(bm_bscan, dtype=float)
    valid = np.where(~np.isnan(s))[0]
    if len(valid) < 3:
        return not_evaluable(feature_id, 'length', 'BM missing')
    x0, x1 = valid[0], valid[-1]
    chord = s[x0] + (s[x1] - s[x0]) * (np.arange(len(s)) - x0) / (x1 - x0)
    depth = np.nanmax(s - chord) * (spacing.z_um if spacing and spacing.z_um else 1.0)
    return Measurement(feature_id, float(max(depth, 0.0)), _unit(spacing))
