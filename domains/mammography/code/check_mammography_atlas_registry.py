"""Check the whole mammography atlas registry: keys, cross-references, files, checksums and licence policy.

Every table in ``docs/surveys/mammography_atlas_catalog/`` is listed in ``SCHEMA`` with its primary key and
foreign keys (multi-valued cells use ``;``). Knowledge-table semantics (enumerations, applicability) are
checked by the catalog builder, which this check also runs.

    .venv/bin/python -B domains/mammography/code/check_mammography_atlas_registry.py
"""
from __future__ import annotations

import csv
import sys

import build_mammography_atlas_catalog as catalog_builder
import export_mammography_atlas_registry as export
import mammography_atlas_registry as registry

CATALOG = registry.CATALOG
LICENCES = ('CC BY 2.0', 'CC BY 2.5', 'CC BY 3.0', 'CC BY 4.0', 'CC0 1.0')   # project policy: CC BY 2.0 or later / CC0
VALUE_STATUS = {'ok', 'not_observed', 'not_evaluable', 'reading'}
DOMAINS = {
    'imaging': ('a_imaging_v01.csv', 'imaging_id'), 'anatomy': ('b_anatomy_v01.csv', 'entity_id'),
    'lesion': ('c_lesions_v01.csv', 'entity_id'), 'feature': ('d_features_v01.csv', 'feature_id'),
    'disease': ('e_diseases_v01.csv', 'disease_id'), 'reference': ('sources_v01.csv', 'source_id'),
    'scheme': ('e_grading_schemes_v01.csv', 'scheme_id'), 'image_source': ('g_image_sources_v01.csv', 'source_id'),
    'masked_figure': ('h_masked_figures_v01.csv', 'figure_id'), 'example': ('h_measure_examples_v01.csv', 'example_id'),
}
ITEM = ('anatomy', 'lesion')
TARGET = ('anatomy', 'lesion', 'imaging')
FINDING = ('anatomy', 'lesion', 'feature')
TARGET_LEVEL_ROWS = {'d_applicability_overrides_v01.csv', 'd_feature_applicability_v01.csv'}
SCHEMA = {
    'a_imaging_v01.csv': (['imaging_id'], {'parent_id': (('imaging',), False, False), 'source_ids': (('reference',), True, False)}),
    'b_anatomy_v01.csv': (['entity_id'], {'parent_id': (('anatomy',), False, False), 'best_imaging_ids': (('imaging',), True, False),
                                          'source_ids': (('reference',), True, False)}),
    'c_lesions_v01.csv': (['entity_id'], {'affected_structure_ids': (('anatomy',), True, False),
                                          'best_imaging_ids': (('imaging',), True, False), 'source_ids': (('reference',), True, False)}),
    'bc_observations_v01.csv': (['observation_id'], {'target_id': (ITEM, False, True), 'imaging_id': (('imaging',), False, True),
                                                     'source_ids': (('reference',), True, False)}),
    'd_features_v01.csv': (['feature_id'], {'target_id': (TARGET, False, True), 'imaging_ids': (('imaging',), True, False),
                                            'definition_source_ids': (('reference',), True, False)}),
    'd_common_feature_sets_v01.csv': (['scope', 'class_id', 'feature_id'], {'feature_id': (('feature',), False, True)}),
    'd_applicability_overrides_v01.csv': (['target_id', 'feature_id'], {'target_id': (TARGET, False, True),
                                                                        'feature_id': (('feature',), False, False)}),
    'd_feature_applicability_v01.csv': (['target_id', 'feature_id'], {'target_id': (TARGET, False, True),
                                                                      'feature_id': (('feature',), False, False)}),
    'e_diseases_v01.csv': (['disease_id'], {'parent_id': (('disease',), False, False),
                                            'classification_source_ids': (('reference',), True, False)}),
    'e_disease_findings_v01.csv': (['relation_id'], {'disease_id': (('disease',), False, True), 'finding_id': (FINDING, False, True),
                                                     'classification_source_id': (('reference',), False, False),
                                                     'evidence_source_ids': (('reference',), True, False)}),
    'e_grading_schemes_v01.csv': (['scheme_id'], {'disease_id': (('disease',), False, True), 'imaging_ids': (('imaging',), True, False),
                                                  'source_ids': (('reference',), True, False)}),
    'e_grading_steps_v01.csv': (['step_id'], {'scheme_id': (('scheme',), False, True), 'finding_ids': (FINDING, True, False)}),
    'sources_v01.csv': (['source_id'], {}),
    'g_image_sources_v01.csv': (['source_id'], {}),
    'g_provider_figures_v01.csv': (['file'], {'source_id': (('image_source',), False, True)}),
    'h_masked_figures_v01.csv': (['figure_id'], {'source_id': (('image_source',), False, True)}),
    'h_masked_figure_items_v01.csv': (['figure_id', 'item_id'], {'figure_id': (('masked_figure',), False, True),
                                                                 'item_id': (ITEM, False, True)}),
    'h_measure_examples_v01.csv': (['example_id'], {'source_id': (('image_source',), False, True)}),
    'h_example_layers_v01.csv': (['example_id', 'layer_key'], {'example_id': (('example',), False, True)}),
    'h_example_values_v01.csv': (['example_id', 'layer_key', 'feature_id'], {'example_id': (('example',), False, True),
                                                                             'feature_id': (('feature',), False, True)}),
    'i_feature_implementations_v01.csv': (['feature_id'], {'feature_id': (('feature',), False, True),
                                                           'target_id': (TARGET, False, True)}),
    'i_measure_disease_links_v01.csv': (['feature_id', 'disease_id'], {'feature_id': (('feature',), False, True),
                                                                       'disease_id': (('disease',), False, True),
                                                                       'via_item_id': (ITEM, False, False)}),
    'i_example_coverage_v01.csv': (['feature_id', 'modality'], {'feature_id': (('feature',), False, True),
                                                                'example_id': (('example',), False, False)}),
}


def read(name):
    with (CATALOG / name).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def check():
    errors, warnings = [], []
    present = {p.name for p in CATALOG.glob('*.csv')}
    errors += [f'{n}: table not in SCHEMA' for n in sorted(present - set(SCHEMA))]
    errors += [f'{n}: table missing' for n in sorted(set(SCHEMA) - present)]
    tables = {n: read(n) for n in SCHEMA if n in present}
    keys = {d: {r[col] for r in tables.get(t, [])} for d, (t, col) in DOMAINS.items()}
    for name, (pk, fks) in SCHEMA.items():
        rows = tables.get(name, [])
        seen = set()
        for i, row in enumerate(rows, 2):
            key = tuple(row[c] for c in pk)
            if pk and key in seen:
                errors.append(f'{name}:{i}: duplicate key {key}')
            seen.add(key)
            if pk and any(not v for v in key) and not (name in TARGET_LEVEL_ROWS and row.get('target_id')):
                errors.append(f'{name}:{i}: empty key {key}')
            for col, (domains, multi, required) in fks.items():
                values = [v for v in row[col].split(';') if v] if multi else ([row[col]] if row[col] else [])
                if required and not values:
                    errors.append(f'{name}:{i}: {col} is empty')
                for v in values:
                    if not any(v in keys[d] for d in domains):
                        errors.append(f'{name}:{i}: {col}={v!r} not in {"/".join(domains)}')
    for row in tables.get('g_image_sources_v01.csv', []):
        if row['license'] not in LICENCES:
            errors.append(f"g_image_sources: {row['source_id']} licence {row['license']!r} not allowed")
        path = registry.ROOT / row['resource_path'] if row['resource_path'] else None
        if path and not path.exists():
            warnings.append(f"g_image_sources: {row['source_id']} local data missing at {row['resource_path']}")
    for row in tables.get('h_masked_figures_v01.csv', []):
        for col, sha in (('base_file', 'base_sha256'), ('overlay_file', 'overlay_sha256')):
            path = registry.MASKED_DIR / row[col]
            if not path.is_file():
                errors.append(f"h_masked_figures: {row['figure_id']} missing {row[col]}")
            elif registry.sha256(path) != row[sha]:
                errors.append(f"h_masked_figures: {row['figure_id']} checksum mismatch {row[col]}")
    for row in tables.get('h_measure_examples_v01.csv', []):
        if not (registry.EXAMPLE_DIR / row['base_file']).is_file():
            errors.append(f"h_measure_examples: {row['example_id']} missing {row['base_file']}")
    for row in tables.get('h_example_layers_v01.csv', []):
        if not (registry.EXAMPLE_DIR / row['file']).is_file():
            errors.append(f"h_example_layers: {row['example_id']}/{row['layer_key']} missing {row['file']}")
    impl = {r['feature_id']: r for r in tables.get('i_feature_implementations_v01.csv', [])}
    for row in tables.get('h_example_values_v01.csv', []):
        if row['status'] not in VALUE_STATUS:
            errors.append(f"h_example_values: invalid status {row['status']}")
    layer_fn = {(r['example_id'], r['layer_key']): r['function'] for r in tables.get('h_example_layers_v01.csv', [])}
    for row in tables.get('h_example_values_v01.csv', []):
        fn = layer_fn.get((row['example_id'], row['layer_key']), '')
        if (row['status'] == 'reading') == bool(fn):
            errors.append(f"h_example_values: {row['example_id']}/{row['layer_key']} reading status must match an empty function")
        if fn and row['feature_id'] in impl and impl[row['feature_id']]['function'] == '':
            warnings.append(f"h_example_values: {row['feature_id']} computed in an example but has no registry function")
    tables_kb = catalog_builder.load_tables()
    errors += [f'catalog: {e}' for e in catalog_builder.check_integrity(
        tables_kb, catalog_builder.build_applicability(tables_kb), catalog_builder.measure_registry())]
    expected = export.build_tables()
    for name, rows in expected.items():
        if (CATALOG / name).read_text(encoding='utf-8') != export.render(name, rows):
            errors.append(f'{name}: stale (run export_mammography_atlas_registry.py)')
    return errors, warnings


def main() -> int:
    errors, warnings = check()
    for w in warnings:
        print('WARN', w)
    for e in errors:
        print('ERROR', e, file=sys.stderr)
    print(f'{len(SCHEMA)} tables · {len(errors)} errors · {len(warnings)} warnings')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
