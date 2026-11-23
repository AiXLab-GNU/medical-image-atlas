import csv
from pathlib import Path
import sys
import unittest

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_ROOT = next(parent for parent in PACKAGE_ROOT.parents if (parent / "DOMAIN.yaml").is_file())
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.fundus_metrics import (  # noqa: E402
    FUNDUS_METRIC_IDS,
    REQUIRED_UPSTREAM_VALUES,
    extract_fundus_metrics,
)


def synthetic_fundus() -> tuple[np.ndarray, np.ndarray]:
    size = 160
    yy, xx = np.indices((size, size))
    circle = (xx - 80) ** 2 + (yy - 80) ** 2 <= 72**2
    rgb = np.zeros((size, size, 3), dtype=np.uint8)
    rgb[..., 0][circle] = np.clip(130 + xx[circle] // 3, 0, 255)
    rgb[..., 1][circle] = np.clip(65 + yy[circle] // 4, 0, 255)
    rgb[..., 2][circle] = 35
    vessel = circle & (((xx - 80) % 17 == 0) | ((yy - 80) % 23 == 0))
    return rgb, vessel


class FundusMetricTest(unittest.TestCase):
    def test_catalog_exactly_matches_frozen_e012_dictionary(self) -> None:
        source = DOMAIN_ROOT / "references/e012_session_metric_dictionary.csv"   # frozen copy of P001 E012
        with source.open(encoding="utf-8", newline="") as handle:
            upstream_ids = tuple(row["metric"] for row in csv.DictReader(handle))
        self.assertEqual(len(FUNDUS_METRIC_IDS), 139)
        self.assertEqual(FUNDUS_METRIC_IDS, upstream_ids)

    def test_all_139_metrics_are_deterministic(self) -> None:
        rgb, vessel = synthetic_fundus()
        upstream = {name: float(index) / 10 for index, name in enumerate(REQUIRED_UPSTREAM_VALUES)}
        upstream["mask_failure"] = False
        first = extract_fundus_metrics(rgb, vessel, upstream_values=upstream, strict=True)
        second = extract_fundus_metrics(rgb, vessel, upstream_values=upstream, strict=True)
        self.assertEqual(tuple(first), FUNDUS_METRIC_IDS)
        self.assertEqual(len(first), 139)
        for key in FUNDUS_METRIC_IDS:
            if np.isnan(first[key]):
                self.assertTrue(np.isnan(second[key]), key)
            else:
                self.assertEqual(first[key], second[key], key)

    def test_missing_model_outputs_fail_in_strict_mode(self) -> None:
        rgb, vessel = synthetic_fundus()
        with self.assertRaisesRegex(ValueError, "upstream"):
            extract_fundus_metrics(rgb, vessel, upstream_values={}, strict=True)


if __name__ == "__main__":
    unittest.main()
