"""Server-rendered mammography atlas (2D mammography, DBT, CEM); no portal or experiment dependency.

``data/atlas.json`` is generated from the domain tables by ``code/build_mammography_atlas_catalog.py``;
``data/masked_figures.json`` and ``data/measurement_examples.json`` by ``code/build_mammography_figures.py``.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_file

from .code_links import PACKAGES, CodeIndex, default_packages_root
from .disease_links import measurement_diseases

DATA = Path(__file__).parent / 'data'
NAV = [('/', '홈', 'home'), ('/anatomy/', '해부학 지도', 'anatomy'), ('/lesions/', '병변 목록', 'lesions'),
       ('/measurements/', '측정 목록', 'measurements'), ('/diseases/', '질병 목록', 'diseases'),
       ('/imaging/', '영상 종류', 'imaging')]
MODALITIES = [('ffdm', '2D 유방촬영'), ('dbt', 'DBT'), ('cem', 'CEM')]
MODALITY_VIEWS = {
    'ffdm': {'imaging_id': 'img_ffdm', 'short': 'FFDM',
             'summary': '유방을 눌러 펴고 위→아래(CC)와 사선(MLO) 두 방향으로 찍는 2D X선 영상. 선별 검사의 기본입니다.'},
    'dbt': {'imaging_id': 'img_dbt', 'short': 'DBT',
            'summary': 'X선관을 호 모양으로 움직이며 여러 각도로 찍어 1 mm 안팎 간격의 단면으로 재구성합니다. 조직 겹침이 줄어듭니다.'},
    'cem': {'imaging_id': 'img_cem', 'short': 'CEM',
            'summary': '요오드 조영제를 주사한 뒤 저·고에너지로 찍고 감산해 조영 증강되는 병변을 보는 2D 영상입니다.'},
}
MODALITY_FIGURES = {
    'ffdm': ['anat_dense_cc', 'anat_pectoralis', 'mass_spiculated_1', 'calc_cluster_1'],
    'dbt': ['dbt_vs_2d', 'mass_spiculated_dbt', 'distortion_dbt', 'calc_dbt'],
    'cem': ['enhancing_mass_cem', 'nme_cem', 'bpe_cem'],
}
OBS_LABEL = {'direct': '직접 관찰', 'limited': '제한적', 'none': '—'}
REVIEW_LABEL = {'draft': '서비스 초안', 'needs_source': '근거 필요', 'source_linked': '출처 연결',
                'definition_checked_abstract': '정의 확인(초록)', 'definition_checked': '정의 확인',
                'measurement_checked': '측정법 확인', 'expert_reviewed': '전문가 검토'}
RELATION_LABEL = {'diagnostic_criterion': '진단·판정 기준 소견', 'severity_classification': '병기·단계 판정에 쓰는 소견',
                  'activity_monitoring': '경과 관찰', 'prognostic': '위험·예후 관련',
                  'characteristic_nonspecific': '동반 소견(비특이)'}
RELATION_ORDER = list(RELATION_LABEL)
FEATURE_STATUS_LABEL = {'direct': '고유 특징', 'common_applied': '공통 특징 적용', 'not_applicable': '측정 대상 아님',
                        'not_investigated': '특징 미정리'}
MAP_AXES = [
    ('face', '영상에서 보는 위치', '사분면 · 유륜하 · 중앙부 · 액와 꼬리 등 위치 구역과 유두·액와'),
    ('tissue', '조직층과 구조', '피부에서 흉벽까지의 층 · 실질 · 대흉근'),
    ('reference', '측정 기준', '유두 · 후유두선 · 대흉근 경계와 위치를 적는 체계'),
]
LESION_CATEGORIES = [
    ('mass', '종괴', '두 방향에서 보이는 볼록한 병변 · 모양·경계·밀도로 서술', ['mass']),
    ('calc', '석회화', '형태와 분포로 전형적 양성과 의심을 가름', ['calcification', 'calcification_suspicious',
                                                              'calcification_benign']),
    ('distortion', '구조왜곡·비대칭', '종괴 없이 실질 배열이나 양이 달라진 소견', ['distortion', 'asymmetry']),
    ('other', '그 밖의 소견·동반 소견', '림프절 · 피부 · 유관과 함몰·비후 등 동반 소견', ['other_finding', 'associated']),
    ('treatment', '치료 흔적·기구', '흉터 · 조직검사 표지자 · 보형물', ['treatment']),
    ('enhancement', '조영 증강(CEM)', 'CEM 재조합 영상에서 증강되는 병변', ['enhancement']),
]
DISEASE_CLUSTERS = [
    ('malignant', '유방암', ['dis_breast_cancer', 'dis_idc', 'dis_ilc', 'dis_dcis', 'dis_mucinous_carcinoma',
                          'dis_inflammatory_breast_cancer', 'dis_paget_nipple']),
    ('benign_mass', '양성 종괴', ['dis_fibroadenoma', 'dis_breast_cyst', 'dis_phyllodes_tumor', 'dis_intraductal_papilloma',
                              'dis_lipoma', 'dis_hamartoma']),
    ('benign_change', '양성 변화', ['dis_fibrocystic_change', 'dis_duct_ectasia', 'dis_radial_scar']),
    ('inflammatory', '염증·외상·치료 후', ['dis_mastitis_abscess', 'dis_fat_necrosis', 'dis_post_treatment_change']),
    ('nodes_vessels', '림프절·혈관', ['dis_axillary_lymphadenopathy', 'dis_breast_arterial_calcification']),
]
IMPL_LEVELS = [
    ('auto', '영상만으로 자동', '유방촬영 한 장만 넣으면 경계·유두·대흉근을 찾아 계산'),
    ('mask', '병변 mask 입력', '병변 범위(전문가 주석 또는 검증된 분할)를 함께 넣으면 계산'),
    ('pair', '영상 쌍 필요', '같은 유방의 CC·MLO 또는 좌우 같은 방향 영상 쌍이 필요'),
    ('reading', '판독', '눈으로 판단하는 서술 항목(계산 코드 없음)'),
    ('none', '구현 없음', '정의만 있고 계산 구현이 아직 없음'),
]
READY_LEVELS = {'auto', 'mask', 'pair'}
SCHEMATIC_ITEMS = {
    'ana_breast', 'ana_upper_outer_quadrant', 'ana_upper_inner_quadrant', 'ana_lower_outer_quadrant',
    'ana_lower_inner_quadrant', 'ana_subareolar_region', 'ana_central_region', 'ana_axillary_tail', 'ana_nipple_areola',
    'ana_inframammary_fold', 'ana_axilla', 'ana_axillary_lymph_nodes', 'ana_skin', 'ana_subcutaneous_fat',
    'ana_fibroglandular_tissue', 'ana_retromammary_fat', 'ana_pectoralis_major', 'ana_chest_wall', 'ref_nipple',
    'ref_posterior_nipple_line', 'ref_pectoral_edge', 'zone_quadrants', 'zone_depth_thirds', 'zone_clock_face',
    'ana_cooper_ligaments', 'ana_ducts'}
UNIT_TEXT = [('count/area', '개/면적'), ('mm2', 'mm²'), ('px2', 'px²'), ('category', '범주'), ('presence', '있음/없음'),
             ('ratio', '비율'), ('index', '지수'), ('count', '개')]
# Why a measurement has no image example on a given image type yet.
DBT_REASON = '이 측정을 보여 줄 DBT 그림을 CC BY 논문에서 아직 찾지 못함(공개 DBT 영상 자료는 CC BY-NC)'
CEM_REASON = '이 측정을 보여 줄 CEM 그림을 CC BY 논문에서 아직 찾지 못함'
PENDING_REASON_BY_MODALITY = {
    ('dbt', 'ft_calc_distribution'): '석회화 DBT 그림의 저자가 분포를 서술하지 않음',
}
PRIOR = '같은 유방의 이전 검사 영상이 필요하나 DMID에는 시점 정보가 없음'
BILATERAL = '같은 검사의 좌우 같은 방향 영상 쌍이 필요하나 DMID는 환자 번호를 주지 않음'
PENDING_REASON = {
    'ft_lesion_generic_change': PRIOR, 'ft_asym_bilateral_difference': BILATERAL,
    'ft_asym_area': '비대칭 ROI가 있는 DMID 영상이 없음(비대칭 6건 모두 mask 없음)',
    'ft_skin_thickness': '피부 두께를 재는 함수가 아직 없음(접선 방향 프로파일 필요)',
    'ft_ln_long_axis': '액와 림프절 주석이 있는 공개 영상이 없음', 'ft_ln_fatty_hilum': '액와 림프절 주석이 있는 공개 영상이 없음',
    'ft_ln_density': '액와 림프절 주석이 있는 공개 영상이 없음',
    'ft_imf_visible': '유방하주름 검출 함수가 아직 없음', 'ft_nipple_in_profile': '유두 측면 노출 판정 함수가 아직 없음',
    'ft_img_positioning_quality': 'CC·MLO 쌍의 자세 항목을 묶은 판정 함수가 아직 없음',
    'ft_mass_shape': '공급자가 모양을 따로 분류하지 않음(경계 분류만 있음)', 'ft_mass_density': '공급자가 밀도를 분류하지 않음',
    'ft_calc_distribution': '공급자가 분포를 분류하지 않음', 'ft_ad_presence': '판독 항목 · 구조왜곡 예시의 수렴 지수 참고',
}


def unit_text(value: str) -> str:
    for raw, label in UNIT_TEXT:
        value = value.replace(raw, label)
    return value


def _domain_resource(name: str, env: str) -> Path:
    if configured := os.environ.get(env):
        return Path(configured).expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / 'DOMAIN.yaml').is_file():
            return parent / 'resources/datasets' / name
    return Path('/data') / name


def modality_of(imaging_id: str) -> str:
    if imaging_id.startswith(('img_dbt', 'img_synthetic')):
        return 'dbt'
    if imaging_id.startswith('img_cem'):
        return 'cem'
    if imaging_id.startswith(('img_ffdm', 'img_spot', 'img_magnification')):
        return 'ffdm'
    return ''


def pending_by_modality(features: dict, items: dict, examples: list[dict]) -> dict[str, list[dict]]:
    """Per image type: measurements that apply to it but have no image example there, grouped by target."""
    shown: dict[str, set] = {}
    anywhere: dict[str, str] = {}
    for ex in examples:
        for layer in ex['layers']:
            for f in layer['features']:
                shown.setdefault(ex['modality'], set()).add(f['id'])
                anywhere.setdefault(f['id'], ex['id'])
    out: dict[str, list[dict]] = {}
    for mod, _ in MODALITIES:
        groups: dict[str, list[dict]] = {}
        for f in features.values():
            if (f['role'] != 'measurement' or f['id'] in shown.get(mod, set())
                    or mod not in {modality_of(i) for i in f.get('imaging', [])}):
                continue
            target = items.get(f.get('target') or '')
            impl = f.get('impl', {})
            reason = (PENDING_REASON_BY_MODALITY.get((mod, f['id'])) or PENDING_REASON.get(f['id'])
                      or {'dbt': DBT_REASON, 'cem': CEM_REASON}.get(mod, ''))
            groups.setdefault(target['name'] if target else '공통', []).append({
                'feature': f, 'target': target, 'level': impl.get('level', 'none'),
                'function': (impl.get('package') or {}).get('function', ''), 'elsewhere': anywhere.get(f['id']),
                'reason': reason})
        out[mod] = [{'label': k, 'rows': sorted(v, key=lambda r: r['feature']['name'])}
                    for k, v in sorted(groups.items(), key=lambda kv: (kv[0] == '공통', kv[0]))]
    return out


def load_content() -> dict:
    atlas = json.loads((DATA / 'atlas.json').read_text(encoding='utf-8'))
    items = atlas['items']
    masked = json.loads((DATA / 'masked_figures.json').read_text(encoding='utf-8'))['figures']
    masked_by_item = {item_id: [] for item_id in items}
    for fig in masked:
        for item_id in fig['items']:
            if item_id not in items:
                raise ValueError(f"masked figure {fig['id']} links unknown item {item_id}")
            masked_by_item[item_id].append(fig)
    masked_files = {name for fig in masked for name in (fig['base'], fig['overlay'], fig.get('context')) if name}
    examples = json.loads((DATA / 'measurement_examples.json').read_text(encoding='utf-8'))['examples']
    for ex in examples:
        for layer in ex['layers']:
            for f in layer['features']:
                if f['id'] not in atlas['features']:
                    raise ValueError(f"measurement example {ex['id']} names unknown feature {f['id']}")
    measure_files = {name for ex in examples for name in [ex['base']] + [la['file'] for la in ex['layers']]}
    by_slug = {(item['section'], item['slug']): item for item in items.values()}
    diseases = atlas['diseases']
    return {'atlas': atlas, 'items': items, 'masked': masked, 'masked_by_item': masked_by_item,
            'masked_files': masked_files, 'measure_examples': examples, 'measure_files': measure_files,
            'by_slug': by_slug, 'diseases': diseases, 'disease_by_slug': {d['slug']: d for d in diseases.values()},
            'measure_diseases': measurement_diseases(atlas)}


def item_path(item: dict) -> str:
    return f"/{item['section']}/{item['slug']}/"


def matches(item: dict, query: str) -> bool:
    if not query:
        return True
    haystack = ' '.join([item['name'], item['name_en'], item['abbr'], item['definition'], item.get('location', '')]).lower()
    return all(token in haystack for token in query.lower().split())


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(MASKED_ROOT=_domain_resource('mammography_atlas_masked_figures', 'MAMMOGRAPHY_ATLAS_MASKED_ROOT'),
                            MEASURE_ROOT=_domain_resource('mammography_atlas_measurement_examples', 'MAMMOGRAPHY_ATLAS_MEASURE_ROOT'),
                            PACKAGES_ROOT=default_packages_root())
    if config:
        app.config.update(config)
    masked_root = Path(app.config['MASKED_ROOT']).expanduser().resolve()
    measure_root = Path(app.config['MEASURE_ROOT']).expanduser().resolve()
    packages_root = app.config['PACKAGES_ROOT']
    code_index = CodeIndex(Path(packages_root).expanduser().resolve() if packages_root else None)
    content = load_content()
    atlas, items = content['atlas'], content['items']
    features = atlas['features']
    imaging_names = {k: v['name'] for k, v in atlas['imaging'].items()}

    @app.context_processor
    def shared_context():
        return {'nav': NAV, 'items': items, 'atlas': atlas, 'item_path': item_path, 'modalities': MODALITIES,
                'obs_label': OBS_LABEL, 'review_label': REVIEW_LABEL, 'relation_label': RELATION_LABEL,
                'feature_status_label': FEATURE_STATUS_LABEL, 'query': request.args.get('q', '').strip(),
                'schematic_items': SCHEMATIC_ITEMS, 'disease_by_id': content['diseases'],
                'impl_label': {k: label for k, label, _ in IMPL_LEVELS}, 'measure_diseases': content['measure_diseases'],
                'mod_key': {label: k for k, label in MODALITIES}}

    @app.after_request
    def response_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; "
            "frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'")
        return response

    app.add_template_filter(unit_text, 'unit')
    id_pattern = re.compile(r'\b(?:zone|ref|ana|les)_[a-z0-9_]+\b')

    def region_text(value: str) -> str:
        return id_pattern.sub(lambda m: items[m.group(0)]['name'] if m.group(0) in items else m.group(0), value or '')

    app.add_template_filter(region_text, 'region')

    def section_items(section):
        return sorted((i for i in items.values() if i['section'] == section), key=lambda i: i['order'])

    def modality_filter(entries):
        modality = request.args.get('img', '')
        if modality in dict(MODALITIES):
            entries = [e for e in entries if e['obs'].get(modality) in {'direct', 'limited'}]
        return entries, modality

    @app.get('/')
    def home():
        lesions = section_items('lesions')
        return render_template('home.html', active='home', title='유방촬영 영상 지도',
                               counts={'anatomy': len(section_items('anatomy')), 'lesions': len(lesions),
                                       'measures': sum(1 for f in features.values() if f['role'] == 'measurement'),
                                       'diseases': sum(1 for d in atlas['diseases'].values() if d['scope'] == 'primary')},
                               figures=[f for f in content['masked'] if not f['id'].startswith(('zone_', 'anat_'))][:6])

    @app.get('/anatomy/')
    def anatomy_index():
        entries, modality = modality_filter([i for i in section_items('anatomy') if matches(i, request.args.get('q', ''))])
        axes = []
        for key, label, note in MAP_AXES:
            members = [i for i in entries if i.get('axis') == key]
            axes.append({'key': key, 'label': label, 'note': note, 'members': members})
        return render_template('anatomy_index.html', active='anatomy', title='해부학 지도', axes=axes,
                               modality=modality, total=len(entries),
                               filtered=bool(modality or request.args.get('q')))

    @app.get('/lesions/')
    def lesion_index():
        entries, modality = modality_filter([i for i in section_items('lesions') if matches(i, request.args.get('q', ''))])
        category = request.args.get('cat', '')
        labels = {e['group']: e['group_label'] for e in section_items('lesions')}
        categories = []
        for key, label, note, groups in LESION_CATEGORIES:
            if category and category != key:
                continue
            sub = [(labels.get(g, g), g, [e for e in entries if e['group'] == g]) for g in groups]
            sub = [s for s in sub if s[2]]
            if sub:
                categories.append({'key': key, 'label': label, 'note': note, 'groups': sub,
                                   'count': sum(len(m) for _, _, m in sub)})
        counts = {key: sum(1 for e in section_items('lesions') if e['group'] in groups)
                  for key, _, _, groups in LESION_CATEGORIES}
        return render_template('lesion_index.html', active='lesions', title='병변 목록', categories=categories,
                               category_defs=LESION_CATEGORIES, counts=counts, category=category, modality=modality,
                               total=len(entries), filtered=bool(modality or request.args.get('q') or category))

    def render_item(section, slug):
        item = content['by_slug'].get((section, slug))
        if item is None:
            abort(404)
        siblings = [i for i in section_items(section) if i['group'] == item['group'] and i['id'] != item['id']]
        disease_groups = {}
        for link in item['diseases']:
            disease_groups.setdefault(link['disease'], []).append(link)
        examples = [ex for ex in content['measure_examples']
                    if any(f['id'] in {x['id'] for x in item['features']} for la in ex['layers'] for f in la['features'])]
        return render_template('item.html', active=section, title=item['name'], item=item,
                               masked=content['masked_by_item'][item['id']], siblings=siblings[:12],
                               disease_groups=disease_groups, examples=examples[:4])

    @app.get('/anatomy/<slug>/')
    def anatomy_item(slug):
        return render_item('anatomy', slug)

    @app.get('/lesions/<slug>/')
    def lesion_item(slug):
        return render_item('lesions', slug)

    @app.get('/search/')
    def search():
        query = request.args.get('q', '').strip()
        results = sorted((i for i in items.values() if query and matches(i, query)),
                         key=lambda i: (i['section'] != 'anatomy', i['name']))
        return render_template('search.html', active='', title='검색', results=results)

    def resolve_finding(finding_id):
        if finding_id in items:
            item = items[finding_id]
            measures = [f for f in item['features'] if f['type'] == 'quantitative' and not f['common']]
            measures = measures or [f for f in item['features'] if f['type'] == 'quantitative'][:4]
            where = [items[s] for s in item.get('structures', []) if s in items]
            mods = [label for key, label in MODALITIES if item['obs'].get(key) == 'direct']
            return {'kind': 'item', 'name': item['name'], 'link': item_path(item), 'location': item.get('location', ''),
                    'where': where, 'modalities': mods, 'measures': measures}
        feature = features.get(finding_id)
        if feature:
            target = items.get(feature['target'])
            return {'kind': 'feature', 'name': feature['name'],
                    'link': f"/measurements/code/{finding_id}/" if feature['role'] == 'measurement' else '',
                    'target': target, 'location': feature['region'], 'where': [target] if target else [],
                    'modalities': [imaging_names.get(i, i) for i in feature['imaging']], 'measures': [feature]}
        return {'kind': 'unknown', 'name': finding_id, 'link': '', 'location': '', 'where': [], 'modalities': [],
                'measures': []}

    def disease_summary(disease):
        relations = sorted(disease['relations'] + [r for cid in disease['children'] for r in content['diseases'][cid]['relations']],
                           key=lambda r: RELATION_ORDER.index(r['type']))
        names, mods = [], set()
        for rel in relations:
            info = resolve_finding(rel['finding'])
            if info['name'] not in names:
                names.append(info['name'])
            if rel['finding'] in items:
                mods |= {k for k, v in items[rel['finding']]['obs'].items() if v == 'direct'}
            elif rel['finding'] in features:
                mods |= {modality_of(i) for i in features[rel['finding']]['imaging']}
        schemes = [dict(g, owner=disease) for g in disease.get('grading', [])]
        return {'findings': names[:5], 'more': max(0, len(names) - 5), 'schemes': schemes,
                'modalities': [(k, label) for k, label in MODALITIES if k in mods]}

    @app.get('/diseases/')
    def disease_index():
        diseases = content['diseases']
        clusters = [{'key': key, 'label': label,
                     'members': [(diseases[i], disease_summary(diseases[i])) for i in ids if i in diseases]}
                    for key, label, ids in DISEASE_CLUSTERS]
        return render_template('disease_index.html', active='diseases', title='질병 목록', clusters=clusters,
                               diseases=diseases)

    @app.get('/diseases/<slug>/')
    def disease_page(slug):
        disease = content['disease_by_slug'].get(slug)
        if disease is None:
            abort(404)
        grouped = []
        for relation_type in RELATION_ORDER:
            rows = [dict(rel, finding_info=resolve_finding(rel['finding'])) for rel in disease['relations']
                    if rel['type'] == relation_type]
            if rows:
                grouped.append((relation_type, rows))
        ladders, node = [], disease
        while node:
            for scheme in node.get('grading', []):
                steps = [dict(st, finding_info=[resolve_finding(f) for f in st['findings']]) for st in scheme['steps']]
                ladders.append(dict(scheme, steps=steps, owner=node, inherited=node is not disease,
                                    imaging_names=[imaging_names.get(i, i) for i in scheme['imaging']]))
            node = content['diseases'].get(node['parent']) if node['parent'] else None
        return render_template('disease.html', active='diseases', title=disease['name'], disease=disease,
                               grouped=grouped, diseases=content['diseases'], ladders=ladders)

    def modality_summary(key):
        view = dict(MODALITY_VIEWS[key], key=key)
        record = atlas['imaging'][view['imaging_id']]
        children = [dict(v, id=i) for i, v in atlas['imaging'].items() if v.get('parent') == view['imaging_id']]
        seen = {(s, lv): [i for i in section_items(s) if i['obs'].get(key) == lv]
                for s in ('anatomy', 'lesions') for lv in ('direct', 'limited')}
        measures = [f for f in features.values() if f['role'] == 'measurement' and any(modality_of(i) == key for i in f['imaging'])]
        wanted = MODALITY_FIGURES[key]
        figs = sorted((f for f in content['masked'] if f['id'] in wanted), key=lambda f: wanted.index(f['id']))
        examples = [e for e in content['measure_examples'] if e['modality'] == key]
        return {'view': view, 'record': record, 'children': children, 'seen': seen, 'measures': measures,
                'figures': figs, 'examples': examples}

    @app.get('/imaging/')
    def modality_index():
        return render_template('modality_index.html', active='imaging', title='영상 종류',
                               cards=[modality_summary(k) for k, _ in MODALITIES])

    @app.get('/imaging/<key>/')
    def modality_page(key):
        if key not in MODALITY_VIEWS:
            abort(404)
        info = modality_summary(key)
        by_target = {}
        for f in info['measures']:
            by_target.setdefault(f['target'], []).append(f)
        groups = sorted(((items[t], fs) for t, fs in by_target.items() if t in items),
                        key=lambda p: (p[0]['section'] != 'anatomy', p[0]['order']))
        loose = [f for t, fs in by_target.items() if t not in items for f in fs]
        return render_template('modality.html', active='imaging', title=info['record']['name'], groups=groups,
                               loose=loose, **info)

    @app.get('/measurements/')
    def measurement_index():
        level = request.args.get('level', '')
        level = level if level in {k for k, _, _ in IMPL_LEVELS} | {'ready'} else ''
        kind = request.args.get('kind', '')
        kind = kind if kind in {'qualitative', 'quantitative'} else ''
        img = request.args.get('img', '')
        img = img if img in MODALITY_VIEWS else ''

        def mods_of(f):
            return {modality_of(i) for i in f['imaging']} - {''}

        def keep(f):
            if f['role'] != 'measurement' or (kind and f['type'] != kind) or (img and img not in mods_of(f)):
                return False
            if not level:
                return True
            return f['impl']['level'] in READY_LEVELS if level == 'ready' else f['impl']['level'] == level

        by_target = {}
        for f in features.values():
            by_target.setdefault(f['target'], []).append(f)

        def block(targets):
            return [(i, fs) for i in targets if (fs := [f for f in by_target.get(i['id'], []) if keep(f)])]

        anatomy, lesions = section_items('anatomy'), section_items('lesions')
        sections = []
        for key, label, note in MAP_AXES:
            if rows := block([i for i in anatomy if i.get('axis') == key]):
                sections.append({'key': 'a-' + key, 'label': label, 'kind': '해부 구조', 'note': note, 'rows': rows})
        for key, label, note, groups in LESION_CATEGORIES:
            if rows := block([i for i in lesions if i['group'] in groups]):
                sections.append({'key': 'l-' + key, 'label': label, 'kind': '병변', 'note': note, 'rows': rows})
        common = [f for f in by_target.get('les_generic', []) if keep(f)]
        image = [f for f in features.values() if f['target'].startswith('img_') and keep(f)]
        measures = [f for f in features.values() if f['role'] == 'measurement']
        all_levels = [f['impl']['level'] for f in measures]
        for s in sections:
            levels = [f['impl']['level'] for _, fs in s['rows'] for f in fs]
            s['count'], s['ready'] = len(levels), sum(1 for lv in levels if lv in READY_LEVELS)
        example_of = {}
        for ex in content['measure_examples']:
            for layer in ex['layers']:
                for f in layer['features']:
                    example_of.setdefault(f['id'], ex['id'])
        return render_template(
            'measurements.html', active='measurements', title='측정 목록', sections=sections,
            examples=content['measure_examples'], example_of=example_of,
            code_links={f['id']: code_index.links_for(f) for f in measures},
            packages=[(k, PACKAGES[k]) for k in PACKAGES if k in code_index.available], common=common, image=image,
            summary=[(k, label, note, all_levels.count(k)) for k, label, note in IMPL_LEVELS], total=len(all_levels),
            ready=sum(1 for lv in all_levels if lv in READY_LEVELS), level=level, levels=IMPL_LEVELS, kind=kind,
            type_counts={k: sum(1 for f in measures if f['type'] == k) for k in ('qualitative', 'quantitative')},
            packaged=sum(1 for f in measures if f['impl'].get('package')), img=img,
            img_counts=[(k, label, sum(1 for f in measures if k in mods_of(f)),
                         sum(1 for f in measures if k in mods_of(f) and f['impl']['level'] in READY_LEVELS))
                        for k, label in MODALITIES],
            img_names=dict(MODALITIES), feature_mods={f['id']: [k for k, _ in MODALITIES if k in mods_of(f)] for f in measures},
            pending=pending_by_modality(features, items, content['measure_examples']))

    @app.get('/measurements/code/<feature_id>/')
    def measurement_code(feature_id):
        feature = features.get(feature_id)
        if not feature or feature['role'] != 'measurement':
            abort(404)
        links = code_index.links_for(feature)
        fn = code_index.function_source(links['function']) if links['function'] else None
        example = next((ex for ex in content['measure_examples']
                        if any(f['id'] == feature_id for la in ex['layers'] for f in la['features'])), None)
        return render_template('measure_code.html', active='measurements', title=f"{feature['name']} · 코드",
                               feature=feature, target=items.get(feature['target']), links=links, fn=fn,
                               example=example, versions={k: code_index.version(k) for k in code_index.available})

    def serve_file(root, allowed, name):
        if name not in allowed:
            abort(404)
        target = root / name
        if not target.is_file():
            abort(503)
        return send_file(target, conditional=True, max_age=3600)

    @app.get('/figures/<name>')
    def masked_figure(name):
        return serve_file(masked_root, content['masked_files'], name)

    @app.get('/measure-figures/<name>')
    def measure_figure(name):
        return serve_file(measure_root, content['measure_files'], name)

    @app.get('/code/<package>.zip')
    def code_zip(package):
        if package not in code_index.available:
            abort(404)
        data, filename = code_index.zip_bytes(package)
        return Response(data, mimetype='application/zip', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    @app.get('/code/<package>/<path:rel>')
    def code_file(package, rel):
        target = code_index.safe_file(package, rel)
        if target is None:
            abort(404)
        headers = {'Content-Disposition': f'attachment; filename="{target.name}"'} if request.args.get('download') else {}
        return Response(target.read_text(encoding='utf-8'), mimetype='text/plain; charset=utf-8', headers=headers)

    @app.get('/sources/')
    def sources():
        image_sources = sorted({(f['name'], f['credit'], f['url'], f['license'], f['license_url']) for f in content['masked']})
        return render_template('sources.html', active='sources', title='출처와 라이선스', image_sources=image_sources)

    @app.get('/health')
    def health():
        missing = [n for n in content['masked_files'] if not (masked_root / n).is_file()]
        missing += [n for n in content['measure_files'] if not (measure_root / n).is_file()]
        ready = not missing
        return jsonify(status='ok' if ready else 'unavailable', site='mammography_atlas_web', stage='atlas_v01',
                       items=len(items), figures=len(content['masked']), examples=len(content['measure_examples']),
                       missing_files=len(missing)), 200 if ready else 503

    @app.errorhandler(404)
    @app.errorhandler(503)
    def unavailable(error):
        return render_template('error.html', active='', title='페이지를 표시할 수 없습니다', code=error.code), error.code

    return app
