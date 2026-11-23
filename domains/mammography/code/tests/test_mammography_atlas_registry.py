"""Registry integrity of the mammography atlas: tables, keys, files, checksums and generated tables."""
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

import build_mammography_atlas_catalog as builder  # noqa: E402
import check_mammography_atlas_registry as check  # noqa: E402
import mammography_atlas_registry as registry  # noqa: E402


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

    def test_dmid_metadata_parses(self):
        rows = registry.dmid_findings()
        self.assertGreater(len(rows), 500)
        self.assertTrue({'CC', 'MLO'} >= {r['view'] for r in rows})

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
