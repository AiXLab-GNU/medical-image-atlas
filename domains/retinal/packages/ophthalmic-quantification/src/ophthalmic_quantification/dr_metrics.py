"""Deterministic diabetic-retinopathy lesion and clinical-combination metrics."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from scipy import ndimage
from skimage.measure import label, regionprops

from .fundus_metrics import fundus_fov


ALGORITHM_VERSION = "ophthalmic_quantification.dr.v0.1.0"
DR_LESIONS = ("hemorrhage", "microaneurysm", "hard_exudate", "cotton_wool_spot")
DR_LEGACY_LESIONS = ("hemorrhage", "hard_exudate", "microaneurysm", "cotton_wool_spot")
DR_NEGATIVE_MASKS = ("drusen", "red_uncertain", "bright_uncertain")
DR_REQUIRED_MASKS = (
    *DR_LESIONS,
    "neovascularization",
    *DR_NEGATIVE_MASKS,
    "optic_disc",
    "macula",
    "vessel",
)
DR_LEGACY_LESION_METRIC_IDS = tuple(
    f"{name}_{suffix}"
    for name in (*DR_LEGACY_LESIONS, "lesion_union")
    for suffix in ("area_fraction", "component_count")
)
DR_INTERACTION_INPUTS = (
    "hemorrhage_area_fraction",
    "vessel_branch_tortuosity",
    "microaneurysm_area_fraction",
    "vessel_fractal_dimension",
    "e029_background_luminance_cv",
)
DR_INTERACTION_METRIC_IDS = (
    "red_lesion_area_x_quadrants",
    "hemorrhage_area_x_vessel_tortuosity",
    "microaneurysm_area_x_vessel_fractal",
    "hard_exudate_macula_x_background_luminance",
    "cotton_wool_peripapillary_x_vessel_density_cv",
)


def _center(mask: np.ndarray, fallback: tuple[float, float]) -> tuple[float, float]:
    yy, xx = np.nonzero(mask)
    return (float(yy.mean()), float(xx.mean())) if len(yy) else fallback


def _component_metrics(mask: np.ndarray, disc_area: float) -> dict[str, float]:
    areas = np.asarray([region.area / disc_area for region in regionprops(label(mask))], float)
    if not len(areas):
        return {
            "component_count": 0.0,
            "component_area_mean_dd2": 0.0,
            "component_area_p90_dd2": 0.0,
            "component_area_max_dd2": 0.0,
            "component_area_cv": 0.0,
        }
    return {
        "component_count": float(len(areas)),
        "component_area_mean_dd2": float(areas.mean()),
        "component_area_p90_dd2": float(np.quantile(areas, 0.9)),
        "component_area_max_dd2": float(areas.max()),
        "component_area_cv": float(areas.std() / max(areas.mean(), 1e-12)),
    }


def _quadrant_metrics(
    mask: np.ndarray, center: tuple[float, float], fov_area: float,
) -> dict[str, float]:
    yy, xx = np.indices(mask.shape)
    cy, cx = center
    quadrants = (
        (yy < cy) & (xx < cx),
        (yy < cy) & (xx >= cx),
        (yy >= cy) & (xx < cx),
        (yy >= cy) & (xx >= cx),
    )
    burden = np.asarray([(mask & region).sum() / fov_area for region in quadrants], float)
    occupied = int(np.sum(burden > 0))
    total = burden.sum()
    probability = burden[burden > 0] / total if total > 0 else np.array([], float)
    entropy = -float(np.sum(probability * np.log(probability))) / np.log(4) if len(probability) else 0.0
    return {
        "quadrants_occupied": float(occupied),
        "quadrant_burden_max": float(burden.max()),
        "quadrant_burden_cv": float(burden.std() / max(burden.mean(), 1e-12)) if total else 0.0,
        "quadrant_entropy": entropy,
    }


def _distance_metrics(
    mask: np.ndarray, center: tuple[float, float], disc_diameter: float,
) -> dict[str, float]:
    yy, xx = np.nonzero(mask)
    if not len(yy):
        return {"distance_min_dd": 0.0, "distance_median_dd": 0.0}
    distance = np.sqrt((yy - center[0]) ** 2 + (xx - center[1]) ** 2) / disc_diameter
    return {
        "distance_min_dd": float(distance.min()),
        "distance_median_dd": float(np.median(distance)),
    }


def _vessel_heterogeneity(
    vessel: np.ndarray, fov: np.ndarray, disc_diameter: float,
) -> dict[str, float]:
    radius = ndimage.distance_transform_edt(vessel)
    ridge = vessel & (radius >= ndimage.maximum_filter(radius, size=3)) & (radius > 0)
    widths = 2 * radius[ridge] / disc_diameter
    if len(widths):
        width_median = float(np.median(widths))
        width_p90 = float(np.quantile(widths, 0.9))
        width_cv = float(widths.std() / max(widths.mean(), 1e-12))
    else:
        width_median = width_p90 = width_cv = 0.0
    densities: list[float] = []
    for y_indices in np.array_split(np.arange(vessel.shape[0]), 6):
        for x_indices in np.array_split(np.arange(vessel.shape[1]), 6):
            block_fov = fov[np.ix_(y_indices, x_indices)]
            if block_fov.sum() < 0.25 * block_fov.size:
                continue
            densities.append(float(vessel[np.ix_(y_indices, x_indices)].sum() / block_fov.sum()))
    density = np.asarray(densities, float)
    if not len(density):
        return {
            "vessel_width_median_dd": width_median,
            "vessel_width_p90_dd": width_p90,
            "vessel_width_cv": width_cv,
            "vessel_density_grid_cv": 0.0,
            "vessel_density_grid_p95": 0.0,
            "vessel_density_grid_max": 0.0,
        }
    return {
        "vessel_width_median_dd": width_median,
        "vessel_width_p90_dd": width_p90,
        "vessel_width_cv": width_cv,
        "vessel_density_grid_cv": float(density.std() / max(density.mean(), 1e-12)),
        "vessel_density_grid_p95": float(np.quantile(density, 0.95)),
        "vessel_density_grid_max": float(density.max()),
    }


def _validated_masks(rgb: np.ndarray, masks: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    image = np.asarray(rgb)
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("rgb must have shape HxWx3")
    missing = sorted(set(DR_REQUIRED_MASKS) - set(masks))
    if missing:
        raise ValueError(f"missing DR masks: {missing}")
    output: dict[str, np.ndarray] = {}
    for name in DR_REQUIRED_MASKS:
        mask = np.asarray(masks[name], dtype=bool)
        if mask.shape != image.shape[:2]:
            raise ValueError(f"mask {name!r} shape {mask.shape} differs from rgb {image.shape[:2]}")
        output[name] = mask
    return output


def extract_dr_legacy_lesion_metrics(
    rgb: np.ndarray, masks: Mapping[str, np.ndarray],
) -> dict[str, float]:
    """Calculate the 10 frozen E019 lesion burden and count metrics."""
    image = np.asarray(rgb)
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("rgb must have shape HxWx3")
    missing = sorted(set(DR_LESIONS) - set(masks.keys()))
    if missing:
        raise ValueError(f"missing legacy DR lesion masks: {missing}")
    validated: dict[str, np.ndarray] = {}
    for name in DR_LESIONS:
        lesion = np.asarray(masks[name], dtype=bool)
        if lesion.shape != image.shape[:2]:
            raise ValueError(f"mask {name!r} shape {lesion.shape} differs from rgb {image.shape[:2]}")
        validated[name] = lesion
    validated["lesion_union"] = np.logical_or.reduce([validated[name] for name in DR_LESIONS])
    fov = fundus_fov(image)
    fov_count = max(int(fov.sum()), 1)
    output: dict[str, float] = {}
    for name in (*DR_LEGACY_LESIONS, "lesion_union"):
        clean = validated[name] & fov
        output[f"{name}_area_fraction"] = float(clean.sum() / fov_count)
        output[f"{name}_component_count"] = float(label(clean, connectivity=2).max())
    if tuple(output) != DR_LEGACY_LESION_METRIC_IDS:
        raise RuntimeError("legacy DR lesion metric contract changed")
    return output


def dr_legacy_lesion_metric_catalog() -> tuple[dict[str, str], ...]:
    return tuple({
        "metric_id": metric_id,
        "domain": "legacy_dr_lesion_burden",
        "input_source": "rgb_and_expert_or_validated_lesion_masks",
        "unit": "fraction" if metric_id.endswith("area_fraction") else "count",
        "algorithm_version": ALGORITHM_VERSION,
    } for metric_id in DR_LEGACY_LESION_METRIC_IDS)


def extract_dr_mask_metrics(
    rgb: np.ndarray, masks: Mapping[str, np.ndarray],
) -> tuple[dict[str, float], tuple[dict[str, str], ...], dict[str, float | int]]:
    """Calculate 72 DR clinical metrics and 6 explicit negative controls."""
    image = np.asarray(rgb)
    mask = _validated_masks(image, masks)
    fov = ndimage.binary_fill_holes(image.max(axis=2) > 15)
    fov_area = float(max(fov.sum(), 1))
    disc_area = float(max(mask["optic_disc"].sum(), 1))
    disc_diameter = float(max(np.sqrt(4 * disc_area / np.pi), 1))
    fallback = (image.shape[0] / 2, image.shape[1] / 2)
    disc_center = _center(mask["optic_disc"], fallback)
    fovea_center = _center(mask["macula"], fallback)
    yy, xx = np.indices(fov.shape)
    disc_distance = np.sqrt((yy - disc_center[0]) ** 2 + (xx - disc_center[1]) ** 2) / disc_diameter
    fovea_distance = np.sqrt((yy - fovea_center[0]) ** 2 + (xx - fovea_center[1]) ** 2) / disc_diameter
    vessel_distance = ndimage.distance_transform_edt(~mask["vessel"]) / disc_diameter
    metrics: dict[str, float] = {}
    registry: list[dict[str, str]] = []

    def add(name: str, value: float, block: str, definition: str, role: str = "clinical") -> None:
        metrics[name] = float(value)
        registry.append({"metric": name, "block": block, "role": role, "definition": definition})

    red_union = mask["hemorrhage"] | mask["microaneurysm"]
    quadrants = _quadrant_metrics(red_union, disc_center, fov_area)
    add("red_lesion_area_fraction", red_union.sum() / fov_area, "red_lesion_distribution", "H/MA union FOV area")
    for suffix, value in quadrants.items():
        add(f"red_lesion_{suffix}", value, "red_lesion_distribution", f"H/MA {suffix}")
    add("red_lesion_central_2dd_fraction", (red_union & (disc_distance <= 2)).sum() / fov_area,
        "red_lesion_distribution", "H/MA within 2 disc diameters of disc")
    add("red_lesion_peripheral_fraction", (red_union & (disc_distance > 2)).sum() / fov_area,
        "red_lesion_distribution", "H/MA outside 2 disc diameters of disc")
    add("red_lesion_peripheral_central_ratio",
        (red_union & (disc_distance > 2)).sum() / max((red_union & (disc_distance <= 2)).sum(), 1),
        "red_lesion_distribution", "peripheral/central H/MA pixel ratio")

    for lesion_name in DR_LESIONS:
        lesion = mask[lesion_name]
        add(f"{lesion_name}_expert_area_fraction", lesion.sum() / fov_area,
            "lesion_morphology", f"{lesion_name} expert-mask FOV area")
        for suffix, value in _component_metrics(lesion, disc_area).items():
            add(f"{lesion_name}_expert_{suffix}", value, "lesion_morphology", f"{lesion_name} {suffix}")
        add(f"{lesion_name}_macula_1dd_fraction", (lesion & (fovea_distance <= 1)).sum() / fov_area,
            "macular_exudative", f"{lesion_name} within 1 disc diameter of fovea")
        add(f"{lesion_name}_macula_2dd_fraction", (lesion & (fovea_distance <= 2)).sum() / fov_area,
            "macular_exudative", f"{lesion_name} within 2 disc diameters of fovea")
        for suffix, value in _distance_metrics(lesion, fovea_center, disc_diameter).items():
            add(f"{lesion_name}_fovea_{suffix}", value, "macular_exudative", f"{lesion_name} foveal {suffix}")
        lesion_pixels = int(lesion.sum())
        add(f"{lesion_name}_near_vessel_01dd",
            ((vessel_distance <= 0.1) & lesion).sum() / max(lesion_pixels, 1),
            "lesion_vessel_coupling", f"{lesion_name} pixels within 0.1 DD of vessel")
        add(f"{lesion_name}_near_vessel_025dd",
            ((vessel_distance <= 0.25) & lesion).sum() / max(lesion_pixels, 1),
            "lesion_vessel_coupling", f"{lesion_name} pixels within 0.25 DD of vessel")
        add(f"{lesion_name}_vessel_distance_mean_dd",
            vessel_distance[lesion].mean() if lesion_pixels else 0,
            "lesion_vessel_coupling", f"mean {lesion_name}-to-vessel distance")

    lesion_counts = np.asarray([mask[name].sum() for name in DR_LESIONS], float)
    add("lesion_type_diversity", np.sum(lesion_counts > 0), "lesion_morphology", "number of present major lesion types")
    add("red_to_bright_lesion_ratio",
        red_union.sum() / max((mask["hard_exudate"] | mask["cotton_wool_spot"]).sum(), 1),
        "lesion_morphology", "H/MA to HE/CWS area ratio")
    add("cotton_wool_peripapillary_fraction",
        (mask["cotton_wool_spot"] & (disc_distance <= 1)).sum() / fov_area,
        "macular_exudative", "CWS within 1 DD of optic disc")

    neovascularization = mask["neovascularization"]
    add("neovascularization_area_fraction", neovascularization.sum() / fov_area,
        "proliferative", "NV FOV area", "discovery_only")
    add("neovascularization_component_count", len(regionprops(label(neovascularization))),
        "proliferative", "NV component count", "discovery_only")
    add("neovascularization_peripapillary_fraction",
        (neovascularization & (disc_distance <= 1)).sum() / fov_area,
        "proliferative", "NV within 1 DD of disc", "discovery_only")

    for name in DR_NEGATIVE_MASKS:
        negative = mask[name]
        add(f"{name}_area_fraction", negative.sum() / fov_area,
            "negative_control", f"{name} FOV area", "negative_control")
        add(f"{name}_component_count", len(regionprops(label(negative))),
            "negative_control", f"{name} component count", "negative_control")

    for name, value in _vessel_heterogeneity(mask["vessel"], fov, disc_diameter).items():
        add(name, value, "vascular_heterogeneity", name.replace("_", " "))

    if len(metrics) != 78 or len(registry) != 78:
        raise RuntimeError(f"DR direct metric contract changed: metrics={len(metrics)}, registry={len(registry)}")
    qc: dict[str, float | int] = {
        "fov_pixels": int(fov_area),
        "disc_pixels": int(disc_area),
        "disc_diameter_pixels": disc_diameter,
        "macula_missing": int(not mask["macula"].any()),
        "metric_finite_fraction": float(np.mean(np.isfinite(list(metrics.values())))),
    }
    return metrics, tuple(registry), qc


def add_dr_prespecified_interactions(
    metrics: Mapping[str, float], upstream_values: Mapping[str, float], *, strict: bool = True,
) -> dict[str, float]:
    """Return the five frozen E030 interactions from direct and upstream metrics."""
    missing = sorted(set(DR_INTERACTION_INPUTS) - set(upstream_values.keys()))
    if strict and missing:
        raise ValueError(f"missing DR interaction inputs: {missing}")
    values = {name: float(upstream_values.get(name, np.nan)) for name in DR_INTERACTION_INPUTS}
    return {
        "red_lesion_area_x_quadrants": float(metrics["red_lesion_area_fraction"] * metrics["red_lesion_quadrants_occupied"]),
        "hemorrhage_area_x_vessel_tortuosity": float(values["hemorrhage_area_fraction"] * values["vessel_branch_tortuosity"]),
        "microaneurysm_area_x_vessel_fractal": float(values["microaneurysm_area_fraction"] * values["vessel_fractal_dimension"]),
        "hard_exudate_macula_x_background_luminance": float(metrics["hard_exudate_macula_1dd_fraction"] * values["e029_background_luminance_cv"]),
        "cotton_wool_peripapillary_x_vessel_density_cv": float(metrics["cotton_wool_peripapillary_fraction"] * metrics["vessel_density_grid_cv"]),
    }


def dr_metric_catalog() -> tuple[dict[str, str], ...]:
    """Return metadata for all 77 clinical metrics and 6 negative controls."""
    size = 96
    rgb = np.full((size, size, 3), 80, dtype=np.uint8)
    empty = np.zeros((size, size), dtype=bool)
    masks = {name: empty.copy() for name in DR_REQUIRED_MASKS}
    masks["optic_disc"][40:48, 20:28] = True
    masks["macula"][44:48, 62:66] = True
    metrics, registry, _ = extract_dr_mask_metrics(rgb, masks)
    rows = [
        {
            "metric_id": row["metric"],
            "domain": row["block"],
            "input_source": "rgb_and_expert_or_validated_masks",
            "unit": "defined_by_metric",
            "algorithm_version": ALGORITHM_VERSION,
            "role": row["role"],
            "definition": row["definition"],
        }
        for row in registry
    ]
    rows.extend({
        "metric_id": metric_id,
        "domain": "prespecified_interaction",
        "input_source": "direct_and_upstream_metrics",
        "unit": "product_of_component_units",
        "algorithm_version": ALGORITHM_VERSION,
        "role": "clinical",
        "definition": metric_id.replace("_", " "),
    } for metric_id in DR_INTERACTION_METRIC_IDS)
    if len(metrics) + len(DR_INTERACTION_METRIC_IDS) != 83:
        raise RuntimeError("DR catalog contract changed")
    return tuple(rows)


DR_DIRECT_METRIC_IDS = tuple(row["metric_id"] for row in dr_metric_catalog()[:-5])
DR_METRIC_IDS = tuple(row["metric_id"] for row in dr_metric_catalog())
