"""Deterministic AMD-SD combined-image splitting and palette decoding."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

import numpy as np
from PIL import Image


CLASS_ID_TO_NAME: Mapping[int, str] = {
    0: "background",
    1: "IRF",
    2: "SRF",
    3: "PED",
    4: "SHRM",
    5: "IS_OS",
}
CLASS_NAME_TO_ID = {name: class_id for class_id, name in CLASS_ID_TO_NAME.items()}
DEFAULT_PALETTE_RGB = np.array(
    [
        [0, 0, 0],
        [0, 255, 0],
        [255, 0, 0],
        [0, 0, 255],
        [255, 255, 0],
        [255, 0, 255],
    ],
    dtype=np.uint8,
)


@dataclass(frozen=True)
class DecodeInfo:
    rule: str
    distance: str
    tie_break: str
    total_pixels: int
    tie_pixels: int
    maximum_distance: float
    exact_fraction: float
    within_5_fraction: float
    within_10_fraction: float
    within_32_fraction: float
    within_64_fraction: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def split_combined_image(
    image: np.ndarray,
    *,
    expected_half_width: int | None = 570,
    expected_height: int | None = 380,
) -> tuple[np.ndarray, np.ndarray]:
    """Split a horizontal OCT/mask pair without modifying either half."""

    array = np.asarray(image)
    if array.ndim not in (2, 3):
        raise ValueError(f"Expected a 2D or 3D image array, got shape {array.shape}")
    height, width = array.shape[:2]
    if width % 2:
        raise ValueError(f"Combined image width must be even, got {width}")
    half_width = width // 2
    if expected_half_width is not None and half_width != expected_half_width:
        raise ValueError(f"Expected half width {expected_half_width}, got {half_width}")
    if expected_height is not None and height != expected_height:
        raise ValueError(f"Expected height {expected_height}, got {height}")
    return array[:, :half_width].copy(), array[:, half_width:].copy()


def decode_rgb_mask(
    mask_rgb: np.ndarray,
    *,
    palette_rgb: np.ndarray = DEFAULT_PALETTE_RGB,
) -> tuple[np.ndarray, DecodeInfo]:
    """Assign every RGB pixel to its nearest canonical color.

    Euclidean RGB distance and palette order make ties deterministic. The default palette
    order is identical to the integer class IDs, so ``argmin`` implements the locked
    lowest-class-ID tie break.
    """

    rgb = np.asarray(mask_rgb)
    if rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError(f"Expected HxWx3 RGB mask, got shape {rgb.shape}")
    if not np.issubdtype(rgb.dtype, np.integer):
        raise TypeError(f"RGB mask must have integer dtype, got {rgb.dtype}")
    palette = np.asarray(palette_rgb)
    if palette.ndim != 2 or palette.shape[1] != 3:
        raise ValueError(f"Palette must have shape Kx3, got {palette.shape}")
    flat = rgb.reshape(-1, 3).astype(np.int32, copy=False)
    delta = flat[:, None, :] - palette[None, :, :].astype(np.int32, copy=False)
    squared_distances = (delta * delta).sum(axis=2)
    labels = np.argmin(squared_distances, axis=1).astype(np.uint8)
    minimum = squared_distances[np.arange(len(flat)), labels]
    distances = np.sqrt(minimum.astype(np.float64))
    ties = (squared_distances == minimum[:, None]).sum(axis=1) > 1
    total = max(len(flat), 1)
    info = DecodeInfo(
        rule="nearest_palette_all_pixels",
        distance="euclidean_rgb",
        tie_break="lowest_class_id",
        total_pixels=len(flat),
        tie_pixels=int(ties.sum()),
        maximum_distance=float(distances.max(initial=0.0)),
        exact_fraction=float((distances == 0).sum() / total),
        within_5_fraction=float((distances <= 5).sum() / total),
        within_10_fraction=float((distances <= 10).sum() / total),
        within_32_fraction=float((distances <= 32).sum() / total),
        within_64_fraction=float((distances <= 64).sum() / total),
    )
    return labels.reshape(rgb.shape[:2]), info


def load_amd_sd_combined_png(
    path: str | Path,
    *,
    expected_half_width: int = 570,
    expected_height: int = 380,
) -> tuple[np.ndarray, np.ndarray, DecodeInfo]:
    """Load one AMD-SD PNG and return OCT RGB, integer label mask, and decoder QC."""

    source = Path(path)
    with Image.open(source) as image:
        image.load()
        rgb = np.asarray(image.convert("RGB"))
    oct_rgb, mask_rgb = split_combined_image(
        rgb, expected_half_width=expected_half_width, expected_height=expected_height
    )
    labels, info = decode_rgb_mask(mask_rgb)
    return oct_rgb, labels, info
