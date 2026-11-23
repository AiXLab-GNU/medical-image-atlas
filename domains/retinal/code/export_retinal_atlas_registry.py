"""Export the generated cross-reference tables (H, I) of the retinal atlas registry.

The figure / example builders write JSON manifests for the web service; this script flattens them,
together with ``atlas.json``, into relational CSV tables next to the hand-authored catalog so every
image, layer, value, implementation and disease link can be joined by ID:

* H (images): masked figures (+ items), modality figures, measurement examples, layers, values
* I (derived): feature implementations, measurement → disease links, example coverage per image type

Generated files are overwritten; never edit them by hand. Run after the builders, then run
``check_retinal_atlas_registry.py``.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path

import retinal_atlas_registry as registry

PROJECT = registry.PROJECT
CATALOG = registry.CATALOG
WEB_DATA = PROJECT / 'packages/retinal-atlas-web/src/retinal_atlas_web/data'
MODALITY_ROOT = registry.ROOT / 'resources/datasets/retinal_atlas_modality_figures'
SEP = ';'

# table → (columns, primary key columns); the order is the documentation order in the schema document
TABLES = {
    'h_masked_figures_v01.csv': (['figure_id', 'name', 'source_id', 'source_file', 'mask_label', 'base_file', 'base_sha256',
                                  'overlay_file', 'overlay_sha256', 'width', 'height', 'transform', 'caption'], ['figure_id']),
    'h_masked_figure_items_v01.csv': (['figure_id', 'item_id'], ['figure_id', 'item_id']),
    'h_modality_figures_v01.csv': (['figure_id', 'modality', 'served', 'file', 'masked_figure_id', 'provider_file', 'source_id',
                                    'panel', 'crop_box', 'width', 'height', 'transform', 'caption'], ['figure_id']),
    'h_measure_examples_v01.csv': (['example_id', 'modality', 'modality_label', 'region', 'title', 'builder', 'source_id',
                                    'modality_figure_id', 'provider_file', 'source_file', 'base_file', 'width', 'height',
                                    'n_layers', 'caption'], ['example_id']),
    'h_example_layers_v01.csv': (['example_id', 'layer_key', 'layer_order', 'label', 'kind', 'function', 'tone', 'file', 'how'],
                                 ['example_id', 'layer_key']),
    'h_example_values_v01.csv': (['example_id', 'layer_key', 'feature_id', 'status', 'value_text'],
                                 ['example_id', 'layer_key', 'feature_id']),
    'i_feature_implementations_v01.csv': (['feature_id', 'role', 'impl_level', 'package_function', 'package_input',
                                           'package_input_label', 'method', 'reference', 'existing_rows', 'existing_usable',
                                           'existing_sources'], ['feature_id']),
    'i_measure_disease_links_v01.csv': (['feature_id', 'disease_id', 'link_kind', 'via_item_id', 'relation_type'],
                                        ['feature_id', 'disease_id']),
    'i_example_coverage_v01.csv': (['feature_id', 'example_modality', 'covered', 'example_ids'],
                                   ['feature_id', 'example_modality']),
}
EXAMPLE_MODALITIES = ['cfp', 'uwf', 'fa', 'faf', 'nir', 'icga', 'oct', 'octa']


def _load(name: str):
    return json.loads((WEB_DATA / name).read_text(encoding='utf-8'))


def _disease_links_module():
    path = PROJECT / 'packages/retinal-atlas-web/src/retinal_atlas_web/disease_links.py'
    spec = importlib.util.spec_from_file_location('retinal_atlas_disease_links', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _example_modality(imaging_id: str) -> str:
    for prefix, key in (('img_octa', 'octa'), ('img_oct', 'oct'), ('img_cfp', 'cfp'), ('img_uwf', 'uwf'),
                        ('img_faf', 'faf'), ('img_nir', 'nir'), ('img_fa', 'fa'), ('img_icga', 'icga')):
        if imaging_id.startswith(prefix):
            return key
    return ''


def build_tables() -> dict[str, list[dict]]:
    atlas = _load('atlas.json')
    masked = _load('masked_figures.json')['figures']
    modality = _load('modality_figures.json')['figures']
    examples = _load('measurement_examples.json')['examples']
    crops = {r['file']: r for r in json.loads((MODALITY_ROOT / 'source_manifest.json').read_text(encoding='utf-8'))}
    masked_by_base = {f['base']: f['id'] for f in masked}
    sources = registry.image_sources()
    provider = registry.provider_figures()
    out = {name: [] for name in TABLES}

    for f in masked:
        out['h_masked_figures_v01.csv'].append({
            'figure_id': f['id'], 'name': f['name'], 'source_id': f['source'], 'source_file': f['source_file'],
            'mask_label': f['mask_label'], 'base_file': f['base'], 'base_sha256': f['base_sha256'],
            'overlay_file': f['overlay'], 'overlay_sha256': f['overlay_sha256'], 'width': f['width'], 'height': f['height'],
            'transform': f['transform'], 'caption': f['caption']})
        for item in f['items']:
            out['h_masked_figure_items_v01.csv'].append({'figure_id': f['id'], 'item_id': item})

    url_to_source = {}
    for key, row in sources.items():
        url_to_source.setdefault(row['url'], key)
    for f in modality:
        crop = crops.get(f['file'], {})
        provider_file = crop.get('provider_file', '').split('/')[-1]
        masked_id = masked_by_base.get(f['file'], '') if f['served'] == 'masked' else ''
        source_id = (provider[provider_file]['source_id'] if provider_file else
                     next((m['source'] for m in masked if m['id'] == masked_id), url_to_source.get(f['url'], '')))
        out['h_modality_figures_v01.csv'].append({
            'figure_id': f['id'], 'modality': f['modality'], 'served': f['served'], 'file': f['file'],
            'masked_figure_id': masked_id, 'provider_file': provider_file, 'source_id': source_id, 'panel': f['panel'],
            'crop_box': SEP.join(map(str, crop.get('crop_box', []))), 'width': f['width'], 'height': f['height'],
            'transform': f['transform'], 'caption': f['caption']})

    modality_ids = {f['file']: f['id'] for f in modality}
    for ex in examples:
        modality_file = ex['source'].split(':', 1)[1] if ex['source'].startswith('modality:') else ''
        provider_file = ex['source_file'].split('/', 1)[1] if ex['source_file'].startswith('provider_figures/') else ''
        out['h_measure_examples_v01.csv'].append({
            'example_id': ex['id'], 'modality': ex['modality'], 'modality_label': ex['modality_label'], 'region': ex['region'],
            'title': ex['title'], 'builder': ex.get('builder', ''),
            'source_id': '' if modality_file else ex['source'], 'modality_figure_id': modality_ids.get(modality_file, ''),
            'provider_file': provider_file, 'source_file': ex['source_file'], 'base_file': ex['base'],
            'width': ex['width'], 'height': ex['height'], 'n_layers': len(ex['layers']), 'caption': ex['caption']})
        for order, la in enumerate(ex['layers'], 1):
            reading = any(f['status'] == 'reading' for f in la['features'])
            out['h_example_layers_v01.csv'].append({
                'example_id': ex['id'], 'layer_key': la['key'], 'layer_order': order, 'label': la['label'],
                'kind': 'reading' if reading else 'computed', 'function': la['function'], 'tone': la['tone'],
                'file': la['file'], 'how': la['how']})
            for f in la['features']:
                out['h_example_values_v01.csv'].append({
                    'example_id': ex['id'], 'layer_key': la['key'], 'feature_id': f['id'], 'status': f['status'],
                    'value_text': f['value']})

    for fid, f in sorted(atlas['features'].items()):
        impl = f.get('impl', {})
        pkg = impl.get('package') or {}
        out['i_feature_implementations_v01.csv'].append({
            'feature_id': fid, 'role': f['role'], 'impl_level': impl.get('level', ''),
            'package_function': pkg.get('function', ''), 'package_input': pkg.get('input', ''),
            'package_input_label': pkg.get('input_label', ''), 'method': pkg.get('method', ''),
            'reference': pkg.get('reference', ''), 'existing_rows': impl.get('count', 0),
            'existing_usable': impl.get('usable', 0), 'existing_sources': SEP.join(impl.get('sources', []))})

    links = _disease_links_module().measurement_diseases(atlas)
    for fid in sorted(links):
        if atlas['features'].get(fid, {}).get('role') != 'measurement':
            continue
        for d in links[fid]:
            out['i_measure_disease_links_v01.csv'].append({
                'feature_id': fid, 'disease_id': d['id'], 'link_kind': 'via_item' if d['via'] else 'direct',
                'via_item_id': d.get('via_id') or '', 'relation_type': d['type']})

    shown: dict[tuple, list] = {}
    for ex in examples:
        for la in ex['layers']:
            for f in la['features']:
                shown.setdefault((f['id'], ex['modality']), [])
                if ex['id'] not in shown[(f['id'], ex['modality'])]:
                    shown[(f['id'], ex['modality'])].append(ex['id'])
    for fid, f in sorted(atlas['features'].items()):
        if f['role'] != 'measurement':
            continue
        applies = {_example_modality(i) for i in f.get('imaging', [])} - {''}
        for mod in EXAMPLE_MODALITIES:
            ids = shown.get((fid, mod), [])
            if mod in applies or ids:
                out['i_example_coverage_v01.csv'].append({
                    'feature_id': fid, 'example_modality': mod,
                    'covered': 'yes' if ids else ('no' if mod in applies else 'extra'),
                    'example_ids': SEP.join(ids)})
    return out


def write_tables(tables: dict[str, list[dict]]) -> None:
    for name, rows in tables.items():
        cols, _ = TABLES[name]
        with (CATALOG / name).open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, cols, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail if a generated table is out of date')
    args = parser.parse_args()
    tables = build_tables()
    if args.check:
        stale = []
        for name, rows in tables.items():
            cols, _ = TABLES[name]
            path = CATALOG / name
            current = path.read_text(encoding='utf-8') if path.is_file() else ''
            import io
            buf = io.StringIO()
            writer = csv.DictWriter(buf, cols, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
            if buf.getvalue() != current:
                stale.append(name)
        if stale:
            print('out of date:', ', '.join(stale))
            return 1
        print('generated tables up to date')
        return 0
    write_tables(tables)
    for name, rows in tables.items():
        print(f'{name}: {len(rows)} rows')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
