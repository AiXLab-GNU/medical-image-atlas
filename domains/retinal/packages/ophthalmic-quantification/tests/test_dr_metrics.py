from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.catalog import p003_metric_catalog  # noqa: E402
from ophthalmic_quantification.dr_metrics import (  # noqa: E402
    DR_DIRECT_METRIC_IDS,
    DR_INTERACTION_METRIC_IDS,
    DR_LEGACY_LESION_METRIC_IDS,
    DR_METRIC_IDS,
    DR_REQUIRED_MASKS,
    add_dr_prespecified_interactions,
    dr_metric_catalog,
    extract_dr_legacy_lesion_metrics,
    extract_dr_mask_metrics,
)


def synthetic_case() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    size = 128
    yy, xx = np.indices((size, size))
    fov = (xx - 64) ** 2 + (yy - 64) ** 2 <= 58 ** 2
    rgb = np.zeros((size, size, 3), dtype=np.uint8)
    rgb[fov] = (130, 80, 45)
    masks = {name: np.zeros((size, size), dtype=bool) for name in DR_REQUIRED_MASKS}
    masks["optic_disc"] = (xx - 35) ** 2 + (yy - 62) ** 2 <= 7 ** 2
    masks["macula"] = (xx - 82) ** 2 + (yy - 66) ** 2 <= 3 ** 2
    masks["vessel"] = fov & (
        (np.abs(yy - 64 - 0.20 * (xx - 35)) < 1.5)
        | (np.abs(yy - 64 + 0.28 * (xx - 35)) < 1.5)
    )
    masks["hemorrhage"][45:51, 53:60] = True
    masks["hemorrhage"][82:88, 88:94] = True
    masks["microaneurysm"][58:61, 75:78] = True
    masks["hard_exudate"][65:72, 78:87] = True
    masks["cotton_wool_spot"][50:56, 39:47] = True
    masks["neovascularization"][58:63, 38:45] = True
    masks["drusen"][73:76, 73:76] = True
    return rgb, masks


class DiabeticRetinopathyMetricTest(unittest.TestCase):
    def test_legacy_e019_lesion_metrics_cover_all_ten_values(self) -> None:
        rgb, masks = synthetic_case()
        metrics = extract_dr_legacy_lesion_metrics(rgb, masks)
        self.assertEqual(tuple(metrics), DR_LEGACY_LESION_METRIC_IDS)
        self.assertEqual(len(metrics), 10)
        self.assertTrue(np.isfinite(list(metrics.values())).all())
        self.assertGreater(metrics["lesion_union_area_fraction"], 0)
        self.assertGreaterEqual(metrics["lesion_union_component_count"], 1)

    def test_direct_catalog_and_output_cover_78_metrics(self) -> None:
        rgb, masks = synthetic_case()
        metrics, registry, qc = extract_dr_mask_metrics(rgb, masks)
        self.assertEqual(len(DR_DIRECT_METRIC_IDS), 78)
        self.assertEqual(len(metrics), 78)
        self.assertEqual(set(metrics), set(DR_DIRECT_METRIC_IDS))
        self.assertEqual({row["metric"] for row in registry}, set(metrics))
        self.assertTrue(np.isfinite(list(metrics.values())).all())
        self.assertEqual(qc["metric_finite_fraction"], 1.0)

    def test_five_interactions_complete_77_clinical_plus_six_controls(self) -> None:
        rgb, masks = synthetic_case()
        direct = extract_dr_mask_metrics(rgb, masks)[0]
        upstream = {
            "hemorrhage_area_fraction": 0.02,
            "vessel_branch_tortuosity": 1.12,
            "microaneurysm_area_fraction": 0.004,
            "vessel_fractal_dimension": 1.41,
            "e029_background_luminance_cv": 0.16,
        }
        interactions = add_dr_prespecified_interactions(direct, upstream)
        self.assertEqual(set(interactions), set(DR_INTERACTION_METRIC_IDS))
        self.assertTrue(np.isfinite(list(interactions.values())).all())
        series_interactions = add_dr_prespecified_interactions(
            pd.Series({**direct, **upstream}), pd.Series({**direct, **upstream})
        )
        self.assertEqual(interactions, series_interactions)
        self.assertEqual(len(DR_METRIC_IDS), 83)
        self.assertEqual(len(dr_metric_catalog()), 83)
        self.assertEqual(sum(row["role"] == "negative_control" for row in dr_metric_catalog()), 6)

    def test_extraction_is_deterministic_and_empty_lesions_follow_zero_rule(self) -> None:
        rgb, masks = synthetic_case()
        first = extract_dr_mask_metrics(rgb, masks)[0]
        second = extract_dr_mask_metrics(rgb, masks)[0]
        np.testing.assert_allclose(list(first.values()), list(second.values()), rtol=0, atol=0)
        empty = {name: value.copy() for name, value in masks.items()}
        for name in ("hemorrhage", "microaneurysm", "hard_exudate", "cotton_wool_spot"):
            empty[name][:] = False
        values = extract_dr_mask_metrics(rgb, empty)[0]
        self.assertEqual(values["red_lesion_area_fraction"], 0.0)
        self.assertEqual(values["lesion_type_diversity"], 0.0)
        self.assertEqual(values["hemorrhage_expert_component_count"], 0.0)

    def test_invalid_masks_fail_closed(self) -> None:
        rgb, masks = synthetic_case()
        missing = dict(masks)
        del missing["vessel"]
        with self.assertRaisesRegex(ValueError, "missing DR masks"):
            extract_dr_mask_metrics(rgb, missing)
        wrong_shape = dict(masks)
        wrong_shape["vessel"] = np.zeros((8, 8), dtype=bool)
        with self.assertRaisesRegex(ValueError, "differs from rgb"):
            extract_dr_mask_metrics(rgb, wrong_shape)

    def test_unified_p003_catalog_has_326_unique_calculators(self) -> None:
        catalog = p003_metric_catalog()
        keys = {(row["collection"], row["metric_id"]) for row in catalog}
        self.assertEqual(len(catalog), 326)
        self.assertEqual(len(keys), 326)
        self.assertEqual(sum(row["collection"] == "p003_extended_fundus_43" for row in catalog), 43)
        self.assertEqual(sum(row["collection"] == "p003_dr_legacy_lesion_10" for row in catalog), 10)
        self.assertEqual(sum(row["collection"] == "p003_dr_clinical_83" for row in catalog), 83)


if __name__ == "__main__":
    unittest.main()
