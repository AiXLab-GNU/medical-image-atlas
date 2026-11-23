from pathlib import Path
import sys
import unittest

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from ophthalmic_quantification.oct_metrics import (  # noqa: E402
    OCT_METRIC_IDS,
    extract_oct_metrics,
)


class OctMetricTest(unittest.TestCase):
    def test_exact_25_metric_contract(self) -> None:
        mask = np.zeros((20, 30), dtype=np.uint8)
        mask[2:6, 3:8] = 1
        mask[8:12, 10:18] = 2
        mask[13:16, 4:12] = 3
        mask[4:8, 21:27] = 4
        mask[17, 2:28] = 5
        metrics = extract_oct_metrics(mask)
        self.assertEqual(tuple(metrics), OCT_METRIC_IDS)
        self.assertEqual(len(metrics), 25)
        self.assertEqual(metrics["irf_area_px"], 20)
        self.assertEqual(metrics["is_os_presence"], 1)

    def test_invalid_oct_label_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "class"):
            extract_oct_metrics(np.array([[9]], dtype=np.uint8))


if __name__ == "__main__":
    unittest.main()
