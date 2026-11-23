"""Registry integrity: every table, key, cross-reference, file and checksum of the retinal atlas."""
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

import check_retinal_atlas_registry as check  # noqa: E402
import retinal_atlas_registry as registry  # noqa: E402


class RegistryTest(unittest.TestCase):
    def test_registry_is_consistent(self):
        errors, _ = check.check()
        self.assertEqual(errors, [])

    def test_every_catalog_table_is_described(self):
        present = {p.name for p in registry.CATALOG.glob('*.csv')}
        self.assertEqual(present, set(check.SCHEMA))
        readme = (registry.CATALOG / 'README.md').read_text(encoding='utf-8')
        for name in check.SCHEMA:
            self.assertIn(f'`{name}`', readme, name)

    def test_builders_read_the_tables(self):
        import build_atlas_masked_figures as masked
        import build_atlas_modality_figures as modality
        import build_measurement_examples as examples
        self.assertEqual(masked.SOURCES, registry.source_records())
        self.assertEqual(set(masked.PAPER_FIGURES), set(registry.provider_figures_for('masked_figures')))
        self.assertEqual(set(modality.PROVIDER_FILES), set(registry.provider_figures_for('modality_figures')))
        self.assertEqual(set(examples.NEW_PROVIDER), set(registry.provider_figures_for('measurement_examples')))

    def test_broken_reference_is_reported(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            for path in registry.CATALOG.glob('*'):
                shutil.copy(path, tmp / path.name)
            target = tmp / 'g_provider_figures_v01.csv'
            rows = list(csv.DictReader(target.open(encoding='utf-8')))
            rows[0]['source_id'] = 'no_such_source'
            with target.open('w', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, rows[0].keys(), lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)
            with mock.patch.object(check, 'CATALOG', tmp):
                errors, _ = check.check()
            self.assertTrue(any("source_id='no_such_source'" in e for e in errors), errors[:5])
        finally:
            shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main()
