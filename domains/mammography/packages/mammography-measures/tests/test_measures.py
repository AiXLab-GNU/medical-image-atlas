"""Synthetic checks of the mammography measurement functions."""
from __future__ import annotations

import unittest

import numpy as np

from mammography_measures import REGISTRY, breast, calcification, distortion, enhancement, location, mass


def disk(shape, centre, r):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return np.hypot(yy - centre[0], xx - centre[1]) <= r


def phantom():
    """Half-ellipse breast on the left edge with a bright dense core and a mass."""
    h, w = 400, 300
    yy, xx = np.mgrid[0:h, 0:w]
    br = ((yy - 200) / 180.0) ** 2 + (xx / 260.0) ** 2 <= 1
    img = np.where(br, 0.35, 0.0)
    img[br & (((yy - 200) / 90.0) ** 2 + (xx / 140.0) ** 2 <= 1)] = 0.7
    m = disk((h, w), (220, 150), 18)
    img[m] = 0.9
    return img, br, m


class MeasuresTest(unittest.TestCase):
    def test_registry_functions_exist(self):
        for entry in REGISTRY.values():
            self.assertTrue(callable(entry.load()), entry.function)

    def test_breast_geometry(self):
        img, br, _ = phantom()
        geo = breast.geometry(img, 'CC')
        self.assertEqual(geo.chest_side, 'left')
        self.assertGreater(geo.nipple[1], 240)
        self.assertGreater((geo.breast & br).sum() / br.sum(), 0.9)
        pd = breast.percent_density(breast.dense_tissue(img, geo.breast), geo.breast)
        self.assertTrue(10 < pd.value < 60, pd.value)
        self.assertEqual(breast.pnl_length(geo).unit, 'px')

    def test_nipple_is_local_protrusion_not_widest_breast_point(self):
        # The upper breast reaches col 220; the lower nipple tip reaches only 209.
        yy, xx = np.mgrid[:400, :300]
        body = ((yy - 200) / 185.0) ** 2 + (xx / 220.0) ** 2 <= 1
        nipple = (yy - 290) ** 2 + (xx - 195) ** 2 <= 14 ** 2
        for side, mask, want_col in [('left', body | nipple, 209),
                                      ('right', (body | nipple)[:, ::-1], 90)]:
            with self.subTest(side=side):
                row, col = breast.nipple_point(mask, side)
                self.assertAlmostEqual(row, 290, delta=3)
                self.assertAlmostEqual(col, want_col, delta=2)

    def test_nipple_centre_is_inside_the_lobe(self):
        yy, xx = np.mgrid[:400, :300]
        body = ((yy - 200) / 185.0) ** 2 + (xx / 220.0) ** 2 <= 1
        lobe = (yy - 290) ** 2 + (xx - 205) ** 2 <= 16 ** 2
        img = np.where(body, 0.7, 0.0)
        img[lobe & ~body] = 0.2
        row, col = breast.nipple_centre(img, 'left')
        self.assertAlmostEqual(row, 290, delta=4)
        self.assertTrue(195 < col < 221, col)
        self.assertTrue(lobe[int(round(row)), int(round(col))])

    def test_geometry_refines_dim_nipple_tip_in_original_image(self):
        yy, xx = np.mgrid[:400, :300]
        body = ((yy - 200) / 185.0) ** 2 + (xx / 220.0) ** 2 <= 1
        nipple = (yy - 290) ** 2 + (xx - 195) ** 2 <= 14 ** 2
        tip = (yy - 290) ** 2 + (xx - 209) ** 2 <= 6 ** 2
        img = np.where(body | nipple, 0.7, 0.0)
        img[tip & ~(body | nipple)] = 0.06
        geo = breast.geometry(img, 'CC')
        self.assertAlmostEqual(geo.nipple[0], 290, delta=6)
        self.assertTrue(200 < geo.nipple[1] < 216, geo.nipple)   # inside the nipple, not on the body outline

    def test_mass_shape(self):
        img, _, m = phantom()
        self.assertAlmostEqual(mass.size(m).value, 37, delta=2)
        self.assertGreater(mass.circularity(m).value, 0.85)
        self.assertGreater(mass.solidity(m).value, 0.95)
        self.assertLess(mass.radial_sd(m).value, 0.05)
        self.assertEqual(mass.size(m, pixel_mm=0.1).unit, 'mm')

    def test_calcifications(self):
        img = np.full((200, 200), 0.3)
        region = disk(img.shape, (100, 100), 40)
        for r, c in [(80, 90), (95, 100), (110, 110), (100, 120)]:
            img[disk(img.shape, (r, c), 1.5)] = 0.9
        found = calcification.detect(img, region, tophat_px=4)
        self.assertEqual(calcification.count(found).value, 4)
        self.assertIsNotNone(calcification.nn_distance(found).value)

    def test_location(self):
        nip, foot = (200, 280), (200, 0)
        self.assertEqual(location.depth_third((200, 250), nip, foot).value, 'anterior')
        self.assertEqual(location.depth_third((200, 20), nip, foot).value, 'posterior')
        self.assertEqual(location.view_half((150, 200), nip, foot, 'CC').value, 'lateral')
        self.assertEqual(location.view_half((250, 200), nip, foot, 'MLO').value, 'lower')
        self.assertEqual(location.quadrant('lateral', 'upper').value, 'UOQ')
        self.assertEqual(location.clock_position(1, 0, 'R').value, '9:00')
        self.assertEqual(location.clock_position(1, 0, 'L').value, '3:00')
        self.assertEqual(location.clock_position(0, 1, 'L').value, '12:00')

    def test_enhancement(self):
        img = np.full((120, 120), 0.2)
        m = disk(img.shape, (60, 60), 10)
        img[m] = 0.6
        self.assertAlmostEqual(enhancement.intensity_ratio(img, m).value, 3.0, delta=0.3)
        est = enhancement.enhancing_region(img, (60, 60), 25)
        self.assertGreater((est & m).sum() / m.sum(), 0.8)
        self.assertAlmostEqual(enhancement.nme_extent(m).value, 21, delta=2)

    def test_convergence(self):
        h = w = 161
        img = np.zeros((h, w))
        for ang in np.linspace(0, np.pi, 12, endpoint=False):
            for t in np.linspace(-70, 70, 400):
                r, c = int(80 + t * np.sin(ang)), int(80 + t * np.cos(ang))
                img[r, c] = 1.0
        star = distortion.convergence_index(img, (80, 80), 70).value
        noise = distortion.convergence_index(np.random.default_rng(0).random((h, w)), (80, 80), 70).value
        self.assertGreater(star, noise)


if __name__ == '__main__':
    unittest.main()
