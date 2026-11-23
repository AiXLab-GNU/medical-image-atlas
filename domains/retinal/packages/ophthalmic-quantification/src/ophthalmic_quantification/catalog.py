"""Machine-readable registry for every calculator exposed by the package."""

from __future__ import annotations

from .dr_metrics import dr_legacy_lesion_metric_catalog, dr_metric_catalog
from .extended_fundus_metrics import extended_fundus_metric_catalog
from .fundus_metrics import fundus_metric_catalog
from .mask_metrics import AGREEMENT_METRIC_IDS, BINARY_MASK_METRIC_IDS
from .oct_metrics import oct_metric_catalog


def metric_catalog() -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    rows.extend({"collection": "fundus_legacy_139", **row} for row in fundus_metric_catalog())
    rows.extend(
        {
            "collection": "oct_mask_25",
            "metric_id": row["metric_name"],
            "domain": "oct_mask_phenotype",
            "input_source": "integer_label_mask",
            "unit": row["unit"],
            "algorithm_version": row["algorithm_version"],
        }
        for row in oct_metric_catalog()
    )
    rows.extend(
        {
            "collection": "generic_binary_mask",
            "metric_id": metric_id,
            "domain": "mask_morphology",
            "input_source": "binary_mask",
            "unit": "defined_by_metric",
            "algorithm_version": "ophthalmic_quantification.mask.v0.1.0",
        }
        for metric_id in BINARY_MASK_METRIC_IDS
    )
    rows.extend(
        {
            "collection": "segmentation_agreement",
            "metric_id": metric_id,
            "domain": "mask_agreement",
            "input_source": "prediction_and_ground_truth_masks",
            "unit": "fraction_or_binary",
            "algorithm_version": "ophthalmic_quantification.mask.v0.1.0",
        }
        for metric_id in AGREEMENT_METRIC_IDS
    )
    clinical = (
        ("structured_clinical", "va_decimal", "visual_acuity", "decimal_acuity"),
        ("structured_clinical", "va_logmar", "visual_acuity", "logMAR"),
        ("structured_clinical", "iop_mmhg", "intraocular_pressure", "mmHg"),
        ("clinical_text", "text_iop_value", "intraocular_pressure", "mmHg"),
        ("clinical_text", "text_visual_acuity_value", "visual_acuity", "decimal_acuity"),
        ("clinical_text", "text_thickness_value", "retinal_thickness", "um"),
        ("clinical_text_hybrid", "ai_rnfl_thickness_value", "retinal_thickness", "um"),
    )
    rows.extend(
        {
            "collection": collection,
            "metric_id": metric_id,
            "domain": domain,
            "input_source": "structured_field" if collection == "structured_clinical" else "clinical_text_evidence_span",
            "unit": unit,
            "algorithm_version": "ophthalmic_quantification.clinical.v0.1.0",
        }
        for collection, metric_id, domain, unit in clinical
    )
    keys = [(str(row["collection"]), str(row["metric_id"])) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate metric catalog key")
    return tuple(rows)


def p003_metric_catalog() -> tuple[dict[str, object], ...]:
    """Return one registry for all calculators currently used by P003."""
    rows = list(metric_catalog())
    rows.extend(
        {"collection": "p003_extended_fundus_43", **row}
        for row in extended_fundus_metric_catalog()
    )
    rows.extend(
        {"collection": "p003_dr_legacy_lesion_10", **row}
        for row in dr_legacy_lesion_metric_catalog()
    )
    rows.extend(
        {"collection": "p003_dr_clinical_83", **row}
        for row in dr_metric_catalog()
    )
    keys = [(str(row["collection"]), str(row["metric_id"])) for row in rows]
    if len(keys) != 326 or len(keys) != len(set(keys)):
        raise ValueError(f"P003 metric catalog contract changed: total={len(keys)}, unique={len(set(keys))}")
    return tuple(rows)
