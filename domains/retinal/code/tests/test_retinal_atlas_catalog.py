"""Integrity and semantic checks for the retinal atlas survey tables (A–F)."""
from __future__ import annotations

import copy
import csv
import sys
import unittest
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))

import build_retinal_atlas_catalog as builder  # noqa: E402


def written(name):
    with (builder.CATALOG / name).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


class RetinalAtlasCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = builder.load_tables()
        cls.rules = builder.read_table('f_mapping_rules_v01.csv')
        cls.sources = builder.registered_sources()
        cls.f_rows = builder.map_sources(cls.sources, cls.rules)
        cls.applicability = builder.build_applicability(cls.tables)

    def errors_with(self, f_rows=None, tables=None):
        tables = tables or self.tables
        return builder.check_integrity(tables, f_rows or self.f_rows, builder.build_applicability(tables))

    def by_id(self, collection, measurement):
        return next(r for r in self.f_rows
                    if r['collection'] == collection and r['source_measurement_id'] == measurement)

    def test_identifiers_targets_and_outputs_are_consistent(self):
        self.assertEqual(self.errors_with(), [])

    def test_every_registered_source_is_preserved_once(self):
        counts = {}
        for row in self.f_rows:
            counts[row['source_name']] = counts.get(row['source_name'], 0) + 1
        self.assertEqual(counts, {'package_p003_metric_catalog': 326,
                                  'package_known_lesion_phenomics': 140,
                                  'e118_hierarchical_feature_registry': 178})

    def test_e118_original_identifiers_and_definitions_are_preserved(self):
        with builder.E118_REGISTRY.open(encoding='utf-8', newline='') as handle:
            registry = {r['measurement_id']: r for r in csv.DictReader(handle)}
        rows = [r for r in self.f_rows if r['collection'] == 'e118_registry']
        self.assertEqual({r['source_record_id'] for r in rows}, set(registry))
        for row in rows:
            source = registry[row['source_record_id']]
            self.assertEqual(row['source_concept_id'], source['concept_id'])
            self.assertEqual(row['source_definition_sha256'], source['definition_sha256'])
            self.assertEqual(row['source_region'], source['region'])
            self.assertEqual(row['source_derived_from'], source['derived_from'])

    def test_reviewed_mismatches_now_map_to_matching_properties(self):
        expected = {('fundus_legacy_139', 'skeleton_pixel_count'): ('ft_vessel_pixel_count', 'count'),
                    ('e118_registry', 'v_path_length_mean'): ('ft_vessel_path_length', 'length'),
                    ('oct_mask_25', 'ped_presence'): ('ft_lesion_generic_presence', 'presence')}
        for key, (feature, output) in expected.items():
            row = self.by_id(*key)
            self.assertEqual((row['feature_id'], row['output_type']), (feature, output))

    def test_pooled_hemorrhage_never_resolves_to_dot_blot(self):
        feature_target = {r['feature_id']: r['target_id'] for r in self.tables['d']}
        for row in self.f_rows:
            if row['target_id'] == 'les_hemorrhage_pooled' and row['feature_id']:
                self.assertNotEqual(feature_target[row['feature_id']], 'les_hemorrhage_dot_blot')

    def test_checker_rejects_target_and_output_mismatches(self):
        broken = copy.deepcopy(self.f_rows)
        hemorrhage = next(r for r in broken if r['source_measurement_id'] == 'hemorrhage_area_fraction')
        hemorrhage['feature_id'] = 'ft_hem_area'
        presence = next(r for r in broken if r['source_measurement_id'] == 'ped_presence')
        presence['feature_id'] = 'ft_lesion_generic_count'
        messages = '\n'.join(self.errors_with(f_rows=broken))
        self.assertIn('hemorrhage_area_fraction: target les_hemorrhage_pooled differs', messages)
        self.assertIn('ped_presence: output presence incompatible', messages)

    def test_component_counts_are_not_clinical_counts(self):
        for row in self.f_rows:
            if row['source_measurement_id'].endswith('component_count'):
                with self.subTest(measurement=row['source_measurement_id']):
                    self.assertNotEqual(row['relation_type'], 'same_definition')
                    self.assertNotEqual(row['feature_id'], 'ft_hem_count_quadrant')

    def test_quadrant_occupancy_is_only_a_proxy_for_421_counts(self):
        for row in self.f_rows:
            if row['source_measurement_id'] in {'quadrant_occupancy', 'red_lesion_quadrants_occupied'}:
                self.assertEqual(row['relation_type'], 'proxy')

    def test_no_rule_claims_confirmed_equivalence(self):
        self.assertFalse(any(r['relation_type'] == 'same_definition' for r in self.f_rows))
        self.assertTrue(all(r['mapping_status'] == 'unreviewed_rule_candidate' for r in self.f_rows))

    def test_every_structure_and_lesion_has_an_applicability_status(self):
        covered = {r['target_id'] for r in self.applicability}
        for key in ('b', 'c'):
            for entity in self.tables[key]:
                self.assertIn(entity['entity_id'], covered)

    def test_layers_receive_explicit_layer_features(self):
        applied = {(r['target_id'], r['feature_id']) for r in self.applicability}
        for layer in ('ana_gcl', 'ana_ipl', 'ana_inl', 'ana_opl'):
            self.assertIn((layer, 'ft_layer_thickness_generic'), applied)

    def test_relations_without_evidence_are_marked(self):
        for row in self.tables['ef']:
            if not row['evidence_source_ids']:
                self.assertEqual(row['review_status'], 'needs_source', row['relation_id'])

    def test_web_data_matches_current_tables(self):
        import json
        expected = builder.export_web_data(self.tables, self.applicability, self.f_rows)
        written_payload = json.loads(builder.WEB_DATA.read_text(encoding='utf-8'))
        self.assertEqual(written_payload, json.loads(json.dumps(expected)))

    def test_written_outputs_match_current_sources(self):
        self.assertEqual(written('f_existing_measurements_v01.csv'),
                         [{k: r[k] for k in builder.F_COLUMNS} for r in self.f_rows])
        columns = ('target_id', 'feature_id', 'applicability', 'basis', 'note_ko')
        self.assertEqual(written('d_feature_applicability_v01.csv'),
                         [{k: r[k] for k in columns} for r in self.applicability])


if __name__ == '__main__':
    unittest.main()
