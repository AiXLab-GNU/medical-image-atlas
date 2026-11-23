from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.disease_metric_map import (  # noqa: E402
    build_disease_metric_map_catalog,
    write_disease_metric_map,
)


class DiseaseMetricMapTest(unittest.TestCase):
    def test_catalog_aggregates_only_explicit_disease_metric_links(self) -> None:
        catalog = build_disease_metric_map_catalog()
        self.assertEqual(catalog["summary"]["calculator_total"], 190)
        self.assertEqual(catalog["summary"]["disease_linked_metric_total"], 84)
        self.assertGreaterEqual(len(catalog["diseases"]), 8)
        self.assertTrue(catalog["edges"])
        self.assertTrue(all(edge["count"] == len(edge["metric_ids"]) for edge in catalog["edges"]))
        self.assertTrue(all(family["tier"] in {"T1", "T2", "T3", "T4"} for family in catalog["families"]))

    def test_map_is_one_self_contained_svg_with_reciprocal_navigation(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "ophthalmic_disease_metric_map_v01_ko.html"
            write_disease_metric_map(target)
            html = target.read_text(encoding="utf-8")
            self.assertIn('id="disease-metric-svg"', html)
            self.assertEqual(html.count('id="disease-metric-svg"'), 1)
            self.assertIn("질병–정량지표 한 장 지도", html)
            self.assertIn('href="ophthalmic_quantitative_metric_examples_v01_ko.html"', html)
            self.assertIn('href="/"', html)
            self.assertIn("window.OPHTHALMIC_DISEASE_METRIC_MAP", html)
            self.assertNotIn("<script src=", html)
            self.assertNotIn('<link rel="stylesheet"', html)


if __name__ == "__main__":
    unittest.main()
