"""retinal-measures: measurement functions for the retinal atlas feature list.

Every function takes segmentation outputs (masks, surfaces, landmarks) or raw images and returns
a :class:`Measurement` tagged with the atlas feature ID. Segmentation itself is out of scope.
"""
from ._common import Measurement, Spacing
from .registry import REGISTRY, Entry, get

__all__ = ['Measurement', 'Spacing', 'REGISTRY', 'Entry', 'get']
__version__ = '0.1.0'
