from pathlib import Path
import sys
import unittest

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.extended_fundus_metrics import (  # noqa: E402
    FAMILIES,
    METRICS,
    extended_fundus_metric_catalog,
    extract_extended_metrics,
)


def synthetic_case() -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, float]]:
    size = 160
    yy, xx = np.indices((size, size))
    fov = (xx - 80) ** 2 + (yy - 80) ** 2 <= 72 ** 2
    rgb = np.zeros((size, size, 3), np.uint8)
    rgb[fov] = np.stack([
        np.clip(150 + 30 * xx[fov] / size, 0, 255),
        np.clip(90 + 20 * yy[fov] / size, 0, 255),
        np.full(fov.sum(), 55),
    ], axis=1).astype(np.uint8)
    vessel = fov & (
        (np.abs(yy - 80 - 0.25 * (xx - 55)) < 2)
        | (np.abs(yy - 80 + 0.30 * (xx - 55)) < 2)
        | (np.abs(yy - 80) < 2)
    )
    anatomy = fov & (
        ((xx - 42) ** 2 + (yy - 76) ** 2 < 10 ** 2)
        | ((xx - 98) ** 2 + (yy - 83) ** 2 < 8 ** 2)
    )
    border = fov & ~(((xx - 80) ** 2 + (yy - 80) ** 2) <= 65 ** 2)
    top_masks = {
        "anatomy": anatomy,
        "vessel": vessel,
        "fov_border": border,
        "retinal_residual": ~(anatomy | vessel | border),
    }
    landmarks = {
        "disc_x": 42 / 159,
        "disc_y": 76 / 159,
        "fovea_x": 98 / 159,
        "fovea_y": 83 / 159,
    }
    return rgb, top_masks, landmarks


class ExtendedFundusMetricTest(unittest.TestCase):
    def test_catalog_and_output_cover_all_43_metrics(self) -> None:
        rgb, masks, landmarks = synthetic_case()
        metrics, family_masks, qc = extract_extended_metrics(rgb, masks, landmarks)
        self.assertEqual(len(FAMILIES), 8)
        self.assertEqual(len(METRICS), 43)
        self.assertEqual({row["metric_id"] for row in extended_fundus_metric_catalog()}, set(METRICS))
        self.assertEqual(set(metrics), set(METRICS))
        self.assertEqual(set(family_masks), set(FAMILIES))
        self.assertTrue(np.isfinite(list(metrics.values())).all())
        self.assertEqual(qc["metric_finite_fraction"], 1.0)

    def test_extraction_is_deterministic(self) -> None:
        rgb, masks, landmarks = synthetic_case()
        first = extract_extended_metrics(rgb, masks, landmarks)[0]
        second = extract_extended_metrics(rgb, masks, landmarks)[0]
        np.testing.assert_allclose(list(first.values()), list(second.values()), rtol=0, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
