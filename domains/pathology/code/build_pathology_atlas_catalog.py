"""Build the pathology atlas: derived applicability table, reading document and the web ``atlas.json``.

Hand-authored tables (A–E, observations, common feature sets, overrides, sources) are canonical. This script
(1) checks identifiers, references and enumerations, (2) derives target × feature applicability,
(3) renders a Markdown reading view and (4) exports the web payload, attaching the pathology-measures
function that computes each feature.

    .venv/bin/python -B domains/pathology/code/build_pathology_atlas_catalog.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict

import pathology_atlas_registry as registry

CATALOG = registry.CATALOG
DOMAIN = registry.DOMAIN
READING_DOC = DOMAIN / 'docs/surveys/10_pathology_atlas_catalog_survey_v01_ko.md'
WEB_DATA = registry.WEB_DATA / 'atlas.json'

TABLE_FILES = {'a': 'a_imaging_v01.csv', 'b': 'b_anatomy_v01.csv', 'c': 'c_lesions_v01.csv',
               'd': 'd_features_v01.csv', 'e': 'e_diseases_v01.csv', 'ef': 'e_disease_findings_v01.csv',
               'src': 'sources_v01.csv', 'sets': 'd_common_feature_sets_v01.csv',
               'over': 'd_applicability_overrides_v01.csv', 'obs': 'bc_observations_v01.csv',
               'gs': 'e_grading_schemes_v01.csv', 'gst': 'e_grading_steps_v01.csv'}
OBS_COLUMNS = ('obs_he', 'obs_ihc')
OBS_KEYS = {'obs_he': 'he', 'obs_ihc': 'ihc'}
OBS_VALUES = {'direct', 'limited', 'none'}
GRADING_KINDS = {'staging', 'typing', 'diagnostic', 'representative'}
STEP_LOGIC = {'any', 'all', 'single', 'atleast2', 'atleast3'}
E_RELATIONS = {'diagnostic_criterion', 'severity_classification', 'activity_monitoring', 'prognostic',
               'characteristic_nonspecific'}
REVIEW_STATUSES = {'draft', 'needs_source', 'source_linked', 'definition_checked_abstract', 'definition_checked',
                   'measurement_checked', 'expert_reviewed'}
APPLICABILITY = {'direct', 'common_applied', 'not_applicable', 'not_investigated'}
OUTPUT_TYPES = {'presence', 'category', 'count', 'count_per_area', 'length', 'area', 'ratio', 'index', 'angle',
                'intensity', 'score'}
FEATURE_ROLES = {'measurement', 'classification'}
NON_POSITIONAL_CLASSES = {'reference', 'zone', 'boundary'}
HIDDEN_TARGETS = {'les_generic'}
LESION_GROUP_KO = {
    'carcinoma': '선암(통합)', 'gleason_pattern': '글리슨 패턴', 'gleason_architecture': '패턴을 정하는 성장 양상',
    'intraductal': '관내·상피내 병변', 'invasion': '침범', 'benign_mimic': '암을 모방하는 양성 병변',
    'benign_change': '양성 변화', 'artifact': '인공물', 'aggregate': '공통 대상',
}
ANATOMY_GROUP = {
    'reference': ('reference', '측정 기준'), 'zone': ('region', '구역'), 'region': ('region', '구역'),
    'structure': ('structure', '구조'), 'layer': ('layer', '상피층·간질'), 'boundary': ('structure', '구조'),
}
INPUT_LEVEL = {'image': 'auto', 'label_map': 'mask', 'region_mask': 'mask', 'pattern_mask': 'mask',
               'matched_views': 'pair'}


def read_table(name):
    with (CATALOG / name).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def load_tables():
    return {key: read_table(name) for key, name in TABLE_FILES.items()}


def split(value):
    return [part for part in (value or '').split(';') if part]


def slug_of(entity_id):
    return entity_id.split('_', 1)[1].replace('_', '-')


def measure_registry():
    if str(registry.MEASURES_SRC) not in sys.path:
        sys.path.insert(0, str(registry.MEASURES_SRC))
    from pathology_measures.registry import INPUT_LABELS, REGISTRY
    return {fid: {'function': 'pathology_measures.' + e.function, 'input': e.input,
                  'input_label': INPUT_LABELS[e.input], 'method': e.method, 'reference': e.reference}
            for fid, e in REGISTRY.items()}


def build_applicability(tables):
    rows, seen = [], set()

    def add(target, feature, status, basis, note=''):
        if (target, feature) in seen:
            return
        seen.add((target, feature))
        rows.append({'target_id': target, 'feature_id': feature, 'applicability': status, 'basis': basis,
                     'note_ko': note})

    for feature in tables['d']:
        add(feature['target_id'], feature['feature_id'], 'direct', 'd_target')
    for override in tables['over']:
        add(override['target_id'], override['feature_id'], override['applicability'], 'override', override['note_ko'])
    sets = defaultdict(list)
    for entry in tables['sets']:
        sets[(entry['scope'], entry['class_id'])].append(entry)
    for entity in tables['c']:
        for entry in sets.get(('lesion', entity['morphology_class']), []):
            add(entity['entity_id'], entry['feature_id'], 'common_applied', f"class:{entity['morphology_class']}",
                entry['note_ko'])
    covered = {row['target_id'] for row in rows}
    for entity in tables['b']:
        if entity['entity_id'] not in covered and entity['measure_class'] in NON_POSITIONAL_CLASSES:
            add(entity['entity_id'], '', 'not_applicable', f"class:{entity['measure_class']}",
                '위치 기준·구역·경계(자체 측정 대상 아님)')
    for table in ('b', 'c'):
        for entity in tables[table]:
            if entity['entity_id'] not in covered and (entity['entity_id'], '') not in seen:
                add(entity['entity_id'], '', 'not_investigated', 'uncovered', '특징 연결 미조사')
    return rows


def check_integrity(tables, applicability, measures):
    errors = []
    ids = {}
    for name, key in (('a', 'imaging_id'), ('b', 'entity_id'), ('c', 'entity_id'), ('d', 'feature_id'),
                      ('e', 'disease_id'), ('src', 'source_id'), ('ef', 'relation_id'), ('obs', 'observation_id'),
                      ('gs', 'scheme_id'), ('gst', 'step_id')):
        values = [row[key] for row in tables[name]]
        errors += [f'duplicate {name} id: {v}' for v, n in Counter(values).items() if n > 1]
        ids[name] = set(values)
    items = ids['b'] | ids['c']
    targets = items | ids['a']
    findings = items | ids['d']

    def sources(label, value):
        return [f'{label}: unknown source {v}' for v in split(value) if v not in ids['src']]

    for name in ('b', 'c'):
        for row in tables[name]:
            label = row['entity_id']
            errors += [f'{label}: invalid {c}={row[c]!r}' for c in OBS_COLUMNS if row[c] not in OBS_VALUES]
            errors += [f'{label}: unknown imaging {v}' for v in split(row['best_imaging_ids']) if v not in ids['a']]
            errors += sources(label, row['source_ids'])
            if row['review_status'] not in REVIEW_STATUSES:
                errors.append(f'{label}: invalid review_status {row["review_status"]}')
    for row in tables['b']:
        if row['parent_id'] and row['parent_id'] not in ids['b']:
            errors.append(f"{row['entity_id']}: unknown parent {row['parent_id']}")
    for row in tables['c']:
        errors += [f"{row['entity_id']}: unknown structure {v}" for v in split(row['affected_structure_ids'])
                   if v not in ids['b']]
        if row['lesion_group'] not in LESION_GROUP_KO:
            errors.append(f"{row['entity_id']}: unknown lesion_group {row['lesion_group']}")
    for row in tables['a']:
        if row['parent_id'] and row['parent_id'] not in ids['a']:
            errors.append(f"{row['imaging_id']}: unknown parent {row['parent_id']}")
        errors += sources(row['imaging_id'], row['source_ids'])
    for row in tables['d']:
        label = row['feature_id']
        if row['target_id'] not in targets:
            errors.append(f'{label}: unknown target {row["target_id"]}')
        errors += [f'{label}: unknown imaging {v}' for v in split(row['imaging_ids']) if v not in ids['a']]
        errors += sources(label, row['definition_source_ids'])
        for col, allowed in (('output_type', OUTPUT_TYPES), ('review_status', REVIEW_STATUSES),
                             ('feature_role', FEATURE_ROLES), ('feature_type', {'qualitative', 'quantitative'})):
            if row[col] not in allowed:
                errors.append(f'{label}: invalid {col} {row[col]!r}')
    for row in tables['sets'] + tables['over']:
        if row['feature_id'] and row['feature_id'] not in ids['d']:
            errors.append(f"set/override: unknown feature {row['feature_id']}")
    for row in tables['over']:
        if row['target_id'] not in targets:
            errors.append(f"override: unknown target {row['target_id']}")
        if row['applicability'] not in APPLICABILITY:
            errors.append(f"override: invalid applicability {row['applicability']}")
    for row in tables['obs']:
        if row['target_id'] not in items:
            errors.append(f"{row['observation_id']}: unknown target {row['target_id']}")
        if row['imaging_id'] not in ids['a']:
            errors.append(f"{row['observation_id']}: unknown imaging {row['imaging_id']}")
        errors += sources(row['observation_id'], row['source_ids'])
    for row in tables['e']:
        if row['parent_id'] and row['parent_id'] not in ids['e']:
            errors.append(f"{row['disease_id']}: unknown parent {row['parent_id']}")
        errors += sources(row['disease_id'], row['classification_source_ids'])
    for row in tables['ef']:
        label = row['relation_id']
        if row['disease_id'] not in ids['e']:
            errors.append(f'{label}: unknown disease {row["disease_id"]}')
        if row['finding_id'] not in findings:
            errors.append(f'{label}: unknown finding {row["finding_id"]}')
        if row['relation_type'] not in E_RELATIONS:
            errors.append(f'{label}: invalid relation_type {row["relation_type"]}')
        errors += sources(label, row['classification_source_id']) + sources(label, row['evidence_source_ids'])
    for row in tables['gs']:
        if row['disease_id'] not in ids['e']:
            errors.append(f"{row['scheme_id']}: unknown disease")
        if row['kind'] not in GRADING_KINDS:
            errors.append(f"{row['scheme_id']}: invalid kind {row['kind']}")
        errors += [f"{row['scheme_id']}: unknown imaging {v}" for v in split(row['imaging_ids']) if v not in ids['a']]
        errors += sources(row['scheme_id'], row['source_ids'])
    for row in tables['gst']:
        if row['scheme_id'] not in ids['gs']:
            errors.append(f"{row['step_id']}: unknown scheme")
        if row['logic'] not in STEP_LOGIC:
            errors.append(f"{row['step_id']}: invalid logic {row['logic']}")
        errors += [f"{row['step_id']}: unknown finding {v}" for v in split(row['finding_ids']) if v not in findings]
    errors += [f'pathology-measures registry names unknown feature {f}' for f in measures if f not in ids['d']]
    for row in applicability:
        if row['applicability'] not in APPLICABILITY:
            errors.append(f'applicability: invalid {row}')
    return errors


def implementation(feature, package):
    if package:
        level = INPUT_LEVEL.get(package['input'], 'mask')
    elif feature['feature_type'] == 'qualitative':
        level = 'reading'
    else:
        level = 'none'
    return {'level': level, 'package': package, 'count': 1 if package else 0, 'usable': 1 if package else 0,
            'sources': ['pathology-measures'] if package else [], 'inputs': [package['input']] if package else [],
            'examples': []}


def export_web_data(tables, applicability, measures):
    features = {row['feature_id']: row for row in tables['d']}
    obs_by_target = defaultdict(list)
    for row in tables['obs']:
        obs_by_target[row['target_id']].append({
            'imaging': row['imaging_id'], 'signal': row['observed_signal_ko'],
            'condition': row['interpretation_condition_ko'], 'sources': split(row['source_ids']),
            'review': row['review_status']})
    app_by_target = defaultdict(list)
    for row in applicability:
        app_by_target[row['target_id']].append(row)
    relations = defaultdict(list)
    for row in tables['ef']:
        relations[row['finding_id']].append(row)
    lesions_by_structure = defaultdict(list)
    for row in tables['c']:
        if row['entity_id'] in HIDDEN_TARGETS:
            continue
        for structure in split(row['affected_structure_ids']):
            lesions_by_structure[structure].append(row['entity_id'])
    children = defaultdict(list)
    for row in tables['b']:
        if row['parent_id']:
            children[row['parent_id']].append(row['entity_id'])

    def feature_list(entity_id):
        out = []
        own = {(features[a['feature_id']]['axis'], features[a['feature_id']]['output_type'])
               for a in app_by_target.get(entity_id, []) if a['applicability'] == 'direct' and a['feature_id'] in features}
        for app in app_by_target.get(entity_id, []):
            f = features.get(app['feature_id'])
            if not f or f['feature_role'] == 'classification' or app['applicability'] == 'not_applicable':
                continue
            if app['applicability'] != 'direct' and (f['axis'], f['output_type']) in own:
                continue
            out.append({'id': f['feature_id'], 'name': f['name_ko'], 'type': f['feature_type'], 'axis': f['axis'],
                        'definition': f['definition_ko'], 'unit': f['unit'], 'region': f['region_spec'],
                        'requirements': f['requirements'], 'imaging': split(f['imaging_ids']),
                        'common': app['applicability'] != 'direct', 'review': f['review_status']})
        return out

    def disease_links(finding_ids):
        return [{'disease': rel['disease_id'], 'finding': fid, 'type': rel['relation_type'],
                 'version': rel['classification_version'], 'condition': rel['condition_ko'],
                 'sources': split(rel['evidence_source_ids'] or rel['classification_source_id']),
                 'review': rel['review_status']}
                for fid in finding_ids for rel in relations.get(fid, [])]

    def feature_status(entity_id):
        states = {r['applicability'] for r in app_by_target.get(entity_id, [])}
        return next((s for s in ('direct', 'common_applied', 'not_applicable', 'not_investigated') if s in states),
                    'not_investigated')

    items = {}
    for row in tables['b']:
        group, label = ANATOMY_GROUP.get(row['kind'], ('structure', '구조'))
        items[row['entity_id']] = {
            'id': row['entity_id'], 'section': 'anatomy', 'slug': slug_of(row['entity_id']), 'order': len(items),
            'group': group, 'group_label': label, 'kind': row['kind'], 'axis': row['map_axis'],
            'subgroup': row['map_subgroup'], 'name': row['name_ko'], 'name_en': row['name_en'],
            'abbr': row['abbreviation'], 'definition': row['definition_ko'], 'location': row['location_ko'],
            'parent': row['parent_id'], 'children': children.get(row['entity_id'], []),
            'obs': {v: row[k] for k, v in OBS_KEYS.items()}, 'best_imaging': split(row['best_imaging_ids']),
            'features': feature_list(row['entity_id']), 'feature_status': feature_status(row['entity_id']),
            'observations': obs_by_target.get(row['entity_id'], []),
            'related_lesions': lesions_by_structure.get(row['entity_id'], []),
            'diseases': disease_links([row['entity_id']]), 'sources': split(row['source_ids']),
            'basis': row['definition_basis'], 'review': row['review_status'], 'existing_measures': 0}
    for row in tables['c']:
        if row['entity_id'] in HIDDEN_TARGETS:
            continue
        own = feature_list(row['entity_id'])
        items[row['entity_id']] = {
            'id': row['entity_id'], 'section': 'lesions', 'slug': slug_of(row['entity_id']), 'order': len(items),
            'group': row['lesion_group'], 'group_label': LESION_GROUP_KO[row['lesion_group']],
            'kind': row['morphology_class'], 'secondary': False, 'aggregate': False,
            'name': row['name_ko'], 'name_en': row['name_en'], 'abbr': row['abbreviation'],
            'definition': row['definition_ko'], 'location': row['depth_ko'], 'differentials': row['differentials_ko'],
            'structures': split(row['affected_structure_ids']), 'obs': {v: row[k] for k, v in OBS_KEYS.items()},
            'best_imaging': split(row['best_imaging_ids']), 'features': own,
            'feature_status': feature_status(row['entity_id']), 'observations': obs_by_target.get(row['entity_id'], []),
            'diseases': disease_links([row['entity_id']] + [f['id'] for f in own if not f['common']]),
            'sources': split(row['source_ids']), 'basis': row['definition_basis'], 'review': row['review_status'],
            'existing_measures': 0}
    slugs = Counter((i['section'], i['slug']) for i in items.values())
    if dup := [k for k, n in slugs.items() if n > 1]:
        raise ValueError(f'duplicate web slugs: {dup}')
    return {
        'version': 'v01', 'generated_by': 'domains/pathology/code/build_pathology_atlas_catalog.py',
        'imaging': {r['imaging_id']: {'name': r['name_ko'], 'name_en': r['name_en'], 'level': r['level'],
                                      'parent': r['parent_id'], 'shows': r['shows'], 'limits': r['limits'],
                                      'signal': r['signal'], 'dimensionality': r['dimensionality'],
                                      'sources': split(r['source_ids'])} for r in tables['a']},
        'diseases': {r['disease_id']: {
            'id': r['disease_id'], 'slug': slug_of(r['disease_id']), 'name': r['name_ko'], 'name_en': r['name_en'],
            'abbr': r['abbreviation'], 'scope': r['scope'], 'parent': r['parent_id'], 'note': r['note_ko'],
            'classification_sources': split(r['classification_source_ids']),
            'children': [x['disease_id'] for x in tables['e'] if x['parent_id'] == r['disease_id']],
            'relations': [{'finding': rel['finding_id'], 'type': rel['relation_type'],
                           'version': rel['classification_version'], 'condition': rel['condition_ko'],
                           'sources': split(rel['evidence_source_ids'] or rel['classification_source_id']),
                           'review': rel['review_status']} for rel in tables['ef'] if rel['disease_id'] == r['disease_id']],
            'grading': [{
                'id': gs['scheme_id'], 'name': gs['name_ko'], 'kind': gs['kind'], 'imaging': split(gs['imaging_ids']),
                'read_rule': gs['read_rule_ko'], 'sources': split(gs['source_ids']), 'review': gs['review_status'],
                'note': gs['note_ko'],
                'steps': [{'grade': st['grade_ko'], 'logic': st['logic'],
                           'criteria': [c.strip() for c in st['criteria_ko'].split('|') if c.strip()],
                           'findings': split(st['finding_ids']), 'note': st['note_ko']}
                          for st in sorted((t for t in tables['gst'] if t['scheme_id'] == gs['scheme_id']),
                                           key=lambda t: int(t['step_order']))]}
                for gs in tables['gs'] if gs['disease_id'] == r['disease_id']],
        } for r in tables['e']},
        'features': {r['feature_id']: {
            'id': r['feature_id'], 'target': r['target_id'], 'name': r['name_ko'], 'type': r['feature_type'],
            'definition': r['definition_ko'], 'unit': r['unit'], 'region': r['region_spec'],
            'requirements': r['requirements'], 'imaging': split(r['imaging_ids']), 'axis': r['axis'],
            'output': r['output_type'], 'review': r['review_status'], 'role': r['feature_role'],
            'impl': implementation(r, measures.get(r['feature_id']))} for r in tables['d']},
        'sources': {r['source_id']: {'name': r['short_name'], 'citation': r['citation'], 'url': r['url'],
                                     'verification': r['verification']} for r in tables['src']},
        'items': items,
    }


def render(tables, applicability):
    names = {r['entity_id']: r['name_ko'] for r in tables['b'] + tables['c']}
    names.update({r['feature_id']: r['name_ko'] for r in tables['d']})
    out = ['# 병리 영상 지도(전립선) 조사 표 v01', '',
           '`code/build_pathology_atlas_catalog.py`가 등록 표에서 만든 읽기용 문서다. 손으로 고치지 않는다.', '',
           f"영상 종류 {len(tables['a'])} · 해부 {len(tables['b'])} · 병변 {len(tables['c'])} · 특징 {len(tables['d'])} · "
           f"질병 {len(tables['e'])} · 질병–소견 관계 {len(tables['ef'])} · 판정 체계 {len(tables['gs'])} · 근거 문헌 {len(tables['src'])}", '']
    out += ['## A. 영상 종류', '', '| ID | 이름 | 보이는 것 | 한계 |', '| --- | --- | --- | --- |']
    out += [f"| `{r['imaging_id']}` | {r['name_ko']} | {r['shows']} | {r['limits']} |" for r in tables['a']]
    out += ['', '## B. 해부', '', '| ID | 이름 | 정의 | H&E·IHC |', '| --- | --- | --- | --- |']
    out += [f"| `{r['entity_id']}` | {r['name_ko']} | {r['definition_ko']} | {r['obs_he']}·{r['obs_ihc']} |"
            for r in tables['b']]
    out += ['', '## C. 병변', '', '| ID | 묶음 | 이름 | 정의 | 감별 |', '| --- | --- | --- | --- | --- |']
    out += [f"| `{r['entity_id']}` | {LESION_GROUP_KO[r['lesion_group']]} | {r['name_ko']} | {r['definition_ko']} | {r['differentials_ko']} |"
            for r in tables['c']]
    out += ['', '## D. 특징·측정', '', '| ID | 대상 | 이름 | 유형 | 단위 | 영상 |', '| --- | --- | --- | --- | --- | --- |']
    out += [f"| `{r['feature_id']}` | {names.get(r['target_id'], r['target_id'])} | {r['name_ko']} | {r['feature_type']} | {r['unit']} | {r['imaging_ids'].replace(';', ' ')} |"
            for r in tables['d']]
    out += ['', '## E. 질병과 판정 체계', '']
    for d in tables['e']:
        out.append(f"### {d['name_ko']} (`{d['disease_id']}`)")
        out.append('')
        for rel in (r for r in tables['ef'] if r['disease_id'] == d['disease_id']):
            out.append(f"- {names.get(rel['finding_id'], rel['finding_id'])} — {rel['relation_type']}: {rel['condition_ko']}")
        for gs in (g for g in tables['gs'] if g['disease_id'] == d['disease_id']):
            out.append(f"- 판정 체계 **{gs['name_ko']}** ({gs['kind']})")
            for st in sorted((t for t in tables['gst'] if t['scheme_id'] == gs['scheme_id']), key=lambda t: int(t['step_order'])):
                out.append(f"  {st['step_order']}. {st['grade_ko']} — {st['criteria_ko'].replace('|', '·')}")
        out.append('')
    counts = Counter(r['applicability'] for r in applicability)
    out += ['## 적용 관계', '', ' · '.join(f'{k} {v}' for k, v in sorted(counts.items())), '']
    return '\n'.join(out) + '\n'


def write_csv(path, columns, rows):
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        writer.writerows({k: r[k] for k in columns} for r in rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='validate only')
    args = parser.parse_args()
    tables = load_tables()
    measures = measure_registry()
    applicability = build_applicability(tables)
    errors = check_integrity(tables, applicability, measures)
    for error in errors:
        print('ERROR', error, file=sys.stderr)
    print(f"items={len(tables['b']) + len(tables['c'])} features={len(tables['d'])} functions={len(measures)} "
          f"applicability={len(applicability)} errors={len(errors)}")
    if errors:
        return 1
    if not args.check:
        write_csv(CATALOG / 'd_feature_applicability_v01.csv',
                  ('target_id', 'feature_id', 'applicability', 'basis', 'note_ko'), applicability)
        READING_DOC.write_text(render(tables, applicability), encoding='utf-8')
        payload = export_web_data(tables, applicability, measures)
        WEB_DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
        print(f'wrote reading doc and atlas.json ({len(payload["items"])} items)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
