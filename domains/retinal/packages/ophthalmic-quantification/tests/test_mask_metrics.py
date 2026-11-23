from pathlib import Path
import sys
import unittest

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.mask_metrics import (  # noqa: E402
    binary_mask_metrics,
    segmentation_agreement,
)


class MaskMetricTest(unittest.TestCase):
    def test_binary_mask_geometry_and_spacing(self) -> None:
        mask = np.zeros((10, 10), dtype=bool)
        mask[2:5, 3:7] = True
        metrics = binary_mask_metrics(mask, pixel_spacing=(0.01, 0.02))
        self.assertEqual(metrics["presence"], 1)
        self.assertEqual(metrics["area_px"], 12)
        self.assertAlmostEqual(metrics["area_fraction"], 0.12)
        self.assertAlmostEqual(metrics["area_physical"], 0.0024)
        self.assertEqual(metrics["component_count"], 1)

    def test_empty_agreement_has_explicit_zero_rule(self) -> None:
        empty = np.zeros((4, 4), dtype=bool)
        metrics = segmentation_agreement(empty, empty)
        self.assertEqual(metrics["dice"], 1.0)
        self.assertEqual(metrics["iou"], 1.0)
        self.assertEqual(metrics["both_empty"], 1)

    def test_invalid_shapes_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "2D"):
            binary_mask_metrics(np.zeros((2, 2, 2)))
        with self.assertRaisesRegex(ValueError, "identical"):
            segmentation_agreement(np.zeros((2, 2)), np.zeros((3, 3)))


if __name__ == "__main__":
    unittest.main()
