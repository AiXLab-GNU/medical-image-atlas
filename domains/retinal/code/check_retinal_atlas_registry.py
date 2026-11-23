"""Check the whole retinal atlas registry: keys, cross-references, files, checksums and licence policy.

Every table in ``docs/surveys/retinal_atlas_catalog/`` is listed in ``SCHEMA`` with its primary key and
foreign keys. Multi-valued cells use ``;``. The check fails (exit 1) on any error; missing optional
local datasets are reported as warnings because they are not needed to serve the atlas.

    .venv/bin/python -B domains/retinal/code/check_retinal_atlas_registry.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import export_retinal_atlas_registry as export
import retinal_atlas_registry as registry

CATALOG = registry.CATALOG
ROOT = registry.ROOT
MASKED_DIR = ROOT / 'resources/datasets/retinal_atlas_masked_figures'
MODALITY_DIR = ROOT / 'resources/datasets/retinal_atlas_modality_figures'
EXAMPLE_DIR = ROOT / 'resources/datasets/retinal_atlas_measurement_examples'
LICENCES = ('CC BY 4.0', 'CC0 1.0')          # project policy: only CC BY / CC0 images are published
VALUE_STATUS = {'ok', 'not_observed', 'not_evaluable', 'reading'}

# Domains that foreign keys point to: name → (table, key column)
DOMAINS = {
    'imaging': ('a_imaging_v01.csv', 'imaging_id'),
    'anatomy': ('b_anatomy_v01.csv', 'entity_id'),
    'lesion': ('c_lesions_v01.csv', 'entity_id'),
    'feature': ('d_features_v01.csv', 'feature_id'),
    'disease': ('e_diseases_v01.csv', 'disease_id'),
    'reference': ('sources_v01.csv', 'source_id'),
    'scheme': ('e_grading_schemes_v01.csv', 'scheme_id'),
    'image_source': ('g_image_sources_v01.csv', 'source_id'),
    'provider_figure': ('g_provider_figures_v01.csv', 'file'),
    'masked_figure': ('h_masked_figures_v01.csv', 'figure_id'),
    'modality_figure': ('h_modality_figures_v01.csv', 'figure_id'),
    'example': ('h_measure_examples_v01.csv', 'example_id'),
}
ITEM = ('anatomy', 'lesion')                      # a measured / reported item
TARGET = ('anatomy', 'lesion', 'imaging')         # a feature target (image-level features target img_*)
FINDING = ('anatomy', 'lesion', 'feature')        # what a disease relation or grading step names

# tables whose rows may leave feature_id empty to state something about the whole target
# ("not_applicable" / "not_investigated" for every feature of that target)
TARGET_LEVEL_ROWS = {'d_applicability_overrides_v01.csv', 'd_feature_applicability_v01.csv'}

# table → (primary key columns, {column: (domains, multi-valued, required)}, kind)
SCHEMA = {
    'a_imaging_v01.csv': (['imaging_id'], {'parent_id': (('imaging',), False, False), 'source_ids': (('reference',), True, False)}, 'hand'),
    'b_anatomy_v01.csv': (['entity_id'], {'parent_id': (('anatomy',), False, False), 'best_imaging_ids': (('imaging',), True, False),
                                          'source_ids': (('reference',), True, False)}, 'hand'),
    'c_lesions_v01.csv': (['entity_id'], {'affected_structure_ids': (('anatomy',), True, False), 'best_imaging_ids': (('imaging',), True, False),
                                          'source_ids': (('reference',), True, False)}, 'hand'),
    'd_features_v01.csv': (['feature_id'], {'target_id': (TARGET, False, True), 'imaging_ids': (('imaging',), True, False),
                                            'definition_source_ids': (('reference',), True, False)}, 'hand'),
    'd_common_feature_sets_v01.csv': (['scope', 'class_id', 'feature_id'], {'feature_id': (('feature',), False, True)}, 'hand'),
    'd_applicability_overrides_v01.csv': (['target_id', 'feature_id'], {'target_id': (TARGET, False, True),
                                                                        'feature_id': (('feature',), False, False)}, 'hand'),
    'bc_observations_v01.csv': (['observation_id'], {'target_id': (ITEM, False, True), 'imaging_id': (('imaging',), False, True),
                                                     'source_ids': (('reference',), True, False)}, 'hand'),
    'e_diseases_v01.csv': (['disease_id'], {'parent_id': (('disease',), False, False),
                                            'classification_source_ids': (('reference',), True, False)}, 'hand'),
    'e_disease_findings_v01.csv': (['relation_id'], {'disease_id': (('disease',), False, True), 'finding_id': (FINDING, False, True),
                                                     'classification_source_id': (('reference',), False, False),
                                                     'evidence_source_ids': (('reference',), True, False)}, 'hand'),
    'e_grading_schemes_v01.csv': (['scheme_id'], {'disease_id': (('disease',), False, True), 'imaging_ids': (('imaging',), True, False),
                                                  'source_ids': (('reference',), True, False)}, 'hand'),
    'e_grading_steps_v01.csv': (['step_id'], {'scheme_id': (('scheme',), False, True), 'finding_ids': (FINDING, True, False)}, 'hand'),
    'sources_v01.csv': (['source_id'], {}, 'hand'),
    'f_mapping_rules_v01.csv': (['rule_id'], {'target_id': (TARGET, False, False), 'feature_id': (('feature',), False, False)}, 'hand'),
    'f_existing_measurements_v01.csv': ([], {'target_id': (TARGET, False, False), 'feature_id': (('feature',), False, False)}, 'generated'),
    'd_feature_applicability_v01.csv': (['target_id', 'feature_id'], {'target_id': (TARGET, False, True),
                                                                      'feature_id': (('feature',), False, False)}, 'generated'),
    'g_image_sources_v01.csv': (['source_id'], {}, 'hand'),
    'g_provider_figures_v01.csv': (['file'], {'source_id': (('image_source',), False, True)}, 'hand'),
    'h_masked_figures_v01.csv': (['figure_id'], {'source_id': (('image_source',), False, True)}, 'generated'),
    'h_masked_figure_items_v01.csv': (['figure_id', 'item_id'], {'figure_id': (('masked_figure',), False, True),
                                                                 'item_id': (TARGET, False, True)}, 'generated'),
    'h_modality_figures_v01.csv': (['figure_id'], {'masked_figure_id': (('masked_figure',), False, False),
                                                   'provider_file': (('provider_figure',), False, False),
                                                   'source_id': (('image_source',), False, True)}, 'generated'),
    'h_measure_examples_v01.csv': (['example_id'], {'source_id': (('image_source',), False, False),
                                                    'modality_figure_id': (('modality_figure',), False, False),
                                                    'provider_file': (('provider_figure',), False, False)}, 'generated'),
    'h_example_layers_v01.csv': (['example_id', 'layer_key'], {'example_id': (('example',), False, True)}, 'generated'),
    'h_example_values_v01.csv': (['example_id', 'layer_key', 'feature_id'], {'example_id': (('example',), False, True),
                                                                            'feature_id': (('feature',), False, True)}, 'generated'),
    'i_feature_implementations_v01.csv': (['feature_id'], {'feature_id': (('feature',), False, True)}, 'generated'),
    'i_measure_disease_links_v01.csv': (['feature_id', 'disease_id'], {'feature_id': (('feature',), False, True),
                                                                       'disease_id': (('disease',), False, True),
                                                                       'via_item_id': (TARGET, False, False)}, 'generated'),
    'i_example_coverage_v01.csv': (['feature_id', 'example_modality'], {'feature_id': (('feature',), False, True)}, 'generated'),
}


def read(name: str) -> list[dict]:
    with (CATALOG / name).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def check() -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    present = {p.name for p in CATALOG.glob('*.csv')}
    for name in sorted(present - set(SCHEMA)):
        errors.append(f'{name}: table not described in SCHEMA')
    for name in sorted(set(SCHEMA) - present):
        errors.append(f'{name}: table missing')
    tables = {name: read(name) for name in SCHEMA if name in present}
    keys = {dom: {r[col] for r in tables.get(tab, [])} for dom, (tab, col) in DOMAINS.items()}

    for name, (pk, fks, _) in SCHEMA.items():
        rows = tables.get(name, [])
        if pk:
            seen = set()
            for i, r in enumerate(rows, 2):
                k = tuple(r[c] for c in pk)
                if not all(k[:1] if name in TARGET_LEVEL_ROWS else k):
                    errors.append(f'{name}:{i}: empty primary key {pk}')
                if k in seen:
                    errors.append(f'{name}:{i}: duplicate primary key {k}')
                seen.add(k)
        for col, (domains, multi, required) in fks.items():
            allowed = set().union(*(keys[d] for d in domains))
            for i, r in enumerate(rows, 2):
                raw = r.get(col, '')
                if not raw:
                    if required:
                        errors.append(f'{name}:{i}: {col} is required')
                    continue
                for value in (raw.split(';') if multi else [raw]):
                    if value not in allowed:
                        errors.append(f'{name}:{i}: {col}={value!r} not in {"/".join(domains)}')

    # image sources: licence policy, citation and local dataset path
    for r in tables.get('g_image_sources_v01.csv', []):
        if r['kind'] not in {'dataset', 'article'}:
            errors.append(f"g_image_sources: {r['source_id']} kind {r['kind']!r}")
        if r['license'] not in LICENCES:
            errors.append(f"g_image_sources: {r['source_id']} licence {r['license']!r} outside CC BY / CC0 policy")
        if not r['url'] or not r['credit']:
            errors.append(f"g_image_sources: {r['source_id']} needs url and credit")
        if r['kind'] == 'dataset' and not (ROOT / r['resource_path']).exists():
            warnings.append(f"dataset {r['source_id']} not present locally at {r['resource_path']}")
    # provider figures: stored once, checksum pinned
    for r in tables.get('g_provider_figures_v01.csv', []):
        path = registry.PROVIDER_DIR / r['file']
        if not path.is_file():
            errors.append(f"provider figure missing: {path.relative_to(ROOT)}")
        elif registry.sha256(path) != r['sha256']:
            errors.append(f"provider figure checksum changed: {r['file']}")
    # generated images exist
    for r in tables.get('h_masked_figures_v01.csv', []):
        for col in ('base_file', 'overlay_file'):
            if not (MASKED_DIR / r[col]).is_file():
                errors.append(f"masked figure file missing: {r[col]}")
    for r in tables.get('h_modality_figures_v01.csv', []):
        folder = MASKED_DIR if r['served'] == 'masked' else MODALITY_DIR
        if not (folder / r['file']).is_file():
            errors.append(f"modality figure file missing: {r['file']}")
    for r in tables.get('h_measure_examples_v01.csv', []):
        if not (EXAMPLE_DIR / r['base_file']).is_file():
            errors.append(f"example base image missing: {r['base_file']}")
        if not r['source_id'] and not r['modality_figure_id']:
            errors.append(f"example {r['example_id']} has no source")
    layer_keys = {(r['example_id'], r['layer_key']) for r in tables.get('h_example_layers_v01.csv', [])}
    for r in tables.get('h_example_layers_v01.csv', []):
        if not (EXAMPLE_DIR / r['file']).is_file():
            errors.append(f"example layer image missing: {r['file']}")
        if (r['kind'] == 'reading') != (r['function'] == ''):
            errors.append(f"layer {r['example_id']}/{r['layer_key']}: reading layers and only they have no function")
    for r in tables.get('h_example_values_v01.csv', []):
        if (r['example_id'], r['layer_key']) not in layer_keys:
            errors.append(f"value {r['example_id']}/{r['layer_key']} has no layer")
        if r['status'] not in VALUE_STATUS:
            errors.append(f"value {r['example_id']}/{r['layer_key']}/{r['feature_id']} status {r['status']!r}")
    # coverage: every measurement has an example on every image type it applies to
    for r in tables.get('i_example_coverage_v01.csv', []):
        if r['covered'] == 'no':
            warnings.append(f"no example for {r['feature_id']} on {r['example_modality']}")
    # generated tables are current
    fresh = export.build_tables()
    for name, rows in fresh.items():
        cols, _ = export.TABLES[name]
        current = tables.get(name, [])
        if [{c: str(r.get(c, '')) for c in cols} for r in rows] != [{c: r.get(c, '') for c in cols} for r in current]:
            errors.append(f'{name}: out of date — run export_retinal_atlas_registry.py')
    return errors, warnings


def main() -> int:
    errors, warnings = check()
    for w in warnings:
        print('warning:', w)
    for e in errors:
        print('error:', e)
    total = sum(1 for name in SCHEMA if (CATALOG / name).is_file())
    print(f'{total} tables · {len(errors)} errors · {len(warnings)} warnings')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
