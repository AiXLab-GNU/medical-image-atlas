"""Reference implementations of H&E histology measurements mapped to the pathology atlas (prostate first).

Every function returns a :class:`Measurement` whose ``feature_id`` is the atlas feature it computes. Pass the
image's microns per pixel (``mpp``) to get µm²/mm²/mm; without it values stay in pixels. Transparent reference
implementations for display and teaching, not validated diagnostic tools.
"""
from . import glands, grading, ihc, nuclei, texture, tissue
from ._common import Measurement
from .registry import INPUT_LABELS, REGISTRY

__all__ = ['Measurement', 'REGISTRY', 'INPUT_LABELS', 'glands', 'grading', 'ihc', 'nuclei', 'texture', 'tissue']
__version__ = '0.1.0'
