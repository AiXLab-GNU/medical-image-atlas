"""Server-rendered pathology atlas (prostate H&E and IHC); no portal or experiment dependency.

``data/atlas.json`` is generated from the domain tables by ``code/build_pathology_atlas_catalog.py``;
``data/masked_figures.json`` and ``data/measurement_examples.json`` by ``code/build_pathology_figures.py``.
"""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_file

from .code_links import PACKAGES, CodeIndex, default_packages_root
from .disease_links import measurement_diseases

DATA = Path(__file__).parent / 'data'
NAV = [('/', '전립선 홈', 'home'), ('/anatomy/', '해부학 지도', 'anatomy'), ('/lesions/', '병변 목록', 'lesions'),
       ('/measurements/', '측정 목록', 'measurements'), ('/diseases/', '질병 목록', 'diseases'),
       ('/imaging/', '영상 종류', 'imaging')]
MODALITIES = [('he', 'H&E'), ('ihc', 'IHC')]
MODALITY_VIEWS = {
    'he': {'imaging_id': 'img_he', 'short': 'H&E',
           'summary': '헤마톡실린이 핵을 청자색으로, 에오신이 세포질·간질을 분홍색으로 물들인 조직 절편입니다. 병리 진단의 기본 영상입니다.'},
    'ihc': {'imaging_id': 'img_ihc', 'short': 'IHC',
            'summary': '항체로 특정 단백질을 색으로 표시합니다. 전립선에서는 기저세포(HMWCK·p63)와 AMACR로 침윤암과 모방 병변을 가릅니다.'},
}
MODALITY_FIGURES = {
    'he': ['core_tumor', 'benign_glands', 'gp4', 'cribriform'],
    'ihc': ['he_ihc_pair', 'ihc_basal', 'ihc_amacr', 'ihc_hgpin'],
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
    ('face', '전립선 구역과 구조', '구역(말초대·이행대·중심대) · 피막 · 요도 · 정낭'),
    ('tissue', '샘과 간질', '양성 샘 · 내강 · 분비 세포 · 기저세포층 · 간질 · 신경 · 혈관'),
    ('cell', '세포', '핵 · 핵소체'),
    ('reference', '측정 기준', '조직 면적 · 화소 크기 · 고배율 시야'),
]
LESION_CATEGORIES = [
    ('carcinoma', '선암과 글리슨 패턴', '침윤 선암과 패턴 3·4·5', ['carcinoma', 'gleason_pattern']),
    ('architecture', '패턴을 정하는 성장 양상', '불완전·융합·사상·사구체 샘, 고형 판, 면포 괴사', ['gleason_architecture']),
    ('intraductal', '관내·상피내 병변', '관내암 · 비정형 관내 증식 · 고등급 PIN', ['intraductal']),
    ('invasion', '침범', '신경주위 · 림프혈관 · 피막 밖 · 정낭 침범', ['invasion']),
    ('benign', '양성 병변과 암 모방', '위축 · 부분 위축 · 선증 · 기저세포 과형성 · 결절성 과형성 · 염증', ['benign_mimic', 'benign_change']),
    ('artifact', '인공물', '판독·측정에서 빼야 할 부분', ['artifact']),
]
DISEASE_CLUSTERS = [
    ('malignant', '전립선암', ['dis_prostate_adenocarcinoma', 'dis_idc_p', 'dis_ductal_adenocarcinoma']),
    ('precursor', '전구·비정형 병변', ['dis_hgpin', 'dis_asap']),
    ('benign', '양성 질환과 모방 병변', ['dis_bph', 'dis_prostatitis', 'dis_atrophy_benign', 'dis_adenosis']),
]
IMPL_LEVELS = [
    ('auto', '영상만으로 자동', 'H&E 영상만 넣으면 조직을 찾아 계산'),
    ('mask', '주석·mask 입력', '병변·샘·종양 주석(또는 검증된 분할)을 함께 넣으면 계산'),
    ('reading', '판독', '눈으로 판단하는 서술 항목(계산 코드 없음)'),
    ('none', '구현 없음', '정의만 있고 계산 구현이 아직 없음'),
]
READY_LEVELS = {'auto', 'mask'}
SCHEMATIC_ITEMS = {
    'ana_benign_gland', 'ana_gland_lumen', 'ana_secretory_cells', 'ana_basal_cell_layer', 'ana_corpora_amylacea',
    'ana_stroma', 'ana_nerve', 'ana_blood_vessel', 'ana_nucleus', 'ana_nucleolus', 'les_gleason_pattern_3',
    'les_gleason_pattern_4', 'les_gleason_pattern_5', 'les_cribriform', 'les_fused_glands', 'les_poorly_formed_glands',
    'les_solid_sheets', 'les_perineural_invasion', 'les_hgpin', 'les_intraductal_carcinoma', 'les_adenocarcinoma'}
UNIT_TEXT = [('count/mm2', '개/mm²'), ('count/area', '개/면적'), ('mm2', 'mm²'), ('um2', 'µm²'), ('px2', 'px²'),
             ('category', '범주'), ('presence', '있음/없음'), ('ratio', '비율'), ('index', '지수'), ('count', '개')]
IHC_REASON = 'IHC에서 이 측정을 보여 줄 주석 예시를 아직 만들지 않음'
PENDING_REASON = {
    'ft_basal_cell_presence': 'H&E만으로는 기저세포를 확실히 볼 수 없음 — 연속 절편 IHC를 정합한 예시(측정 표시 예시)와 IHC 탭 참고',
    'ft_basal_cell_coverage': 'H&E만으로는 기저세포를 확실히 볼 수 없음(IHC 탭 예시 참고)',
    'ft_nucleolus_prominence': '40× 핵소체 검출을 시도했으나 종양과 양성 샘을 가르지 못해(검증 페이지) 판독 항목으로 둠',
    'ft_pni_presence': '논문 그림(병변 탭)은 있으나 신경 주석이 있는 공개 영상이 없어 측정 예시 없음',
    'ft_epe_presence': '논문 그림(병변 탭)은 있으나 피막 경계 주석이 있는 공개 영상이 없어 측정 예시 없음',
    'ft_gland_count': '샘 하나하나의 주석이 있는 영상이 양성 샘 예시뿐',
}

# ------------------------------------------------------------------ links between the three atlases
# Two ways to run: one service (portal at /, domains mounted at /retinal/, /mammography/, /pathology/ — see
# portal/packages/medical-atlas-portal-web) or each atlas on its own port (portal 8875, retinal 8877,
# mammography 8879, pathology 8881). When mounted, request.script_root is the mount path; otherwise links reuse the
# request host with each service's port. MEDICAL_ATLAS_URL_<ID> overrides one link.
ATLAS_SITES = [('portal', '의료영상 지도', 8875), ('retinal', '안과', 8877), ('mammography', '유방', 8879),
               ('pathology', '전립선', 8881)]


def atlas_links(current: str) -> dict:
    urls = {}
    mounted = bool(request.script_root)
    host = request.host
    host = host.rsplit(':', 1)[0] if host.count(':') == 1 else (host.split(']')[0] + ']' if host.startswith('[') else host)
    for sid, _, port in ATLAS_SITES:
        env = os.environ.get(f'MEDICAL_ATLAS_URL_{sid.upper()}')
        if env:
            urls[sid] = env.rstrip('/') + '/'
        elif mounted:
            urls[sid] = request.host_url + ('' if sid == 'portal' else f'{sid}/')     # full URL: not re-prefixed below
        else:
            urls[sid] = f'{request.scheme}://{host}:{port}/'
    return {'portal': urls['portal'],
            'domains': [{'id': sid, 'label': label, 'url': urls[sid], 'current': sid == current}
                        for sid, label, _ in ATLAS_SITES if sid != 'portal']}


def mount_prefix(response):
    """When mounted under a path, put that path in front of root links of rendered pages and of redirects."""
    root = request.script_root
    if not root:
        return response
    if response.location and response.location.startswith('/') and not response.location.startswith(root + '/'):
        response.location = root + response.location
    if response.mimetype == 'text/html' and not response.direct_passthrough:
        skip = re.escape(root.lstrip('/')) + '/'
        html = response.get_data(as_text=True)
        html = re.sub(r'((?:href|src|action)=")/(?!/|' + skip + ')', r'\1' + root + '/', html)
        response.set_data(html)
    return response



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
    if imaging_id.startswith('img_he'):
        return 'he'
    if imaging_id.startswith('img_ihc'):
        return 'ihc'
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
            reason = PENDING_REASON.get(f['id']) or (IHC_REASON if mod == 'ihc' else '')
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
    grading_path = DATA / 'grading.json'
    grading_data = json.loads(grading_path.read_text(encoding='utf-8')) if grading_path.is_file() else None
    validation_path = DATA / 'validation.json'
    validation = json.loads(validation_path.read_text(encoding='utf-8')) if validation_path.is_file() else None
    masked_by_id = {f['id']: f for f in masked}
    return {'atlas': atlas, 'items': items, 'masked': masked, 'masked_by_item': masked_by_item,
            'masked_files': masked_files, 'measure_examples': examples, 'measure_files': measure_files,
            'by_slug': by_slug, 'diseases': diseases, 'disease_by_slug': {d['slug']: d for d in diseases.values()},
            'measure_diseases': measurement_diseases(atlas), 'grading': grading_data, 'masked_by_id': masked_by_id,
            'validation': validation}


def item_path(item: dict) -> str:
    return f"/{item['section']}/{item['slug']}/"


def matches(item: dict, query: str) -> bool:
    if not query:
        return True
    haystack = ' '.join([item['name'], item['name_en'], item['abbr'], item['definition'], item.get('location', '')]).lower()
    return all(token in haystack for token in query.lower().split())


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.after_request(mount_prefix)
    app.config.from_mapping(MASKED_ROOT=_domain_resource('pathology_atlas_masked_figures', 'PATHOLOGY_ATLAS_MASKED_ROOT'),
                            MEASURE_ROOT=_domain_resource('pathology_atlas_measurement_examples', 'PATHOLOGY_ATLAS_MEASURE_ROOT'),
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
        return {'nav': NAV, 'atlas_links': atlas_links('pathology'), 'items': items, 'atlas': atlas, 'item_path': item_path, 'modalities': MODALITIES,
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
    app.add_template_filter(lambda v: round(math.cos(v), 4), 'cos_')
    app.add_template_filter(lambda v: round(math.sin(v), 4), 'sin_')
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
        return render_template('home.html', active='home', title='병리 영상 지도',
                               counts={'anatomy': len(section_items('anatomy')), 'lesions': len(lesions),
                                       'measures': sum(1 for f in features.values() if f['role'] == 'measurement'),
                                       'diseases': sum(1 for d in atlas['diseases'].values() if d['scope'] == 'primary')},
                               figures=[f for f in content['masked'] if not f['id'].endswith('_nuclei')][:6])

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
        grading_view = None
        if content['grading'] and disease['id'] == 'dis_prostate_adenocarcinoma':
            g = content['grading']
            grading_view = dict(g, gallery=[dict(e, fig=content['masked_by_id'][e['figure']]) for e in g['par_examples']
                                            if e['figure'] in content['masked_by_id']])
        return render_template('disease.html', active='diseases', title=disease['name'], disease=disease,
                               grouped=grouped, diseases=content['diseases'], ladders=ladders, grading=grading_view)

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
        if not feature or feature['role'] not in ('measurement', 'classification'):
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

    @app.get('/validation/')
    def validation_page():
        return render_template('validation.html', active='validation', title='측정 검증', validation=content['validation'])

    @app.get('/sources/')
    def sources():
        seen = {}
        for f in content['masked']:
            row = seen.setdefault(f['source'], {'id': f['source'], 'kind': f.get('kind', 'masked'), 'name': f['name'],
                                                'credit': f.get('source_credit', f['credit']), 'url': f['url'],
                                                'license': f['license'], 'license_url': f['license_url'], 'panels': []})
            if f.get('panel'):
                row['panels'].append(f['panel'])
        image_sources = sorted(seen.values(), key=lambda r: (r['kind'] == 'paper', r['name']))
        return render_template('sources.html', active='sources', title='출처와 라이선스', image_sources=image_sources)

    @app.get('/health')
    def health():
        missing = [n for n in content['masked_files'] if not (masked_root / n).is_file()]
        missing += [n for n in content['measure_files'] if not (measure_root / n).is_file()]
        ready = not missing
        return jsonify(status='ok' if ready else 'unavailable', site='pathology_atlas_web', stage='atlas_v01',
                       items=len(items), figures=len(content['masked']), examples=len(content['measure_examples']),
                       missing_files=len(missing)), 200 if ready else 503

    @app.errorhandler(404)
    @app.errorhandler(503)
    def unavailable(error):
        return render_template('error.html', active='', title='페이지를 표시할 수 없습니다', code=error.code), error.code

    return app
