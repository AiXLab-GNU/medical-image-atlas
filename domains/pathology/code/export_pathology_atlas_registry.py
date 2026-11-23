"""Export the generated H (images) and I (derived) tables of the pathology atlas from the web data.

    .venv/bin/python -B domains/pathology/code/export_pathology_atlas_registry.py [--check]

``--check`` fails when a generated table differs from what the current web data would produce.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import sys

import pathology_atlas_registry as registry

WEB = registry.WEB_DATA
CATALOG = registry.CATALOG


def _disease_links():
    path = WEB.parent / 'disease_links.py'
    spec = importlib.util.spec_from_file_location('patho_disease_links', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.measurement_diseases


def _modality_of(imaging_id):
    if imaging_id.startswith('img_he'):
        return 'he'
    if imaging_id.startswith('img_ihc'):
        return 'ihc'
    return ''


TABLES = {
    'h_masked_figures_v01.csv': ['figure_id', 'source_id', 'source_file', 'mask_label', 'base_file', 'base_sha256',
                                 'overlay_file', 'overlay_sha256', 'context_file', 'width', 'height', 'transform', 'caption'],
    'h_masked_figure_items_v01.csv': ['figure_id', 'item_id'],
    'h_measure_examples_v01.csv': ['example_id', 'modality', 'region', 'title', 'source_id', 'source_file', 'builder',
                                   'base_file', 'width', 'height', 'caption'],
    'h_example_layers_v01.csv': ['example_id', 'layer_key', 'label', 'tone', 'function', 'file', 'how'],
    'h_example_values_v01.csv': ['example_id', 'layer_key', 'feature_id', 'status', 'value'],
    'i_feature_implementations_v01.csv': ['feature_id', 'target_id', 'role', 'level', 'function', 'input', 'method', 'reference'],
    'i_measure_disease_links_v01.csv': ['feature_id', 'disease_id', 'relation_type', 'via_item_id'],
    'i_example_coverage_v01.csv': ['feature_id', 'modality', 'has_example', 'example_id'],
}


def build_tables():
    atlas = json.loads((WEB / 'atlas.json').read_text(encoding='utf-8'))
    figs = json.loads((WEB / 'masked_figures.json').read_text(encoding='utf-8'))['figures']
    examples = json.loads((WEB / 'measurement_examples.json').read_text(encoding='utf-8'))['examples']
    out = {name: [] for name in TABLES}
    for f in figs:
        out['h_masked_figures_v01.csv'].append({
            'figure_id': f['id'], 'source_id': f['source'], 'source_file': f['source_file'], 'mask_label': f['mask_label'],
            'base_file': f['base'], 'base_sha256': f['base_sha256'], 'overlay_file': f['overlay'],
            'overlay_sha256': f['overlay_sha256'], 'context_file': f.get('context', ''), 'width': f['width'],
            'height': f['height'], 'transform': f['transform'], 'caption': f['caption']})
        out['h_masked_figure_items_v01.csv'] += [{'figure_id': f['id'], 'item_id': i} for i in f['items']]
    shown = {}
    for ex in examples:
        out['h_measure_examples_v01.csv'].append({
            'example_id': ex['id'], 'modality': ex['modality'], 'region': ex['region'], 'title': ex['title'],
            'source_id': ex['source'], 'source_file': ex['source_file'], 'builder': ex['builder'], 'base_file': ex['base'],
            'width': ex['width'], 'height': ex['height'], 'caption': ex['caption']})
        for la in ex['layers']:
            out['h_example_layers_v01.csv'].append({
                'example_id': ex['id'], 'layer_key': la['key'], 'label': la['label'], 'tone': la['tone'],
                'function': la['function'], 'file': la['file'], 'how': la['how']})
            for v in la['features']:
                out['h_example_values_v01.csv'].append({'example_id': ex['id'], 'layer_key': la['key'],
                                                        'feature_id': v['id'], 'status': v['status'], 'value': v['value']})
                shown.setdefault((v['id'], ex['modality']), ex['id'])
    for fid, f in sorted(atlas['features'].items()):
        pkg = f['impl'].get('package') or {}
        out['i_feature_implementations_v01.csv'].append({
            'feature_id': fid, 'target_id': f['target'], 'role': f['role'], 'level': f['impl']['level'],
            'function': pkg.get('function', ''), 'input': pkg.get('input', ''), 'method': pkg.get('method', ''),
            'reference': pkg.get('reference', '')})
        if f['role'] != 'measurement':
            continue
        for mod in sorted({_modality_of(i) for i in f['imaging']} - {''}):
            ex_id = shown.get((fid, mod), '')
            out['i_example_coverage_v01.csv'].append({'feature_id': fid, 'modality': mod,
                                                      'has_example': 'yes' if ex_id else 'no', 'example_id': ex_id})
    for fid, entries in sorted(_disease_links()(atlas).items()):
        if fid not in atlas['features']:
            continue
        for e in entries:
            out['i_measure_disease_links_v01.csv'].append({'feature_id': fid, 'disease_id': e['id'],
                                                           'relation_type': e['type'], 'via_item_id': e.get('via_id') or ''})
    return out


def render(name, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=TABLES[name], lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    stale = []
    for name, rows in build_tables().items():
        text = render(name, rows)
        path = CATALOG / name
        if args.check:
            if not path.is_file() or path.read_text(encoding='utf-8') != text:
                stale.append(name)
        else:
            path.write_text(text, encoding='utf-8')
            print(f'{name}: {len(rows)} rows')
    if args.check:
        for name in stale:
            print('STALE', name, file=sys.stderr)
        print('generated tables up to date' if not stale else f'{len(stale)} stale tables')
        return 1 if stale else 0
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
