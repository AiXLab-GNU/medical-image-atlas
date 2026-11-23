"""Synthetic checks of the pathology measurement functions."""
from __future__ import annotations

import unittest

import numpy as np

from pathology_measures import REGISTRY, glands, grading, ihc, nuclei, register, stain, texture, tissue


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

    def test_segment_glands(self):
        img = np.zeros((200, 260, 3), np.uint8)
        img[:] = (235, 165, 200)                                    # stroma without nuclei
        g = disk(img.shape[:2], (60, 60), 30) | disk(img.shape[:2], (140, 170), 35)
        img[g] = (150, 90, 170)                                     # haematoxylin-rich epithelium
        img[disk(img.shape[:2], (60, 60), 12) | disk(img.shape[:2], (140, 170), 14)] = (250, 250, 250)
        seg = glands.segment_glands(img, np.ones(img.shape[:2], bool), sigma_um=3.0)
        self.assertEqual(glands.count(seg).value, 2)
        self.assertGreater((seg & g).sum() / g.sum(), 0.7)

    def test_nuclei(self):
        img, _ = he_patch()
        region = np.ones(img.shape[:2], bool)
        n = nuclei.detect(img, region, mpp=1.0, min_um2=10, max_um2=60)
        self.assertGreater(len(n.props), 100)
        self.assertAlmostEqual(nuclei.mean_area(n).value, 29, delta=10)
        self.assertGreater(nuclei.hematoxylin_od(img, region).value, 0)

    def test_grading(self):
        self.assertEqual(grading.gleason_from_areas({3: 70, 4: 30}).value, '3+4')
        self.assertEqual(grading.gleason_from_areas({4: 80, 3: 18, 5: 2}).value, '4+5')     # biopsy: highest remaining
        self.assertEqual(grading.gleason_from_areas({4: 97, 3: 3}, specimen='prostatectomy').value, '4+4')
        self.assertEqual(grading.gleason_from_areas({3: 100}).value, '3+3')
        self.assertEqual(grading.gleason_from_areas({5: 99, 4: 1}).value, '5+5')                # lower minor < 5 %: ignored
        self.assertEqual(grading.gleason_from_areas({5: 90, 4: 10}).value, '5+4')
        self.assertEqual(grading.gleason_from_areas({4: 98, 5: 2}).value, '4+5')                # higher minor: any amount
        self.assertEqual(grading.gleason_from_areas({}).status, 'not_observed')
        self.assertEqual([grading.grade_group(s).value for s in ('3+3', '3+4', '4+3', '4+4', '4+5')], [1, 2, 3, 4, 5])
        cats = [0, 1, 2]
        self.assertAlmostEqual(grading.kappa([0, 1, 2, 2], [0, 1, 2, 2], cats), 1.0)
        self.assertLess(grading.kappa([0, 1, 2, 2], [2, 2, 0, 1], cats, 'quadratic'), 0)

    def test_ihc(self):
        img = np.full((120, 120, 3), 240, np.uint8)
        gland = disk(img.shape[:2], (60, 60), 30)
        rim = gland & ~disk(img.shape[:2], (60, 60), 26)
        img[rim] = (120, 75, 40)                                   # brown basal rim
        img[disk(img.shape[:2], (60, 60), 15)] = (225, 90, 160)   # pink-red AMACR centre
        cov = ihc.basal_coverage(img, gland)
        self.assertGreater(cov.value, 10)
        self.assertEqual(ihc.basal_coverage(np.full((120, 120, 3), 240, np.uint8), gland).value, 0.0)
        frag = ihc.basal_fragments(img, gland, mpp=0.5)
        self.assertGreater(frag.value, 0)
        self.assertTrue(ihc.basal_cell_presence(frag).value)
        broken = img.copy()
        yy, xx = np.mgrid[:120, :120]
        broken[rim & ((np.arctan2(yy - 60, xx - 60) * 4 / np.pi).astype(int) % 2 == 0)] = 240   # patchy rim
        self.assertGreater(ihc.basal_fragments(broken, gland, mpp=0.5).value, frag.value)       # more, separate fragments
        self.assertFalse(ihc.basal_cell_presence(ihc.basal_fragments(np.full((120, 120, 3), 240, np.uint8), gland, mpp=0.5)).value)
        self.assertTrue(ihc.amacr_positivity(ihc.amacr_fraction(img, gland)).value)

    def test_stain(self):
        img, _ = he_patch()
        out = stain.macenko_normalise(img)
        self.assertEqual(out.shape, img.shape)
        self.assertGreater(out[:, 240:].mean(), 220)                             # glass stays bright
        self.assertTrue((stain.macenko_normalise(np.full((50, 50, 3), 250, np.uint8)) == 250).all())   # nothing to fit

    def test_register(self):
        rng = np.random.default_rng(1)
        he = np.full((400, 400, 3), 250, np.uint8)
        yy, xx = np.mgrid[:400, :400]
        core1 = (np.abs((yy - 120) - 0.3 * (xx - 200)) < 18) & (xx > 60) & (xx < 340)
        core2 = disk((400, 400), (290, 150), 45) | disk((400, 400), (300, 250), 30)
        he[core1 | core2] = (200, 120, 180)
        ihc_img = np.full((400, 400, 3), 250, np.uint8)
        moved = np.zeros((400, 400), bool)
        A = register._matrix(12.0, False)
        t = np.array([15.0, -10.0])
        moved = register.warp_to(core1 | core2, (400, 400), np.linalg.inv(A), -np.linalg.inv(A) @ t)
        ihc_img[moved] = (170, 190, 220)
        res = register.align(he, 16.0, ihc_img, 16.0, grid_um=16.0, min_core_mm2=0.01)
        self.assertGreater(res['dice_global'], 0.85)
        self.assertGreater(res['dice_global'], res['dice_before'])
        self.assertLess(abs(res['global']['angle'] - 12.0) % 360, 3.0)
        del rng

    def test_texture(self):
        flat = np.full((80, 80, 3), 128, np.uint8)
        noisy = np.random.default_rng(0).integers(0, 255, (80, 80, 3)).astype(np.uint8)
        region = np.ones((80, 80), bool)
        self.assertLess(texture.glcm_contrast(flat, region).value, texture.glcm_contrast(noisy, region).value)


if __name__ == '__main__':
    unittest.main()
