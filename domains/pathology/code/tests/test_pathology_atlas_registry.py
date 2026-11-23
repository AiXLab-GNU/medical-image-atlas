"""Registry integrity of the pathology atlas: tables, keys, files, checksums and generated tables."""
from __future__ import annotations

import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))

import build_pathology_atlas_catalog as builder  # noqa: E402
import check_pathology_atlas_registry as check  # noqa: E402
import pathology_atlas_registry as registry  # noqa: E402


class RegistryTest(unittest.TestCase):
    def test_registry_is_consistent(self):
        errors, _ = check.check()
        self.assertEqual(errors, [])

    def test_every_table_is_described(self):
        present = {p.name for p in registry.CATALOG.glob('*.csv')}
        self.assertEqual(present, set(check.SCHEMA))
        readme = (registry.CATALOG / 'README.md').read_text(encoding='utf-8')
        for name in check.SCHEMA:
            self.assertIn(f'`{name}`', readme, name)

    def test_only_open_licences(self):
        for row in registry.read('g_image_sources_v01.csv'):
            self.assertIn(row['license'], check.LICENCES)

    def test_every_registry_function_names_a_feature(self):
        features = {r['feature_id'] for r in registry.read('d_features_v01.csv')}
        self.assertLessEqual(set(builder.measure_registry()), features)

    def test_dataset_metadata_reads(self):
        self.assertEqual(len(registry.precise_participants()), 27)
        self.assertAlmostEqual(registry.precise_mpp('sub-02_ses-01'), 0.2433, places=3)
        self.assertGreater(len(registry.sicap_table()), 1000)

    def test_broken_reference_is_reported(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            for path in registry.CATALOG.glob('*'):
                shutil.copy(path, tmp / path.name)
            target = tmp / 'e_disease_findings_v01.csv'
            rows = list(csv.DictReader(target.open(encoding='utf-8')))
            rows[0]['finding_id'] = 'les_no_such_finding'
            with target.open('w', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, rows[0].keys(), lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)
            with mock.patch.object(check, 'CATALOG', tmp):
                errors, _ = check.check()
            self.assertTrue(any('les_no_such_finding' in e for e in errors), errors[:5])
        finally:
            shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main()
