from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.atlas import (  # noqa: E402
    build_atlas_catalog,
    write_medical_metric_atlas,
)


class MedicalMetricAtlasTest(unittest.TestCase):
    def test_catalog_covers_all_190_calculators_and_separates_registries(self) -> None:
        catalog = build_atlas_catalog()
        self.assertEqual(catalog["summary"]["calculator_total"], 190)
        self.assertEqual(len(catalog["metrics"]), 190)
        self.assertEqual(
            catalog["summary"]["medical_tier_total"]
            + catalog["summary"]["analysis_registry_total"],
            190,
        )
        self.assertEqual(catalog["summary"]["standalone_diagnostic_total"], 0)
        self.assertTrue(catalog["summary"]["disease_context_complete"])
        self.assertEqual(len({row["id"] for row in catalog["metrics"]}), 190)

    def test_atlas_is_self_contained_and_has_required_exploration_sections(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "atlas.html"
            write_medical_metric_atlas(target)
            html = target.read_text(encoding="utf-8")
            self.assertIn("Ophthalmic Medical Metric Atlas", html)
            for section in ("hierarchy", "diseases", "network", "explorer", "analysis", "evidence"):
                self.assertIn(f'id="{section}"', html)
            self.assertIn("window.OPHTHALMIC_METRIC_ATLAS", html)
            self.assertIn("190", html)
            self.assertNotIn("<script src=", html)
            self.assertNotIn("<link rel=\"stylesheet\"", html)

    def test_every_evidence_link_is_available_in_metric_detail_data(self) -> None:
        catalog = build_atlas_catalog()
        evidence_ids = {row["id"] for row in catalog["evidence"]}
        for metric in catalog["metrics"]:
            self.assertTrue(set(metric["evidence_ids"]).issubset(evidence_ids))


if __name__ == "__main__":
    unittest.main()
