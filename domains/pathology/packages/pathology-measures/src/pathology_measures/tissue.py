"""Slide-level tissue composition from an RGB image and an annotation label map.

``tissue_mask`` separates tissue from the bright glass background (saturation and luminance, as in pathology-ai
E022). Fractions use the tissue area as denominator. Labels follow the provider's integer classes; pass the class
numbers that mean tumour, benign gland, stroma or artifact for that dataset.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from ._common import Measurement, area_mm2, length_mm, max_feret, rgb_u8


def tissue_mask(rgb, saturation_min=0.07, luminance_max=0.88, min_object_px=64) -> np.ndarray:
    x = rgb_u8(rgb).astype(np.float32) / 255.0
    mx, mn = x.max(2), x.min(2)
    sat = (mx - mn) / np.maximum(mx, 1 / 255)
    lum = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    m = (sat > saturation_min) & (lum < luminance_max)
    m = ndi.binary_opening(m, iterations=1)
    labels, n = ndi.label(m)
    if n:
        sizes = np.bincount(labels.ravel())
        keep = sizes >= min_object_px
        keep[0] = False
        m = keep[labels]
    return ndi.binary_fill_holes(m)


def tissue_area(tissue, mpp=None) -> Measurement:
    value, unit = area_mm2(np.asarray(tissue, bool).sum(), mpp)
    return Measurement('ft_tissue_area', round(value, 3), unit)


def _fraction(feature_id, part, tissue, note=''):
    t = np.asarray(tissue, bool)
    if t.sum() == 0:
        return Measurement(feature_id, None, '%', 'not_evaluable', '조직 없음')
    v = 100.0 * (np.asarray(part, bool) & t).sum() / t.sum()
    return Measurement(feature_id, round(float(v), 1), '%', 'ok' if v > 0 else 'not_observed', note)


def tumor_fraction(labels, tissue, tumor_classes=(1,)) -> Measurement:
    return _fraction('ft_tumor_fraction', np.isin(labels, tumor_classes), tissue)


def stroma_fraction(labels, tissue, stroma_classes=(7,)) -> Measurement:
    return _fraction('ft_stroma_fraction', np.isin(labels, stroma_classes), tissue, '간질 주석에 자동 보충이 섞일 수 있음')


def benign_gland_fraction(labels, tissue, gland_classes=(2,)) -> Measurement:
    return _fraction('ft_benign_gland_fraction', np.isin(labels, gland_classes), tissue)


def artifact_fraction(labels, tissue, artifact_classes=(3,)) -> Measurement:
    return _fraction('ft_artifact_fraction', np.isin(labels, artifact_classes), tissue)


def lesion_fraction(mask, tissue) -> Measurement:
    return _fraction('ft_lesion_generic_fraction', mask, tissue)


def tumor_area(labels, mpp=None, tumor_classes=(1,)) -> Measurement:
    value, unit = area_mm2(np.isin(labels, tumor_classes).sum(), mpp)
    return Measurement('ft_tumor_area', round(value, 3), unit)


def lesion_area(mask, mpp=None) -> Measurement:
    value, unit = area_mm2(np.asarray(mask, bool).sum(), mpp)
    return Measurement('ft_lesion_generic_area', round(value, 4), unit)


def tumor_extent(labels, mpp=None, tumor_classes=(1,)) -> Measurement:
    m = np.isin(labels, tumor_classes)
    if not m.any():
        return Measurement('ft_tumor_extent', None, 'mm', 'not_observed')
    value, unit = length_mm(max_feret(m), mpp)
    return Measurement('ft_tumor_extent', round(value, 2), unit, note='종양 화소 사이 최대 거리')


def lesion_count(mask, min_px=1, merge_px=0) -> Measurement:
    """Separate foci; pieces closer than about ``merge_px`` pixels are merged first."""
    m = np.asarray(mask, bool)
    if merge_px:
        m = ndi.binary_closing(m, structure=np.ones((3, 3)), iterations=int(merge_px))
    labels, n = ndi.label(m)
    if n and min_px > 1:
        n = int((np.bincount(labels.ravel())[1:] >= min_px).sum())
    return Measurement('ft_lesion_generic_count', int(n), 'count', 'ok' if n else 'not_observed',
                       note=f'{merge_px}px 안의 조각은 하나로 셈' if merge_px else '')


def presence(mask, min_px=1) -> Measurement:
    return Measurement('ft_lesion_generic_presence', bool(np.asarray(mask, bool).sum() >= min_px), 'presence')


def pattern_percent(pattern_mask, tumor_mask, pattern: int) -> Measurement:
    """Share of tumour area occupied by Gleason pattern 3, 4 or 5."""
    fid = {3: 'ft_pattern3_percent', 4: 'ft_pattern4_percent', 5: 'ft_pattern5_percent'}[pattern]
    t = np.asarray(tumor_mask, bool)
    if t.sum() == 0:
        return Measurement(fid, None, '%', 'not_evaluable', '종양 없음')
    v = 100.0 * (np.asarray(pattern_mask, bool) & t).sum() / t.sum()
    return Measurement(fid, round(float(v), 1), '%', 'ok' if v > 0 else 'not_observed')
