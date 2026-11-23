"""Calcification detection and cluster measurements inside a lesion region.

Detection follows mammography-xai E124: white top-hat (disk ≈ 0.5 mm, or a fixed pixel radius when the
pixel size is unknown) inside the region dilated by a margin, candidates above median + k·MAD of the
top-hat values. Cluster descriptors (count, extent, density, size and its variation, elongation,
branching, linear arrangement, nearest-neighbour spacing, contrast) are computed on the detected spots.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage import filters, measure, morphology

from ._common import Measurement, area, as_float, length


@dataclass
class Calcifications:
    labels: np.ndarray           # integer label image of detected spots
    props: list                  # skimage regionprops of the spots
    region: np.ndarray           # search region
    mad: float                   # robust noise of the top-hat values


def detect(image, region, pixel_mm=None, k=4.0, min_px=2, tophat_px=None) -> Calcifications:
    img = filters.gaussian(as_float(image), 0.7)
    radius = tophat_px or (int(round(0.5 / pixel_mm)) if pixel_mm else 7)
    search = ndi.binary_dilation(region, iterations=max(radius, 1))
    th = morphology.white_tophat(img, morphology.disk(radius))
    vals = th[search]
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med)) * 1.4826 + 1e-6)
    spots = (th > med + k * mad) & search
    labels = measure.label(spots)
    props = [p for p in measure.regionprops(labels, intensity_image=th) if p.area >= min_px]
    keep = np.zeros(labels.max() + 1, bool)
    keep[[p.label for p in props]] = True
    labels = np.where(keep[labels], labels, 0)
    return Calcifications(labels, props, search, mad)


def count(c: Calcifications) -> Measurement:
    n = len(c.props)
    return Measurement('ft_calc_count', n, 'count', 'ok' if n else 'not_observed')


def extent(c: Calcifications, pixel_mm=None) -> Measurement:
    if len(c.props) < 2:
        return Measurement('ft_calc_extent', None, 'px', 'not_evaluable', '석회화 2개 미만')
    cen = np.array([p.centroid for p in c.props])
    d = np.sqrt(((cen[:, None] - cen[None]) ** 2).sum(-1)).max()
    value, unit = length(d, pixel_mm)
    return Measurement('ft_calc_extent', round(value, 1), unit, note='석회화 중심 사이 최대 거리')


def density(c: Calcifications, pixel_mm=None) -> Measurement:
    a, unit = area(c.region.sum(), pixel_mm)
    per = 'count/cm2' if pixel_mm else 'count/10^4 px2'
    scale = 100.0 if pixel_mm else 1e4
    return Measurement('ft_calc_density', round(len(c.props) / max(a, 1e-9) * scale, 2), per)


def spot_size(c: Calcifications, pixel_mm=None) -> Measurement:
    if not c.props:
        return Measurement('ft_calc_size', None, 'px2', 'not_observed')
    areas = np.array([p.area for p in c.props], float)
    mean, unit = area(areas.mean(), pixel_mm)
    big, _ = area(areas.max(), pixel_mm)
    return Measurement('ft_calc_size', round(mean, 2), unit, detail={'max': round(big, 2)})


def size_variation(c: Calcifications) -> Measurement:
    if len(c.props) < 3:
        return Measurement('ft_calc_size_variation', None, 'ratio', 'not_evaluable', '석회화 3개 미만')
    a = np.array([p.area for p in c.props], float)
    return Measurement('ft_calc_size_variation', round(float(a.std() / a.mean()), 3), 'ratio')


def elongation(c: Calcifications) -> Measurement:
    if not c.props:
        return Measurement('ft_calc_elongation', None, 'ratio', 'not_observed')
    e = np.array([p.eccentricity for p in c.props])
    return Measurement('ft_calc_elongation', round(float((e > 0.9).mean()), 3), 'ratio')


def branching(c: Calcifications, min_px=6) -> Measurement:
    big = [p for p in c.props if p.area >= min_px]
    if not big:
        return Measurement('ft_calc_branching', None, 'ratio', 'not_evaluable', '골격을 낼 만큼 큰 석회화 없음')
    hits = []
    for p in big:
        sk = morphology.skeletonize(p.image)
        nb = ndi.convolve(sk.astype(int), np.ones((3, 3)), mode='constant') - 1
        hits.append(bool(((nb >= 3) & sk).any()))
    return Measurement('ft_calc_branching', round(float(np.mean(hits)), 3), 'ratio')


def linearity(c: Calcifications) -> Measurement:
    if len(c.props) < 3:
        return Measurement('ft_calc_linearity', None, 'index', 'not_evaluable', '석회화 3개 미만')
    cen = np.array([p.centroid for p in c.props])
    ev = np.linalg.eigvalsh(np.cov(cen.T))
    return Measurement('ft_calc_linearity', round(float(1 - ev[0] / max(ev[1], 1e-9)), 3), 'index')


def nn_distance(c: Calcifications, pixel_mm=None) -> Measurement:
    if len(c.props) < 3:
        return Measurement('ft_calc_nn_distance', None, 'px', 'not_evaluable', '석회화 3개 미만')
    cen = np.array([p.centroid for p in c.props])
    d, _ = cKDTree(cen).query(cen, k=2)
    value, unit = length(d[:, 1].mean(), pixel_mm)
    return Measurement('ft_calc_nn_distance', round(value, 1), unit)


def spot_contrast(c: Calcifications) -> Measurement:
    if not c.props:
        return Measurement('ft_calc_contrast', None, 'index', 'not_observed')
    v = np.array([p.mean_intensity for p in c.props]) / c.mad
    return Measurement('ft_calc_contrast', round(float(v.mean()), 1), 'index', note='top-hat ÷ MAD')
