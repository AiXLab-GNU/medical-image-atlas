"""Whole-breast measurements on one 2D mammogram view (FFDM CC or MLO).

The image is any grey array; the chest wall side is found from the image. Masks are boolean arrays of the
image shape. Pixel size is optional: without it lengths and areas stay in pixels.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi, signal
from skimage import filters, measure, morphology, transform

from ._common import Measurement, area, as_float, largest_component, length


@dataclass
class BreastGeometry:
    """Landmarks of one view. Points are (row, col) in image pixels."""
    breast: np.ndarray                 # breast tissue mask (pectoral muscle excluded for MLO)
    chest_side: str                    # 'left' or 'right' image edge touching the chest wall
    nipple: tuple[float, float]
    pectoral: np.ndarray | None        # MLO pectoral muscle mask
    pectoral_line: tuple[tuple[float, float], tuple[float, float]] | None   # two points on the anterior edge
    pnl_foot: tuple[float, float]      # where the posterior nipple line meets the pectoral line / chest edge


def segment_breast(image: np.ndarray, scale: float = 0.25) -> np.ndarray:
    """Breast (with pectoral muscle) mask: Otsu threshold on a smoothed copy, largest component, holes filled."""
    img = as_float(image)
    small = transform.rescale(img, scale, anti_aliasing=True) if scale != 1 else img
    small = filters.gaussian(small, 2)
    fg = small > max(filters.threshold_otsu(small) * 0.35, 0.02)
    fg = morphology.binary_opening(fg, morphology.disk(3))
    fg = ndi.binary_fill_holes(largest_component(fg))
    if scale != 1:
        fg = transform.resize(fg.astype(float), img.shape, order=0) > 0.5
    return fg


def chest_side(breast: np.ndarray) -> str:
    """The image edge with more breast pixels touches the chest wall."""
    return 'left' if breast[:, 0].sum() >= breast[:, -1].sum() else 'right'


def nipple_point(breast: np.ndarray, side: str, image: np.ndarray | None = None) -> tuple[float, float]:
    """Estimate the nipple's local protrusion, not the globally widest breast point.

    Remove the broad breast curvature from the anterior contour to locate a nipple candidate.
    When the source image is supplied, refine its tip in a small, lower-threshold crop: the
    coarse breast segmentation can erase a dim nipple. This remains a service estimate.
    """
    valid = np.flatnonzero(breast.any(axis=1))
    if not valid.size:
        raise ValueError('Cannot locate a nipple in an empty breast mask')
    rows = np.arange(valid[0], valid[-1] + 1)
    w = breast.shape[1]
    edge = (np.argmax(breast, axis=1) if side == 'right'
            else w - 1 - np.argmax(breast[:, ::-1], axis=1))[rows].astype(float)
    depth = w - 1 - edge if side == 'right' else edge
    fine = ndi.gaussian_filter1d(depth, max(1.0, len(rows) * 0.003))
    prominence = fine - ndi.gaussian_filter1d(fine, max(2.0, len(rows) * 0.035))
    peaks, properties = signal.find_peaks(prominence, prominence=max(2.0, 0.015 * depth.max()))
    eligible = ((rows[peaks] > rows[0] + 0.12 * len(rows))
                & (rows[peaks] < rows[0] + 0.92 * len(rows)) & (depth[peaks] > 0.65 * depth.max()))
    if eligible.any():
        candidates = peaks[eligible]
        centre = int(candidates[np.argmax(properties['prominences'][eligible])])
    else:
        # A smooth, featureless contour has no distinguishable nipple protrusion.
        candidates = np.flatnonzero(depth == depth.max())
        centre = int(candidates[len(candidates) // 2])
    radius = max(3, int(len(rows) * 0.05))
    lo, hi = max(0, centre - radius), min(len(rows), centre + radius + 1)
    if image is not None:
        col = int(edge[centre])
        margin = max(12, int(max(breast.shape) * 0.06))
        r0, r1 = int(rows[lo]), int(rows[hi - 1]) + 1
        c0, c1 = max(0, col - margin), min(w, col + margin + 1)
        local = filters.gaussian(as_float(image[r0:r1, c0:c1]), 1)
        foreground = largest_component(local > 0.05)
        if foreground.any():
            cols = np.flatnonzero(foreground.any(axis=0))
            tip = int(cols.min() if side == 'right' else cols.max())
            tip_rows = np.flatnonzero(foreground[:, tip])
            return float(r0 + tip_rows.mean()), float(c0 + tip)
    tip_depth = depth[lo:hi].max()
    tips = np.flatnonzero(depth[lo:hi] == tip_depth) + lo
    tip = int(tips[len(tips) // 2])
    return float(rows[tip]), float(edge[tip])


def nipple_centre(image: np.ndarray, side: str, threshold: float = 0.03) -> tuple[float, float] | None:
    """Centre of the nipple lobe on the full-resolution silhouette (service estimate).

    The breast silhouette (smoothed image above ``threshold``) gives the anterior depth per row. The nipple is
    the row band where the depth bulges above its broad median trend; that band is widened by a quarter, the
    breast contour across it is bridged by a quadratic fitted to the rows just above and below, and the
    centroid of the silhouette pixels in front of that bridge is returned. None when no lobe is found
    (nipple not in profile).
    """
    img = as_float(image)
    fg = largest_component(ndi.binary_fill_holes(ndi.gaussian_filter(img, 2) > threshold))
    rows = np.flatnonzero(fg.any(axis=1))
    if rows.size < 50:
        return None
    h, w = len(rows), fg.shape[1]
    edge = (np.argmax(fg[rows], axis=1) if side == 'right'
            else w - 1 - np.argmax(fg[rows, ::-1], axis=1)).astype(float)
    depth = (w - 1 - edge) if side == 'right' else edge.copy()
    d = ndi.gaussian_filter1d(depth, 3)
    prom = d - ndi.median_filter(d, size=int(0.15 * h) | 1, mode='nearest')
    lo, hi = int(0.1 * h), int(0.97 * h)
    k = lo + int(np.argmax(prom[lo:hi] * (d[lo:hi] / max(d.max(), 1)) ** 4))
    if prom[k] < max(3.0, 0.002 * h):
        return None
    a, b = k, k
    while a > 0 and prom[a] > 0.15 * prom[k]:
        a -= 1
    while b < h - 1 and prom[b] > 0.15 * prom[k]:
        b += 1
    span = max(b - a, 10)
    a, b = max(0, a - span // 4), min(h - 1, b + span // 4)
    context = np.r_[np.arange(max(0, a - span), a), np.arange(b + 1, min(h, b + 1 + span))]
    if context.size < 6:
        return None
    ys = np.arange(a, b + 1)
    bridge = np.polyval(np.polyfit(context, d[context], 2), ys)
    pr, pc = [], []
    for y, base in zip(ys, bridge):
        if depth[y] <= base:
            continue
        c0, c1 = (edge[y], w - 1 - base) if side == 'right' else (base, edge[y])
        cols = np.arange(int(c0), int(c1) + 1)
        cols = cols[(cols >= 0) & (cols < w)]
        cols = cols[fg[rows[y], cols]]
        pr += [rows[y]] * len(cols)
        pc += cols.tolist()
    if len(pr) < 20:
        return None
    return float(np.mean(pr)), float(np.mean(pc))


def segment_pectoral(image: np.ndarray, breast: np.ndarray, side: str, scale: float = 0.25):
    """MLO pectoral muscle as the bright region in the upper chest-wall corner, bounded by a fitted straight line.

    Returns (mask, ((r0, c0), (r1, c1))) or (None, None) when no consistent edge is found. A straight-line
    approximation of the anterior edge in the spirit of Kwok et al. 2004 (curvature refinement omitted).
    """
    img = as_float(image)
    if side == 'right':
        img, br = img[:, ::-1], breast[:, ::-1]
    else:
        br = breast
    small = transform.rescale(img, scale, anti_aliasing=True)
    bsmall = transform.resize(br.astype(float), small.shape, order=0) > 0.5
    h, w = small.shape
    sm = filters.gaussian(small, 3)
    # candidate edge: in each upper row, the first strong negative gradient going away from the chest wall
    gx = ndi.sobel(sm, axis=1)
    pts = []
    for r in range(int(0.02 * h), int(0.6 * h)):
        row = np.where(bsmall[r])[0]
        if len(row) < 10:
            continue
        span = row.max()
        g = gx[r, : int(span * 0.7)]
        if g.size < 5:
            continue
        c = int(np.argmin(g))
        if g[c] < -0.004 and c > 2:
            pts.append((r, c))
    if len(pts) < 15:
        return None, None
    pts = np.array(pts, float)
    model, inliers = measure.ransac(pts, measure.LineModelND, min_samples=2, residual_threshold=3, max_trials=500)
    if inliers is None or inliers.sum() < 10:
        return None, None
    good = pts[inliers]
    a, b = np.polyfit(good[:, 0], good[:, 1], 1)           # col = a*row + b
    if a >= 0 or b <= 0:                                      # the edge must slope back toward the chest wall
        return None, None
    rows = np.arange(h)[:, None]
    cols = np.arange(w)[None, :]
    mask_small = (cols < a * rows + b) & bsmall
    if mask_small.sum() < 0.01 * bsmall.sum() or mask_small.sum() > 0.5 * bsmall.sum():
        return None, None
    mask = transform.resize(mask_small.astype(float), img.shape, order=0) > 0.5
    r_end = min(-b / a, h - 1)
    line = ((0.0, b / scale), (r_end / scale, (a * r_end + b) / scale))
    if side == 'right':
        mask = mask[:, ::-1]
        W = image.shape[1] - 1
        line = ((line[0][0], W - line[0][1]), (line[1][0], W - line[1][1]))
    return mask & breast, line


def geometry(image: np.ndarray, view: str) -> BreastGeometry:
    """Breast mask, chest side, nipple, pectoral muscle (MLO) and the posterior nipple line foot."""
    full = segment_breast(image)
    side = chest_side(full)
    pect, line = (segment_pectoral(image, full, side) if view.upper() == 'MLO' else (None, None))
    breast = full & ~pect if pect is not None else full
    nip = nipple_centre(image, side) or nipple_point(full, side, image)
    if line is not None:
        foot = _foot_on_line(nip, line)
    else:
        foot = (nip[0], 0.0 if side == 'left' else float(image.shape[1] - 1))
    return BreastGeometry(breast, side, nip, pect, line, foot)


def _foot_on_line(p, line):
    (r0, c0), (r1, c1) = line
    d = np.array([r1 - r0, c1 - c0], float)
    d /= np.linalg.norm(d)
    v = np.array([p[0] - r0, p[1] - c0])
    q = np.array([r0, c0]) + d * (v @ d)
    return float(q[0]), float(q[1])


def breast_area(geo: BreastGeometry, pixel_mm: float | None = None) -> Measurement:
    value, unit = area(geo.breast.sum(), pixel_mm)
    return Measurement('ft_breast_area', value, unit, note='대흉근 제외(MLO)' if geo.pectoral is not None else '')


def dense_tissue(image: np.ndarray, breast: np.ndarray, method: str = 'otsu') -> np.ndarray:
    """Dense (fibroglandular) pixels inside the breast: Otsu threshold of the smoothed breast intensities.

    A simple stand-in for clustering-based estimators such as LIBRA (Keller 2012); values depend on the
    vendor processing of the image, so they are comparable only within one image source.
    """
    img = filters.gaussian(as_float(image), 2)
    inner = ndi.binary_erosion(breast, iterations=max(3, int(0.01 * max(breast.shape))))   # drop the skin edge
    vals = img[inner]
    if vals.size < 100:
        return np.zeros_like(breast)
    thr = filters.threshold_otsu(vals)
    return inner & (img > thr)


def percent_density(dense: np.ndarray, breast: np.ndarray) -> Measurement:
    if breast.sum() == 0:
        return Measurement('ft_percent_density', None, '%', 'not_evaluable', '유방 영역 없음')
    return Measurement('ft_percent_density', round(100.0 * dense.sum() / breast.sum(), 1), '%',
                       note='Otsu 경계값(영상 처리 방식에 따라 달라짐)')


def dense_area(dense: np.ndarray, pixel_mm: float | None = None) -> Measurement:
    value, unit = area(dense.sum(), pixel_mm)
    return Measurement('ft_dense_area', value, unit)


def pectoral_area(geo: BreastGeometry, pixel_mm: float | None = None) -> Measurement:
    if geo.pectoral is None:
        return Measurement('ft_pectoral_area', None, 'px2', 'not_evaluable', '대흉근 경계를 찾지 못함(CC 또는 검출 실패)')
    value, unit = area(geo.pectoral.sum(), pixel_mm)
    return Measurement('ft_pectoral_area', value, unit)


def pectoral_angle(geo: BreastGeometry) -> Measurement:
    if geo.pectoral_line is None:
        return Measurement('ft_pectoral_angle', None, 'deg', 'not_evaluable', '대흉근 경계 없음')
    (r0, c0), (r1, c1) = geo.pectoral_line
    ang = float(np.degrees(np.arctan2(abs(c1 - c0), abs(r1 - r0))))
    return Measurement('ft_pectoral_angle', round(ang, 1), 'deg', note='영상 세로축 기준 · 직선 근사')


def pnl_length(geo: BreastGeometry, pixel_mm: float | None = None) -> Measurement:
    px = float(np.hypot(geo.nipple[0] - geo.pnl_foot[0], geo.nipple[1] - geo.pnl_foot[1]))
    value, unit = length(px, pixel_mm)
    basis = '대흉근 앞 경계까지' if geo.pectoral_line is not None else '영상 뒤 끝(흉벽 쪽)까지'
    return Measurement('ft_pnl_length', round(value, 1), unit, note=basis)


def pectoral_reaches_pnl(geo: BreastGeometry) -> Measurement:
    """True when the pectoral muscle extends down to (or below) the nipple level along its edge."""
    if geo.pectoral_line is None:
        return Measurement('ft_pectoral_reaches_pnl', None, 'presence', 'not_evaluable', '대흉근 경계 없음')
    lowest = max(geo.pectoral_line[0][0], geo.pectoral_line[1][0])
    return Measurement('ft_pectoral_reaches_pnl', bool(lowest >= geo.pnl_foot[0]), 'presence',
                       detail={'pectoral_bottom_row': lowest, 'pnl_row': geo.pnl_foot[0]})


def pnl_cc_mlo_difference(cc: BreastGeometry, mlo: BreastGeometry, pixel_mm: float | None = None) -> Measurement:
    """|PNL(CC) − PNL(MLO)| for one breast; within 1 cm suggests enough posterior tissue on CC."""
    a = pnl_length(cc, pixel_mm).value
    b = pnl_length(mlo, pixel_mm).value
    unit = 'mm' if pixel_mm else 'px'
    return Measurement('ft_pnl_cc_mlo_difference', round(abs(a - b), 1), unit)
