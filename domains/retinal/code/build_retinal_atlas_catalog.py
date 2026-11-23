"""Build the retinal atlas survey tables and the integrated reading document.

Hand-authored tables A–E, the common feature sets, applicability overrides,
observations and the F mapping rules are the canonical sources. This script only
(1) derives the F table from the registered measurement sources while preserving
their original identifiers, (2) derives the feature applicability table,
(3) checks identifier, target and output-type consistency, and (4) renders a
Markdown reading view. It copies definitions and identifiers, never patient values.

A rule-based F relation is an unreviewed candidate. It does not prove that a source
measurement is, or is not, equivalent to a clinical definition.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
CATALOG = PROJECT / 'docs/surveys/retinal_atlas_catalog'
READING_DOC = PROJECT / 'docs/surveys/10_retinal_atlas_catalog_survey_v01_ko.md'
E118_REGISTRY = PROJECT / 'references/e118_hierarchical_feature_registry.csv'   # frozen copy of the E118 registry (oculophenome-xai P003)
PACKAGE_SRC = PROJECT / 'packages/ophthalmic-quantification/src'
MEASURES_SRC = PROJECT / 'packages/retinal-measures/src'

TABLE_FILES = {'a': 'a_imaging_v01.csv', 'b': 'b_anatomy_v01.csv', 'c': 'c_lesions_v01.csv',
               'd': 'd_features_v01.csv', 'e': 'e_diseases_v01.csv', 'ef': 'e_disease_findings_v01.csv',
               'src': 'sources_v01.csv', 'sets': 'd_common_feature_sets_v01.csv',
               'over': 'd_applicability_overrides_v01.csv', 'obs': 'bc_observations_v01.csv',
               'gs': 'e_grading_schemes_v01.csv', 'gst': 'e_grading_steps_v01.csv'}
GRADING_KINDS = {'staging', 'typing', 'diagnostic', 'representative'}
STEP_LOGIC = {'any', 'all', 'single', 'atleast2', 'atleast3'}
OBS_VALUES = {'direct', 'limited', 'none'}
OBS_COLUMNS = ('obs_cfp', 'obs_oct', 'obs_octa', 'obs_faf', 'obs_nir', 'obs_fa', 'obs_icga')
F_RELATIONS = {'same_definition', 'variant_specification', 'proxy', 'derived', 'qc_validation',
               'clinical_record', 'model_output', 'image_signal', 'unmapped'}
E_RELATIONS = {'diagnostic_criterion', 'severity_classification', 'activity_monitoring',
               'prognostic', 'characteristic_nonspecific'}
REVIEW_STATUSES = {'draft', 'needs_source', 'source_linked', 'definition_checked_abstract',
                   'definition_checked', 'measurement_checked', 'expert_reviewed'}
APPLICABILITY = {'direct', 'common_applied', 'not_applicable', 'not_investigated'}
OUTPUT_TYPES = {'presence', 'category', 'count', 'count_per_area', 'length', 'length_per_area', 'area',
                'volume', 'ratio', 'index', 'angle', 'intensity', 'score', 'rate'}
# Output types that may differ only by normalisation or unit within one property.
COMPATIBLE_OUTPUTS = [{'presence', 'category'}, {'count', 'count_per_area'}]
SEMANTIC_RELATIONS = {'same_definition', 'variant_specification'}
NON_POSITIONAL_CLASSES = {'reference', 'zone', 'boundary'}
LESION_PREFIX_TARGET = {
    'hemorrhage': 'les_hemorrhage_pooled', 'microaneurysm': 'les_microaneurysm',
    'hard_exudate': 'les_hard_exudate', 'cotton_wool_spot': 'les_cotton_wool_spot',
    'soft_exudate': 'les_cotton_wool_spot', 'irma': 'les_irma',
    'venous_beading': 'les_venous_beading', 'neovascularization': 'les_neovascularization_pooled',
    'irf': 'les_intraretinal_fluid', 'srf': 'les_subretinal_fluid',
    'ped': 'les_ped_unspecified', 'shrm': 'les_shrm',
}
SOURCE_FIELDS = ('source_record_id', 'source_concept_id', 'source_definition_sha256', 'source_region',
                 'source_statistic', 'source_coordinate_frame', 'source_derived_from',
                 'source_algorithm_version', 'source_role')
F_COLUMNS = ('source_name', 'collection', 'domain', 'source_measurement_id', 'input_source', 'unit',
             'source_definition') + SOURCE_FIELDS + (
             'target_id', 'feature_id', 'relation_type', 'output_type', 'rule_id', 'mapping_status',
             'note_ko')


def read_table(name: str) -> list[dict[str, str]]:
    with (CATALOG / name).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def load_tables() -> dict[str, list[dict[str, str]]]:
    return {key: read_table(name) for key, name in TABLE_FILES.items()}


def blank_source_fields() -> dict[str, str]:
    return {field: '' for field in SOURCE_FIELDS}


def registered_sources() -> list[dict[str, str]]:
    """Return one row per registered source measurement (definitions and identifiers only)."""
    sys.path.insert(0, str(PACKAGE_SRC))
    from ophthalmic_quantification import catalog, lesion_annotation_catalog
    from ophthalmic_quantification.known_lesion_phenomics import (
        ALGORITHM_VERSION, KNOWN_LESION_MEASUREMENT_IDS)

    rows = []
    for metric in catalog.p003_metric_catalog():
        row = {'source_name': 'package_p003_metric_catalog', 'collection': metric['collection'],
               'domain': metric['domain'], 'source_measurement_id': metric['metric_id'],
               'input_source': metric['input_source'], 'unit': metric['unit'],
               'source_definition': metric.get('definition', '')} | blank_source_fields()
        row.update(source_record_id=f"{metric['collection']}:{metric['metric_id']}",
                   source_algorithm_version=metric['algorithm_version'], source_role=metric.get('role', ''))
        rows.append(row)
    for lesion in lesion_annotation_catalog():
        for measurement in KNOWN_LESION_MEASUREMENT_IDS:
            row = {'source_name': 'package_known_lesion_phenomics', 'collection': 'e046_known_lesion',
                   'domain': lesion['lesion_id'], 'source_measurement_id': measurement,
                   'input_source': 'expert_annotation_mask', 'unit': 'defined_by_metric',
                   'source_definition': ''} | blank_source_fields()
            row.update(source_record_id=f"{lesion['lesion_id']}:{measurement}",
                       source_algorithm_version=ALGORITHM_VERSION)
            rows.append(row)
    with E118_REGISTRY.open(encoding='utf-8', newline='') as handle:
        for entry in csv.DictReader(handle):
            row = {'source_name': 'e118_hierarchical_feature_registry', 'collection': 'e118_registry',
                   'domain': f"{entry['root']}/{entry['family']}",
                   'source_measurement_id': entry['source_feature_name'],
                   'input_source': entry['representation'], 'unit': entry['unit'],
                   'source_definition': entry['measurement_target']}
            row.update(source_record_id=entry['measurement_id'], source_concept_id=entry['concept_id'],
                       source_definition_sha256=entry['definition_sha256'], source_region=entry['region'],
                       source_statistic=entry['statistic'], source_coordinate_frame=entry['coordinate_frame'],
                       source_derived_from=entry['derived_from'], source_algorithm_version=entry['definition_source'],
                       source_role=entry['role'])
            rows.append(row)
    return rows


def infer_target(row: dict[str, str]) -> str:
    if row['collection'] == 'e046_known_lesion':
        return LESION_PREFIX_TARGET.get(row['domain'], '')
    for prefix in sorted(LESION_PREFIX_TARGET, key=len, reverse=True):
        if row['source_measurement_id'].startswith(prefix + '_'):
            return LESION_PREFIX_TARGET[prefix]
    return ''


def map_sources(sources, rules) -> list[dict[str, str]]:
    compiled = [(rule, re.compile(rule['pattern'])) for rule in rules]
    mapped = []
    for source in sources:
        key = f"{source['collection']}|{source['domain']}|{source['source_measurement_id']}"
        row = dict(source, target_id='', feature_id='', relation_type='unmapped', output_type='',
                   rule_id='', mapping_status='unreviewed_rule_candidate', note_ko='')
        for rule, pattern in compiled:
            if pattern.search(key):
                row.update(target_id=rule['target_id'] or infer_target(source), feature_id=rule['feature_id'],
                           relation_type=rule['relation_type'], output_type=rule['output_type'],
                           rule_id=rule['rule_id'], note_ko=rule['note_ko'])
                break
        mapped.append(row)
    return mapped


def build_applicability(tables) -> list[dict[str, str]]:
    """Derive target × feature applicability from direct targets, common sets and overrides."""
    rows = []
    seen = set()

    def add(target, feature, status, basis, note=''):
        key = (target, feature)
        if key in seen:
            return
        seen.add(key)
        rows.append({'target_id': target, 'feature_id': feature, 'applicability': status,
                     'basis': basis, 'note_ko': note})

    for feature in tables['d']:
        add(feature['target_id'], feature['feature_id'], 'direct', 'd_target')
    for override in tables['over']:
        add(override['target_id'], override['feature_id'], override['applicability'], 'override',
            override['note_ko'])
    sets = defaultdict(list)
    for entry in tables['sets']:
        sets[(entry['scope'], entry['class_id'])].append(entry)
    for scope, key, table in (('anatomy', 'measure_class', 'b'), ('lesion', 'morphology_class', 'c')):
        for entity in tables[table]:
            for entry in sets.get((scope, entity[key]), []):
                add(entity['entity_id'], entry['feature_id'], 'common_applied', f"class:{entity[key]}",
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


def outputs_compatible(left: str, right: str) -> bool:
    return left == right or any(left in group and right in group for group in COMPATIBLE_OUTPUTS)


def check_integrity(tables, f_rows, applicability) -> list[str]:
    errors = []
    ids = {}
    for name, key in (('a', 'imaging_id'), ('b', 'entity_id'), ('c', 'entity_id'), ('d', 'feature_id'),
                      ('e', 'disease_id'), ('src', 'source_id'), ('ef', 'relation_id'),
                      ('obs', 'observation_id')):
        values = [row[key] for row in tables[name]]
        errors += [f'duplicate {name} id: {v}' for v, n in Counter(values).items() if n > 1]
        ids[name] = set(values)
    entity_ids = ids['b'] | ids['c']
    target_ids = entity_ids | ids['a']
    feature_by_id = {row['feature_id']: row for row in tables['d']}

    def split(value):
        return [part for part in value.split(';') if part]

    def check_sources(label, value):
        return [f'{label}: unknown source {v}' for v in split(value) if v not in ids['src']]

    for name in ('b', 'c'):
        for row in tables[name]:
            label = row['entity_id']
            errors += [f'{label}: invalid {c}={row[c]!r}' for c in OBS_COLUMNS if row[c] not in OBS_VALUES]
            errors += [f'{label}: unknown imaging {v}' for v in split(row['best_imaging_ids']) if v not in ids['a']]
            errors += check_sources(label, row['source_ids'])
            if row['review_status'] not in REVIEW_STATUSES:
                errors.append(f'{label}: invalid review_status {row["review_status"]}')
    for row in tables['b']:
        if row['parent_id'] and row['parent_id'] not in ids['b']:
            errors.append(f"{row['entity_id']}: unknown parent {row['parent_id']}")
    for row in tables['c']:
        errors += [f"{row['entity_id']}: unknown structure {v}" for v in split(row['affected_structure_ids'])
                   if v not in ids['b']]
    for row in tables['a']:
        if row['parent_id'] and row['parent_id'] not in ids['a']:
            errors.append(f"{row['imaging_id']}: unknown parent {row['parent_id']}")
    for row in tables['d']:
        label = row['feature_id']
        if row['target_id'] not in target_ids:
            errors.append(f'{label}: unknown target {row["target_id"]}')
        errors += [f'{label}: unknown imaging {v}' for v in split(row['imaging_ids']) if v not in ids['a']]
        errors += check_sources(label, row['definition_source_ids'])
        if row['output_type'] not in OUTPUT_TYPES:
            errors.append(f'{label}: invalid output_type {row["output_type"]}')
        if row['review_status'] not in REVIEW_STATUSES:
            errors.append(f'{label}: invalid review_status {row["review_status"]}')
    for row in tables['e']:
        if row['parent_id'] and row['parent_id'] not in ids['e']:
            errors.append(f"{row['disease_id']}: unknown parent {row['parent_id']}")
    for row in tables['ef']:
        label = row['relation_id']
        if row['disease_id'] not in ids['e']:
            errors.append(f'{label}: unknown disease {row["disease_id"]}')
        if row['finding_id'] not in entity_ids | ids['d']:
            errors.append(f'{label}: unknown finding {row["finding_id"]}')
        if row['relation_type'] not in E_RELATIONS:
            errors.append(f'{label}: invalid relation {row["relation_type"]}')
        errors += check_sources(label, row['classification_source_id'])
        errors += check_sources(label, row['evidence_source_ids'])
        if row['review_status'] not in REVIEW_STATUSES:
            errors.append(f'{label}: invalid review_status {row["review_status"]}')
        if row['review_status'] != 'needs_source' and not row['evidence_source_ids']:
            errors.append(f'{label}: evidence missing but not marked needs_source')
    scheme_ids = {row['scheme_id'] for row in tables['gs']}
    for row in tables['gs']:
        label = row['scheme_id']
        if row['disease_id'] not in ids['e']:
            errors.append(f'{label}: unknown disease {row["disease_id"]}')
        if row['kind'] not in GRADING_KINDS:
            errors.append(f'{label}: invalid kind {row["kind"]}')
        errors += [f'{label}: unknown imaging {v}' for v in split(row['imaging_ids']) if v not in ids['a']]
        errors += check_sources(label, row['source_ids'])
        if row['review_status'] not in REVIEW_STATUSES:
            errors.append(f'{label}: invalid review_status {row["review_status"]}')
        if row['review_status'] != 'needs_source' and not row['source_ids']:
            errors.append(f'{label}: source missing but not marked needs_source')
    orders = Counter()
    for row in tables['gst']:
        label = row['step_id']
        if row['scheme_id'] not in scheme_ids:
            errors.append(f'{label}: unknown scheme {row["scheme_id"]}')
        if row['logic'] not in STEP_LOGIC:
            errors.append(f'{label}: invalid logic {row["logic"]}')
        errors += [f'{label}: unknown finding {v}' for v in split(row['finding_ids']) if v not in entity_ids | ids['d']]
        orders[(row['scheme_id'], row['step_order'])] += 1
    errors += [f'{k[0]}: duplicate step order {k[1]}' for k, n in orders.items() if n > 1]
    for row in tables['obs']:
        label = row['observation_id']
        if row['target_id'] not in entity_ids | ids['d']:
            errors.append(f'{label}: unknown target {row["target_id"]}')
        if row['imaging_id'] not in ids['a']:
            errors.append(f'{label}: unknown imaging {row["imaging_id"]}')
        errors += check_sources(label, row['source_ids'])
    for row in tables['sets']:
        if row['feature_id'] not in ids['d']:
            errors.append(f"common set {row['class_id']}: unknown feature {row['feature_id']}")
    for row in tables['over']:
        if row['target_id'] not in entity_ids:
            errors.append(f"override: unknown target {row['target_id']}")
        if row['feature_id'] and row['feature_id'] not in ids['d']:
            errors.append(f"override: unknown feature {row['feature_id']}")
    for row in applicability:
        if row['applicability'] not in APPLICABILITY:
            errors.append(f"applicability {row['target_id']}: invalid {row['applicability']}")
    applicable = {(r['target_id'], r['feature_id']) for r in applicability
                  if r['applicability'] in {'direct', 'common_applied'}}
    covered = {r['target_id'] for r in applicability}
    for table in ('b', 'c'):
        for entity in tables[table]:
            if entity['entity_id'] not in covered:
                errors.append(f"{entity['entity_id']}: no applicability status")
    for row in f_rows:
        label = f"{row['collection']}|{row['source_measurement_id']}"
        if row['relation_type'] not in F_RELATIONS:
            errors.append(f'{label}: invalid relation {row["relation_type"]}')
        if row['output_type'] and row['output_type'] not in OUTPUT_TYPES:
            errors.append(f'{label}: invalid output_type {row["output_type"]}')
        if row['target_id'] and row['target_id'] not in target_ids:
            errors.append(f'{label}: unknown target {row["target_id"]}')
        feature = feature_by_id.get(row['feature_id'])
        if row['feature_id'] and feature is None:
            errors.append(f'{label}: unknown feature {row["feature_id"]}')
            continue
        if feature is None or row['relation_type'] in {'qc_validation', 'image_signal', 'model_output',
                                                         'clinical_record'}:
            continue
        # F → D → C must not change the measured object (proxy is the only declared crossing).
        if row['target_id'] and row['relation_type'] != 'proxy' \
                and feature['target_id'] != row['target_id'] \
                and (row['target_id'], row['feature_id']) not in applicable:
            errors.append(f"{label}: target {row['target_id']} differs from feature target "
                          f"{feature['target_id']} without applicability")
        if row['relation_type'] in SEMANTIC_RELATIONS \
                and not outputs_compatible(row['output_type'], feature['output_type']):
            errors.append(f"{label}: output {row['output_type']} incompatible with "
                          f"{row['feature_id']} ({feature['output_type']})")
    return errors


OBS_MARK = {'direct': '●', 'limited': '◐', 'none': '—'}
REVIEW_MARK = {'draft': '초안', 'needs_source': '근거 필요', 'source_linked': '출처 연결',
               'definition_checked_abstract': '정의 확인(초록)', 'definition_checked': '정의 확인',
               'measurement_checked': '측정법 확인', 'expert_reviewed': '전문가 검토'}


def render(tables, f_rows, applicability) -> str:
    feature_name = {row['feature_id']: row['name_ko'] for row in tables['d']}
    feature_type = {row['feature_id']: row['feature_type'] for row in tables['d']}
    app_by_target = defaultdict(list)
    for row in applicability:
        app_by_target[row['target_id']].append(row)
    relations_by_finding = defaultdict(list)
    for row in tables['ef']:
        relations_by_finding[row['finding_id']].append(row)
    disease_name = {row['disease_id']: row['name_ko'] for row in tables['e']}
    f_by_feature = Counter(row['feature_id'] for row in f_rows if row['feature_id'])
    f_by_target = Counter(row['target_id'] for row in f_rows if row['target_id'])
    obs_by_target = Counter(row['target_id'] for row in tables['obs'])

    def obs(row):
        return ' '.join(OBS_MARK[row[c]] for c in OBS_COLUMNS)

    def features_text(target):
        items = app_by_target.get(target, [])
        statuses = {r['applicability'] for r in items}
        if not any(r['feature_id'] for r in items):
            return ('해당 없음' if 'not_applicable' in statuses else '미조사'), '—'
        def names(kind):
            parts = []
            for r in items:
                if r['feature_id'] and feature_type.get(r['feature_id']) == kind:
                    mark = '' if r['applicability'] == 'direct' else '*'
                    parts.append(feature_name[r['feature_id']] + mark)
            return '·'.join(parts) or '—'
        return names('qualitative'), names('quantitative')

    out = ['# 망막 영상 지도 조사 표 v01 (읽기용)', '',
           '2026-11-20 · medical-image-atlas 망막 영역 · `code/build_retinal_atlas_catalog.py`가 표 데이터에서 생성', '',
           '이 문서는 생성물이다. 내용을 고칠 때는 `retinal_atlas_catalog/`의 CSV를 고친 뒤 다시 만든다.',
           '범위와 규칙은 [조사 범위](../concept/40_retinal_atlas_survey_scope_v01_ko.md)를 따른다.', '',
           '**상태:** 범위가 넓은 목록 초안이다. 대부분의 정의는 원문 대조·전문가 검토 전이며, '
           'F 대응은 규칙으로 만든 미검토 후보다.', '',
           '- 관측 표시(영상 종류 단위의 신호 가용성): 안저 · OCT · OCTA · FAF · NIR · FA · ICGA '
           '(● 직접 · ◐ 제한 · — 없음). 표현 단위의 신호와 해석 조건은 관측 절에 따로 적는다.',
           '- 특징 이름 뒤 `*`는 공통 특징을 적용한 것(대상 고유 정의 아님)이다.',
           '- 검토 상태: 초안 → 출처 연결 → 정의 확인(초록) → 정의 확인 → 측정법 확인 → 전문가 검토.', '']
    out += ['## 요약', '', '| 목록 | 행 수 |', '| --- | ---: |']
    for label, key in (('A 영상 종류·표현', 'a'), ('B 해부 구조·위치 기준', 'b'), ('C 병변·소견', 'c'),
                       ('D 특징·측정', 'd'), ('E 질병', 'e'), ('E 질병–소견 관계', 'ef'),
                       ('관측(대상 × 영상 표현)', 'obs'), ('출처', 'src')):
        out.append(f'| {label} | {len(tables[key])} |')
    out.append(f'| F 기존 측정 등록 | {len(f_rows)} |')
    review_counts = Counter()
    for key in ('b', 'c', 'd', 'ef'):
        review_counts.update((key, r['review_status']) for r in tables[key])
    out += ['', '### 검토 상태', '', '| 목록 | ' + ' | '.join(REVIEW_MARK.values()) + ' |',
            '| --- | ' + ' | '.join('---:' for _ in REVIEW_MARK) + ' |']
    for label, key in (('B', 'b'), ('C', 'c'), ('D', 'd'), ('E 관계', 'ef')):
        out.append(f'| {label} | ' + ' | '.join(str(review_counts.get((key, s), 0)) for s in REVIEW_MARK) + ' |')
    app_counts = Counter()
    for key in ('b', 'c'):
        for entity in tables[key]:
            statuses = {r['applicability'] for r in app_by_target[entity['entity_id']]}
            state = 'direct' if 'direct' in statuses else ('common_applied' if 'common_applied' in statuses
                                                           else next(iter(statuses)))
            app_counts[(key, state)] += 1
    out += ['', '### 특징 연결 상태', '', '| 목록 | 고유 특징 있음 | 공통 특징만 | 해당 없음 | 미조사 |',
            '| --- | ---: | ---: | ---: | ---: |']
    for label, key in (('B', 'b'), ('C', 'c')):
        out.append(f"| {label} | " + ' | '.join(str(app_counts.get((key, s), 0)) for s in
                   ('direct', 'common_applied', 'not_applicable', 'not_investigated')) + ' |')
    out += ['', '## A. 영상 종류와 표현', '', '| ID | 수준 | 이름 | 보여주는 것 | 한계 | 수록 |',
            '| --- | --- | --- | --- | --- | --- |']
    for row in tables['a']:
        name = row['name_ko'] if row['level'] == 'modality' else '└ ' + row['name_ko']
        out.append(f"| `{row['imaging_id']}` | {row['level']} | {name} | {row['shows']} | {row['limits']} | {row['inclusion']} |")
    out += ['', '## B. 해부 구조와 위치 기준', '',
            '| ID | 이름 | 정의 | 관측 | 정성 특징 | 정량 측정 | 근거·검토 | 기존 측정 |',
            '| --- | --- | --- | --- | --- | --- | --- | ---: |']
    for row in tables['b']:
        qual, quant = features_text(row['entity_id'])
        out.append(f"| `{row['entity_id']}` | {row['name_ko']} ({row['name_en']}) | {row['definition_ko']} | {obs(row)} | {qual} | {quant} | {REVIEW_MARK[row['review_status']]} · {row['source_ids'] or '출처 없음'} | {f_by_target.get(row['entity_id'], 0)} |")
    groups = defaultdict(list)
    for row in tables['c']:
        groups[row['lesion_group']].append(row)
    out += ['', '## C. 병변·소견', '']
    for group, rows in groups.items():
        out += [f'### {group}', '',
                '| ID | 이름 | 정의 | 깊이 | 관측 | 정성 특징 | 정량 측정 | 관련 질병 | 근거·검토 | 기존 측정 |',
                '| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: |']
        for row in rows:
            qual, quant = features_text(row['entity_id'])
            diseases = sorted({disease_name[r['disease_id']] for r in relations_by_finding.get(row['entity_id'], [])})
            out.append(f"| `{row['entity_id']}` | {row['name_ko']} ({row['name_en']}) | {row['definition_ko']} | {row['depth_ko']} | {obs(row)} | {qual} | {quant} | {'·'.join(diseases) or '—'} | {REVIEW_MARK[row['review_status']]} · {row['source_ids'] or '출처 없음'} | {f_by_target.get(row['entity_id'], 0)} |")
        out.append('')
    out += ['## 관측: 대상 × 영상 표현', '',
            '영상 종류 단위의 관측 표시는 신호를 볼 수 있는지만 나타낸다. 아래는 표현 단위로 직접 보이는 것과 '
            '해석 조건을 분리한 기록이며, 아직 일부 대상만 작성했다.', '',
            '| 대상 | 영상 표현 | 직접 보이는 것 | 해석 조건 | 근거·검토 |', '| --- | --- | --- | --- | --- |']
    for row in tables['obs']:
        out.append(f"| `{row['target_id']}` | `{row['imaging_id']}` | {row['observed_signal_ko']} | {row['interpretation_condition_ko']} | {REVIEW_MARK[row['review_status']]} · {row['source_ids'] or '출처 없음'} |")
    out += ['', '## D. 특징·측정', '',
            '| ID | 대상 | 유형 | 출력 | 이름 | 정의 | 구역 | 단위 | 조건 | 단계 | 근거·검토 | 기존 측정 |',
            '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: |']
    for row in tables['d']:
        out.append(f"| `{row['feature_id']}` | `{row['target_id']}` | {row['feature_type']} | {row['output_type']} | {row['name_ko']} | {row['definition_ko']} | {row['region_spec']} | {row['unit']} | {row['requirements']} | {row['detail_stage']} | {REVIEW_MARK[row['review_status']]} · {row['definition_source_ids'] or '출처 없음'} | {f_by_feature.get(row['feature_id'], 0)} |")
    out += ['', '## E. 질병과 소견의 관계', '']
    by_disease = defaultdict(list)
    for row in tables['ef']:
        by_disease[row['disease_id']].append(row)
    for disease in tables['e']:
        rows = by_disease.get(disease['disease_id'], [])
        if not rows:
            continue
        out += [f"### {disease['name_ko']} ({disease['name_en']}) · {disease['scope']}", '',
                '| 소견·측정 | 관계 | 분류 체계·판본 | 조건 | 근거·검토 |', '| --- | --- | --- | --- | --- |']
        for row in rows:
            out.append(f"| `{row['finding_id']}` | {row['relation_type']} | {row['classification_version']} | {row['condition_ko']} | {REVIEW_MARK[row['review_status']]} · {row['evidence_source_ids'] or '근거 없음'} |")
        out.append('')
    out += ['## F. 기존 측정 대응', '',
            '모든 F 관계는 규칙으로 만든 **미검토 후보**다. 같은 정의로 확정한 대응은 아직 0건이며, '
            '이것이 동등한 측정이 없다는 증명은 아니다. 대상·특징·출력 형태의 일관성만 자동 검사했다.', '',
            '### 관계 유형별 개수', '', '| 출처 | ' + ' | '.join(sorted(F_RELATIONS)) + ' | 합계 |',
            '| --- | ' + ' | '.join('---:' for _ in F_RELATIONS) + ' | ---: |']
    for source in sorted({r['source_name'] for r in f_rows}):
        counts = Counter(r['relation_type'] for r in f_rows if r['source_name'] == source)
        out.append(f'| {source} | ' + ' | '.join(str(counts.get(k, 0)) for k in sorted(F_RELATIONS))
                   + f' | {sum(counts.values())} |')
    out += ['', '같은 측정이 여러 출처에 재등록될 수 있으므로 합계는 고유 측정 개수가 아니다. 원본 ID·개념 ID·정의 해시·'
            '구역·통계량·파생 관계는 `retinal_atlas_catalog/f_existing_measurements_v01.csv`에 보존했다.', '']
    out += ['## 미확인·확인 필요 목록', '']
    needs = [r['relation_id'] for r in tables['ef'] if r['review_status'] == 'needs_source']
    out.append(f'- 근거 출처가 없는 질병–소견 관계 {len(needs)}건/{len(tables["ef"])}건(분류 이외의 활동성·예후·동반 소견 포함)')
    pending = [r['source_id'] for r in tables['src'] if r['verification'] not in {'pmid_checked', 'doi_checked', 'url_checked', 'internal'}]
    out.append('- 서지 확인이 남은 출처: ' + ', '.join(f'`{p}`' for p in pending))
    for key, label in (('c', 'C'), ('b', 'B')):
        compressed = [r['entity_id'] for r in tables[key] if r.get('definition_check') == 'compressed_needs_expansion']
        if compressed:
            out.append(f'- 정의가 지나치게 축약돼 원문 대조·확장이 필요한 {label} 항목 {len(compressed)}건: '
                       + ', '.join(f'`{n}`' for n in compressed))
    not_inv = sorted({r['target_id'] for r in applicability if r['applicability'] == 'not_investigated'})
    out.append(f'- 특징 연결이 미조사인 대상 {len(not_inv)}건: ' + ', '.join(f'`{n}`' for n in not_inv))
    no_obs = [r['entity_id'] for r in tables['c'] if r['status'] == 'stage1_drafted' and not obs_by_target.get(r['entity_id'])]
    out.append(f'- 표현 단위 관측 기록이 없는 1차 병변 {len(no_obs)}건(영상 종류 단위 표시만 있음)')
    out.append('- D 측정 정의의 출처가 없는 특징 '
               f"{sum(1 for r in tables['d'] if not r['definition_source_ids'])}건/{len(tables['d'])}건")
    out.append('- 모든 항목의 대표 실제 영상은 아직 수집하지 않았다(영상 미확보).')
    return '\n'.join(out) + '\n'


WEB_DATA = PROJECT / 'packages/retinal-atlas-web/src/retinal_atlas_web/data/atlas.json'
LESION_GROUP_KO = {
    'vascular': '혈관 변화', 'hemorrhage': '출혈', 'neovascular': '신생혈관', 'perfusion': '관류',
    'ischemic': '허혈', 'exudate_deposit': '삼출물·침착물', 'fluid_elevation': '액체 공간·융기',
    'reflectivity_layer': '반사 소견·층 배열', 'outer_retina_rpe': '외망막·RPE 변화', 'pigment': '색소 변화',
    'vitreoretinal_interface': '유리체–망막 경계', 'peripheral_detachment': '주변부 변성·망막박리',
    'optic_disc': '시신경유두', 'scar_treatment': '반흔·치료 흔적', 'myopic': '근시성 변화',
    'choroidal': '맥락막', 'aggregate': '기존 측정의 통합 대상', 'tumor_secondary': '종양(2차 범위)',
    'inflammatory_secondary': '염증(2차 범위)', 'inherited_secondary': '유전 질환(2차 범위)',
}
ANATOMY_GROUP = {
    'reference': ('reference', '위치 기준·구역'), 'zone': ('reference', '위치 기준·구역'),
    'region': ('region', '영역'), 'structure': ('structure', '구조'),
    'layer': ('layer', '망막·맥락막의 층과 경계'), 'band': ('layer', '망막·맥락막의 층과 경계'),
    'measurement_region': ('layer', '망막·맥락막의 층과 경계'), 'boundary': ('layer', '망막·맥락막의 층과 경계'),
    'vessel': ('vessel', '혈관'),
}
OBS_KEYS = {'obs_cfp': 'cfp', 'obs_oct': 'oct', 'obs_octa': 'octa', 'obs_faf': 'faf', 'obs_nir': 'nir',
            'obs_fa': 'fa', 'obs_icga': 'icga'}
HIDDEN_TARGETS = {'les_generic', 'ana_generic_layer'}


def slug_of(entity_id: str) -> str:
    return entity_id.split('_', 1)[1].replace('_', '-')


INPUT_CATEGORY = {
    'fundus_rgb': 'auto', 'partition_vessel': 'auto', 'partition_vessel_two_thinnings': 'auto',
    'sato_lines_union_thinning': 'auto',
    'vessel_mask': 'auto_seg', 'rgb_vessel_mask_and_label_blind_landmarks': 'auto_seg',
    'rgb_and_expert_or_validated_masks': 'mask', 'rgb_and_expert_or_validated_lesion_masks': 'mask',
    'expert_annotation_mask': 'mask', 'integer_label_mask': 'mask', 'binary_mask': 'mask',
    'direct_and_upstream_metrics': 'mask', 'upstream_model_output': 'model',
    'clinical_text_evidence_span': 'record', 'structured_field': 'record',
    'prediction_and_ground_truth_masks': 'qc',
}
LEVEL_ORDER = ['auto', 'auto_seg', 'mask', 'model', 'record']
SOURCE_LABEL = {'package_p003_metric_catalog': '정량화 패키지', 'package_known_lesion_phenomics': '병변 주석 계측',
                'e118_hierarchical_feature_registry': '안저 특징 등록표(E118)'}


def measure_registry() -> dict:
    """Feature ID → retinal-measures registry entry (function, input, method, reference)."""
    if str(MEASURES_SRC) not in sys.path:
        sys.path.insert(0, str(MEASURES_SRC))
    from retinal_measures.registry import INPUT_LABELS, REGISTRY
    return {fid: {'function': 'retinal_measures.' + e.function, 'input': e.input,
                  'input_label': INPUT_LABELS[e.input], 'method': e.method, 'reference': e.reference}
            for fid, e in REGISTRY.items()}


def implementation_summary(feature_id: str, target_id: str, f_rows, package=None) -> dict:
    """How (and whether) a feature is computed by an existing implementation, best path first."""
    rows = [r for r in f_rows if r['feature_id'] == feature_id]
    image_level = target_id.startswith('img_')
    usable = [r for r in rows if r['relation_type'] in {'same_definition', 'variant_specification', 'derived'}
              or (image_level and r['relation_type'] in {'image_signal', 'qc_validation'})]
    categories = {INPUT_CATEGORY.get(r['input_source'], 'mask') for r in usable}
    level = next((c for c in LEVEL_ORDER if c in categories), None)
    if level is None:
        if any(r['relation_type'] == 'proxy' for r in rows):
            level = 'proxy'
        elif any(r['relation_type'] == 'clinical_record' for r in rows):
            level = 'record'
        else:
            level = 'none'
    if package and level in {'proxy', 'none'}:
        level = 'package'
    return {'level': level, 'package': package, 'count': len(rows), 'usable': len(usable),
            'sources': sorted({SOURCE_LABEL.get(r['source_name'], r['source_name']) for r in rows}),
            'inputs': sorted({r['input_source'] for r in usable or rows}),
            'examples': [r['source_measurement_id'] for r in (usable or rows)[:4]]}


def export_web_data(tables, applicability, f_rows) -> dict:
    """Return the self-contained JSON payload used by the retinal-atlas-web package."""
    registry = measure_registry()
    unknown = sorted(set(registry) - {row['feature_id'] for row in tables['d']})
    if unknown:
        raise ValueError(f'retinal-measures registry names unknown features: {unknown}')
    features = {row['feature_id']: row for row in tables['d']}
    f_count = Counter(row['target_id'] for row in f_rows if row['target_id'])
    obs_by_target = defaultdict(list)
    for row in tables['obs']:
        obs_by_target[row['target_id']].append({
            'imaging': row['imaging_id'], 'signal': row['observed_signal_ko'],
            'condition': row['interpretation_condition_ko'], 'sources': row['source_ids'].split(';') if row['source_ids'] else [],
            'review': row['review_status']})
    app_by_target = defaultdict(list)
    for row in applicability:
        app_by_target[row['target_id']].append(row)
    relations = defaultdict(list)
    for row in tables['ef']:
        relations[row['finding_id']].append(row)
    lesions_by_structure = defaultdict(list)
    for row in tables['c']:
        for structure in filter(None, row['affected_structure_ids'].split(';')):
            lesions_by_structure[structure].append(row['entity_id'])
    children = defaultdict(list)
    for row in tables['b']:
        if row['parent_id'] and row['entity_id'] not in HIDDEN_TARGETS:
            children[row['parent_id']].append(row['entity_id'])

    def feature_list(entity_id):
        items = []
        own = {(features[a['feature_id']]['axis'], features[a['feature_id']]['output_type'])
               for a in app_by_target.get(entity_id, [])
               if a['applicability'] == 'direct' and a['feature_id'] in features}
        for app in app_by_target.get(entity_id, []):
            feature = features.get(app['feature_id'])
            if not feature or feature.get('feature_role') == 'classification':
                continue  # classification outputs belong to disease criteria, not measurement lists
            # A common feature adds nothing when the item already defines its own on the same axis and output.
            if app['applicability'] != 'direct' and (feature['axis'], feature['output_type']) in own:
                continue
            items.append({'id': feature['feature_id'], 'name': feature['name_ko'], 'type': feature['feature_type'],
                          'axis': feature['axis'], 'definition': feature['definition_ko'], 'unit': feature['unit'],
                          'region': feature['region_spec'], 'requirements': feature['requirements'],
                          'imaging': feature['imaging_ids'].split(';'), 'common': app['applicability'] != 'direct',
                          'review': feature['review_status']})
        return items

    def disease_links(finding_ids):
        out = []
        for finding in finding_ids:
            for rel in relations.get(finding, []):
                out.append({'disease': rel['disease_id'], 'finding': finding, 'type': rel['relation_type'],
                            'version': rel['classification_version'], 'condition': rel['condition_ko'],
                            'sources': [s for s in (rel['evidence_source_ids'] or rel['classification_source_id']).split(';') if s],
                            'review': rel['review_status']})
        return out

    def feature_status(entity_id):
        statuses = {r['applicability'] for r in app_by_target.get(entity_id, [])}
        for state in ('direct', 'common_applied', 'not_applicable', 'not_investigated'):
            if state in statuses:
                return state
        return 'not_investigated'

    items = {}
    for row in tables['b']:
        if row['entity_id'] in HIDDEN_TARGETS:
            continue
        group, group_label = ANATOMY_GROUP.get(row['kind'], ('structure', '구조'))
        own = feature_list(row['entity_id'])
        items[row['entity_id']] = {
            'id': row['entity_id'], 'section': 'anatomy', 'slug': slug_of(row['entity_id']), 'order': len(items),
            'group': group, 'group_label': group_label, 'kind': row['kind'], 'axis': row['map_axis'], 'subgroup': row['map_subgroup'],
            'name': row['name_ko'], 'name_en': row['name_en'], 'abbr': row['abbreviation'],
            'definition': row['definition_ko'], 'location': row['location_ko'], 'parent': row['parent_id'],
            'children': children.get(row['entity_id'], []), 'obs': {v: row[k] for k, v in OBS_KEYS.items()},
            'best_imaging': [i for i in row['best_imaging_ids'].split(';') if i],
            'features': own, 'feature_status': feature_status(row['entity_id']),
            'observations': obs_by_target.get(row['entity_id'], []),
            'related_lesions': lesions_by_structure.get(row['entity_id'], []),
            'diseases': disease_links([row['entity_id']]),
            'sources': [s for s in row['source_ids'].split(';') if s], 'basis': row['definition_basis'],
            'review': row['review_status'], 'existing_measures': f_count.get(row['entity_id'], 0)}
    for row in tables['c']:
        if row['entity_id'] in HIDDEN_TARGETS or row['status'] == 'out_of_retinal_imaging':
            continue
        own = feature_list(row['entity_id'])
        finding_ids = [row['entity_id']] + [f['id'] for f in own if not f['common']]
        items[row['entity_id']] = {
            'id': row['entity_id'], 'section': 'lesions', 'slug': slug_of(row['entity_id']), 'order': len(items),
            'group': row['lesion_group'], 'group_label': LESION_GROUP_KO.get(row['lesion_group'], row['lesion_group']),
            'kind': row['morphology_class'], 'secondary': row['status'] == 'stage2_secondary',
            'aggregate': row['lesion_group'] == 'aggregate',
            'name': row['name_ko'], 'name_en': row['name_en'], 'abbr': row['abbreviation'],
            'definition': row['definition_ko'], 'location': row['depth_ko'], 'differentials': row['differentials_ko'],
            'structures': [s for s in row['affected_structure_ids'].split(';') if s and s not in HIDDEN_TARGETS],
            'obs': {v: row[k] for k, v in OBS_KEYS.items()},
            'best_imaging': [i for i in row['best_imaging_ids'].split(';') if i],
            'features': own, 'feature_status': feature_status(row['entity_id']),
            'observations': obs_by_target.get(row['entity_id'], []),
            'diseases': disease_links(finding_ids),
            'sources': [s for s in row['source_ids'].split(';') if s], 'basis': row['definition_basis'],
            'review': row['review_status'], 'existing_measures': f_count.get(row['entity_id'], 0)}
    slugs = Counter((item['section'], item['slug']) for item in items.values())
    duplicates = [key for key, count in slugs.items() if count > 1]
    if duplicates:
        raise ValueError(f'duplicate web slugs: {duplicates}')
    return {
        'version': 'v01', 'generated_by': 'code/build_retinal_atlas_catalog.py',
        'imaging': {row['imaging_id']: {'name': row['name_ko'], 'name_en': row['name_en'], 'level': row['level'],
                                        'parent': row['parent_id'], 'shows': row['shows'], 'limits': row['limits'],
                                        'inclusion': row['inclusion']} for row in tables['a']},
        'diseases': {row['disease_id']: {
            'id': row['disease_id'], 'slug': slug_of(row['disease_id']), 'name': row['name_ko'],
            'name_en': row['name_en'], 'abbr': row['abbreviation'], 'scope': row['scope'], 'parent': row['parent_id'],
            'note': row['note_ko'],
            'classification_sources': [s for s in row['classification_source_ids'].split(';') if s],
            'children': [r['disease_id'] for r in tables['e'] if r['parent_id'] == row['disease_id']],
            'relations': [{'finding': rel['finding_id'], 'type': rel['relation_type'],
                           'version': rel['classification_version'], 'condition': rel['condition_ko'],
                           'sources': [s for s in (rel['evidence_source_ids'] or rel['classification_source_id']).split(';') if s],
                           'review': rel['review_status']}
                          for rel in tables['ef'] if rel['disease_id'] == row['disease_id']],
            'grading': [{
                'id': gs['scheme_id'], 'name': gs['name_ko'], 'kind': gs['kind'],
                'imaging': [i for i in gs['imaging_ids'].split(';') if i], 'read_rule': gs['read_rule_ko'],
                'sources': [x for x in gs['source_ids'].split(';') if x], 'review': gs['review_status'], 'note': gs['note_ko'],
                'steps': [{'grade': st['grade_ko'], 'logic': st['logic'],
                           'criteria': [c.strip() for c in st['criteria_ko'].split('|') if c.strip()],
                           'findings': [x for x in st['finding_ids'].split(';') if x], 'note': st['note_ko']}
                          for st in sorted((t for t in tables['gst'] if t['scheme_id'] == gs['scheme_id']),
                                           key=lambda t: int(t['step_order']))],
            } for gs in tables['gs'] if gs['disease_id'] == row['disease_id']],
        } for row in tables['e']},
        'features': {row['feature_id']: {
            'id': row['feature_id'], 'target': row['target_id'], 'name': row['name_ko'], 'type': row['feature_type'],
            'definition': row['definition_ko'], 'unit': row['unit'], 'region': row['region_spec'],
            'requirements': row['requirements'], 'imaging': [i for i in row['imaging_ids'].split(';') if i],
            'axis': row['axis'], 'output': row['output_type'], 'review': row['review_status'],
            'role': row['feature_role'],
            'impl': implementation_summary(row['feature_id'], row['target_id'], f_rows,
                                           registry.get(row['feature_id']))} for row in tables['d']},
        'sources': {row['source_id']: {'name': row['short_name'], 'citation': row['citation'], 'url': row['url'],
                                       'verification': row['verification']} for row in tables['src']},
        'items': items,
    }


def write_csv(path: Path, columns, rows) -> None:
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({k: row[k] for k in columns} for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='validate only; do not write outputs')
    args = parser.parse_args()
    tables = load_tables()
    f_rows = map_sources(registered_sources(), read_table('f_mapping_rules_v01.csv'))
    applicability = build_applicability(tables)
    errors = check_integrity(tables, f_rows, applicability)
    for error in errors:
        print('ERROR', error, file=sys.stderr)
    counts = Counter(r['relation_type'] for r in f_rows)
    print(f'F rows={len(f_rows)} ' + ' '.join(f'{k}={v}' for k, v in sorted(counts.items()))
          + f' applicability={len(applicability)} errors={len(errors)}')
    if errors:
        return 1
    if not args.check:
        write_csv(CATALOG / 'f_existing_measurements_v01.csv', F_COLUMNS, f_rows)
        write_csv(CATALOG / 'd_feature_applicability_v01.csv',
                  ('target_id', 'feature_id', 'applicability', 'basis', 'note_ko'), applicability)
        READING_DOC.write_text(render(tables, f_rows, applicability), encoding='utf-8')
        payload = export_web_data(tables, applicability, f_rows)
        WEB_DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + '\n',
                            encoding='utf-8')
        print(f'wrote {READING_DOC.relative_to(PROJECT)} and {WEB_DATA.relative_to(PROJECT)} '
              f'({len(payload["items"])} items)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
