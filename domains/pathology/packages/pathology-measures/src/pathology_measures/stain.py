"""H&E stain normalisation (Macenko et al., ISBI 2009).

The two stain vectors of an image are estimated from the angular extremes of its optical-density pixels in the plane
of the two leading eigenvectors; the image is then re-coloured to a reference stain matrix and reference maximum
concentrations. Used to test whether stain variation between slides changes the measurements.
"""
from __future__ import annotations

import numpy as np

from ._common import rgb_u8

# reference stain matrix (rows: haematoxylin, eosin; OD per R, G, B) and 99th-percentile concentrations
REF_HE = np.array([[0.5626, 0.7201, 0.4062],
                   [0.2159, 0.8012, 0.5581]])
REF_MAX = np.array([1.9705, 1.0308])


def _od(rgb, io=240):
    x = rgb_u8(rgb).reshape(-1, 3).astype(np.float64)
    return -np.log((x + 1) / io)


def macenko_vectors(rgb, io=240, beta=0.15, alpha=1.0):
    """Stain matrix (2×3, haematoxylin first) and 99th-percentile concentrations of an H&E image."""
    od = _od(rgb, io)
    keep = od[(od > beta).all(1)]
    if len(keep) < 100:
        raise ValueError('too few stained pixels')
    _, vecs = np.linalg.eigh(np.cov(keep.T))
    plane = keep @ vecs[:, 1:3]
    phi = np.arctan2(plane[:, 1], plane[:, 0])
    lo, hi = np.percentile(phi, alpha), np.percentile(phi, 100 - alpha)
    v1 = vecs[:, 1:3] @ np.array([np.cos(lo), np.sin(lo)])
    v2 = vecs[:, 1:3] @ np.array([np.cos(hi), np.sin(hi)])
    he = np.array([v1, v2]) if v1[0] > v2[0] else np.array([v2, v1])      # haematoxylin has the larger red OD
    he = he * np.sign(he.sum(1, keepdims=True))
    he /= np.linalg.norm(he, axis=1, keepdims=True)
    conc = np.linalg.lstsq(he.T, od.T, rcond=None)[0]
    return he, np.percentile(conc, 99, axis=1)


def macenko_normalise(rgb, ref_he=REF_HE, ref_max=REF_MAX, io=240) -> np.ndarray:
    """Re-colour ``rgb`` to the reference stains; returns uint8 RGB of the same shape (unchanged if it fails)."""
    x = rgb_u8(rgb)
    try:
        he, mx = macenko_vectors(x, io)
    except (ValueError, np.linalg.LinAlgError):
        return x
    od = _od(x, io)
    conc = np.linalg.lstsq(he.T, od.T, rcond=None)[0]
    conc *= (ref_max / np.maximum(mx, 1e-6))[:, None]
    out = io * np.exp(-(ref_he.T @ conc))
    return np.clip(out.T.reshape(x.shape), 0, 255).astype(np.uint8)
