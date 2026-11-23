"""Validated, outcome-blind retinal-lesion annotation interchange and rasterization."""

from __future__ import annotations

from collections.abc import Mapping
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from skimage.draw import disk, line, polygon
from skimage.morphology import binary_dilation

from .dr_grading import (
    reconstruct_icdr_grade,
    validate_dr_grading_assessment,
    validate_grading_lesion_consistency,
)
from .known_lesion_phenomics import KNOWN_DR_LESIONS, extract_known_lesion_bank


ANNOTATION_SCHEMA_VERSION = 2
SUPPORTED_ANNOTATION_SCHEMA_VERSIONS = {1, ANNOTATION_SCHEMA_VERSION}
REVIEW_STATUSES = {"not_reviewed", "absent", "present", "uncertain"}
CONFIDENCE_LEVELS = {"definite", "probable", "uncertain"}
GEOMETRY_TYPES = {"point", "polygon", "brush"}
LESION_ANNOTATION_CATALOG = (
    {
        "lesion_id": "microaneurysm",
        "label_ko": "미세동맥류",
        "label_en": "Microaneurysm",
        "default_tool": "point",
        "allowed_tools": ("point", "brush"),
        "instruction_ko": "각각의 작은 적색 원형 병변 중심을 한 번씩 찍습니다.",
    },
    {
        "lesion_id": "hemorrhage",
        "label_ko": "망막출혈",
        "label_en": "Retinal hemorrhage",
        "default_tool": "polygon",
        "allowed_tools": ("polygon", "brush"),
        "instruction_ko": "출혈의 보이는 외곽을 따라 닫힌 영역으로 표시합니다.",
    },
    {
        "lesion_id": "hard_exudate",
        "label_ko": "경성삼출물",
        "label_en": "Hard exudate",
        "default_tool": "polygon",
        "allowed_tools": ("polygon", "brush"),
        "instruction_ko": "밝고 경계가 뚜렷한 침착물 군집의 외곽을 표시합니다.",
    },
    {
        "lesion_id": "soft_exudate",
        "label_ko": "연성삼출물(면화반)",
        "label_en": "Soft exudate / cotton-wool spot",
        "default_tool": "polygon",
        "allowed_tools": ("polygon", "brush"),
        "instruction_ko": "흐릿하고 솜털 모양인 병변의 보이는 경계를 표시합니다.",
    },
    {
        "lesion_id": "irma",
        "label_ko": "망막내 미세혈관 이상(IRMA)",
        "label_en": "Intraretinal microvascular abnormality",
        "default_tool": "brush",
        "allowed_tools": ("brush", "polygon"),
        "instruction_ko": "이상 혈관망이 차지하는 영역을 따라가며 표시합니다.",
    },
    {
        "lesion_id": "venous_beading",
        "label_ko": "정맥염주",
        "label_en": "Venous beading",
        "default_tool": "brush",
        "allowed_tools": ("brush",),
        "instruction_ko": "굵기가 반복적으로 변하는 정맥 구간만 선으로 추적합니다.",
    },
    {
        "lesion_id": "neovascularization",
        "label_ko": "신생혈관",
        "label_en": "Neovascularization",
        "default_tool": "brush",
        "allowed_tools": ("brush", "polygon"),
        "instruction_ko": "비정상 신생혈관망을 추적하거나 전체 외곽을 둘러 표시합니다.",
    },
)
_CATALOG_BY_ID = {row["lesion_id"]: row for row in LESION_ANNOTATION_CATALOG}


def lesion_annotation_catalog() -> tuple[dict[str, object], ...]:
    """Return detached catalog rows suitable for a UI or annotation manual."""
    return tuple(dict(row) for row in LESION_ANNOTATION_CATALOG)


def _image_shape(document: Mapping[str, Any]) -> tuple[int, int]:
    image = document.get("image")
    if not isinstance(image, Mapping):
        raise ValueError("annotation image metadata is required")
    width, height = image.get("width"), image.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise ValueError("annotation image width and height must be positive integers")
    return height, width


def _validated_points(
    annotation: Mapping[str, Any], shape: tuple[int, int], geometry_type: str
) -> tuple[tuple[float, float], ...]:
    points = annotation.get("points")
    if not isinstance(points, list):
        raise ValueError("annotation points must be a list")
    minimum = {"point": 1, "brush": 2, "polygon": 3}[geometry_type]
    maximum = 1 if geometry_type == "point" else None
    if len(points) < minimum or (maximum is not None and len(points) > maximum):
        raise ValueError(f"{geometry_type} annotation has an invalid point count")
    height, width = shape
    result = []
    for point in points:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError("each annotation point must be [x, y]")
        x, y = point
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (x, y)):
            raise ValueError("annotation coordinates must be finite numbers")
        if not 0 <= float(x) < width or not 0 <= float(y) < height:
            raise ValueError("annotation coordinate lies outside the image")
        result.append((float(x), float(y)))
    return tuple(result)


def validate_annotation_document(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a v1 document without turning unreviewed lesions into negative truth."""
    if not isinstance(document, Mapping):
        raise ValueError("annotation document must be an object")
    schema_version = document.get("schema_version")
    if schema_version not in SUPPORTED_ANNOTATION_SCHEMA_VERSIONS:
        raise ValueError("unsupported annotation schema version")
    shape = _image_shape(document)
    reviews = document.get("lesion_reviews", {})
    if not isinstance(reviews, Mapping):
        raise ValueError("lesion_reviews must be an object")
    unknown_reviews = set(reviews) - set(KNOWN_DR_LESIONS)
    if unknown_reviews:
        raise ValueError(f"unknown lesion review ids: {sorted(unknown_reviews)}")
    statuses: dict[str, str] = {}
    for lesion_id in KNOWN_DR_LESIONS:
        review = reviews.get(lesion_id, {"status": "not_reviewed"})
        if not isinstance(review, Mapping) or review.get("status") not in REVIEW_STATUSES:
            raise ValueError(f"invalid review status for {lesion_id}")
        statuses[lesion_id] = str(review["status"])

    annotations = document.get("annotations", [])
    if not isinstance(annotations, list):
        raise ValueError("annotations must be a list")
    validated_annotations = []
    seen_ids = set()
    annotation_counts = {lesion_id: 0 for lesion_id in KNOWN_DR_LESIONS}
    for annotation in annotations:
        if not isinstance(annotation, Mapping):
            raise ValueError("each annotation must be an object")
        annotation_id = annotation.get("id")
        if not isinstance(annotation_id, str) or not annotation_id or annotation_id in seen_ids:
            raise ValueError("annotation ids must be unique non-empty strings")
        seen_ids.add(annotation_id)
        lesion_id = annotation.get("lesion_id")
        if lesion_id not in _CATALOG_BY_ID:
            raise ValueError(f"unknown lesion id: {lesion_id}")
        geometry_type = annotation.get("geometry_type")
        if geometry_type not in GEOMETRY_TYPES:
            raise ValueError(f"invalid geometry type for {annotation_id}")
        if geometry_type not in _CATALOG_BY_ID[lesion_id]["allowed_tools"]:
            raise ValueError(f"{geometry_type} is not allowed for {lesion_id}")
        points = _validated_points(annotation, shape, str(geometry_type))
        radius = annotation.get("radius_px", 3)
        if geometry_type in {"point", "brush"} and (
            not isinstance(radius, (int, float)) or not math.isfinite(radius) or radius <= 0
        ):
            raise ValueError("point and brush radius_px must be positive")
        confidence = annotation.get("confidence", "definite")
        if confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"invalid confidence for {annotation_id}")
        annotation_counts[str(lesion_id)] += 1
        validated_annotations.append(
            {
                "id": annotation_id,
                "lesion_id": lesion_id,
                "geometry_type": geometry_type,
                "points": [list(point) for point in points],
                "radius_px": float(radius),
                "confidence": confidence,
            }
        )
    for lesion_id, status in statuses.items():
        count = annotation_counts[lesion_id]
        if status == "present" and count == 0:
            raise ValueError(f"present review requires an annotation for {lesion_id}")
        if status in {"absent", "not_reviewed"} and count:
            raise ValueError(f"{status} review cannot contain annotations for {lesion_id}")
    output = {
        "schema_version": schema_version,
        "image": dict(document["image"]),
        "lesion_reviews": {
            lesion_id: {"status": statuses[lesion_id]} for lesion_id in KNOWN_DR_LESIONS
        },
        "annotations": validated_annotations,
    }
    if schema_version == 2:
        grading_assessment = validate_dr_grading_assessment(
            document.get("grading_assessment")
        )
        validate_grading_lesion_consistency(output["lesion_reviews"], grading_assessment)
        output["grading_assessment"] = grading_assessment
    return output


def rasterize_annotation_document(
    document: Mapping[str, Any], *, include_uncertain: bool = False
) -> dict[str, np.ndarray]:
    """Rasterize reviewed lesion geometry; omit unknown and, by default, uncertain truth."""
    validated = validate_annotation_document(document)
    shape = _image_shape(validated)
    masks: dict[str, np.ndarray] = {}
    statuses = {
        lesion_id: review["status"]
        for lesion_id, review in validated["lesion_reviews"].items()
    }
    for lesion_id, status in statuses.items():
        if status == "not_reviewed" or (status == "uncertain" and not include_uncertain):
            continue
        masks[lesion_id] = np.zeros(shape, dtype=bool)
    for annotation in validated["annotations"]:
        lesion_id = annotation["lesion_id"]
        if lesion_id not in masks:
            continue
        mask = masks[lesion_id]
        points = annotation["points"]
        geometry_type = annotation["geometry_type"]
        radius = max(1, int(round(annotation["radius_px"])))
        if geometry_type == "point":
            x, y = points[0]
            rr, cc = disk((y, x), radius, shape=shape)
            mask[rr, cc] = True
        elif geometry_type == "polygon":
            rr, cc = polygon(
                np.asarray([point[1] for point in points]),
                np.asarray([point[0] for point in points]),
                shape=shape,
            )
            mask[rr, cc] = True
        else:
            centerline = np.zeros(shape, dtype=bool)
            for start, end in zip(points, points[1:]):
                rr, cc = line(
                    int(round(start[1])), int(round(start[0])),
                    int(round(end[1])), int(round(end[0])),
                )
                centerline[rr, cc] = True
            footprint = np.ones((radius * 2 + 1, radius * 2 + 1), dtype=bool)
            mask |= binary_dilation(centerline, footprint=footprint)
    return masks


def quantify_annotation_document(
    document: Mapping[str, Any],
    *,
    fov_mask: np.ndarray,
    disc_mask: np.ndarray | None = None,
    fovea_mask: np.ndarray | None = None,
    vessel_mask: np.ndarray | None = None,
) -> dict[str, float]:
    """Convert reviewed expert geometry into the deterministic E046 measurement bank."""
    lesion_masks = rasterize_annotation_document(document)
    return extract_known_lesion_bank(
        lesion_masks,
        fov_mask=fov_mask,
        disc_mask=disc_mask,
        fovea_mask=fovea_mask,
        vessel_mask=vessel_mask,
    )


def quantify_annotation_file(
    annotation_path: Path,
    *,
    fov_mask_path: Path,
    output_path: Path,
    disc_mask_path: Path | None = None,
    fovea_mask_path: Path | None = None,
    vessel_mask_path: Path | None = None,
) -> Path:
    """Quantify a web-exported JSON document with explicit NumPy mask inputs."""
    document = json.loads(annotation_path.read_text(encoding="utf-8"))

    def load(path: Path | None) -> np.ndarray | None:
        return None if path is None else np.load(path, allow_pickle=False)

    measurements = quantify_annotation_document(
        document,
        fov_mask=load(fov_mask_path),
        disc_mask=load(disc_mask_path),
        fovea_mask=load(fovea_mask_path),
        vessel_mask=load(vessel_mask_path),
    )
    payload = {
        "schema_version": document["schema_version"],
        "annotation_file": annotation_path.name,
        "measurement_count": len(measurements),
        "measurements": {
            key: float(value) if np.isfinite(value) else None
            for key, value in measurements.items()
        },
    }
    if document["schema_version"] == 2:
        validated = validate_annotation_document(document)
        payload["grading_reconstruction"] = reconstruct_icdr_grade(
            validated["lesion_reviews"], validated["grading_assessment"]
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return output_path
