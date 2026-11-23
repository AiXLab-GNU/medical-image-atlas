"""Rigid alignment of serial H&E and IHC sections (needle-biopsy slides with several cores).

Both slides are reduced to tissue masks on a common grid (µm per pixel given by each slide's calibration), then
1. whole slide: mirror × rotation (4° steps, refined to 1°) × translation (phase correlation), scored by mask Dice;
2. per core: each H&E tissue piece is refined on its own (±10°, translation), because cores shift and bend
   independently between sections.
Transforms map H&E µm → IHC µm (``p_ihc = A @ p_he + t``; rows, cols; mirroring in A). Alignment is rigid and at
the level of tissue pieces: on PRECISE the sections differ enough that individual glands do not correspond (a
window-level match of haematoxylin maps reached a correlation of only 0.09–0.15), so a mapped window shows the same
region of the core, not the same glands.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage import measure, morphology, registration, transform

from ._common import rgb_u8


def tissue_od(rgb, mpp, grid_um=16.0, od_min=0.12) -> np.ndarray:
    """Tissue mask on a ``grid_um`` grid for both H&E and pale IHC counterstain: summed optical density, averaged
    onto the grid, above ``od_min``; gaps closed (~50 µm) and holes (lumina, glass inside cores) filled."""
    x = rgb_u8(rgb).astype(np.float32)
    od = -np.log((x + 1) / 256).sum(2)
    small = transform.rescale(od, mpp / grid_um, order=1, anti_aliasing=True)
    m = ndi.binary_closing(small > od_min, structure=morphology.disk(3))
    m = ndi.binary_fill_holes(m)
    return morphology.remove_small_objects(m, 20)


def _matrix(angle_deg, mirror):
    a = np.deg2rad(angle_deg)
    r = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return r @ (np.diag([1.0, -1.0]) if mirror else np.eye(2))      # mirror flips columns


def warp_to(moving, shape, A, t):
    """Sample ``moving`` on an output grid of ``shape``: out[p] = moving[A p + t] (nearest)."""
    rr, cc = np.indices(shape, dtype=np.float32)
    src_r = A[0, 0] * rr + A[0, 1] * cc + t[0]
    src_c = A[1, 0] * rr + A[1, 1] * cc + t[1]
    return ndi.map_coordinates(np.asarray(moving, np.float32), [src_r, src_c], order=0, cval=0) > 0.5


def _dice(a, b):
    return 2 * float((a & b).sum()) / max(int(a.sum() + b.sum()), 1)


def _search(A_mask, B_mask, angles, mirrors, centre_a, centre_b):
    best = (-1.0, (0.0, False, np.zeros(2)))
    for mirror in mirrors:
        for ang in angles:
            M = _matrix(ang, mirror)
            t = np.asarray(centre_b) - M @ np.asarray(centre_a)
            w = warp_to(B_mask, A_mask.shape, M, t)
            if not w.any():
                continue
            shift, _, _ = registration.phase_cross_correlation(A_mask.astype(np.float32), w.astype(np.float32),
                                                               normalization=None)
            t2 = t - M @ shift
            d = _dice(A_mask, warp_to(B_mask, A_mask.shape, M, t2))
            if d > best[0]:
                best = (d, (float(ang), mirror, t2))
    return best


def align(he_rgb, he_mpp, ihc_rgb, ihc_mpp, grid_um=16.0, min_core_mm2=0.05):
    """Whole-slide and per-core rigid transforms H&E µm → IHC µm, with mask Dice before and after."""
    A = tissue_od(he_rgb, he_mpp, grid_um)
    B = tissue_od(ihc_rgb, ihc_mpp, grid_um)
    ca, cb = ndi.center_of_mass(A), ndi.center_of_mass(B)
    d0 = _dice(A, warp_to(B, A.shape, np.eye(2), np.asarray(cb) - np.asarray(ca)))
    _, (ang, mirror, _) = _search(A, B, np.arange(0, 360, 4), (False, True), ca, cb)
    d, (ang, mirror, t) = _search(A, B, np.arange(ang - 3, ang + 3.01, 1.0), (mirror,), ca, cb)
    M = _matrix(ang, mirror)
    cores = []
    lab = measure.label(A)
    min_px = min_core_mm2 * 1e6 / grid_um ** 2
    composite = np.zeros(A.shape, bool)
    for p in measure.regionprops(lab):
        if p.area < min_px:
            continue
        one = lab == p.label
        r0, c0, r1, c1 = p.bbox
        r0, c0 = max(r0 - 20, 0), max(c0 - 20, 0)
        r1, c1 = min(r1 + 20, A.shape[0]), min(c1 + 20, A.shape[1])
        crop = one[r0:r1, c0:c1]
        off = np.array([r0, c0], float)
        t_crop = t + M @ off
        base = _dice(crop, warp_to(B, crop.shape, M, t_crop))
        best = (base, ang, t_crop)
        cen = np.array(ndi.center_of_mass(crop))
        for a2 in np.arange(ang - 10, ang + 10.01, 2.0):
            M2 = _matrix(a2, mirror)
            t2 = (M @ cen + t_crop) - M2 @ cen                     # rotate about the core centre
            w = warp_to(B, crop.shape, M2, t2)
            if not w.any():
                continue
            shift, _, _ = registration.phase_cross_correlation(crop.astype(np.float32), w.astype(np.float32),
                                                               normalization=None)
            if np.hypot(*shift) > 40:                              # > 640 µm would jump to another core
                continue
            t3 = t2 - M2 @ shift
            dd = _dice(crop, warp_to(B, crop.shape, M2, t3))
            if dd > best[0]:
                best = (dd, a2, t3)
        dd, a2, t3 = best
        M2 = _matrix(a2, mirror)
        t_full = t3 - M2 @ off
        composite[one] = warp_to(B, A.shape, M2, t_full)[one]
        cores.append({'centre_um': [float(v * grid_um) for v in p.centroid], 'area_mm2': round(p.area * grid_um ** 2 / 1e6, 3),
                      'A': M2.tolist(), 't_um': (t_full * grid_um).tolist(), 'dice_global': round(base, 3), 'dice': round(dd, 3)})
    big = A & (lab > 0) & np.isin(lab, [p.label for p in measure.regionprops(lab) if p.area >= min_px])
    d_core = 2 * float((big & composite).sum()) / max(int(big.sum() + composite.sum()), 1) if cores else d
    return {'grid_um': grid_um, 'global': {'A': M.tolist(), 't_um': (t * grid_um).tolist(), 'angle': ang, 'mirror': mirror},
            'cores': cores, 'dice_before': round(d0, 3), 'dice_global': round(d, 3), 'dice_cores': round(d_core, 3)}


def core_for(result, point_um):
    """Transform of the H&E core nearest to ``point_um`` (row, col in H&E µm); the global one if there are no cores."""
    if not result['cores']:
        return np.array(result['global']['A']), np.array(result['global']['t_um'])
    c = min(result['cores'], key=lambda k: np.hypot(k['centre_um'][0] - point_um[0], k['centre_um'][1] - point_um[1]))
    return np.array(c['A']), np.array(c['t_um'])


def map_window(result, he_shape, he_mpp, he_origin_um):
    """(A_px, t_px) taking H&E-window pixels to IHC pixels at level 0 µm, for an H&E window at ``he_origin_um``."""
    centre = (he_origin_um[0] + he_shape[0] * he_mpp / 2, he_origin_um[1] + he_shape[1] * he_mpp / 2)
    A, t = core_for(result, centre)
    return A * he_mpp, A @ np.asarray(he_origin_um, float) + t      # result in IHC µm; divide by IHC mpp at use

