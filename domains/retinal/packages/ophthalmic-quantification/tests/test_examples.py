from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.examples import (  # noqa: E402
    build_synthetic_examples,
    write_example_bundle,
)


class ExampleBundleTest(unittest.TestCase):
    def test_every_registered_metric_has_a_synthetic_example(self) -> None:
        bundle = build_synthetic_examples()
        keys = [(row.collection, row.metric_id) for row in bundle]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(sum(row.collection == "fundus_legacy_139" for row in bundle), 139)
        self.assertEqual(sum(row.collection == "oct_mask_25" for row in bundle), 25)
        self.assertTrue(all(row.synthetic_example for row in bundle))
        self.assertTrue(all(row.status in {"computed", "undefined_by_rule"} for row in bundle))

    def test_bundle_writes_self_contained_nonclinical_html(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory)
            result = write_example_bundle(output)
            html = result["html"].read_text(encoding="utf-8")
            self.assertIn("SYNTHETIC · NOT CLINICAL RESULT", html)
            self.assertNotIn("https://", html)
            self.assertNotIn("http://", html)
            self.assertTrue(result["csv"].is_file())
            self.assertTrue(result["disease_map"].is_file())
            self.assertTrue(result["full_relationship_map"].is_file())
            self.assertTrue(result["validation"].is_file())

    def test_wide_table_has_one_top_helper_and_one_native_bottom_scrollbar(self) -> None:
        with TemporaryDirectory() as directory:
            html = write_example_bundle(directory)["html"].read_text(encoding="utf-8")
            self.assertIn('id="table-scroll-top"', html)
            self.assertNotIn('id="table-scroll-bottom"', html)
            self.assertIn('id="table-wrap"', html)
            self.assertIn("table.scrollWidth", html)
            self.assertIn("position:sticky;top:0", html)
            self.assertNotIn("position:sticky;top:60px", html)

    def test_html_exposes_disease_filter_role_and_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            html = write_example_bundle(directory)["html"].read_text(encoding="utf-8")
            self.assertIn('id="disease"', html)
            self.assertIn("질병 연결", html)
            self.assertIn("임상 역할", html)
            self.assertIn("근거 수준", html)
            self.assertIn("단독 진단용 아님", html)

    def test_html_has_interactive_tier_map_lineage_and_table_filter(self) -> None:
        with TemporaryDirectory() as directory:
            html = write_example_bundle(directory)["html"].read_text(encoding="utf-8")
            for identifier in ("tier-map", "lineage-svg", "tier-filter", "metric-table"):
                self.assertIn(f'id="{identifier}"', html)
            for label in ("T1", "T2", "T3", "T4", "Clinician-native", "Model-derived"):
                self.assertIn(label, html)
            self.assertIn("QC·검증은 별도 Analysis registry", html)
            self.assertIn("r.tier===tier.value", html)
            self.assertIn("<th>Tier</th><th>Registry</th>", html)
            self.assertIn('href="ophthalmic_disease_metric_map_v01_ko.html"', html)
            self.assertIn('href="ophthalmic_full_metric_relationship_map_v01_ko.html"', html)


if __name__ == "__main__":
    unittest.main()
