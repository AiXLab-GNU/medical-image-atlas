"""Synthetic checks: each family returns known values on constructed inputs."""
import csv
import math
from pathlib import Path
import unittest

import numpy as np

from retinal_measures import REGISTRY, Spacing
from retinal_measures import atrophy, choroid, image, lesions, oct_layers, oct_lesions, octa, optic_disc, vessels

PROJECT = Path(__file__).resolve().parents[3]
FEATURES = PROJECT / 'docs/surveys/retinal_atlas_catalog/d_features_v01.csv'


def disk(shape, centre, radius):
    rr, cc = np.mgrid[0:shape[0], 0:shape[1]]
    return np.hypot(rr - centre[0], cc - centre[1]) <= radius


class RegistryTest(unittest.TestCase):
    def test_registry_ids_exist_and_functions_load(self):
        with FEATURES.open(encoding='utf-8') as handle:
            rows = {r['feature_id']: r for r in csv.DictReader(handle)}
        for fid, entry in REGISTRY.items():
            with self.subTest(feature=fid):
                self.assertIn(fid, rows)
                self.assertEqual(rows[fid]['feature_role'], 'measurement')
                self.assertTrue(callable(entry.load()))


class LesionTest(unittest.TestCase):
    def test_count_area_and_empty(self):
        m = disk((100, 100), (30, 30), 5) | disk((100, 100), (70, 70), 8)
        self.assertEqual(lesions.count(m).value, 2)
        area = lesions.area(m, spacing=Spacing(0.01, 0.01))
        self.assertAlmostEqual(area.value, (m.sum()) * 1e-4)
        self.assertEqual(area.unit, 'mm2')
        self.assertEqual(lesions.presence(np.zeros((10, 10))).status, 'not_observed')

    def test_quadrant_counts_follow_disc_side(self):
        fovea, disc = (50, 50), (50, 90)  # disc to the right: nasal is right
        m = disk((100, 100), (20, 60), 2) | disk((100, 100), (80, 40), 2)
        q = lesions.quadrant_counts(m, fovea, disc).value
        self.assertEqual(q['superonasal'], 1)
        self.assertEqual(q['inferotemporal'], 1)
        self.assertEqual(sum(q.values()), 2)

    def test_atrophy_growth_sqrt(self):
        a0, a1 = disk((200, 200), (100, 100), 20), disk((200, 200), (100, 100), 40)
        rate = atrophy.growth_rate(a0, a1, interval_years=2)
        self.assertAlmostEqual(rate.value, (math.sqrt(a1.sum()) - math.sqrt(a0.sum())) / 2)


class VesselTest(unittest.TestCase):
    def test_straight_line_tortuosity_and_fractal(self):
        m = np.zeros((128, 128), bool)
        m[64, 10:118] = True
        self.assertAlmostEqual(vessels.tortuosity(m).value, 1.0, places=2)
        self.assertAlmostEqual(vessels.fractal_dimension(m).value, 1.0, delta=0.15)

    def test_knudtson_formula(self):
        self.assertAlmostEqual(vessels.knudtson_equivalent([10, 10], kind='artery'), 0.88 * math.hypot(10, 10))
        self.assertAlmostEqual(vessels.knudtson_equivalent([10, 10], kind='vein'), 0.95 * math.hypot(10, 10))

    def test_caliber_of_band(self):
        m = np.zeros((60, 100), bool)
        m[25:32, 5:95] = True
        self.assertAlmostEqual(vessels.caliber(m).value['median'], 7, delta=1)


class DiscTest(unittest.TestCase):
    def test_cdr_rim_and_tilt(self):
        d, c = disk((200, 200), (100, 100), 40), disk((200, 200), (100, 100), 20)
        self.assertAlmostEqual(optic_disc.cup_disc_ratio(d, c).value, 0.5, delta=0.03)
        self.assertEqual(optic_disc.rim_area(d, c).value, (d & ~c).sum())
        self.assertAlmostEqual(optic_disc.tilt_ratio(d).value, 1.0, delta=0.05)
        self.assertEqual(optic_disc.rim_notch(d, c).status, 'not_observed')

    def test_disc_fovea_and_rnfl_arc(self):
        dist, angle = optic_disc.disc_fovea_geometry((100, 200), (110, 100), disc_diameter_px=40)
        self.assertAlmostEqual(dist.value, math.hypot(10, 100) / 40)
        self.assertGreater(angle.value, 0)
        profile = np.full(360, 100.0)
        profile[10:40] = 50
        self.assertAlmostEqual(optic_disc.rnfl_defect_angle(profile, normal_um=100).value, 30)
        ilm = np.array([[0.0, c] for c in np.linspace(-500, 500, 101)])
        self.assertAlmostEqual(optic_disc.bmo_mrw([(300.0, 0.0)], [ilm]).value, 300.0)


class OctTest(unittest.TestCase):
    def setUp(self):
        self.spacing = Spacing(x_mm=0.05, y_mm=0.05, z_um=4.0)
        shape = (121, 121)
        self.centre = (60, 60)
        self.surfaces = {'ILM': np.full(shape, 100.0), 'RNFL_GCL': np.full(shape, 110.0),
                         'IPL_INL': np.full(shape, 130.0), 'RPE': np.full(shape, 165.0),
                         'BM': np.full(shape, 170.0), 'CSI': np.full(shape, 245.0)}

    def test_flat_retina_thickness_and_volume(self):
        cst = oct_layers.central_subfield_thickness(self.surfaces, self.centre, spacing=self.spacing)
        self.assertAlmostEqual(cst.value, 280.0)
        subfields = oct_layers.etdrs_thickness(self.surfaces, self.centre, spacing=self.spacing).value
        self.assertEqual(len(subfields), 9)
        self.assertTrue(all(abs(v - 280) < 1e-6 for v in subfields.values()))
        vol = oct_layers.macular_volume(self.surfaces, self.centre, spacing=self.spacing).value
        self.assertAlmostEqual(vol, math.pi * 9 * 0.28, delta=0.05)
        self.assertAlmostEqual(oct_layers.subfoveal_choroid_thickness(self.surfaces, self.centre, spacing=self.spacing).value, 300)
        self.assertEqual(oct_layers.layer_order(self.surfaces).value, 'preserved')

    def test_foveal_pit_and_ez_gap(self):
        x = np.arange(121)
        ilm = 100 + 20 * np.exp(-((x - 60) / 10.0) ** 2)
        self.assertEqual(oct_layers.foveal_contour(ilm, spacing=self.spacing).value, 'pit')
        self.assertEqual(oct_layers.foveal_contour(np.full(121, 100.0), spacing=self.spacing).value, 'shallow')
        ez = np.ones((3, 100), bool)
        ez[1, 40:50] = False
        area, fraction, width = oct_layers.ez_preserved(ez, spacing=self.spacing)
        self.assertAlmostEqual(fraction.value, 290 / 300)
        self.assertAlmostEqual(width.value, 10 * 50)

    def test_fluid_volume_height_and_centre(self):
        m = np.zeros((11, 50, 40), bool)
        m[4:7, 20:30, 15:25] = True
        vol = oct_lesions.volume(m, spacing=self.spacing)
        self.assertAlmostEqual(vol.value, 300 * 0.0025 * 4 / 1000)
        self.assertAlmostEqual(oct_lesions.height(m, spacing=self.spacing).value, 40)
        self.assertAlmostEqual(oct_lesions.lateral_diameter(m, spacing=self.spacing).value, 500)
        self.assertTrue(oct_lesions.center_involvement(m, (5, 20), spacing=self.spacing).value)
        self.assertEqual(oct_lesions.lesion_count(m).value, 1)

    def test_mnv_depth_category(self):
        surfaces = {'ILM': np.full((1, 40), 5.0), 'EZ': np.full((1, 40), 30.0),
                    'RPE': np.full((1, 40), 35.0), 'BM': np.full((1, 40), 38.0), 'CSI': np.full((1, 40), 60.0)}
        m = np.zeros((50, 40), bool)
        m[36:38, 10:20] = True
        self.assertEqual(oct_lesions.depth_category(m, surfaces).value, 'sub_rpe')


class OctaTest(unittest.TestCase):
    def test_faz_circularity_and_area(self):
        faz = disk((200, 200), (100, 100), 30)
        self.assertGreater(octa.faz_shape(faz).value, 0.9)
        self.assertEqual(octa.faz_area(faz).value, faz.sum())

    def test_flow_deficit_and_nonperfusion(self):
        rng = np.random.default_rng(0)
        slab = rng.uniform(0.6, 1.0, (100, 100))
        slab[40:60, 40:60] = 0.0
        fd = octa.flow_deficit(slab).value
        self.assertGreater(fd, 0.03)
        npa, index = octa.nonperfusion(disk((100, 100), (50, 50), 10))
        self.assertAlmostEqual(index.value, npa.value / 10000)


class ChoroidImageTest(unittest.TestCase):
    def test_cvi_detects_dark_lumens(self):
        rng = np.random.default_rng(1)
        img = rng.normal(0.8, 0.02, (100, 120))
        for c in range(10, 120, 20):
            img[60:70, c:c + 8] = 0.1
        bm, csi = np.full(120, 50.0), np.full(120, 90.0)
        cvi = choroid.vascularity_index(img, bm, csi).value
        self.assertGreater(cvi, 0.05)
        self.assertLess(cvi, 0.6)
        self.assertEqual(choroid.large_vessel_diameter(img, bm, csi).status, 'ok')

    def test_image_descriptors_run(self):
        rgb = np.zeros((64, 64, 3))
        rgb[disk((64, 64), (32, 32), 28)] = [0.8, 0.4, 0.2]
        self.assertAlmostEqual(image.color_stats(rgb).value['r']['mean'], 0.8)
        self.assertIn('lbp_entropy', image.texture(rgb).value)
        self.assertIn('sharpness', image.quality(rgb).detail)


if __name__ == '__main__':
    unittest.main()
