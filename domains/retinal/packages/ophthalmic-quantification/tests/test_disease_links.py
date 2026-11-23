from pathlib import Path
import sys
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.catalog import metric_catalog  # noqa: E402
from ophthalmic_quantification.disease_links import (  # noqa: E402
    EVIDENCE_REGISTRY,
    disease_context_catalog,
)


class DiseaseLinkCatalogTest(unittest.TestCase):
    def test_every_metric_has_explicit_disease_context(self) -> None:
        metrics = metric_catalog()
        contexts = disease_context_catalog(metrics)
        metric_keys = {(row["collection"], row["metric_id"]) for row in metrics}
        context_keys = {(row["collection"], row["metric_id"]) for row in contexts}
        self.assertEqual(context_keys, metric_keys)
        self.assertEqual(len(contexts), 190)
        self.assertTrue(all(row["clinical_role"] for row in contexts))
        self.assertTrue(all(row["evidence_level"] for row in contexts))

    def test_specific_metrics_have_conservative_expected_links(self) -> None:
        contexts = {
            (row["collection"], row["metric_id"]): row
            for row in disease_context_catalog(metric_catalog())
        }
        self.assertIn("DR", contexts[("fundus_legacy_139", "tortuosity_index")]["disease_ids"])
        self.assertIn("NAMD", contexts[("oct_mask_25", "irf_area_fraction")]["disease_ids"])
        self.assertIn("DME", contexts[("oct_mask_25", "irf_area_fraction")]["disease_ids"])
        self.assertEqual(contexts[("oct_mask_25", "shrm_presence")]["disease_ids"], ("NAMD",))
        self.assertIn("POAG", contexts[("structured_clinical", "iop_mmhg")]["disease_ids"])
        self.assertIn("POAG", contexts[("clinical_text_hybrid", "ai_rnfl_thickness_value")]["disease_ids"])
        self.assertEqual(contexts[("segmentation_agreement", "dice")]["disease_ids"], ())

    def test_qc_and_validation_metrics_are_not_mislabeled_as_diagnostic(self) -> None:
        for row in disease_context_catalog(metric_catalog()):
            if row["domain"] in {"color_quality", "fov_geometry", "mask_agreement", "reliability"}:
                self.assertEqual(row["disease_ids"], (), row["metric_id"])
                self.assertFalse(row["standalone_diagnostic"], row["metric_id"])

    def test_all_evidence_keys_resolve_to_primary_sources(self) -> None:
        for row in disease_context_catalog(metric_catalog()):
            for evidence_id in row["evidence_ids"]:
                self.assertIn(evidence_id, EVIDENCE_REGISTRY)
                self.assertIn("identifier", EVIDENCE_REGISTRY[evidence_id])
                self.assertIn("url", EVIDENCE_REGISTRY[evidence_id])


if __name__ == "__main__":
    unittest.main()
