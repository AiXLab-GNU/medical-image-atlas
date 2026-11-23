import unittest

import numpy as np

from amd_oct_quant.palette import (
    CLASS_NAME_TO_ID,
    DEFAULT_PALETTE_RGB,
    decode_rgb_mask,
    split_combined_image,
)


class MaskDecoderTests(unittest.TestCase):
    def test_exact_palette(self):
        rgb = DEFAULT_PALETTE_RGB.reshape(1, 6, 3)
        labels, info = decode_rgb_mask(rgb)
        np.testing.assert_array_equal(labels, np.arange(6, dtype=np.uint8).reshape(1, 6))
        self.assertEqual(info.tie_pixels, 0)
        self.assertEqual(info.exact_fraction, 1.0)

    def test_intermediate_colors_follow_nearest(self):
        rgb = np.array([[[254, 0, 0], [0, 0, 254], [245, 6, 245]]], dtype=np.uint8)
        labels, _ = decode_rgb_mask(rgb)
        np.testing.assert_array_equal(
            labels,
            np.array(
                [[CLASS_NAME_TO_ID["SRF"], CLASS_NAME_TO_ID["PED"], CLASS_NAME_TO_ID["IS_OS"]]],
                dtype=np.uint8,
            ),
        )

    def test_tie_uses_lowest_class_id(self):
        # Equal distance to SHRM [255, 255, 0] and IS/OS [255, 0, 255].
        rgb = np.array([[[224, 224, 224]]], dtype=np.uint8)
        labels, info = decode_rgb_mask(rgb)
        self.assertEqual(info.tie_pixels, 1)
        self.assertEqual(int(labels[0, 0]), CLASS_NAME_TO_ID["SHRM"])

    def test_split_and_odd_width_failure(self):
        image = np.zeros((4, 10, 3), dtype=np.uint8)
        left, right = split_combined_image(
            image, expected_half_width=5, expected_height=4
        )
        self.assertEqual(left.shape, (4, 5, 3))
        self.assertEqual(right.shape, (4, 5, 3))
        with self.assertRaises(ValueError):
            split_combined_image(np.zeros((4, 9, 3), dtype=np.uint8), expected_half_width=None)


if __name__ == "__main__":
    unittest.main()
