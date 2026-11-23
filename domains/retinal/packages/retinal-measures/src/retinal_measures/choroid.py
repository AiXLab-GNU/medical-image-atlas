"""Choroid measurements on OCT B-scans: vascularity index and large-vessel diameter."""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage import filters

from ._common import Measurement, not_evaluable


def choroid_mask(shape, bm, csi):
    rows = np.arange(shape[0])[:, None]
    return (rows >= np.asarray(bm, float)[None]) & (rows < np.asarray(csi, float)[None])


def luminal_mask(bscan, choroid, *, window=15, k=-0.2):
    """Dark (luminal) choroid pixels by Niblack local thresholding, restricted to the choroid."""
    image = np.asarray(bscan, float)
    if window % 2 == 0:
        window += 1
    return (image < filters.threshold_niblack(image, window_size=window, k=k)) & choroid


def vascularity_index(bscan, bm, csi, *, window=15, k=-0.2,
                      feature_id='ft_choroidal_vascularity_index') -> Measurement:
    """CVI = luminal area / total choroid area on one B-scan (Niblack binarisation)."""
    choroid = choroid_mask(np.shape(bscan), bm, csi)
    if not choroid.any():
        return not_evaluable(feature_id, 'ratio', 'choroid boundaries missing')
    lumen = luminal_mask(bscan, choroid, window=window, k=k)
    return Measurement(feature_id, float(lumen.sum() / choroid.sum()), 'ratio',
                       detail={'luminal_px': int(lumen.sum()), 'total_px': int(choroid.sum())})


def large_vessel_diameter(bscan, bm, csi, *, spacing=None, window=15, k=-0.2,
                          feature_id='ft_haller_vessel_diameter') -> Measurement:
    """Largest inscribed-circle diameter of a luminal region in the outer half of the choroid."""
    image = np.asarray(bscan, float)
    choroid = choroid_mask(image.shape, bm, csi)
    rows = np.arange(image.shape[0])[:, None]
    outer = choroid & (rows >= (np.asarray(bm, float) + np.asarray(csi, float))[None] / 2)
    lumen = luminal_mask(image, choroid, window=window, k=k) & outer
    if not lumen.any():
        return Measurement(feature_id, None, 'length', 'not_observed')
    diameter = 2 * ndimage.distance_transform_edt(lumen).max()
    if spacing and spacing.z_um:
        return Measurement(feature_id, float(diameter * spacing.z_um), 'um', note='axial diameter')
    return Measurement(feature_id, float(diameter), 'px')
