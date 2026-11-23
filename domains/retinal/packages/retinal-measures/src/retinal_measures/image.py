"""Whole-image measurements that need no segmentation: colour, texture and simple quality."""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage import feature, filters

from ._common import Measurement, as_mask


def fov_mask(rgb, *, threshold=0.05):
    """Circular field of view: pixels brighter than ``threshold`` × max in the red channel."""
    image = np.asarray(rgb, float)
    red = image[..., 0] if image.ndim == 3 else image
    return ndimage.binary_fill_holes(red > threshold * red.max())


def color_stats(rgb, *, fov=None, feature_id='ft_image_color_stats') -> Measurement:
    image = np.asarray(rgb, float)
    region = as_mask(fov, ndim=2) if fov is not None else fov_mask(image)
    channels = image[region] if image.ndim == 3 else image[region][:, None]
    names = ['r', 'g', 'b'][:channels.shape[1]]
    stats = {n: {'mean': float(c.mean()), 'std': float(c.std()), 'p05': float(np.percentile(c, 5)),
                 'p95': float(np.percentile(c, 95))} for n, c in zip(names, channels.T)}
    return Measurement(feature_id, stats, 'intensity')


def texture(gray, *, fov=None, levels=32, feature_id='ft_image_texture') -> Measurement:
    """GLCM contrast/homogeneity/energy/correlation (distance 1, four directions) and LBP entropy."""
    image = np.asarray(gray, float)
    if image.ndim == 3:
        image = image[..., 1]
    span = image.max() - image.min()
    q = ((image - image.min()) / span * (levels - 1)).astype(np.uint8) if span else np.zeros(image.shape, np.uint8)
    glcm = feature.graycomatrix(q, [1], [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4], levels=levels,
                                symmetric=True, normed=True)
    props = {p: float(feature.graycoprops(glcm, p).mean()) for p in ['contrast', 'homogeneity', 'energy', 'correlation']}
    lbp = feature.local_binary_pattern(q, 8, 1, 'uniform')
    region = as_mask(fov, ndim=2) if fov is not None else np.ones(q.shape, bool)
    hist = np.bincount(lbp[region].astype(int), minlength=10) / region.sum()
    hist = hist[hist > 0]
    props['lbp_entropy'] = float(-(hist * np.log2(hist)).sum())
    return Measurement(feature_id, props, 'index')


def quality(rgb, *, fov=None, feature_id='ft_image_quality') -> Measurement:
    """Simple quality indicators: sharpness (variance of Laplacian), contrast, illumination uniformity,
    and fractions of under/over-exposed pixels. These are descriptors, not a gradability decision."""
    image = np.asarray(rgb, float)
    gray = image[..., 1] if image.ndim == 3 else image
    region = as_mask(fov, ndim=2) if fov is not None else fov_mask(image)
    scale = gray.max() or 1.0
    g = gray / scale
    lap = ndimage.laplace(g)
    background = filters.gaussian(g, sigma=max(g.shape) / 20)
    detail = {'sharpness': float(lap[region].var()), 'contrast': float(g[region].std()),
              'illumination_cv': float(background[region].std() / (background[region].mean() or 1)),
              'dark_fraction': float((g[region] < 0.05).mean()), 'bright_fraction': float((g[region] > 0.95).mean())}
    return Measurement(feature_id, detail['sharpness'], 'score', detail=detail)


def oct_signal(bscan, *, feature_id='ft_oct_signal_strength') -> Measurement:
    """Signal-to-noise proxy for an OCT B-scan: 99th percentile over background (top rows) noise, in dB."""
    image = np.asarray(bscan, float)
    background = image[: max(image.shape[0] // 10, 1)]
    noise = background.std() or 1e-9
    snr = (np.percentile(image, 99) - background.mean()) / noise
    return Measurement(feature_id, float(20 * np.log10(max(snr, 1e-9))), 'dB')
