from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.full_metric_relationship_map import (  # noqa: E402
    build_full_metric_relationship_catalog,
    write_full_metric_relationship_map,
)


class FullMetricRelationshipMapTest(unittest.TestCase):
    def test_catalog_contains_every_metric_and_auditable_relationships(self) -> None:
        catalog = build_full_metric_relationship_catalog()
        metrics = catalog["metrics"]
        metric_ids = {metric["id"] for metric in metrics}

        self.assertEqual(len(metrics), 190)
        self.assertEqual(len(metric_ids), 190)
        self.assertEqual(
            catalog["summary"]["tier_counts"],
            {"T1": 3, "T2": 41, "T3": 58, "T4": 9, "ANALYSIS": 79},
        )
        self.assertEqual(
            len(catalog["disease_edges"]),
            sum(len(metric["disease_ids"]) for metric in metrics),
        )
        self.assertTrue(
            all(edge["metric_id"] in metric_ids for edge in catalog["disease_edges"])
        )

        scopes = {edge["scope"] for edge in catalog["cross_tier_edges"]}
        self.assertEqual(scopes, {"T1_T2", "T3_T4"})
        self.assertTrue(
            all(
                edge["relation_type"] == "shared_disease_context"
                and edge["shared_disease_ids"]
                and edge["metric_pair_count"] > 0
                for edge in catalog["cross_tier_edges"]
            )
        )
        self.assertTrue(
            all(edge["relation_type"] == "explicit_lineage" for edge in catalog["lineage_edges"])
        )

    def test_html_is_self_contained_and_has_reciprocal_navigation(self) -> None:
        with TemporaryDirectory() as directory:
            target = write_full_metric_relationship_map(
                Path(directory) / "ophthalmic_full_metric_relationship_map_v01_ko.html"
            )
            html = target.read_text(encoding="utf-8")

        self.assertEqual(html.count('id="full-metric-svg"'), 1)
        self.assertIn("190개 전체 지표 관계 지도", html)
        self.assertIn("window.OPHTHALMIC_FULL_METRIC_RELATIONSHIP_MAP", html)
        self.assertIn('href="ophthalmic_quantitative_metric_examples_v01_ko.html"', html)
        self.assertIn('href="ophthalmic_disease_metric_map_v01_ko.html"', html)
        self.assertIn('href="/"', html)
        self.assertIn("data-metric-node", html)
        self.assertIn("shared_disease_context", html)
        self.assertNotIn("<script src=", html)
        self.assertNotIn("<link rel=", html)


if __name__ == "__main__":
    unittest.main()
