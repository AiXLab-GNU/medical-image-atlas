"""Mass outline and margin measurements from a lesion mask and the grey image.

Adapted from the native-resolution morphometry of mammography-xai E124 (outline shape, radial profile,
Fourier energy, radially aligned ridges in an outer band, boundary sharpness and contrast), rewritten
with scikit-image/scipy only. Bands are given in millimetres when the pixel size is known, otherwise
as a fraction of the mass radius.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage import feature, filters, measure

from ._common import Measurement, area, as_float, largest_component, length, max_feret


def _main(mask):
    m = largest_component(np.asarray(mask, bool))
    if not m.any():
        raise ValueError('empty mask')
    return m


def size(mask, pixel_mm=None) -> Measurement:
    value, unit = length(max_feret(_main(mask)), pixel_mm)
    return Measurement('ft_mass_size', round(value, 1), unit, note='경계 두 점 사이 최대 거리')


def mass_area(mask, pixel_mm=None) -> Measurement:
    value, unit = area(_main(mask).sum(), pixel_mm)
    return Measurement('ft_mass_area', value, unit)


def circularity(mask) -> Measurement:
    p = measure.regionprops(_main(mask).astype(int))[0]
    c = 4 * np.pi * p.area / max(p.perimeter, 1) ** 2
    return Measurement('ft_mass_circularity', round(float(min(c, 1.0)), 3), 'index')


def solidity(mask) -> Measurement:
    p = measure.regionprops(_main(mask).astype(int))[0]
    return Measurement('ft_mass_solidity', round(float(p.solidity), 3), 'ratio')


def _radial_profile(m, n=256):
    cy, cx = ndi.center_of_mass(m)
    contour = max(measure.find_contours(m.astype(float), 0.5), key=len)
    ang = np.arctan2(contour[:, 0] - cy, contour[:, 1] - cx)
    r = np.hypot(contour[:, 0] - cy, contour[:, 1] - cx)
    order = np.argsort(ang)
    grid = np.linspace(-np.pi, np.pi, n, endpoint=False)
    return np.interp(grid, ang[order], r[order], period=2 * np.pi), (cy, cx)


def radial_sd(mask) -> Measurement:
    rr, _ = _radial_profile(_main(mask))
    rn = rr / rr.mean()
    spec = np.abs(np.fft.rfft(rn - 1)) ** 2
    hf = float(spec[9:].sum() / max(spec[1:].sum(), 1e-12))
    return Measurement('ft_mass_radial_sd', round(float(rn.std()), 3), 'index',
                       detail={'fourier_high_frequency_fraction': round(hf, 3)})


def _band(m, width_px):
    return ndi.binary_dilation(m, iterations=max(int(width_px), 1)) & ~m


def spiculation_index(image, mask, pixel_mm=None, band_mm=3.0) -> Measurement:
    """Fraction of ridge pixels in the outer band whose direction points to the mass centre (±22.5°)."""
    m = _main(mask)
    img = filters.gaussian(as_float(image), 2)
    radius = np.sqrt(m.sum() / np.pi)
    width = band_mm / pixel_mm if pixel_mm else 0.6 * radius
    band = _band(m, width)
    sigma = max(2.0, radius / 15)
    ridge = filters.sato(img, sigmas=[sigma, 1.5 * sigma], black_ridges=False)
    Arr, Arc, Acc = feature.structure_tensor(img, sigma=2 * sigma, order='rc')
    theta = 0.5 * np.arctan2(2 * Arc, Acc - Arr)              # dominant gradient direction
    vals = ridge[band]
    if vals.size == 0:
        return Measurement('ft_mass_spiculation_index', None, 'ratio', 'not_evaluable', '바깥 띠 없음')
    sel = band & (ridge > np.quantile(vals, 0.9))
    cy, cx = ndi.center_of_mass(m)
    yy, xx = np.nonzero(sel)
    radial = np.arctan2(yy - cy, xx - cx)
    ridge_dir = theta[sel] + np.pi / 2                        # ridges run across the gradient
    align = np.abs(np.cos(ridge_dir - radial))
    frac = float((align > np.cos(np.pi / 8)).mean())
    return Measurement('ft_mass_spiculation_index', round(frac, 3), 'ratio',
                       detail={'band_px': round(float(width), 1), 'ridge_pixels': int(sel.sum()),
                               'ridge_points': np.c_[yy, xx][align > np.cos(np.pi / 8)][::5].tolist()})


def margin_sharpness(image, mask) -> Measurement:
    m = _main(mask)
    img = filters.gaussian(as_float(image), 2)
    radius = np.sqrt(m.sum() / np.pi)
    edge = m & ~ndi.binary_erosion(m)
    inner = m & ~ndi.binary_erosion(m, iterations=max(int(0.2 * radius), 1))
    outer = _band(m, max(int(0.2 * radius), 1))
    gy, gx = np.gradient(img)
    g = np.hypot(gx, gy)
    diff = abs(img[inner].mean() - img[outer].mean())
    return Measurement('ft_mass_margin_sharpness', round(float(g[edge].mean() / (diff + 1e-6)), 3), 'index')


def contrast(image, mask) -> Measurement:
    m = _main(mask)
    img = filters.gaussian(as_float(image), 2)
    radius = np.sqrt(m.sum() / np.pi)
    outer = _band(m, max(int(0.5 * radius), 2))
    c = (img[m].mean() - img[outer].mean()) / (img[outer].std() + 1e-6)
    return Measurement('ft_mass_contrast', round(float(c), 2), 'index')
