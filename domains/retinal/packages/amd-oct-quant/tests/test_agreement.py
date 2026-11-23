import unittest

import numpy as np

from amd_oct_quant.agreement import agreement_statistics
from amd_oct_quant.classification_metrics import classification_summary
from amd_oct_quant.segmentation_metrics import confusion_matrix, metrics_from_confusion


class AgreementTests(unittest.TestCase):
    def test_perfect_agreement(self):
        values = np.array([0.0, 1.0, 3.0, 7.0])
        result = agreement_statistics(values, values.copy())
        self.assertEqual(result["ccc"], 1.0)
        self.assertEqual(result["icc_a1"], 1.0)
        self.assertEqual(result["mae"], 0.0)
        self.assertEqual(result["spearman"], 1.0)
        self.assertEqual(result["bland_altman_bias"], 0.0)

    def test_bias_and_shape_guard(self):
        result = agreement_statistics(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0, 3.0]))
        self.assertEqual(result["mae"], 1.0)
        self.assertEqual(result["bland_altman_bias"], 1.0)
        with self.assertRaises(ValueError):
            agreement_statistics(np.zeros(2), np.zeros(3))

    def test_segmentation_confusion(self):
        truth = np.array([[0, 1], [1, 2]], dtype=np.uint8)
        estimate = np.array([[0, 1], [0, 2]], dtype=np.uint8)
        matrix = confusion_matrix(truth, estimate, num_classes=3)
        result = metrics_from_confusion(matrix)
        self.assertEqual(result[1]["true_positive_px"], 1)
        self.assertAlmostEqual(result[1]["dice"], 2 / 3)
        self.assertEqual(result[2]["dice"], 1.0)

    def test_nonordinal_class_excluded_from_qwk(self):
        targets = np.array([0, 1, 2, 3])
        probability = np.eye(4)
        result = classification_summary(targets, probability)
        self.assertEqual(result["macro_f1"], 1.0)
        self.assertEqual(result["qwk_3class_sensitivity"], 1.0)
        self.assertEqual(result["qwk_rows_true_class_0_1_2"], 3)


if __name__ == "__main__":
    unittest.main()
