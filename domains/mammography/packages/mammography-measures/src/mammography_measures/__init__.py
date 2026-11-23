"""Reference implementations of 2D mammography measurements mapped to the mammography atlas.

Every function returns a :class:`Measurement` whose ``feature_id`` is the atlas feature it computes.
Values are in pixels unless a pixel size in millimetres is given. These are transparent reference
implementations for display and teaching, not validated clinical tools.
"""
from . import breast, calcification, distortion, enhancement, location, mass
from ._common import Measurement
from .registry import INPUT_LABELS, REGISTRY

__all__ = ['Measurement', 'REGISTRY', 'INPUT_LABELS', 'breast', 'calcification', 'distortion', 'enhancement', 'location', 'mass']
__version__ = '0.1.0'
