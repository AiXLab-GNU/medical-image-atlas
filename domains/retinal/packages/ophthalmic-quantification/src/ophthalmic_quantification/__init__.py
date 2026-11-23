"""Auditable ophthalmic quantitative metric engine."""

from .atlas import build_atlas_catalog, write_medical_metric_atlas
from .clinical_extraction import (
    extract_clinical_numbers,
    extract_clinical_numbers_hybrid,
    parse_iop,
    parse_visual_acuity,
)
from .catalog import metric_catalog, p003_metric_catalog
from .dr_metrics import (
    DR_DIRECT_METRIC_IDS,
    DR_INTERACTION_METRIC_IDS,
    DR_LEGACY_LESION_METRIC_IDS,
    DR_METRIC_IDS,
    add_dr_prespecified_interactions,
    extract_dr_legacy_lesion_metrics,
    extract_dr_mask_metrics,
)
from .disease_links import disease_context_catalog
from .disease_metric_map import build_disease_metric_map_catalog, write_disease_metric_map
from .dr_grading import (
    DR_GRADING_ASSESSMENT_VERSION,
    default_dr_grading_assessment,
    reconstruct_icdr_grade,
    validate_dr_grading_assessment,
)
from .fundus_metrics import FUNDUS_METRIC_IDS, extract_fundus_metrics
from .extended_fundus_metrics import (
    FAMILIES as EXTENDED_FUNDUS_FAMILIES,
    METRICS as EXTENDED_FUNDUS_METRIC_IDS,
    extract_extended_metrics,
)
from .full_metric_relationship_map import (
    build_full_metric_relationship_catalog,
    write_full_metric_relationship_map,
)
from .mask_metrics import binary_mask_metrics, segmentation_agreement
from .known_lesion_phenomics import (
    KNOWN_DR_LESIONS,
    KNOWN_LESION_MEASUREMENT_IDS,
    extract_known_lesion_bank,
    extract_known_lesion_measurements,
)
from .lesion_annotation import (
    lesion_annotation_catalog,
    quantify_annotation_file,
    quantify_annotation_document,
    rasterize_annotation_document,
    validate_annotation_document,
)
from .oct_metrics import OCT_METRIC_IDS, extract_oct_metrics

__all__ = [
    "FUNDUS_METRIC_IDS",
    "OCT_METRIC_IDS",
    "DR_DIRECT_METRIC_IDS",
    "DR_INTERACTION_METRIC_IDS",
    "DR_LEGACY_LESION_METRIC_IDS",
    "DR_METRIC_IDS",
    "DR_GRADING_ASSESSMENT_VERSION",
    "KNOWN_DR_LESIONS",
    "KNOWN_LESION_MEASUREMENT_IDS",
    "EXTENDED_FUNDUS_FAMILIES",
    "EXTENDED_FUNDUS_METRIC_IDS",
    "add_dr_prespecified_interactions",
    "binary_mask_metrics",
    "build_atlas_catalog",
    "build_disease_metric_map_catalog",
    "build_full_metric_relationship_catalog",
    "disease_context_catalog",
    "default_dr_grading_assessment",
    "extract_clinical_numbers",
    "extract_clinical_numbers_hybrid",
    "extract_dr_mask_metrics",
    "extract_dr_legacy_lesion_metrics",
    "extract_extended_metrics",
    "extract_fundus_metrics",
    "extract_known_lesion_bank",
    "extract_known_lesion_measurements",
    "extract_oct_metrics",
    "metric_catalog",
    "lesion_annotation_catalog",
    "p003_metric_catalog",
    "parse_iop",
    "parse_visual_acuity",
    "reconstruct_icdr_grade",
    "segmentation_agreement",
    "quantify_annotation_document",
    "quantify_annotation_file",
    "rasterize_annotation_document",
    "validate_annotation_document",
    "validate_dr_grading_assessment",
    "write_medical_metric_atlas",
    "write_disease_metric_map",
    "write_full_metric_relationship_map",
]

__version__ = "0.4.0"
