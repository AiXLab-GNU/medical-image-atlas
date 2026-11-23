"""Label-blind extended fundus metrics promoted from P003 E027."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import ndimage
from skimage import measure, morphology
from sklearn.cluster import KMeans


ALGORITHM_VERSION = "ophthalmic_quantification.extended_fundus.v0.1.0"
SEED = 20260817
FAMILIES = (
    "artery_vein_proxy",
    "vascular_topology",
    "vascular_arcade",
    "disc_fovea_geometry",
    "optic_disc_shape",
    "peripapillary_appearance",
    "macular_structure",
    "pigmentation_choroidal_appearance",
)
METRIC_FAMILIES = {
    "artery_vein_proxy": (
        "av_color_cluster_separation", "av_cluster_area_ratio", "av_cluster_width_ratio",
    ),
    "vascular_topology": (
        "vessel_area_fraction", "skeleton_length_fraction", "fractal_dimension", "width_index",
        "tortuosity_index", "branchpoint_density", "endpoint_density", "mean_branch_angle_deg",
    ),
    "vascular_arcade": (
        "temporal_vessel_fraction", "superior_inferior_density_ratio", "arcade_vertical_extent",
        "arcade_orientation_coherence", "arcade_axis_angle_abs_deg",
    ),
    "disc_fovea_geometry": (
        "disc_fovea_dx_abs", "disc_fovea_dy", "disc_fovea_distance", "disc_fovea_angle_abs_deg",
        "disc_center_eccentricity", "fovea_center_eccentricity",
    ),
    "optic_disc_shape": (
        "disc_proxy_area_fraction", "disc_proxy_eccentricity", "disc_proxy_axis_ratio",
        "disc_proxy_orientation_abs_deg", "disc_proxy_circularity",
    ),
    "peripapillary_appearance": (
        "peripapillary_luminance_contrast", "peripapillary_red_green_ratio",
        "peripapillary_texture_energy", "peripapillary_bright_desaturated_fraction",
        "peripapillary_temporal_nasal_contrast",
    ),
    "macular_structure": (
        "macular_luminance_contrast", "macular_red_green_ratio", "macular_texture_energy",
        "macular_dark_fraction", "macular_radial_asymmetry",
    ),
    "pigmentation_choroidal_appearance": (
        "background_red_green_ratio", "background_saturation_mean", "background_luminance_cv",
        "background_entropy", "tessellation_texture_proxy", "background_horizontal_color_gradient",
    ),
}
METRICS = tuple(metric for family in FAMILIES for metric in METRIC_FAMILIES[family])


def extended_fundus_metric_catalog() -> tuple[dict[str, str], ...]:
    """Return metadata for the 43 label-blind E027 fundus metrics."""
    return tuple(
        {
            "metric_id": metric_id,
            "domain": family,
            "input_source": "rgb_vessel_mask_and_label_blind_landmarks",
            "unit": "defined_by_metric",
            "algorithm_version": ALGORITHM_VERSION,
        }
        for family in FAMILIES
        for metric_id in METRIC_FAMILIES[family]
    )


def fundus_fov(rgb: np.ndarray) -> np.ndarray:
    """Return the frozen E027 field-of-view mask without project-local imports."""
    image = np.asarray(rgb, dtype=np.float32) / 255.0
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("rgb must have shape HxWx3")
    mask = image.max(axis=2) > 0.055
    mask = morphology.binary_closing(mask, morphology.disk(max(2, min(mask.shape) // 150)))
    return np.asarray(ndimage.binary_fill_holes(_largest_component(mask)), dtype=bool)


def fov_diameter(mask: np.ndarray) -> float:
    return float(2.0 * np.sqrt(max(1.0, float(np.asarray(mask, bool).sum())) / np.pi))


def _mean(values: np.ndarray, mask: np.ndarray) -> float:
    return float(np.mean(values[mask])) if np.any(mask) else 0.0


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator / max(1e-8, denominator))


def _largest_component(mask: np.ndarray) -> np.ndarray:
    labels = measure.label(mask)
    if labels.max() == 0:
        return np.zeros_like(mask, dtype=bool)
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    return labels == int(counts.argmax())


def optic_disc_proxy_mask(
    rgb: np.ndarray, disc_x: float | None = None, disc_y: float | None = None
) -> np.ndarray:
    """Bright connected optic-disc proxy; coordinates are normalized when supplied."""
    image = np.asarray(rgb, dtype=np.float32) / 255.0
    fov = fundus_fov(rgb)
    diameter = fov_diameter(fov)
    height, width = fov.shape
    score = ndimage.gaussian_filter(
        0.65 * image[..., 0] + 0.50 * image[..., 1] - 0.15 * image[..., 2],
        sigma=max(1.0, 0.012 * diameter),
    )
    if disc_x is None or disc_y is None:
        interior = morphology.binary_erosion(fov, morphology.disk(max(2, int(0.06 * diameter))))
        local = score.copy()
        local[~interior] = -np.inf
        cy, cx = np.unravel_index(np.argmax(local), local.shape)
    else:
        cx = float(disc_x) * (width - 1)
        cy = float(disc_y) * (height - 1)
    yy, xx = np.indices(fov.shape)
    roi = ((xx - cx) ** 2 + (yy - cy) ** 2 <= (0.095 * diameter) ** 2) & fov
    values = score[roi]
    if values.size == 0:
        return np.zeros_like(fov)
    threshold = float(np.quantile(values, 0.57))
    candidate = (score >= threshold) & roi
    candidate = morphology.binary_closing(candidate, morphology.disk(max(1, int(0.006 * diameter))))
    candidate = morphology.remove_small_objects(candidate, max(8, int(0.0004 * fov.sum())))
    labels = measure.label(candidate)
    if labels.max() == 0:
        return ((xx - cx) ** 2 + (yy - cy) ** 2 <= (0.045 * diameter) ** 2) & fov
    regions = measure.regionprops(labels)
    selected = min(regions, key=lambda region: (region.centroid[1] - cx) ** 2 + (region.centroid[0] - cy) ** 2)
    return ndimage.binary_fill_holes(labels == selected.label) & fov


def dice_score(prediction: np.ndarray, truth: np.ndarray) -> float:
    prediction = np.asarray(prediction, bool)
    truth = np.asarray(truth, bool)
    return float(2 * np.logical_and(prediction, truth).sum() / max(1, prediction.sum() + truth.sum()))


def _fractal_dimension(mask: np.ndarray) -> float:
    binary = np.asarray(mask, bool)
    sizes, counts = [], []
    maximum = int(2 ** np.floor(np.log2(max(2, min(binary.shape)))))
    size = maximum
    while size >= 4:
        reduced = np.add.reduceat(
            np.add.reduceat(binary.astype(np.uint8), np.arange(0, binary.shape[0], size), axis=0),
            np.arange(0, binary.shape[1], size), axis=1,
        )
        count = int(np.count_nonzero(reduced))
        if count:
            sizes.append(size)
            counts.append(count)
        size //= 2
    if len(sizes) < 2:
        return 0.0
    return float(np.polyfit(np.log(1 / np.asarray(sizes)), np.log(counts), 1)[0])


def _shape_metrics(mask: np.ndarray, fov: np.ndarray) -> dict[str, float]:
    clean = _largest_component(mask)
    regions = measure.regionprops(clean.astype(np.uint8))
    if not regions:
        return {
            "disc_proxy_area_fraction": 0.0, "disc_proxy_eccentricity": 0.0,
            "disc_proxy_axis_ratio": 0.0, "disc_proxy_orientation_abs_deg": 0.0,
            "disc_proxy_circularity": 0.0,
        }
    region = regions[0]
    perimeter = max(1.0, float(region.perimeter))
    return {
        "disc_proxy_area_fraction": _safe_ratio(float(clean.sum()), float(fov.sum())),
        "disc_proxy_eccentricity": float(region.eccentricity),
        "disc_proxy_axis_ratio": _safe_ratio(float(region.minor_axis_length), float(region.major_axis_length)),
        "disc_proxy_orientation_abs_deg": float(abs(np.degrees(region.orientation))),
        "disc_proxy_circularity": float(4 * np.pi * region.area / (perimeter * perimeter)),
    }


def _topology_metrics(vessel: np.ndarray, fov: np.ndarray) -> tuple[dict[str, float], np.ndarray, np.ndarray]:
    vessel = np.asarray(vessel, bool) & fov
    skeleton = morphology.skeletonize(vessel)
    neighbours = ndimage.convolve(skeleton.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant") - skeleton
    branchpoints = skeleton & (neighbours >= 3)
    endpoints = skeleton & (neighbours == 1)
    distance = ndimage.distance_transform_edt(vessel)
    skel_count = max(1, int(skeleton.sum()))
    angles: list[float] = []
    for y, x in np.argwhere(branchpoints)[:: max(1, int(branchpoints.sum() // 500) + 1)]:
        coordinates = np.argwhere(skeleton[max(0, y - 1):y + 2, max(0, x - 1):x + 2])
        origin = np.array([min(1, y), min(1, x)])
        vectors = coordinates - origin
        vectors = vectors[np.any(vectors != 0, axis=1)]
        if len(vectors) >= 2:
            pair_angles = []
            for first in range(len(vectors)):
                for second in range(first + 1, len(vectors)):
                    cosine = np.dot(vectors[first], vectors[second]) / (
                        np.linalg.norm(vectors[first]) * np.linalg.norm(vectors[second])
                    )
                    pair_angles.append(np.degrees(np.arccos(np.clip(cosine, -1, 1))))
            angles.append(float(max(pair_angles)))
    segment_labels = measure.label(skeleton & ~morphology.binary_dilation(branchpoints, morphology.disk(1)))
    tortuosities = []
    for region in measure.regionprops(segment_labels):
        if region.area < 5:
            continue
        points = region.coords
        chord = float(np.hypot(*(points.max(axis=0) - points.min(axis=0))))
        if chord > 0:
            tortuosities.append(float(region.area / chord))
    metrics = {
        "vessel_area_fraction": _safe_ratio(float(vessel.sum()), float(fov.sum())),
        "skeleton_length_fraction": _safe_ratio(float(skeleton.sum()), float(fov.sum())),
        "fractal_dimension": _fractal_dimension(skeleton),
        "width_index": float(2 * distance[skeleton].mean()) if skeleton.any() else 0.0,
        "tortuosity_index": float(np.median(tortuosities)) if tortuosities else 0.0,
        "branchpoint_density": float(branchpoints.sum() / skel_count),
        "endpoint_density": float(endpoints.sum() / skel_count),
        "mean_branch_angle_deg": float(np.mean(angles)) if angles else 0.0,
    }
    return metrics, branchpoints, skeleton


def _entropy(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    histogram, _ = np.histogram(values, bins=32, range=(0.0, 1.0))
    probabilities = histogram[histogram > 0] / max(1, histogram.sum())
    return float(-(probabilities * np.log2(probabilities)).sum())


def extract_extended_metrics(
    rgb: np.ndarray, top_masks: dict[str, np.ndarray], landmarks: dict[str, Any]
) -> tuple[dict[str, float], dict[str, np.ndarray], dict[str, float]]:
    """Return 43 metrics and 8 overlapping family regions without label/model input."""
    image = np.asarray(rgb, dtype=np.float32) / 255.0
    fov = fundus_fov(rgb)
    diameter = fov_diameter(fov)
    height, width = fov.shape
    yy, xx = np.indices(fov.shape)
    cx = float(landmarks["disc_x"]) * (width - 1)
    cy = float(landmarks["disc_y"]) * (height - 1)
    fx = float(landmarks["fovea_x"]) * (width - 1)
    fy = float(landmarks["fovea_y"]) * (height - 1)
    fov_cx = float(xx[fov].mean()) if fov.any() else (width - 1) / 2
    fov_cy = float(yy[fov].mean()) if fov.any() else (height - 1) / 2
    temporal_sign = 1.0 if fx >= cx else -1.0
    vessel = np.asarray(top_masks["vessel"], bool) & fov
    retinal = np.asarray(top_masks.get("retinal_residual", fov), bool) & fov
    disc = optic_disc_proxy_mask(rgb, float(landmarks["disc_x"]), float(landmarks["disc_y"]))
    disc_radius = np.sqrt(max(1.0, disc.sum()) / np.pi)
    peripapillary = (
        ((xx - cx) ** 2 + (yy - cy) ** 2 <= (2.2 * disc_radius) ** 2)
        & ((xx - cx) ** 2 + (yy - cy) ** 2 > (1.15 * disc_radius) ** 2) & fov
    )
    macula_core = ((xx - fx) ** 2 + (yy - fy) ** 2 <= (0.055 * diameter) ** 2) & fov
    macula_ring = (
        ((xx - fx) ** 2 + (yy - fy) ** 2 <= (0.115 * diameter) ** 2) & ~macula_core & fov
    )
    macula = macula_core | macula_ring
    dx_line, dy_line = fx - cx, fy - cy
    line_norm = max(1.0, np.hypot(dx_line, dy_line))
    projection = ((xx - cx) * dx_line + (yy - cy) * dy_line) / (line_norm * line_norm)
    perpendicular = np.abs((xx - cx) * dy_line - (yy - cy) * dx_line) / line_norm
    corridor = (projection >= -0.05) & (projection <= 1.05) & (perpendicular <= 0.045 * diameter) & fov
    temporal = ((xx - cx) * temporal_sign > 0) & fov
    arcade = vessel & temporal & (np.abs(yy - fy) <= 0.28 * diameter)

    red, green = image[..., 0], image[..., 1]
    luminance = 0.299 * red + 0.587 * green + 0.114 * image[..., 2]
    low = ndimage.gaussian_filter(luminance, sigma=max(1.0, 0.025 * diameter))
    texture = np.abs(luminance - low)
    maximum, minimum = image.max(axis=2), image.min(axis=2)
    saturation = (maximum - minimum) / np.maximum(maximum, 1e-6)

    metrics, branchpoints, skeleton = _topology_metrics(vessel, fov)
    distance = ndimage.distance_transform_edt(vessel)
    av_mask = np.zeros_like(fov)
    vessel_pixels = np.flatnonzero(vessel)
    if len(vessel_pixels) >= 20:
        features = np.column_stack([
            (red - green).ravel()[vessel_pixels],
            green.ravel()[vessel_pixels],
            distance.ravel()[vessel_pixels] / max(1.0, diameter),
        ])
        scale = features.std(axis=0)
        scale[scale < 1e-6] = 1.0
        normalized = (features - features.mean(axis=0)) / scale
        fit_values = normalized
        if len(fit_values) > 5000:
            sample_rng = np.random.default_rng(SEED)
            fit_values = fit_values[sample_rng.choice(len(fit_values), 5000, replace=False)]
        estimator = KMeans(n_clusters=2, random_state=SEED, n_init=10).fit(fit_values)
        labels = estimator.predict(normalized)
        centers = estimator.cluster_centers_
        bright_cluster = int(np.argmax(centers[:, 1]))
        av_mask.flat[vessel_pixels[labels == bright_cluster]] = True
        counts = np.bincount(labels, minlength=2).astype(float)
        widths = [float(distance.ravel()[vessel_pixels[labels == index]].mean()) for index in range(2)]
        metrics.update({
            "av_color_cluster_separation": float(np.linalg.norm(centers[0] - centers[1])),
            "av_cluster_area_ratio": _safe_ratio(min(counts), max(counts)),
            "av_cluster_width_ratio": _safe_ratio(min(widths), max(widths)),
        })
    else:
        metrics.update({key: 0.0 for key in METRIC_FAMILIES["artery_vein_proxy"]})

    vessel_angles = np.arctan2(yy[arcade] - fy, (xx[arcade] - fx) * temporal_sign) if arcade.any() else np.array([])
    centered_y = np.abs(yy[arcade] - fy) / max(1.0, diameter) if arcade.any() else np.array([])
    upper = vessel & temporal & (yy < fy)
    lower = vessel & temporal & (yy >= fy)
    metrics.update({
        "temporal_vessel_fraction": _safe_ratio(float((vessel & temporal).sum()), float(vessel.sum())),
        "superior_inferior_density_ratio": _safe_ratio(float(upper.sum()), float(lower.sum())),
        "arcade_vertical_extent": float(np.quantile(centered_y, 0.95)) if centered_y.size else 0.0,
        "arcade_orientation_coherence": float(np.hypot(np.mean(np.cos(2 * vessel_angles)), np.mean(np.sin(2 * vessel_angles)))) if vessel_angles.size else 0.0,
        "arcade_axis_angle_abs_deg": float(abs(np.degrees(0.5 * np.arctan2(np.mean(np.sin(2 * vessel_angles)), np.mean(np.cos(2 * vessel_angles)))))) if vessel_angles.size else 0.0,
        "disc_fovea_dx_abs": float(abs(fx - cx) / diameter),
        "disc_fovea_dy": float((fy - cy) / diameter),
        "disc_fovea_distance": float(np.hypot(fx - cx, fy - cy) / diameter),
        "disc_fovea_angle_abs_deg": float(abs(np.degrees(np.arctan2(fy - cy, fx - cx)))),
        "disc_center_eccentricity": float(np.hypot(cx - fov_cx, cy - fov_cy) / diameter),
        "fovea_center_eccentricity": float(np.hypot(fx - fov_cx, fy - fov_cy) / diameter),
    })
    metrics.update(_shape_metrics(disc, fov))

    background = retinal & ~peripapillary & ~macula & ~morphology.binary_dilation(vessel, morphology.disk(2))
    pp_temporal = peripapillary & ((xx - cx) * temporal_sign > 0)
    pp_nasal = peripapillary & ~pp_temporal
    radial = np.hypot(xx - fx, yy - fy)
    mac_inner = macula & (radial <= 0.075 * diameter)
    mac_outer = macula & ~mac_inner
    dark_threshold = float(np.quantile(luminance[macula], 0.25)) if macula.any() else 0.0
    bright_threshold = float(np.quantile(luminance[fov], 0.80)) if fov.any() else 1.0
    texture_threshold = float(np.quantile(texture[background], 0.75)) if background.any() else 1.0
    high_texture = background & (texture >= texture_threshold)
    x_normalized = (xx - fov_cx) / max(1.0, diameter)
    if background.sum() >= 3:
        design = np.column_stack([np.ones(background.sum()), x_normalized[background]])
        horizontal_gradient = float(abs(np.linalg.lstsq(design, red[background] - green[background], rcond=None)[0][1]))
    else:
        horizontal_gradient = 0.0
    metrics.update({
        "peripapillary_luminance_contrast": abs(_mean(luminance, peripapillary) - _mean(luminance, background)),
        "peripapillary_red_green_ratio": _safe_ratio(_mean(red, peripapillary), _mean(green, peripapillary)),
        "peripapillary_texture_energy": _mean(texture, peripapillary),
        "peripapillary_bright_desaturated_fraction": _mean(((luminance >= bright_threshold) & (saturation <= 0.35)).astype(float), peripapillary),
        "peripapillary_temporal_nasal_contrast": abs(_mean(luminance, pp_temporal) - _mean(luminance, pp_nasal)),
        "macular_luminance_contrast": abs(_mean(luminance, macula_core) - _mean(luminance, macula_ring)),
        "macular_red_green_ratio": _safe_ratio(_mean(red, macula), _mean(green, macula)),
        "macular_texture_energy": _mean(texture, macula),
        "macular_dark_fraction": _mean((luminance <= dark_threshold).astype(float), macula),
        "macular_radial_asymmetry": abs(_mean(luminance, mac_inner) - _mean(luminance, mac_outer)),
        "background_red_green_ratio": _safe_ratio(_mean(red, background), _mean(green, background)),
        "background_saturation_mean": _mean(saturation, background),
        "background_luminance_cv": _safe_ratio(float(luminance[background].std()) if background.any() else 0.0, _mean(luminance, background)),
        "background_entropy": _entropy(luminance[background]),
        "tessellation_texture_proxy": _mean(texture, background),
        "background_horizontal_color_gradient": horizontal_gradient,
    })
    family_masks = {
        "artery_vein_proxy": av_mask,
        "vascular_topology": morphology.binary_dilation(branchpoints, morphology.disk(max(1, int(0.012 * diameter)))) & fov,
        "vascular_arcade": arcade,
        "disc_fovea_geometry": corridor,
        "optic_disc_shape": disc,
        "peripapillary_appearance": peripapillary,
        "macular_structure": macula,
        "pigmentation_choroidal_appearance": high_texture,
    }
    missing = set(METRICS) - set(metrics)
    extra = set(metrics) - set(METRICS)
    if missing or extra:
        raise RuntimeError(f"Metric contract mismatch missing={missing} extra={extra}")
    qc = {
        "fov_fraction": float(fov.mean()),
        "disc_proxy_fraction": _safe_ratio(float(disc.sum()), float(fov.sum())),
        "background_fraction": _safe_ratio(float(background.sum()), float(fov.sum())),
        "metric_finite_fraction": float(np.mean(np.isfinite(list(metrics.values())))),
        "family_nonempty_fraction": float(np.mean([mask.any() for mask in family_masks.values()])),
    }
    return metrics, family_masks, qc


def radial_matched_mask(
    target: np.ndarray, eligible: np.ndarray, fov: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """Sample the same pixel count in eight radial bins, excluding the target where possible."""
    target, eligible, fov = map(lambda value: np.asarray(value, bool), (target, eligible, fov))
    yy, xx = np.indices(fov.shape)
    center_x = float(xx[fov].mean()) if fov.any() else (fov.shape[1] - 1) / 2
    center_y = float(yy[fov].mean()) if fov.any() else (fov.shape[0] - 1) / 2
    radius = np.hypot(xx - center_x, yy - center_y)
    maximum = max(1.0, float(radius[fov].max()) if fov.any() else float(radius.max()))
    bins = np.minimum(7, np.floor(radius / maximum * 8).astype(int))
    matched = np.zeros_like(fov)
    for bin_id in range(8):
        need = int((target & (bins == bin_id)).sum())
        if need == 0:
            continue
        candidates = np.flatnonzero(eligible & (bins == bin_id) & ~target)
        if len(candidates) < need:
            candidates = np.flatnonzero(fov & (bins == bin_id) & ~target)
        take = min(need, len(candidates))
        if take:
            matched.flat[rng.choice(candidates, take, replace=False)] = True
    deficit = int(target.sum() - matched.sum())
    if deficit:
        candidates = np.flatnonzero(fov & ~target & ~matched)
        if len(candidates) < deficit:
            raise RuntimeError("Insufficient non-target pixels for exact matched control")
        matched.flat[rng.choice(candidates, deficit, replace=False)] = True
    return matched


def make_perturbation_images(
    rgb: np.ndarray, family_masks: dict[str, np.ndarray], matched_masks: dict[str, np.ndarray]
) -> np.ndarray:
    """Return full, eight targeted removals, and eight matched removals."""
    image = np.asarray(rgb, dtype=np.float32) / 255.0
    fov = fundus_fov(rgb)
    fill = image[fov].mean(axis=0) if fov.any() else image.reshape(-1, 3).mean(axis=0)
    outputs = [image.transpose(2, 0, 1)]
    for masks in (family_masks, matched_masks):
        for family in FAMILIES:
            output = image.copy()
            output[np.asarray(masks[family], bool)] = fill
            outputs.append(output.transpose(2, 0, 1))
    return np.stack(outputs).astype(np.float32)
