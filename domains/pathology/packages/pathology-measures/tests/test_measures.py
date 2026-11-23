"""Synthetic checks of the pathology measurement functions."""
from __future__ import annotations

import unittest

import numpy as np

from pathology_measures import REGISTRY, glands, nuclei, texture, tissue


def disk(shape, centre, r):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return np.hypot(yy - centre[0], xx - centre[1]) <= r


def he_patch():
    """Pink stroma, two glands with white lumina, purple nuclei, glass at the right edge."""
    img = np.zeros((200, 260, 3), np.uint8)
    img[:] = (230, 150, 190)                    # eosin-like stroma
    img[:, 230:] = (245, 245, 245)              # glass
    glands_m = disk(img.shape[:2], (60, 60), 30) | disk(img.shape[:2], (140, 150), 35)
    img[glands_m] = (215, 170, 215)
    img[disk(img.shape[:2], (60, 60), 12) | disk(img.shape[:2], (140, 150), 14)] = (250, 250, 250)
    for y in range(20, 190, 14):
        for x in range(20, 220, 14):
            img[disk(img.shape[:2], (y, x), 3)] = (70, 40, 140)
    return img, glands_m


class MeasuresTest(unittest.TestCase):
    def test_registry_functions_exist(self):
        for entry in REGISTRY.values():
            self.assertTrue(callable(entry.load()), entry.function)

    def test_tissue_and_fractions(self):
        img, g = he_patch()
        t = tissue.tissue_mask(img)
        self.assertLess(t[:, 235:].mean(), 0.05)
        self.assertGreater(t[:, :220].mean(), 0.95)
        labels = np.where(g, 2, 7)
        labels[:, 230:] = 0
        frac = tissue.benign_gland_fraction(labels, t).value
        self.assertTrue(10 < frac < 40, frac)
        self.assertEqual(tissue.tissue_area(t, mpp=0.5).unit, 'mm2')
        self.assertAlmostEqual(tissue.pattern_percent(g, g | ~g, 4).value, 100 * g.mean(), delta=0.2)

    def test_glands(self):
        img, g = he_patch()
        self.assertEqual(glands.count(g).value, 2)
        self.assertGreater(glands.circularity(g).value, 0.85)
        self.assertTrue(5 < glands.lumen_fraction(img, g).value < 30)
        self.assertAlmostEqual(glands.lumina_per_gland(img, g).value, 1.0, delta=0.01)

    def test_nuclei(self):
        img, _ = he_patch()
        region = np.ones(img.shape[:2], bool)
        n = nuclei.detect(img, region, mpp=1.0, min_um2=10, max_um2=60)
        self.assertGreater(len(n.props), 100)
        self.assertAlmostEqual(nuclei.mean_area(n).value, 29, delta=10)
        self.assertGreater(nuclei.hematoxylin_od(img, region).value, 0)

    def test_texture(self):
        flat = np.full((80, 80, 3), 128, np.uint8)
        noisy = np.random.default_rng(0).integers(0, 255, (80, 80, 3)).astype(np.uint8)
        region = np.ones((80, 80), bool)
        self.assertLess(texture.glcm_contrast(flat, region).value, texture.glcm_contrast(noisy, region).value)


if __name__ == '__main__':
    unittest.main()
