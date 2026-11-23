"""Self-contained deterministic implementation of the frozen E012 139-metric contract."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.stats import kurtosis, skew
from skimage.color import rgb2hsv
from skimage.feature import graycomatrix, graycoprops, local_binary_pattern
from skimage.measure import label, perimeter, regionprops
from skimage.morphology import binary_closing, binary_erosion, disk, remove_small_holes, remove_small_objects, skeletonize


ALGORITHM_VERSION = "ophthalmic_quantification.fundus.v0.1.0"
REQUIRED_UPSTREAM_VALUES = (
    "ensemble_uncertainty_mean",
    "mask_failure",
    "retfound_score",
    "dr_expected_grade",
    "referable_probability",
    "he_probability_burden",
    "he_threshold_burden",
    "ex_probability_burden",
    "ex_threshold_burden",
)
_OLD_VESSEL_IDS = (
    "vessel_area_fraction", "skeleton_length_fraction", "fractal_dimension", "width_index",
    "tortuosity_index", "inner_vessel_area_fraction", "outer_vessel_area_fraction",
    "outer_inner_vessel_area_fraction_ratio", "inner_skeleton_length_fraction",
    "outer_skeleton_length_fraction", "outer_inner_skeleton_length_fraction_ratio",
    "vessel_pixel_count", "skeleton_pixel_count",
)
_OLD_QUALITY_IDS = (
    "fov_fraction", "green_mean", "green_robust_contrast", "green_entropy",
    "laplacian_variance", "dark_fraction", "bright_fraction", "center_outer_green_difference",
)
_MODEL_IDS = REQUIRED_UPSTREAM_VALUES[2:]
_GEOMETRY_SUFFIXES = (
    "fov_fraction", "fov_centroid_x", "fov_centroid_y", "fov_equivalent_diameter_fraction",
    "fov_circularity", "fov_eccentricity", "fov_bbox_width_fraction",
    "fov_bbox_height_fraction", "fov_border_touch_fraction",
)
_COLOR_SUFFIXES = tuple(
    f"{channel}_{stat}"
    for channel in ("red", "green", "blue")
    for stat in ("mean", "std", "p05", "median", "p95", "robust_contrast", "entropy", "dark_fraction", "bright_fraction")
) + (
    "red_green_mean_ratio", "blue_green_mean_ratio", "red_minus_green_mean",
    "green_minus_blue_mean", "saturation_mean", "saturation_std", "value_mean", "value_std",
    "green_skewness", "green_excess_kurtosis", "laplacian_variance", "tenengrad_mean",
    "gradient_mean", "gradient_p95", "edge_fraction_gradient_gt20", "local_contrast_mean",
    "local_contrast_p90", "center_outer_green_difference", "center_outer_green_ratio",
    "upper_lower_green_difference", "left_right_green_difference", "quadrant_green_range",
    "quadrant_green_cv", "radial_green_correlation", "radial_green_slope",
    "illumination_block_cv", "illumination_block_range", "fft_high_frequency_energy_ratio",
)
_TEXTURE_SUFFIXES = (
    "glcm_contrast", "glcm_dissimilarity", "glcm_homogeneity", "glcm_ASM", "glcm_energy",
    "glcm_correlation", "lbp_entropy", "lbp_uniform_fraction", "haar_horizontal_energy_ratio",
    "haar_vertical_energy_ratio", "haar_diagonal_energy_ratio", "haar_high_frequency_energy_ratio",
)
_VESSEL_SUFFIXES = (
    "area_fraction", "skeleton_length_fraction", "fractal_dimension",
    "area_to_skeleton_width_index", "branch_tortuosity", "endpoint_density_per_10k_fov",
    "branchpoint_density_per_10k_fov", "branchpoint_endpoint_ratio",
    "component_count_per_10k_fov", "largest_component_area_fraction", "width_mean_px",
    "width_median_px", "width_std_px", "width_p90_px", "width_cv",
    "radial_inner_area_fraction", "middle_area_fraction", "radial_outer_area_fraction",
    "upper_area_fraction", "lower_area_fraction", "left_area_fraction", "right_area_fraction",
    "q1_area_fraction", "q2_area_fraction", "q3_area_fraction", "q4_area_fraction",
    "outer_inner_area_ratio", "upper_lower_area_difference", "left_right_area_difference",
    "quadrant_area_range", "quadrant_area_cv", "orientation_entropy_normalized",
    "orientation_dominance",
)
FUNDUS_METRIC_IDS = (
    REQUIRED_UPSTREAM_VALUES[:2]
    + _OLD_VESSEL_IDS
    + _OLD_QUALITY_IDS
    + _MODEL_IDS
    + tuple(f"std512_geometry_{name}" for name in _GEOMETRY_SUFFIXES)
    + tuple(f"std512_color_quality_{name}" for name in _COLOR_SUFFIXES)
    + tuple(f"std512_texture_{name}" for name in _TEXTURE_SUFFIXES)
    + tuple(f"std512_vessel_{name}" for name in _VESSEL_SUFFIXES)
)


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if np.isfinite(denominator) and denominator != 0 else float("nan")


def _entropy(values: np.ndarray) -> float:
    if values.size == 0:
        return float("nan")
    histogram = np.bincount(np.asarray(values, dtype=np.uint8), minlength=256).astype(float)
    probability = histogram[histogram > 0] / histogram.sum()
    return float(-(probability * np.log2(probability)).sum())


def _largest_component(mask: np.ndarray) -> np.ndarray:
    components = label(np.asarray(mask, bool), connectivity=2)
    if components.max() == 0:
        return np.zeros_like(mask, dtype=bool)
    counts = np.bincount(components.ravel())
    counts[0] = 0
    return components == int(counts.argmax())


def fundus_fov(rgb: np.ndarray) -> np.ndarray:
    image = np.asarray(rgb)
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("rgb must have shape HxWx3")
    raw = image.astype(np.uint8).max(axis=2) > 10
    raw = binary_closing(raw, disk(max(2, round(min(raw.shape) / 300))))
    raw = _largest_component(raw)
    return np.asarray(remove_small_holes(raw, area_threshold=max(64, raw.size // 100)), dtype=bool)


def _clean_vessel(vessel: np.ndarray, fov: np.ndarray) -> np.ndarray:
    if vessel.shape != fov.shape:
        raise ValueError("vessel mask and rgb spatial shape differ")
    min_size = max(1, int(round(30 * vessel.size / float(912 * 912))))
    return np.asarray(remove_small_objects(np.asarray(vessel, bool) & fov, min_size), dtype=bool)


def _fractal_dimension(mask: np.ndarray) -> float:
    binary = np.asarray(mask, bool)
    side = min(binary.shape)
    if binary.sum() in {0, binary.size} or side < 8:
        return float("nan")
    sizes = 2 ** np.arange(int(np.floor(np.log2(side))), 1, -1)
    valid: list[float] = []
    counts: list[float] = []
    for size in sizes:
        reduced = np.add.reduceat(
            np.add.reduceat(binary, np.arange(0, binary.shape[0], size), axis=0),
            np.arange(0, binary.shape[1], size), axis=1,
        )
        count = int(np.count_nonzero((reduced > 0) & (reduced < size * size)))
        if count:
            valid.append(float(size))
            counts.append(float(count))
    return float(-np.polyfit(np.log(valid), np.log(counts), 1)[0]) if len(counts) >= 2 else float("nan")


def _branch_tortuosity(skeleton: np.ndarray) -> float:
    skel = np.asarray(skeleton, bool)
    if skel.sum() < 2:
        return float("nan")
    kernel = np.ones((3, 3), dtype=np.uint8)
    degree = ndimage.convolve(skel.astype(np.uint8), kernel, mode="constant") - skel
    components, _ = ndimage.label(skel & (degree <= 2), structure=kernel)
    weighted_sum = 0.0
    total_weight = 0.0
    for component_id, region in enumerate(ndimage.find_objects(components), start=1):
        if region is None:
            continue
        component = components[region] == component_id
        if component.sum() < 7:
            continue
        horizontal = int((component[:, 1:] & component[:, :-1]).sum())
        vertical = int((component[1:, :] & component[:-1, :]).sum())
        diagonal = int((component[1:, 1:] & component[:-1, :-1]).sum())
        diagonal += int((component[1:, :-1] & component[:-1, 1:]).sum())
        path_length = horizontal + vertical + np.sqrt(2.0) * diagonal
        if path_length < 10:
            continue
        local_degree = ndimage.convolve(component.astype(np.uint8), kernel, mode="constant") - component
        endpoints = np.argwhere(component & (local_degree == 1))
        if len(endpoints) < 2:
            continue
        differences = endpoints[:, None, :] - endpoints[None, :, :]
        chord = float(np.sqrt(np.square(differences).sum(axis=2)).max())
        if chord > 0:
            weighted_sum += (path_length / chord) * path_length
            total_weight += path_length
    return float(weighted_sum / total_weight) if total_weight else float("nan")


def _spatial_maps(fov: np.ndarray) -> dict[str, np.ndarray | float]:
    yy, xx = np.indices(fov.shape)
    points = np.argwhere(fov)
    if len(points):
        center_y, center_x = points.mean(axis=0)
        radius = np.sqrt((yy - center_y) ** 2 + (xx - center_x) ** 2)
        maximum = max(float(radius[fov].max()), 1.0)
    else:
        center_y, center_x = (np.asarray(fov.shape) - 1) / 2
        radius = np.zeros_like(fov, dtype=float)
        maximum = 1.0
    radial = radius / maximum
    return {
        "center_y": float(center_y), "center_x": float(center_x), "radius": radial,
        "inner": fov & (radial <= 0.5), "outer": fov & (radial > 0.5),
        "radial_inner": fov & (radial <= 1 / 3), "middle": fov & (radial > 1 / 3) & (radial <= 2 / 3),
        "radial_outer": fov & (radial > 2 / 3), "upper": fov & (yy < center_y),
        "lower": fov & (yy >= center_y), "left": fov & (xx < center_x), "right": fov & (xx >= center_x),
        "q1": fov & (yy < center_y) & (xx < center_x), "q2": fov & (yy < center_y) & (xx >= center_x),
        "q3": fov & (yy >= center_y) & (xx < center_x), "q4": fov & (yy >= center_y) & (xx >= center_x),
    }


def _old_vessel_metrics(vessel: np.ndarray, fov: np.ndarray) -> dict[str, float]:
    cleaned = _clean_vessel(vessel, fov)
    skeleton = skeletonize(cleaned)
    denominator = float(fov.sum())
    maps = _spatial_maps(fov)
    output = {
        "vessel_area_fraction": _safe_divide(float(cleaned.sum()), denominator),
        "skeleton_length_fraction": _safe_divide(float(skeleton.sum()), denominator),
        "fractal_dimension": _fractal_dimension(cleaned),
        "width_index": _safe_divide(float(cleaned.sum()), float(skeleton.sum())),
        "tortuosity_index": _branch_tortuosity(skeleton),
        "vessel_pixel_count": float(cleaned.sum()),
        "skeleton_pixel_count": float(skeleton.sum()),
    }
    for region_name in ("inner", "outer"):
        region = np.asarray(maps[region_name], bool)
        output[f"{region_name}_vessel_area_fraction"] = _safe_divide(float((cleaned & region).sum()), float(region.sum()))
        output[f"{region_name}_skeleton_length_fraction"] = _safe_divide(float((skeleton & region).sum()), float(region.sum()))
    for base in ("vessel_area_fraction", "skeleton_length_fraction"):
        output[f"outer_inner_{base}_ratio"] = _safe_divide(output[f"outer_{base}"], output[f"inner_{base}"])
    return output


def _old_quality_metrics(rgb: np.ndarray, fov: np.ndarray) -> dict[str, float]:
    green = rgb[..., 1].astype(float)
    values = green[fov]
    if not values.size:
        return {name: float("nan") for name in _OLD_QUALITY_IDS}
    eroded = binary_erosion(fov, disk(max(2, round(min(fov.shape) / 180))))
    if eroded.sum() < 100:
        eroded = fov
    maps = _spatial_maps(fov)
    inner = np.asarray(maps["inner"], bool)
    outer = np.asarray(maps["outer"], bool)
    return {
        "fov_fraction": float(fov.mean()), "green_mean": float(values.mean()),
        "green_robust_contrast": float(np.percentile(values, 95) - np.percentile(values, 5)),
        "green_entropy": _entropy(values), "laplacian_variance": float(ndimage.laplace(green)[eroded].var()),
        "dark_fraction": float(np.mean(values <= 10)), "bright_fraction": float(np.mean(values >= 245)),
        "center_outer_green_difference": float(green[inner].mean() - green[outer].mean()),
    }


def _geometry_metrics(fov: np.ndarray) -> dict[str, float]:
    output = {name: float("nan") for name in _GEOMETRY_SUFFIXES}
    output["fov_fraction"] = float(fov.mean())
    regions = regionprops(label(fov, connectivity=2))
    if not regions:
        return output
    region = max(regions, key=lambda item: item.area)
    y0, x0, y1, x1 = region.bbox
    boundary = fov & ~ndimage.binary_erosion(fov)
    border = np.zeros_like(fov)
    border[[0, -1], :] = True
    border[:, [0, -1]] = True
    boundary_length = float(perimeter(fov, neighborhood=8))
    output.update({
        "fov_centroid_x": float(region.centroid[1] / max(1, fov.shape[1] - 1)),
        "fov_centroid_y": float(region.centroid[0] / max(1, fov.shape[0] - 1)),
        "fov_equivalent_diameter_fraction": float(region.equivalent_diameter_area / min(fov.shape)),
        "fov_circularity": _safe_divide(4 * np.pi * float(region.area), boundary_length**2),
        "fov_eccentricity": float(region.eccentricity),
        "fov_bbox_width_fraction": float((x1 - x0) / fov.shape[1]),
        "fov_bbox_height_fraction": float((y1 - y0) / fov.shape[0]),
        "fov_border_touch_fraction": _safe_divide(float((boundary & border).sum()), float(boundary.sum())),
    })
    return output


def _color_metrics(rgb: np.ndarray, fov: np.ndarray) -> dict[str, float]:
    if fov.sum() < 100:
        return {name: float("nan") for name in _COLOR_SUFFIXES}
    output: dict[str, float] = {}
    for index, name in enumerate(("red", "green", "blue")):
        values = rgb[..., index][fov].astype(float)
        output.update({
            f"{name}_mean": float(values.mean()), f"{name}_std": float(values.std()),
            f"{name}_p05": float(np.percentile(values, 5)), f"{name}_median": float(np.median(values)),
            f"{name}_p95": float(np.percentile(values, 95)),
            f"{name}_robust_contrast": float(np.percentile(values, 95) - np.percentile(values, 5)),
            f"{name}_entropy": _entropy(values), f"{name}_dark_fraction": float(np.mean(values <= 10)),
            f"{name}_bright_fraction": float(np.mean(values >= 245)),
        })
    epsilon = 1e-6
    output.update({
        "red_green_mean_ratio": float((output["red_mean"] + epsilon) / (output["green_mean"] + epsilon)),
        "blue_green_mean_ratio": float((output["blue_mean"] + epsilon) / (output["green_mean"] + epsilon)),
        "red_minus_green_mean": output["red_mean"] - output["green_mean"],
        "green_minus_blue_mean": output["green_mean"] - output["blue_mean"],
    })
    hsv = rgb2hsv(rgb)
    output.update({
        "saturation_mean": float(hsv[..., 1][fov].mean()), "saturation_std": float(hsv[..., 1][fov].std()),
        "value_mean": float(hsv[..., 2][fov].mean()), "value_std": float(hsv[..., 2][fov].std()),
    })
    green = rgb[..., 1].astype(float)
    values = green[fov]
    output["green_skewness"] = float(skew(values, bias=False))
    output["green_excess_kurtosis"] = float(kurtosis(values, fisher=True, bias=False))
    eroded = ndimage.distance_transform_edt(fov) >= max(5, round(min(fov.shape) / 32))
    if eroded.sum() < 100:
        eroded = fov
    laplacian = ndimage.laplace(green)
    gradient = np.hypot(ndimage.sobel(green, axis=1), ndimage.sobel(green, axis=0))
    local_mean = ndimage.uniform_filter(green, size=17)
    local_std = np.sqrt(np.maximum(ndimage.uniform_filter(green**2, size=17) - local_mean**2, 0))
    output.update({
        "laplacian_variance": float(laplacian[eroded].var()),
        "tenengrad_mean": float((gradient[eroded] ** 2).mean()), "gradient_mean": float(gradient[eroded].mean()),
        "gradient_p95": float(np.percentile(gradient[eroded], 95)),
        "edge_fraction_gradient_gt20": float(np.mean(gradient[eroded] > 20)),
        "local_contrast_mean": float(local_std[eroded].mean()),
        "local_contrast_p90": float(np.percentile(local_std[eroded], 90)),
    })
    maps = _spatial_maps(fov)
    means = {name: float(green[np.asarray(maps[name], bool)].mean()) for name in ("inner", "outer", "upper", "lower", "left", "right", "q1", "q2", "q3", "q4")}
    quadrants = [means[f"q{index}"] for index in range(1, 5)]
    output.update({
        "center_outer_green_difference": means["inner"] - means["outer"],
        "center_outer_green_ratio": _safe_divide(means["inner"], means["outer"]),
        "upper_lower_green_difference": means["upper"] - means["lower"],
        "left_right_green_difference": means["left"] - means["right"],
        "quadrant_green_range": float(max(quadrants) - min(quadrants)),
        "quadrant_green_cv": _safe_divide(float(np.std(quadrants)), float(np.mean(quadrants))),
    })
    radius = np.asarray(maps["radius"])[fov]
    output["radial_green_correlation"] = float(np.corrcoef(radius, values)[0, 1]) if np.std(radius) and np.std(values) else float("nan")
    output["radial_green_slope"] = float(np.polyfit(radius, values, 1)[0]) if np.std(radius) and np.std(values) else float("nan")
    block_means: list[float] = []
    block_size = rgb.shape[0] // 8
    for row in range(8):
        for column in range(8):
            region = np.zeros_like(fov)
            region[row * block_size:(row + 1) * block_size, column * block_size:(column + 1) * block_size] = True
            valid = region & fov
            if valid.sum() >= block_size * block_size * 0.25:
                block_means.append(float(green[valid].mean()))
    output["illumination_block_cv"] = _safe_divide(float(np.std(block_means)), float(np.mean(block_means)))
    output["illumination_block_range"] = float(max(block_means) - min(block_means))
    filled = green.copy()
    filled[~fov] = float(np.median(values))
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(filled - filled.mean()))) ** 2
    yy, xx = np.indices(spectrum.shape)
    frequency = np.sqrt((yy - spectrum.shape[0] / 2) ** 2 + (xx - spectrum.shape[1] / 2) ** 2)
    high = frequency >= 0.25 * frequency.max()
    output["fft_high_frequency_energy_ratio"] = _safe_divide(float(spectrum[high].sum()), float(spectrum.sum()))
    return output


def _texture_metrics(rgb: np.ndarray, fov: np.ndarray) -> dict[str, float]:
    green = rgb[..., 1]
    points = np.argwhere(fov)
    if len(points) < 100:
        return {name: float("nan") for name in _TEXTURE_SUFFIXES}
    y0, x0 = points.min(axis=0)
    y1, x1 = points.max(axis=0) + 1
    crop = green[y0:y1, x0:x1].copy()
    crop_fov = fov[y0:y1, x0:x1]
    crop[~crop_fov] = np.uint8(np.median(green[fov]))
    glcm = graycomatrix((crop // 16).astype(np.uint8), distances=[1, 2, 4], angles=[0, np.pi / 4, np.pi / 2, 3 * np.pi / 4], levels=16, symmetric=True, normed=True)
    output = {f"glcm_{name}": float(graycoprops(glcm, name).mean()) for name in ("contrast", "dissimilarity", "homogeneity", "ASM", "energy", "correlation")}
    lbp = local_binary_pattern(green, P=8, R=1, method="uniform")
    histogram = np.bincount(lbp[fov].astype(int), minlength=10).astype(float)
    histogram /= histogram.sum()
    nonzero = histogram[histogram > 0]
    output["lbp_entropy"] = float(-(nonzero * np.log2(nonzero)).sum())
    output["lbp_uniform_fraction"] = float(1 - histogram[-1])
    even = green[:green.shape[0] // 2 * 2, :green.shape[1] // 2 * 2].astype(float)
    a, b, c, d = even[0::2, 0::2], even[0::2, 1::2], even[1::2, 0::2], even[1::2, 1::2]
    bands = ((a + b + c + d) / 2, (a + b - c - d) / 2, (a - b + c - d) / 2, (a - b - c + d) / 2)
    energies = np.asarray([np.mean(band**2) for band in bands])
    total = float(energies.sum())
    output.update({
        "haar_horizontal_energy_ratio": _safe_divide(float(energies[1]), total),
        "haar_vertical_energy_ratio": _safe_divide(float(energies[2]), total),
        "haar_diagonal_energy_ratio": _safe_divide(float(energies[3]), total),
        "haar_high_frequency_energy_ratio": _safe_divide(float(energies[1:].sum()), total),
    })
    return output


def _extended_vessel_metrics(vessel: np.ndarray, fov: np.ndarray) -> dict[str, float]:
    cleaned = _clean_vessel(vessel, fov)
    denominator = float(fov.sum())
    skeleton = skeletonize(cleaned)
    skeleton_count = int(skeleton.sum())
    kernel = np.ones((3, 3), dtype=np.uint8)
    degree = ndimage.convolve(skeleton.astype(np.uint8), kernel, mode="constant") - skeleton
    endpoints = skeleton & (degree == 1)
    branchpoints = skeleton & (degree >= 3)
    components = label(cleaned, connectivity=2)
    counts = np.bincount(components.ravel())[1:]
    widths = 2 * ndimage.distance_transform_edt(cleaned)[skeleton]
    output = {
        "area_fraction": _safe_divide(float(cleaned.sum()), denominator),
        "skeleton_length_fraction": _safe_divide(float(skeleton_count), denominator),
        "fractal_dimension": _fractal_dimension(cleaned),
        "area_to_skeleton_width_index": _safe_divide(float(cleaned.sum()), float(skeleton_count)),
        "branch_tortuosity": _branch_tortuosity(skeleton),
        "endpoint_density_per_10k_fov": _safe_divide(float(endpoints.sum()) * 10_000, denominator),
        "branchpoint_density_per_10k_fov": _safe_divide(float(branchpoints.sum()) * 10_000, denominator),
        "branchpoint_endpoint_ratio": _safe_divide(float(branchpoints.sum()), float(endpoints.sum())),
        "component_count_per_10k_fov": _safe_divide(float(len(counts)) * 10_000, denominator),
        "largest_component_area_fraction": _safe_divide(float(counts.max() if len(counts) else 0), float(cleaned.sum())),
        "width_mean_px": float(np.mean(widths)) if widths.size else float("nan"),
        "width_median_px": float(np.median(widths)) if widths.size else float("nan"),
        "width_std_px": float(np.std(widths)) if widths.size else float("nan"),
        "width_p90_px": float(np.percentile(widths, 90)) if widths.size else float("nan"),
        "width_cv": _safe_divide(float(np.std(widths)), float(np.mean(widths))) if widths.size else float("nan"),
    }
    maps = _spatial_maps(fov)
    regions = ("radial_inner", "middle", "radial_outer", "upper", "lower", "left", "right", "q1", "q2", "q3", "q4")
    densities = {}
    for name in regions:
        region = np.asarray(maps[name], bool)
        densities[name] = _safe_divide(float((cleaned & region).sum()), float(region.sum()))
        output[f"{name}_area_fraction"] = densities[name]
    quadrants = [densities[f"q{index}"] for index in range(1, 5)]
    output.update({
        "outer_inner_area_ratio": _safe_divide(densities["radial_outer"], densities["radial_inner"]),
        "upper_lower_area_difference": densities["upper"] - densities["lower"],
        "left_right_area_difference": densities["left"] - densities["right"],
        "quadrant_area_range": float(max(quadrants) - min(quadrants)),
        "quadrant_area_cv": _safe_divide(float(np.std(quadrants)), float(np.mean(quadrants))),
    })
    orientations = np.asarray([
        (skeleton[:, 1:] & skeleton[:, :-1]).sum(), (skeleton[1:, 1:] & skeleton[:-1, :-1]).sum(),
        (skeleton[1:, :] & skeleton[:-1, :]).sum(), (skeleton[1:, :-1] & skeleton[:-1, 1:]).sum(),
    ], dtype=float)
    if orientations.sum():
        probability = orientations[orientations > 0] / orientations.sum()
        output["orientation_entropy_normalized"] = float(-(probability * np.log2(probability)).sum() / 2)
        output["orientation_dominance"] = float(orientations.max() / orientations.sum())
    else:
        output["orientation_entropy_normalized"] = output["orientation_dominance"] = float("nan")
    return output


def extract_fundus_metrics(
    rgb: np.ndarray,
    vessel_mask: np.ndarray,
    *,
    upstream_values: Mapping[str, object] | None = None,
    strict: bool = False,
) -> dict[str, float]:
    image = np.asarray(rgb)
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("rgb must have shape HxWx3")
    image = image.astype(np.uint8, copy=False)
    vessel = np.asarray(vessel_mask, bool)
    if vessel.shape != image.shape[:2]:
        raise ValueError("vessel mask and rgb spatial shape differ")
    supplied = dict(upstream_values or {})
    missing = [name for name in REQUIRED_UPSTREAM_VALUES if name not in supplied]
    if strict and missing:
        raise ValueError(f"missing required upstream values: {', '.join(missing)}")
    fov = fundus_fov(image)
    values: dict[str, float] = {name: float(supplied.get(name, float("nan"))) for name in REQUIRED_UPSTREAM_VALUES}
    values.update(_old_vessel_metrics(vessel, fov))
    values.update(_old_quality_metrics(image, fov))
    resized_rgb = np.asarray(Image.fromarray(image, mode="RGB").resize((512, 512), Image.Resampling.BILINEAR))
    resized_vessel = np.asarray(Image.fromarray((vessel * 255).astype(np.uint8)).resize((512, 512), Image.Resampling.NEAREST)) > 0
    resized_fov = fundus_fov(resized_rgb)
    values.update({f"std512_geometry_{name}": value for name, value in _geometry_metrics(resized_fov).items()})
    values.update({f"std512_color_quality_{name}": value for name, value in _color_metrics(resized_rgb, resized_fov).items()})
    values.update({f"std512_texture_{name}": value for name, value in _texture_metrics(resized_rgb, resized_fov).items()})
    values.update({f"std512_vessel_{name}": value for name, value in _extended_vessel_metrics(resized_vessel, resized_fov).items()})
    return {metric_id: float(values.get(metric_id, float("nan"))) for metric_id in FUNDUS_METRIC_IDS}


def fundus_metric_catalog() -> tuple[dict[str, str], ...]:
    rows = []
    for metric_id in FUNDUS_METRIC_IDS:
        if metric_id in REQUIRED_UPSTREAM_VALUES:
            domain = "reliability" if metric_id in REQUIRED_UPSTREAM_VALUES[:2] else "model_derived"
            source = "upstream_model_output"
        elif metric_id.startswith("std512_geometry_") or metric_id in {"fov_fraction"}:
            domain, source = "fov_geometry", "fundus_rgb"
        elif metric_id.startswith("std512_color_quality_") or metric_id in _OLD_QUALITY_IDS:
            domain, source = "color_quality", "fundus_rgb"
        elif metric_id.startswith("std512_texture_"):
            domain, source = "texture", "fundus_rgb"
        else:
            domain, source = "vessel", "vessel_mask"
        unit = "mixed_defined_scale"
        if metric_id.endswith("_fraction") or "ratio" in metric_id:
            unit = "fraction_or_ratio"
        elif metric_id.endswith("_count") or "pixel_count" in metric_id:
            unit = "count"
        elif "mean" in metric_id or "median" in metric_id or "p05" in metric_id or "p95" in metric_id:
            unit = "intensity_or_source_scale"
        rows.append({"metric_id": metric_id, "domain": domain, "input_source": source, "unit": unit, "algorithm_version": ALGORITHM_VERSION})
    return tuple(rows)
