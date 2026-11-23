"""Deterministic E046 fine phenomics for one known retinal-lesion mask."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from scipy import ndimage
from skimage.measure import label, regionprops


ALGORITHM_VERSION = "ophthalmic_quantification.known_lesion_phenomics.v0.1.0"
KNOWN_DR_LESIONS = (
    "microaneurysm",
    "hemorrhage",
    "hard_exudate",
    "soft_exudate",
    "irma",
    "venous_beading",
    "neovascularization",
)
KNOWN_LESION_MEASUREMENT_IDS = (
    "presence",
    "component_count",
    "area_fraction",
    "component_area_mean_disc2",
    "component_area_median_disc2",
    "component_area_p90_disc2",
    "component_area_max_disc2",
    "upper_quartile_area_share",
    "circularity_area_weighted",
    "eccentricity_area_weighted",
    "solidity_area_weighted",
    "boundary_irregularity_area_weighted",
    "quadrant_occupancy",
    "quadrant_burden_entropy",
    "radial_centroid_mean_disc",
    "nearest_fovea_distance_disc",
    "perivascular_fraction_025dd",
    "vessel_distance_mean_disc",
    "macular_1dd_area_fraction",
    "macular_2dd_area_fraction",
)


def _center(mask: np.ndarray) -> tuple[float, float]:
    y, x = np.nonzero(mask)
    if not len(y):
        raise ValueError("landmark mask is empty")
    return float(y.mean()), float(x.mean())


def _weighted(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.average(values, weights=weights)) if len(values) else float("nan")


def extract_known_lesion_measurements(
    lesion_mask: np.ndarray,
    *,
    fov_mask: np.ndarray,
    disc_mask: np.ndarray | None = None,
    fovea_mask: np.ndarray | None = None,
    vessel_mask: np.ndarray | None = None,
) -> dict[str, float]:
    """Calculate the 20 outcome-blind E046 measurements for one lesion mask."""
    arrays: dict[str, np.ndarray] = {
        "lesion_mask": np.asarray(lesion_mask, dtype=bool),
        "fov_mask": np.asarray(fov_mask, dtype=bool),
    }
    for name, value in (("disc_mask", disc_mask), ("fovea_mask", fovea_mask), ("vessel_mask", vessel_mask)):
        if value is not None:
            arrays[name] = np.asarray(value, dtype=bool)
    shape = arrays["lesion_mask"].shape
    if len(shape) != 2 or any(value.shape != shape for value in arrays.values()):
        raise ValueError("all E046 masks must share one two-dimensional shape")
    if not arrays["fov_mask"].any():
        raise ValueError("FOV mask is empty")
    if "disc_mask" in arrays and not arrays["disc_mask"].any():
        raise ValueError("disc mask is empty")
    if "fovea_mask" in arrays and not arrays["fovea_mask"].any():
        raise ValueError("fovea mask is empty")

    lesion = arrays["lesion_mask"] & arrays["fov_mask"]
    fov = arrays["fov_mask"]
    disc = arrays.get("disc_mask")
    fovea = arrays.get("fovea_mask")
    vessel = arrays.get("vessel_mask")
    fov_area = float(fov.sum())
    fov_fraction = fov_area / float(fov.size)
    disc_area = float(disc.sum()) if disc is not None else float("nan")
    disc_diameter = float(np.sqrt(4.0 * disc_area / np.pi)) if disc is not None else float("nan")
    disc_center = np.asarray(_center(disc)) if disc is not None else None
    fovea_center = np.asarray(_center(fovea)) if fovea is not None else None

    labelled = label(lesion, connectivity=2)
    regions = regionprops(labelled)
    component_areas = np.asarray([region.area for region in regions], dtype=float)
    component_areas_disc = component_areas / disc_area if disc is not None else np.full_like(component_areas, np.nan)
    lesion_area = float(lesion.sum())

    output = {
        "presence": float(bool(regions)),
        "component_count": float(len(regions) / fov_fraction),
        "area_fraction": lesion_area / fov_area,
    }
    if regions:
        output.update(
            {
                "component_area_mean_disc2": float(component_areas_disc.mean()),
                "component_area_median_disc2": float(np.median(component_areas_disc)),
                "component_area_p90_disc2": float(np.quantile(component_areas_disc, 0.9)),
                "component_area_max_disc2": float(component_areas_disc.max()),
                "upper_quartile_area_share": float(
                    component_areas[component_areas >= np.quantile(component_areas, 0.75)].sum()
                    / component_areas.sum()
                ),
            }
        )
        circularity = []
        irregularity = []
        for region in regions:
            perimeter = max(float(region.perimeter), 1.0)
            circ = 4.0 * np.pi * float(region.area) / perimeter**2
            circularity.append(circ)
            irregularity.append(max(1.0 / max(circ, 1e-12) - 1.0, 0.0))
        output.update(
            {
                "circularity_area_weighted": _weighted(np.asarray(circularity), component_areas),
                "eccentricity_area_weighted": _weighted(
                    np.asarray([region.eccentricity for region in regions]), component_areas
                ),
                "solidity_area_weighted": _weighted(
                    np.asarray([region.solidity for region in regions]), component_areas
                ),
                "boundary_irregularity_area_weighted": _weighted(
                    np.asarray(irregularity), component_areas
                ),
            }
        )
    else:
        for name in KNOWN_LESION_MEASUREMENT_IDS[3:12]:
            output[name] = float("nan")

    yy, xx = np.indices(shape)
    coordinates = np.column_stack((yy[lesion], xx[lesion])).astype(float)
    if len(coordinates) and disc_center is not None and fovea_center is not None:
        axis = fovea_center - disc_center
        axis_norm = float(np.linalg.norm(axis))
        if axis_norm <= 0:
            raise ValueError("disc and fovea centers coincide")
        axis /= axis_norm
        perpendicular = np.asarray([-axis[1], axis[0]])
        relative = coordinates - disc_center
        q1 = relative @ axis >= 0
        q2 = relative @ perpendicular >= 0
        quadrant_areas = np.asarray(
            [np.sum((q1 == along) & (q2 == across)) for along, across in ((0, 0), (0, 1), (1, 0), (1, 1))],
            dtype=float,
        )
        probabilities = quadrant_areas[quadrant_areas > 0] / quadrant_areas.sum()
        output["quadrant_occupancy"] = float(np.sum(quadrant_areas > 0))
        output["quadrant_burden_entropy"] = float(
            -np.sum(probabilities * np.log(probabilities)) / np.log(4.0)
        )
        centroids = np.asarray([region.centroid for region in regions], dtype=float)
        output["radial_centroid_mean_disc"] = _weighted(
            np.linalg.norm(centroids - fovea_center, axis=1) / disc_diameter,
            component_areas,
        )
        foveal_distance = np.linalg.norm(coordinates - fovea_center, axis=1) / disc_diameter
        output["nearest_fovea_distance_disc"] = float(foveal_distance.min())
        if vessel is not None:
            vessel_distance = ndimage.distance_transform_edt(~(vessel & fov))[lesion] / disc_diameter
            output["perivascular_fraction_025dd"] = float(np.mean(vessel_distance <= 0.25))
            output["vessel_distance_mean_disc"] = float(vessel_distance.mean())
        else:
            output["perivascular_fraction_025dd"] = float("nan")
            output["vessel_distance_mean_disc"] = float("nan")
    else:
        for name in KNOWN_LESION_MEASUREMENT_IDS[12:18]:
            output[name] = float("nan")

    if disc is not None and fovea_center is not None:
        distance_to_fovea = np.sqrt((yy - fovea_center[0]) ** 2 + (xx - fovea_center[1]) ** 2)
        for radius, name in (
            (disc_diameter, "macular_1dd_area_fraction"),
            (2.0 * disc_diameter, "macular_2dd_area_fraction"),
        ):
            zone = fov & (distance_to_fovea <= radius)
            output[name] = float((lesion & zone).sum() / max(int(zone.sum()), 1))
    else:
        output["macular_1dd_area_fraction"] = float("nan")
        output["macular_2dd_area_fraction"] = float("nan")
    if tuple(output) != KNOWN_LESION_MEASUREMENT_IDS:
        raise RuntimeError("E046 measurement contract changed")
    return output

def extract_known_lesion_bank(
    lesion_masks: Mapping[str, np.ndarray],
    *,
    fov_mask: np.ndarray,
    disc_mask: np.ndarray | None = None,
    fovea_mask: np.ndarray | None = None,
    vessel_mask: np.ndarray | None = None,
) -> dict[str, float]:
    """Calculate the 20-measurement bank for each supplied known lesion."""
    unknown = set(lesion_masks) - set(KNOWN_DR_LESIONS)
    if unknown:
        raise ValueError(f"unknown DR lesion ids: {sorted(unknown)}")
    output: dict[str, float] = {}
    for lesion_id, lesion_mask in lesion_masks.items():
        values = extract_known_lesion_measurements(
            lesion_mask,
            fov_mask=fov_mask,
            disc_mask=disc_mask,
            fovea_mask=fovea_mask,
            vessel_mask=vessel_mask,
        )
        output.update({f"{lesion_id}__{name}": value for name, value in values.items()})
    return output
