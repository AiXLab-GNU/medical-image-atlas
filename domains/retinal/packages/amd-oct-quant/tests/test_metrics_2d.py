import unittest

import numpy as np

from amd_oct_quant.metrics2d import extract_2d_metrics, metric_dictionary
from amd_oct_quant.palette import CLASS_NAME_TO_ID


class Metric2DTests(unittest.TestCase):
    def test_empty_zero_rules(self):
        metrics = extract_2d_metrics(np.zeros((4, 10), dtype=np.uint8))
        self.assertEqual(metrics["irf_area_px"], 0)
        self.assertEqual(metrics["irf_component_count"], 0)
        self.assertEqual(metrics["irf_largest_component_fraction"], 0.0)
        self.assertEqual(metrics["is_os_preserved_fraction"], 0.0)
        self.assertEqual(metrics["is_os_largest_gap_px"], 10)

    def test_diagonal_pixels_are_one_eight_connected_component(self):
        mask = np.zeros((4, 4), dtype=np.uint8)
        mask[0, 0] = CLASS_NAME_TO_ID["IRF"]
        mask[1, 1] = CLASS_NAME_TO_ID["IRF"]
        metrics = extract_2d_metrics(mask)
        self.assertEqual(metrics["irf_area_px"], 2)
        self.assertEqual(metrics["irf_component_count"], 1)

    def test_multiple_components_and_largest_fraction(self):
        mask = np.zeros((5, 6), dtype=np.uint8)
        mask[0, 0] = CLASS_NAME_TO_ID["PED"]
        mask[3:5, 4:6] = CLASS_NAME_TO_ID["PED"]
        metrics = extract_2d_metrics(mask)
        self.assertEqual(metrics["ped_component_count"], 2)
        self.assertEqual(metrics["ped_area_px"], 5)
        self.assertEqual(metrics["ped_largest_component_fraction"], 0.8)

    def test_is_os_gap_and_central_fraction(self):
        mask = np.zeros((4, 10), dtype=np.uint8)
        mask[2, :] = CLASS_NAME_TO_ID["IS_OS"]
        mask[2, 4:6] = 0
        metrics = extract_2d_metrics(mask)
        self.assertEqual(metrics["is_os_preserved_fraction"], 0.8)
        self.assertEqual(metrics["is_os_largest_gap_px"], 2)
        self.assertEqual(metrics["is_os_central_preserved_fraction"], 0.0)
        self.assertEqual(metrics["is_os_central_preserved"], 0)

    def test_invalid_class_and_dictionary(self):
        with self.assertRaises(ValueError):
            extract_2d_metrics(np.array([[7]], dtype=np.uint8))
        dictionary = metric_dictionary()
        self.assertFalse(dictionary["outcome_dependent"].any())
        self.assertGreaterEqual(len(dictionary), 25)


if __name__ == "__main__":
    unittest.main()
