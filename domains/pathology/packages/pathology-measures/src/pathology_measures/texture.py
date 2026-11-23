"""Grey-level co-occurrence texture of a region (as in pathology-ai E022, scikit-image implementation)."""
from __future__ import annotations

import numpy as np
from skimage import feature

from ._common import Measurement, rgb_u8


def glcm_contrast(rgb, region, levels=32, distance=2) -> Measurement:
    region = np.asarray(region, bool)
    if region.sum() < 100:
        return Measurement('ft_texture_contrast', None, 'index', 'not_evaluable', '영역이 작음')
    g = rgb_u8(rgb).astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    q = 1 + np.clip((g / 256.0 * (levels - 1)).astype(np.uint8), 0, levels - 2)   # region levels 1..levels-1
    q = np.where(region, q, 0).astype(np.uint8)
    # pixels outside the region are level 0, and pairs touching level 0 are dropped below
    m = feature.graycomatrix(q, [distance], [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4], levels=levels, symmetric=True)
    m = m.astype(float)
    m[0, :, :, :] = 0
    m[:, 0, :, :] = 0
    m /= np.maximum(m.sum(axis=(0, 1), keepdims=True), 1)            # normalise each direction
    i, j = np.ogrid[:levels, :levels]
    contrast = float((((i - j) ** 2)[:, :, None] * m[:, :, 0, :]).sum(axis=(0, 1)).mean())
    return Measurement('ft_texture_contrast', round(contrast / (levels - 2) ** 2, 4), 'index',
                       note=f'GLCM 대비 ÷ (단계−2)² · {levels}단계 · 거리 {distance}px · 4방향 평균')
