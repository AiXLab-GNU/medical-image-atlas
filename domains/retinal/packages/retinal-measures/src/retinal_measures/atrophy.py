"""Atrophy (GA / cRORA / chorioretinal atrophy) measurements from en-face masks (FAF, CFP, OCT en-face)."""
from __future__ import annotations

import math

from ._common import Measurement, Spacing, area_value, as_mask, not_evaluable
from . import lesions


def area(mask, *, spacing: Spacing | None = None, feature_id='ft_atrophy_area') -> Measurement:
    pixels = int(as_mask(mask, ndim=2).sum())
    value, unit = area_value(pixels, spacing)
    return Measurement(feature_id, value, unit, 'ok' if pixels else 'not_observed')


def growth_rate(mask_before, mask_after, *, interval_years, spacing=None, sqrt=True,
                feature_id='ft_atrophy_growth_rate') -> Measurement:
    """Enlargement per year; square-root transformed by default (reduces dependence on baseline size)."""
    a0, a1 = area(mask_before, spacing=spacing), area(mask_after, spacing=spacing)
    if not interval_years:
        return not_evaluable(feature_id, 'rate', 'interval required')
    if a0.value is None or a1.value is None:
        return not_evaluable(feature_id, 'rate', 'area missing')
    if sqrt:
        unit = ('mm' if a0.unit == 'mm2' else 'px') + '/year'
        return Measurement(feature_id, (math.sqrt(a1.value) - math.sqrt(a0.value)) / interval_years, unit,
                           detail={'raw_rate': (a1.value - a0.value) / interval_years})
    return Measurement(feature_id, (a1.value - a0.value) / interval_years, f'{a0.unit}/year')


def focality(mask, *, min_area_px=1, feature_id='ft_atrophy_focality') -> Measurement:
    return lesions.focality(mask, min_area_px=min_area_px, feature_id=feature_id)


def foveal_involvement(mask, fovea, *, radius_px=0, feature_id='ft_atrophy_foveal_involvement') -> Measurement:
    return lesions.involves_point(mask, fovea, radius_px=radius_px, feature_id=feature_id)


def perimeter_area_ratio(mask, feature_id='ft_lesion_generic_shape') -> Measurement:
    """Lesion border length per unit area (circularity-type predictor of growth)."""
    from skimage import measure as skm
    m = as_mask(mask, ndim=2)
    if not m.any():
        return Measurement(feature_id, None, 'index', 'not_observed')
    return Measurement(feature_id, float(skm.perimeter(m) / m.sum()), 'index')
