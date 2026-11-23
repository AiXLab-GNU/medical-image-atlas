"""Fail-closed, outcome-blind clinical assessment for ICDR grading reconstruction."""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any


DR_GRADING_ASSESSMENT_VERSION = 1
CLINICAL_STATUSES = frozenset({"not_reviewed", "absent", "present", "uncertain"})
GRADING_QUADRANTS = ("q1", "q2", "q3", "q4")
HEMORRHAGE_COMPARTMENTS = ("intraretinal", "preretinal", "vitreous")
NEOVASCULARIZATION_SITES = ("nvd", "nve")
QUADRANT_FINDINGS = (
    "hemorrhage_microaneurysm_severe",
    "venous_beading",
    "prominent_irma",
)
IMAGE_GRADABILITY = frozenset(
    {"not_reviewed", "gradable", "partially_gradable", "ungradable"}
)
UNGRADABLE_REASONS = frozenset(
    {
        "not_reviewed",
        "none",
        "blur",
        "illumination",
        "media_opacity",
        "field_loss",
        "hemorrhage_obscuration",
        "other",
    }
)
PDR_STATUSES = frozenset(
    {
        "not_reviewed",
        "absent",
        "active",
        "treated_stable",
        "active_after_treatment",
        "uncertain",
    }
)
KNOWN_DR_LESIONS = (
    "microaneurysm",
    "hemorrhage",
    "hard_exudate",
    "soft_exudate",
    "irma",
    "venous_beading",
    "neovascularization",
)


def default_dr_grading_assessment() -> dict[str, Any]:
    """Return a complete, explicitly unreviewed grading-specific assessment."""
    return {
        "assessment_version": DR_GRADING_ASSESSMENT_VERSION,
        "image_gradability": "not_reviewed",
        "ungradable_reason": "not_reviewed",
        "obscuration_fraction": None,
        "pdr_status": "not_reviewed",
        "hemorrhage_compartments": {
            key: "not_reviewed" for key in HEMORRHAGE_COMPARTMENTS
        },
        "neovascularization_sites": {
            key: "not_reviewed" for key in NEOVASCULARIZATION_SITES
        },
        "quadrant_findings": {
            finding: {quadrant: "not_reviewed" for quadrant in GRADING_QUADRANTS}
            for finding in QUADRANT_FINDINGS
        },
    }


def _validated_status_map(
    value: object, *, expected_keys: tuple[str, ...], path: str
) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    if set(value) != set(expected_keys):
        raise ValueError(f"{path} must contain exactly {list(expected_keys)}")
    result = {}
    for key in expected_keys:
        status = value[key]
        if status not in CLINICAL_STATUSES:
            raise ValueError(f"invalid clinical status for {path}.{key}")
        result[key] = str(status)
    return result


def validate_dr_grading_assessment(assessment: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and detach the grading-specific reader assessment."""
    if not isinstance(assessment, Mapping):
        raise ValueError("grading_assessment must be an object")
    expected = set(default_dr_grading_assessment())
    if set(assessment) != expected:
        raise ValueError(f"grading_assessment must contain exactly {sorted(expected)}")
    if assessment.get("assessment_version") != DR_GRADING_ASSESSMENT_VERSION:
        raise ValueError("unsupported grading assessment version")

    gradability = assessment.get("image_gradability")
    if gradability not in IMAGE_GRADABILITY:
        raise ValueError("invalid image_gradability")
    reason = assessment.get("ungradable_reason")
    if reason not in UNGRADABLE_REASONS:
        raise ValueError("invalid ungradable_reason")
    if gradability == "gradable" and reason != "none":
        raise ValueError("gradable image requires ungradable_reason=none")
    if gradability == "ungradable" and reason in {"none", "not_reviewed"}:
        raise ValueError("ungradable image requires a specific ungradable_reason")

    obscuration = assessment.get("obscuration_fraction")
    if obscuration is not None and (
        isinstance(obscuration, bool)
        or not isinstance(obscuration, (int, float))
        or not math.isfinite(float(obscuration))
        or not 0.0 <= float(obscuration) <= 1.0
    ):
        raise ValueError("obscuration_fraction must be null or between 0 and 1")
    pdr_status = assessment.get("pdr_status")
    if pdr_status not in PDR_STATUSES:
        raise ValueError("invalid pdr_status")

    hemorrhage = _validated_status_map(
        assessment.get("hemorrhage_compartments"),
        expected_keys=HEMORRHAGE_COMPARTMENTS,
        path="hemorrhage_compartments",
    )
    neovascularization = _validated_status_map(
        assessment.get("neovascularization_sites"),
        expected_keys=NEOVASCULARIZATION_SITES,
        path="neovascularization_sites",
    )
    quadrant_value = assessment.get("quadrant_findings")
    if not isinstance(quadrant_value, Mapping) or set(quadrant_value) != set(QUADRANT_FINDINGS):
        raise ValueError(f"quadrant_findings must contain exactly {list(QUADRANT_FINDINGS)}")
    quadrants = {
        finding: _validated_status_map(
            quadrant_value[finding],
            expected_keys=GRADING_QUADRANTS,
            path=f"quadrant_findings.{finding}",
        )
        for finding in QUADRANT_FINDINGS
    }
    return {
        "assessment_version": DR_GRADING_ASSESSMENT_VERSION,
        "image_gradability": str(gradability),
        "ungradable_reason": str(reason),
        "obscuration_fraction": None if obscuration is None else float(obscuration),
        "pdr_status": str(pdr_status),
        "hemorrhage_compartments": hemorrhage,
        "neovascularization_sites": neovascularization,
        "quadrant_findings": quadrants,
    }


def _review_statuses(lesion_reviews: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(lesion_reviews, Mapping) or set(lesion_reviews) != set(KNOWN_DR_LESIONS):
        raise ValueError("lesion_reviews must contain all seven known DR lesions")
    result = {}
    for lesion in KNOWN_DR_LESIONS:
        review = lesion_reviews[lesion]
        status = review.get("status") if isinstance(review, Mapping) else review
        if status not in CLINICAL_STATUSES:
            raise ValueError(f"invalid lesion review status for {lesion}")
        result[lesion] = str(status)
    return result


def validate_grading_lesion_consistency(
    lesion_reviews: Mapping[str, Any], assessment: Mapping[str, Any]
) -> None:
    """Reject contradictions between generic lesion and grading-specific reviews."""
    reviews = _review_statuses(lesion_reviews)
    value = validate_dr_grading_assessment(assessment)
    linked = {
        "hemorrhage": tuple(value["hemorrhage_compartments"].values()),
        "neovascularization": tuple(value["neovascularization_sites"].values()),
    }
    for lesion, subtype_statuses in linked.items():
        if reviews[lesion] == "absent" and "present" in subtype_statuses:
            raise ValueError(f"{lesion} is absent but a grading subtype is present")
        if reviews[lesion] == "present" and set(subtype_statuses) == {"absent"}:
            raise ValueError(f"{lesion} is present but all grading subtypes are absent")


def _threshold_status(statuses: tuple[str, ...], threshold: int) -> str:
    present = statuses.count("present")
    unresolved = sum(status in {"not_reviewed", "uncertain"} for status in statuses)
    if present >= threshold:
        return "positive"
    if present + unresolved >= threshold:
        return "indeterminate"
    return "negative"


def reconstruct_icdr_grade(
    lesion_reviews: Mapping[str, Any], assessment: Mapping[str, Any]
) -> dict[str, Any]:
    """Reconstruct a transparent Grade 1--4 candidate without using an AI score."""
    reviews = _review_statuses(lesion_reviews)
    value = validate_dr_grading_assessment(assessment)
    validate_grading_lesion_consistency(reviews, value)

    rule_421 = {
        "four_quadrant_hemorrhage_microaneurysm": _threshold_status(
            tuple(value["quadrant_findings"]["hemorrhage_microaneurysm_severe"].values()), 4
        ),
        "two_quadrant_venous_beading": _threshold_status(
            tuple(value["quadrant_findings"]["venous_beading"].values()), 2
        ),
        "one_quadrant_prominent_irma": _threshold_status(
            tuple(value["quadrant_findings"]["prominent_irma"].values()), 1
        ),
    }
    if "positive" in rule_421.values():
        rule_421["overall"] = "positive"
    elif "indeterminate" in rule_421.values():
        rule_421["overall"] = "indeterminate"
    else:
        rule_421["overall"] = "negative"

    pdr_inputs = (
        value["neovascularization_sites"]["nvd"],
        value["neovascularization_sites"]["nve"],
        value["hemorrhage_compartments"]["preretinal"],
        value["hemorrhage_compartments"]["vitreous"],
    )
    if value["pdr_status"] in {"active", "active_after_treatment"} or "present" in pdr_inputs:
        pdr_evidence = "positive"
    elif value["pdr_status"] in {"not_reviewed", "uncertain"} or any(
        status in {"not_reviewed", "uncertain"} for status in pdr_inputs
    ):
        pdr_evidence = "indeterminate"
    else:
        pdr_evidence = "negative"

    base = {
        "rule_421": rule_421,
        "pdr_visual_evidence": pdr_evidence,
        "treated_pdr_history": value["pdr_status"] in {
            "treated_stable", "active_after_treatment"
        },
    }
    if value["image_gradability"] == "ungradable":
        return {
            **base,
            "disease_presence": "indeterminate",
            "grade_1_to_4": None,
            "grade_status": "ungradable",
            "grade_basis": "image_ungradable",
        }
    if value["image_gradability"] == "not_reviewed":
        return {
            **base,
            "disease_presence": "indeterminate",
            "grade_1_to_4": None,
            "grade_status": "indeterminate",
            "grade_basis": "gradability_not_reviewed",
        }

    if "present" in reviews.values():
        disease_presence = "positive"
    elif any(status in {"not_reviewed", "uncertain"} for status in reviews.values()):
        disease_presence = "indeterminate"
    else:
        disease_presence = "negative"

    if pdr_evidence == "positive":
        grade, status, basis = 4, "assigned", "proliferative_finding"
    elif pdr_evidence == "indeterminate":
        grade, status, basis = None, "indeterminate", "pdr_assessment_incomplete"
    elif rule_421["overall"] == "positive":
        grade, status, basis = 3, "assigned", "severe_npdr_421"
    elif rule_421["overall"] == "indeterminate":
        grade, status, basis = None, "indeterminate", "rule_421_incomplete"
    elif disease_presence == "negative":
        grade, status, basis = None, "outside_scope_no_dr", "no_visible_dr"
    elif disease_presence == "indeterminate":
        grade, status, basis = None, "indeterminate", "lesion_review_incomplete"
    elif reviews["microaneurysm"] == "present" and all(
        reviews[lesion] == "absent" for lesion in KNOWN_DR_LESIONS[1:]
    ):
        grade, status, basis = 1, "assigned", "microaneurysm_only"
    else:
        grade, status, basis = 2, "assigned", "more_than_microaneurysm_below_severe"
    return {
        **base,
        "disease_presence": disease_presence,
        "grade_1_to_4": grade,
        "grade_status": status,
        "grade_basis": basis,
    }
