"""Server-rendered retinal atlas; no portal or experiment dependency.

`data/atlas.json` is generated from the project survey tables by
`code/build_retinal_atlas_catalog.py`; `data/catalog.json` holds the four real-image
reading pages and `data/image_links.json` links their marks to atlas items.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .code_links import PACKAGES, CodeIndex, default_packages_root
from .disease_links import measurement_diseases
from .modality_views import DEPTH_BANDS, MODALITY_VIEWS
from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_file


IMAGE_FILES = {
    'retina_layers.png': '679a4fcbad112.png',
    'choroid.png': 'journal.pone.0099690.g001.png',
    'oct_lesions.jpg': 'jcm-11-03266-g002-550.jpg',
    'atrophy.webp': 'fnins-18-1415575-g001.webp',
}
NAV = [('/', '망막 홈', 'home'), ('/anatomy/', '해부학 지도', 'anatomy'),
       ('/lesions/', '병변 목록', 'lesions'), ('/measurements/', '측정 목록', 'measurements'),
       ('/diseases/', '질병 목록', 'diseases'), ('/imaging/', '영상 종류', 'imaging'),
       ('/images/', '영상 읽기', 'images')]
LEGACY_SAMPLE_PATHS = {'/anatomy/retinal-layers/': 'retinal-layers', '/lesions/oct/': 'oct',
                       '/lesions/atrophy/': 'atrophy'}
MODALITIES = [('cfp', '안저'), ('oct', 'OCT'), ('octa', 'OCTA'), ('faf', 'FAF'), ('nir', 'NIR'),
              ('fa', 'FA'), ('icga', 'ICGA')]
OBS_LABEL = {'direct': '직접 관찰', 'limited': '제한적', 'none': '—'}
REVIEW_LABEL = {'draft': '서비스 초안', 'needs_source': '근거 필요', 'source_linked': '출처 연결',
                'definition_checked_abstract': '정의 확인(초록)', 'definition_checked': '정의 확인',
                'measurement_checked': '측정법 확인', 'expert_reviewed': '전문가 검토'}
RELATION_LABEL = {'diagnostic_criterion': '진단 기준 소견', 'severity_classification': '단계 판정에 쓰는 소견',
                  'activity_monitoring': '활동성·경과 관찰', 'prognostic': '예후 관련',
                  'characteristic_nonspecific': '동반 소견(비특이)'}
FEATURE_STATUS_LABEL = {'direct': '고유 특징', 'common_applied': '공통 특징 적용',
                        'not_applicable': '측정 대상 아님', 'not_investigated': '특징 미정리'}
ANATOMY_GROUP_ORDER = ['region', 'structure', 'layer', 'vessel', 'reference']
# Items drawn on the generated OCT B-scan schematic (templates/_oct_schematic.html).
OCT_SCHEMATIC_ITEMS = {'ana_vitreous', 'ana_posterior_hyaloid', 'ana_ilm', 'ana_rnfl', 'ana_gcl', 'ana_ipl',
                       'ana_inl', 'ana_opl', 'ana_hfl', 'ana_onl', 'ana_elm', 'ana_myoid_zone',
                       'ana_ellipsoid_zone', 'ana_photoreceptor_os', 'ana_interdigitation_zone', 'ana_rpe',
                       'ana_bruch_membrane', 'ana_choriocapillaris', 'ana_sattler_layer', 'ana_haller_layer',
                       'ana_choroid_sclera_junction', 'ana_sclera', 'ana_retina', 'ana_total_retina',
                       'ana_neurosensory_retina', 'ana_inner_retina', 'ana_outer_retina', 'ana_gcipl',
                       'ana_photoreceptors', 'ana_rpe_bruch_complex', 'ana_choroid', 'ana_fovea', 'ana_foveola',
                       'ana_parafovea', 'ana_perifovea', 'ana_macula', 'ref_fovea_center'}
MAP_AXES = [
    ('face', '안저에서 보는 영역', '정면에서 본 위치 · 후극부와 주변부'),
    ('depth', 'OCT로 보는 층', '단면에서 안쪽(유리체)부터 바깥쪽(공막)까지'),
    ('vessel', '혈관', '망막 혈관과 모세혈관망 · 맥락막 혈관은 층에서'),
    ('reference', '측정 기준', '위치 기준점 · 구역 체계 · 두께 측정 구간'),
]
# Items drawn on the generated vessel schematic (templates/_vessel_schematic.html).
VESSEL_SCHEMATIC_ITEMS = {'ana_central_retinal_artery', 'ana_central_retinal_vein', 'ana_retinal_arterioles',
                          'ana_retinal_venules', 'ana_vascular_arcades', 'ana_cilioretinal_artery', 'ana_av_crossing',
                          'ana_radial_peripapillary_capillaries', 'ana_superficial_capillary_plexus',
                          'ana_intermediate_capillary_plexus', 'ana_deep_capillary_plexus',
                          'ana_foveal_avascular_zone', 'ana_retinal_vasculature', 'ana_vascular_tree'}
VESSEL_DEPTH_ITEMS = {'ana_radial_peripapillary_capillaries', 'ana_superficial_capillary_plexus',
                      'ana_intermediate_capillary_plexus', 'ana_deep_capillary_plexus', 'ana_foveal_avascular_zone',
                      'ana_central_retinal_artery', 'ana_central_retinal_vein', 'ana_retinal_vasculature'}
# Items drawn on the hand-made posterior-pole schematic (templates/_schematic.html).
SCHEMATIC_ITEMS = {'ana_posterior_pole', 'ana_mid_periphery', 'ana_macula', 'ana_fovea', 'ana_foveola',
                   'ana_parafovea', 'ana_perifovea', 'ana_optic_disc', 'ana_optic_cup', 'ana_neuroretinal_rim',
                   'ana_peripapillary_region', 'ana_vascular_arcades', 'ana_retinal_arterioles',
                   'ana_retinal_venules', 'ana_retinal_vasculature', 'ana_vascular_tree', 'ref_fovea_center',
                   'ref_disc_center', 'ref_disc_diameter', 'zone_etdrs_grid'}
LESION_GROUP_ORDER = ['hemorrhage', 'vascular', 'neovascular', 'perfusion', 'ischemic', 'exudate_deposit',
                      'fluid_elevation', 'reflectivity_layer', 'outer_retina_rpe', 'pigment',
                      'vitreoretinal_interface', 'peripheral_detachment', 'optic_disc', 'choroidal', 'myopic',
                      'scar_treatment', 'inherited_secondary', 'inflammatory_secondary', 'tumor_secondary',
                      'aggregate']
UNIT_TEXT = [('defined_by_parent', '원 측정과 같음'), ('count/year', '개/년'), ('count/area', '개/면적'),
             ('count(0–4)', '개(0–4)'), ('count', '개'), ('um2', 'µm²'), ('mm2', 'mm²'), ('mm3', 'mm³'),
             ('px2', 'px²'), ('DD2', 'DD²'), ('um', 'µm'), ('count/area', '개/면적'), ('category', '범주'),
             ('presence', '있음/없음'), ('ratio', '비율'), ('intensity', '신호 강도'), ('dimensionless', '무차원'),
             ('score', '점수'), ('deg', '°')]

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
DATA = Path(__file__).parent / 'data'


def default_image_root() -> Path:
    """Prefer deployment config, otherwise find the canonical project view."""
    if configured := os.environ.get('RETINAL_ATLAS_IMAGE_ROOT'):
        return Path(configured).expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / 'DOMAIN.yaml').is_file():
            return parent / 'resources/datasets/retinal_concept_reference_images'
    return Path('/data/retinal_concept_reference_images')


def default_modality_root() -> Path:
    if configured := os.environ.get('RETINAL_ATLAS_MODALITY_ROOT'):
        return Path(configured).expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / 'DOMAIN.yaml').is_file():
            return parent / 'resources/datasets/retinal_atlas_modality_figures'
    return Path('/data/retinal_atlas_modality_figures')


def default_masked_root() -> Path:
    if configured := os.environ.get('RETINAL_ATLAS_MASKED_ROOT'):
        return Path(configured).expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / 'DOMAIN.yaml').is_file():
            return parent / 'resources/datasets/retinal_atlas_masked_figures'
    return Path('/data/retinal_atlas_masked_figures')


def default_measure_root() -> Path:
    if configured := os.environ.get('RETINAL_ATLAS_MEASURE_ROOT'):
        return Path(configured).expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / 'DOMAIN.yaml').is_file():
            return parent / 'resources/datasets/retinal_atlas_measurement_examples'
    return Path('/data/retinal_atlas_measurement_examples')


LESION_CATEGORIES = [
    ('vascular', '혈관·출혈·허혈', '미세동맥류·출혈·신생혈관·무관류 등 혈관에서 시작하는 변화',
     ['hemorrhage', 'vascular', 'neovascular', 'perfusion', 'ischemic']),
    ('deposit', '삼출물·침착물', '경성삼출물·면화반·드루젠처럼 쌓이거나 남는 물질', ['exudate_deposit']),
    ('fluid', '액체·융기', '망막내액·망막하액·색소상피박리 등 공간과 융기', ['fluid_elevation']),
    ('layer', '층·RPE·색소 변화', 'OCT 층 배열·반사, 외망막·RPE 손상과 위축, 색소 변화',
     ['reflectivity_layer', 'outer_retina_rpe', 'pigment']),
    ('interface', '유리체망막 경계·박리', '망막전막·견인·원공과 주변부 열공·박리',
     ['vitreoretinal_interface', 'peripheral_detachment']),
    ('disc', '시신경유두', '유두 함몰·신경섬유층 결손·유두 출혈·부종', ['optic_disc']),
    ('choroid', '맥락막·근시', '맥락막 비후·과투과와 근시성 변화', ['choroidal', 'myopic']),
    ('other', '반흔·기타', '치료 흔적·반흔, 2차 범위 소견과 기존 측정의 통합 대상',
     ['scar_treatment', 'inherited_secondary', 'inflammatory_secondary', 'tumor_secondary', 'aggregate']),
]
DISEASE_CLUSTERS = [
    ('diabetes', '당뇨 관련', ['dis_dr', 'dis_dme']),
    ('amd', '나이관련황반변성', ['dis_amd', 'dis_pcv']),
    ('occlusion', '망막 혈관폐쇄·허혈', ['dis_crvo', 'dis_hrvo', 'dis_brvo', 'dis_crao', 'dis_brao',
                                        'dis_cilioretinal_ao', 'dis_ois', 'dis_purtscher']),
    ('vascular', '그 밖의 망막 혈관 질환', ['dis_mactel2', 'dis_coats', 'dis_ram', 'dis_sickle_retinopathy',
                                          'dis_radiation_retinopathy']),
    ('choroid', '맥락막·중심장액', ['dis_cscr', 'dis_pachychoroid_spectrum', 'dis_angioid_streaks']),
    ('myopia', '근시', ['dis_pathologic_myopia']),
    ('interface', '유리체망막 경계·박리', ['dis_erm', 'dis_vmt', 'dis_macular_hole', 'dis_lamellar_mh', 'dis_rrd']),
    ('macula', '그 밖의 황반 질환', ['dis_pseudophakic_cme', 'dis_amn']),
    ('toxic', '약물 독성', ['dis_hcq_retinopathy', 'dis_pentosan_maculopathy']),
    ('inherited', '유전 망막질환', ['dis_retinitis_pigmentosa', 'dis_stargardt', 'dis_best', 'dis_aofvd',
                                   'dis_cone_rod_dystrophy', 'dis_choroideremia']),
    ('inflammatory', '염증·포도막염', ['dis_uveitis_retinal', 'dis_vkh', 'dis_mewds', 'dis_serpiginous']),
    ('optic', '시신경', ['dis_glaucoma', 'dis_papilledema', 'dis_naion', 'dis_optic_atrophy']),
    ('systemic', '전신 질환', ['dis_hypertensive_retinopathy']),
    ('tumor', '종양', ['dis_choroidal_tumor', 'dis_choroidal_hemangioma', 'dis_chrpe']),
]


def modality_of(imaging_id: str) -> str:
    for prefix, key in (('img_octa', 'octa'), ('img_oct', 'oct'), ('img_cfp', 'cfp'), ('img_uwf', 'cfp'),
                        ('img_faf', 'faf'), ('img_nir', 'nir'), ('img_fa', 'fa'), ('img_icga', 'icga')):
        if imaging_id.startswith(prefix):
            return key
    return ''


def _example_modality(imaging_id: str) -> str:
    """Example-card modality of an atlas imaging id (UWF kept apart from 45° fundus, unlike ``modality_of``)."""
    for prefix, key in (('img_octa', 'octa'), ('img_oct', 'oct'), ('img_cfp', 'cfp'), ('img_uwf', 'uwf'),
                        ('img_faf', 'faf'), ('img_nir', 'nir'), ('img_fa', 'fa'), ('img_icga', 'icga')):
        if imaging_id.startswith(prefix):
            return key
    return ''


# Why a measurement still has no image example on a given image type (what kind of image would be needed).
TWO_TIMES = '같은 눈 두 시점 영상이 필요하나 공개 CC BY 예시가 없음'
NEEDS_DEPTH = '깊이(OCT B-scan) 정보가 필요해 이 영상 한 장으로는 계산 불가'
ONH_3D = '유두 3D 스캔(BMO 전체 둘레)이 필요하나 공개 CC BY 예시가 없음'
PENDING_REASON = {
    'ft_ma_turnover': TWO_TIMES, 'ft_lesion_generic_change': TWO_TIMES, 'ft_atrophy_growth_rate': TWO_TIMES,
    'ft_faz_enlargement': TWO_TIMES, 'ft_mnv_type': NEEDS_DEPTH, 'ft_haller_vessel_diameter': NEEDS_DEPTH,
    'ft_disc_area': ONH_3D, 'ft_isnt_pattern': ONH_3D, 'ft_rim_area': ONH_3D, 'ft_cupping_notch': ONH_3D,
    'ft_cdr_vertical': ONH_3D, 'ft_cup_area': ONH_3D, 'ft_ppa_area': '유두 둘레가 보이는 이 영상 종류의 공개 CC BY 예시가 없음',
    'ft_sdd_stage': 'SDD가 보이는 공개 CC BY B-scan이 없음', 'ft_sdd_extent': 'SDD가 보이는 이 영상 종류의 공개 CC BY 예시가 없음',
    'ft_irma_presence': 'IRMA를 따로 분할할 수 있는 해상도의 공개 예시가 없음', 'ft_irma_quadrants': 'IRMA를 따로 분할할 수 있는 해상도의 공개 예시가 없음',
    'ft_vb_quadrants': '정맥 구슬모양이 보이는 이 영상 종류의 공개 예시가 없음',
    'ft_ma_count': '미세동맥류 점이 구분되는 해상도의 공개 예시가 없음', 'ft_ma_presence': '미세동맥류 점이 구분되는 해상도의 공개 예시가 없음',
    'ft_ma_distance_fovea': '미세동맥류 점이 구분되는 해상도의 공개 예시가 없음',
    'ft_nve_area': '신생혈관이 찍힌 이 영상 종류의 공개 CC BY 예시가 없음', 'ft_nve_presence': '신생혈관이 찍힌 이 영상 종류의 공개 CC BY 예시가 없음',
    'ft_nvd_area': '신생혈관이 찍힌 이 영상 종류의 공개 CC BY 예시가 없음', 'ft_nvd_presence': '신생혈관이 찍힌 이 영상 종류의 공개 CC BY 예시가 없음',
    'ft_mnv_lesion_area': '신생혈관이 찍힌 이 영상 종류의 공개 CC BY 예시가 없음',
    'ft_laser_scar_extent': '레이저 반흔이 찍힌 이 영상 종류의 공개 예시가 없음', 'ft_ischemic_index': '광각 FA가 필요(형광안저혈관조영 탭의 광각 예시 참고)',
    'ft_rd_extent': '망막박리가 찍힌 이 영상 종류의 공개 예시가 없음', 'ft_rd_macula_status': '망막박리가 찍힌 이 영상 종류의 공개 예시가 없음',
    'ft_erm_extent': '망막전막이 찍힌 이 영상 종류의 공개 CC BY 예시가 없음', 'ft_prh_area': '망막앞 출혈이 찍힌 이 영상 종류의 공개 예시가 없음',
}


def pending_by_modality(features: dict, items: dict, examples: list[dict]) -> dict[str, list[dict]]:
    """Per example modality: atlas items that apply to that image type but have no image example there.

    Rows are grouped by measured target (lesion or structure) and carry what is to be measured (definition,
    unit) and why it is not shown (no implementation, or a function exists but was not run on this image type).
    """
    shown: dict[str, set] = {}
    anywhere: dict[str, str] = {}
    for ex in examples:
        for layer in ex['layers']:
            for f in layer['features']:
                shown.setdefault(ex['modality'], set()).add(f['id'])
                anywhere.setdefault(f['id'], ex['id'])
    out: dict[str, list[dict]] = {}
    for mod in {ex['modality'] for ex in examples}:
        groups: dict[str, list[dict]] = {}
        for f in features.values():
            if (f['role'] != 'measurement' or f['id'] in shown.get(mod, set())
                    or mod not in {_example_modality(i) for i in f.get('imaging', [])}):
                continue
            target = items.get(f.get('target') or '')
            impl = f.get('impl', {})
            groups.setdefault(target['name'] if target else '공통', []).append({
                'feature': f, 'target': target, 'level': impl.get('level', 'none'),
                'function': (impl.get('package') or {}).get('function', ''), 'elsewhere': anywhere.get(f['id']),
                'reason': PENDING_REASON.get(f['id'], '')})
        out[mod] = [{'label': k, 'rows': sorted(v, key=lambda r: r['feature']['name'])}
                    for k, v in sorted(groups.items(), key=lambda kv: (kv[0] == '공통', kv[0]))]
    return out


IMPL_LEVELS = [
    ('auto', '영상만으로 자동', '원영상만 넣으면 계산되는 구현이 있음'),
    ('auto_seg', '자동 분할 후 계산', '혈관 분할 도구를 거치면 계산되는 구현이 있음'),
    ('mask', 'mask 입력 필요', '계산기는 있으나 병변·OCT mask(전문가 또는 검증된 분할)가 필요'),
    ('model', 'AI 모델 출력', '모델의 점수·확률로 제공'),
    ('package', '측정 함수 있음', 'retinal-measures 함수는 있으나 입력(mask·경계면)을 만드는 분할이 아직 연결되지 않음'),
    ('proxy', '근사만', '다른 관측량으로 근사한 구현만 있음'),
    ('record', '임상 기록', '영상이 아닌 기록에서 추출'),
    ('none', '구현 없음', '정의만 있고 계산 구현이 아직 없음'),
]
READY_LEVELS = {'auto', 'auto_seg', 'mask', 'model'}
RELATION_ORDER = ['diagnostic_criterion', 'severity_classification', 'activity_monitoring', 'prognostic',
                  'characteristic_nonspecific']


def load_content() -> dict:
    catalog = json.loads((DATA / 'catalog.json').read_text(encoding='utf-8'))
    atlas = json.loads((DATA / 'atlas.json').read_text(encoding='utf-8'))
    links = json.loads((DATA / 'image_links.json').read_text(encoding='utf-8'))
    samples = catalog['samples']
    for key, sample in samples.items():
        sample['path'] = f"/images/{sample['slug']}/"
        sample['links'] = links.get(key, [])
    items = atlas['items']
    figures = {item_id: [] for item_id in items}
    for key, marks in links.items():
        for mark in marks:
            if mark['item'] not in items:
                raise ValueError(f"image link to unknown item {mark['item']}")
            figures[mark['item']].append({'sample': samples[key], 'mark': mark})
    masked = json.loads((DATA / 'masked_figures.json').read_text(encoding='utf-8'))['figures']
    masked_by_item = {item_id: [] for item_id in items}
    for fig in masked:
        for item_id in fig['items']:
            if item_id not in items:
                raise ValueError(f"masked figure {fig['id']} links unknown item {item_id}")
            masked_by_item[item_id].append(fig)
    masked_files = {name for fig in masked for name in (fig['base'], fig['overlay'], fig.get('context')) if name}
    examples_path = DATA / 'measurement_examples.json'
    measure_examples = json.loads(examples_path.read_text(encoding='utf-8'))['examples'] if examples_path.is_file() else []
    for ex in measure_examples:
        for layer in ex['layers']:
            for f in layer['features']:
                if f['id'] not in atlas['features']:
                    raise ValueError(f"measurement example {ex['id']} names unknown feature {f['id']}")
    measure_files = {name for ex in measure_examples for name in [ex['base']] + [la['file'] for la in ex['layers']]}
    by_slug = {(item['section'], item['slug']): item for item in items.values()}
    diseases = atlas['diseases']
    disease_by_slug = {d['slug']: d for d in diseases.values()}
    item_schematics = json.loads((DATA / 'item_schematics.json').read_text(encoding='utf-8'))['items']
    unknown = sorted(set(item_schematics) - set(items))
    if unknown:
        raise ValueError(f'schematics for unknown items: {unknown}')
    modality_figures = json.loads((DATA / 'modality_figures.json').read_text(encoding='utf-8'))['figures']
    for fig in modality_figures:
        if fig['modality'] not in MODALITY_VIEWS:
            raise ValueError(f"modality figure {fig['id']} has unknown modality {fig['modality']}")
        if fig['served'] == 'masked' and fig['file'] not in masked_files:
            raise ValueError(f"modality figure {fig['id']} reuses unknown masked file {fig['file']}")
    return {'measure_diseases': measurement_diseases(atlas), 'catalog': catalog, 'samples': samples, 'atlas': atlas, 'items': items,
            'modality_figures': modality_figures, 'item_schematics': item_schematics,
            'modality_files': {f['file'] for f in modality_figures if f['served'] == 'modality'},
            'figures': figures, 'by_slug': by_slug, 'masked': masked, 'masked_by_item': masked_by_item,
            'masked_files': masked_files, 'diseases': diseases, 'disease_by_slug': disease_by_slug,
            'measure_examples': measure_examples, 'measure_files': measure_files}


def item_path(item: dict) -> str:
    return f"/{item['section']}/{item['slug']}/"


def matches(item: dict, query: str) -> bool:
    if not query:
        return True
    haystack = ' '.join([item['name'], item['name_en'], item['abbr'], item['definition'],
                         item.get('location', '')]).lower()
    return all(token in haystack for token in query.lower().split())


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.after_request(mount_prefix)
    app.config.from_mapping(IMAGE_ROOT=default_image_root(), MASKED_ROOT=default_masked_root(),
                            MODALITY_ROOT=default_modality_root(), MEASURE_ROOT=default_measure_root(),
                            PACKAGES_ROOT=default_packages_root())
    if config:
        app.config.update(config)
    image_root = Path(app.config['IMAGE_ROOT']).expanduser().resolve()
    masked_root = Path(app.config['MASKED_ROOT']).expanduser().resolve()
    modality_root = Path(app.config['MODALITY_ROOT']).expanduser().resolve()
    measure_root = Path(app.config['MEASURE_ROOT']).expanduser().resolve()
    packages_root = app.config['PACKAGES_ROOT']
    code_index = CodeIndex(Path(packages_root).expanduser().resolve() if packages_root else None)
    content = load_content()
    catalog, samples, atlas, items = (content['catalog'], content['samples'], content['atlas'],
                                      content['items'])

    @app.context_processor
    def shared_context():
        return {'nav': NAV, 'atlas_links': atlas_links('retinal'), 'samples': samples, 'items': items, 'atlas': atlas, 'item_path': item_path,
                'modalities': MODALITIES, 'obs_label': OBS_LABEL, 'review_label': REVIEW_LABEL,
                'relation_label': RELATION_LABEL, 'feature_status_label': FEATURE_STATUS_LABEL,
                'query': request.args.get('q', '').strip(), 'schematic_items': SCHEMATIC_ITEMS,
                'oct_items': OCT_SCHEMATIC_ITEMS, 'vessel_items': VESSEL_SCHEMATIC_ITEMS,
                'vessel_depth_items': VESSEL_DEPTH_ITEMS, 'disease_by_id': content['diseases'],
                'impl_label': {key: label for key, label, _ in IMPL_LEVELS},
                'measure_diseases': content['measure_diseases']}

    @app.after_request
    def response_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self'; font-src 'self'; frame-ancestors 'none'; "
            "object-src 'none'; base-uri 'self'; form-action 'self'"
        )
        return response

    app.add_template_filter(unit_text, 'unit')
    id_pattern = re.compile(r'\b(?:zone|ref|ana|les)_[a-z0-9_]+\b')

    def region_text(value: str) -> str:
        return id_pattern.sub(lambda m: items[m.group(0)]['name'] if m.group(0) in items else m.group(0), value or '')

    app.add_template_filter(region_text, 'region')

    def section_items(section):
        return sorted((item for item in items.values() if item['section'] == section),
                      key=lambda item: item['order'])

    def modality_filter(entries):
        modality = request.args.get('img', '')
        if modality in dict(MODALITIES):
            entries = [e for e in entries if e['obs'].get(modality) in {'direct', 'limited'}]
        return entries, modality

    @app.get('/')
    def home():
        anatomy = section_items('anatomy')
        lesions = [i for i in section_items('lesions') if not i.get('aggregate')]
        return render_template('home.html', active='home', title='망막 영상 지도',
                               counts={'anatomy': len(anatomy), 'lesions': len(lesions),
                                       'diseases': sum(1 for d in atlas['diseases'].values() if d['scope'] == 'primary'),
                                       'images': len(samples)})

    @app.get('/anatomy/')
    def anatomy_index():
        entries, modality = modality_filter([i for i in section_items('anatomy') if matches(i, request.args.get('q', ''))])
        groups = []
        for key in ANATOMY_GROUP_ORDER:
            members = [e for e in entries if e['group'] == key]
            if members:
                groups.append((members[0]['group_label'], key, members))
        axes = []
        for key, label, note in MAP_AXES:
            members = [i for i in section_items('anatomy') if i.get('axis') == key]
            roots = [i for i in members if not i['parent'] or items.get(i['parent'], {}).get('axis') != key]
            axes.append({'key': key, 'label': label, 'note': note, 'roots': roots, 'count': len(members)})
        filtered = bool(modality or request.args.get('q'))
        layer_colors = json.loads((DATA / 'oct_layer_colors.json').read_text(encoding='utf-8'))
        return render_template('anatomy_index.html', active='anatomy', title='해부학 지도', groups=groups,
                               modality=modality, total=len(entries), axes=axes, filtered=filtered,
                               layer_colors=layer_colors)

    @app.get('/lesions/')
    def lesion_index():
        group = request.args.get('group', '')
        entries = [i for i in section_items('lesions') if matches(i, request.args.get('q', ''))]
        labels = {entry['group']: entry['group_label'] for entry in section_items('lesions')}
        all_groups = [(key, labels[key]) for key in LESION_GROUP_ORDER if key in labels]
        all_groups += [(key, label) for key, label in labels.items() if key not in LESION_GROUP_ORDER]
        if group:
            entries = [e for e in entries if e['group'] == group]
        entries, modality = modality_filter(entries)
        category = request.args.get('cat', '')
        categories = []
        for key, label, note, groups in LESION_CATEGORIES:
            if category and category != key:
                continue
            sub = []
            for g in groups:
                members = [e for e in entries if e['group'] == g]
                if members:
                    sub.append((labels.get(g, g), g, members))
            if sub:
                categories.append({'key': key, 'label': label, 'note': note, 'groups': sub,
                                   'count': sum(len(m) for _, _, m in sub)})
        counts = {key: sum(1 for e in section_items('lesions') if e['group'] in groups)
                  for key, _, _, groups in LESION_CATEGORIES}
        filtered = bool(modality or request.args.get('q') or group or category)
        return render_template('lesion_index.html', active='lesions', title='병변 목록', categories=categories,
                               category_defs=LESION_CATEGORIES, counts=counts, group=group, category=category,
                               modality=modality, total=len(entries), filtered=filtered)

    def render_item(section, slug):
        if (path := request.path) in LEGACY_SAMPLE_PATHS:
            return redirect(f"/images/{LEGACY_SAMPLE_PATHS[path]}/", code=301)
        item = content['by_slug'].get((section, slug))
        if item is None:
            abort(404)
        siblings = sorted((i for i in items.values() if i['section'] == section and i['group'] == item['group']
                           and i['id'] != item['id']), key=lambda i: i['order'])
        disease_groups = {}
        for link in item['diseases']:
            disease_groups.setdefault(link['disease'], []).append(link)
        return render_template('item.html', active=section, title=item['name'], item=item,
                               figures=content['figures'][item['id']],
                               masked=content['masked_by_item'][item['id']], siblings=siblings[:12],
                               schematics=content['item_schematics'].get(item['id'], []),
                               disease_groups=disease_groups)

    @app.get('/anatomy/<slug>/')
    def anatomy_item(slug):
        return render_item('anatomy', slug)

    @app.get('/lesions/<slug>/')
    def lesion_item(slug):
        return render_item('lesions', slug)

    @app.get('/images/')
    def image_index():
        return render_template('images.html', active='images', title='영상 읽기')

    @app.get('/images/<slug>/')
    def image_page(slug):
        sample = next((s for s in samples.values() if s['slug'] == slug), None)
        if sample is None:
            abort(404)
        viewer = {'layers': catalog['layers'], 'broad': catalog['broad']}
        return render_template('sample.html', active='images', title=sample['label'], sample=sample,
                               viewer=viewer)

    @app.get('/search/')
    def search():
        query = request.args.get('q', '').strip()
        results = [i for i in items.values() if query and matches(i, query)]
        results.sort(key=lambda i: (i['section'] != 'anatomy', i['name']))
        return render_template('search.html', active='', title='검색', results=results)

    features = atlas['features']
    imaging_names = {key: value['name'] for key, value in atlas['imaging'].items()}

    def resolve_finding(finding_id):
        """Return where to look, with which images and what to measure for one disease finding."""
        if finding_id in items:
            item = items[finding_id]
            measures = [f for f in item['features'] if f['type'] == 'quantitative' and not f['common']]
            measures = measures or [f for f in item['features'] if f['type'] == 'quantitative'][:4]
            where = [items[s] for s in item.get('structures', []) if s in items]
            modalities = [label for key, label in MODALITIES if item['obs'].get(key) == 'direct']
            return {'kind': 'item', 'name': item['name'], 'link': item_path(item), 'location': item.get('location', ''),
                    'where': where, 'modalities': modalities, 'measures': measures}
        feature = features.get(finding_id)
        if feature:
            target = items.get(feature['target'])
            return {'kind': 'feature', 'name': feature['name'], 'link': item_path(target) if target else '',
                    'target': target, 'location': feature['region'], 'where': [target] if target else [],
                    'modalities': [imaging_names.get(i, i) for i in feature['imaging']], 'measures': [feature]}
        return {'kind': 'unknown', 'name': finding_id, 'link': '', 'location': '', 'where': [], 'modalities': [],
                'measures': []}

    def disease_summary(disease):
        """Key findings (criteria first) and the imaging they rely on, including sub-diseases."""
        relations = list(disease['relations'])
        for cid in disease['children']:
            relations += content['diseases'][cid]['relations']
        relations.sort(key=lambda r: RELATION_ORDER.index(r['type']))
        names, modalities = [], set()
        for rel in relations:
            info = resolve_finding(rel['finding'])
            if info['name'] not in names:
                names.append(info['name'])
            finding = rel['finding']
            if finding in items:
                modalities |= {k for k, v in items[finding]['obs'].items() if v == 'direct'}
            elif finding in features:
                modalities |= {modality_of(i) for i in features[finding]['imaging']}
        schemes = [dict(g, owner=disease) for g in disease.get('grading', [])]
        for cid in disease['children']:
            child = content['diseases'][cid]
            schemes += [dict(g, owner=child) for g in child.get('grading', [])]
        return {'findings': names[:5], 'more': max(0, len(names) - 5), 'schemes': schemes,
                'modalities': [(k, label) for k, label in MODALITIES if k in modalities],
                'roles': sorted({r['type'] for r in relations}, key=RELATION_ORDER.index)}

    @app.get('/diseases/')
    def disease_index():
        diseases = content['diseases']
        clusters = []
        for key, label, ids in DISEASE_CLUSTERS:
            members = [diseases[i] for i in ids if i in diseases]
            if members:
                clusters.append({'key': key, 'label': label,
                                 'members': [(d, disease_summary(d)) for d in members]})
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
        ladders = []
        chain, node = [], disease
        while node:
            chain.append(node)
            node = content['diseases'].get(node['parent']) if node['parent'] else None
        for owner in chain:
            for scheme in owner.get('grading', []):
                steps = [dict(st, finding_info=[resolve_finding(f) for f in st['findings']]) for st in scheme['steps']]
                ladders.append(dict(scheme, steps=steps, owner=owner, inherited=owner is not disease,
                                    imaging_names=[imaging_names.get(i, i) for i in scheme['imaging']]))
        return render_template('disease.html', active='diseases', title=disease['name'], disease=disease,
                               grouped=grouped, diseases=content['diseases'], ladders=ladders)

    def modality_view(key):
        return dict(MODALITY_VIEWS[key], key=key)

    def modality_summary(key):
        view = modality_view(key)
        imaging = atlas['imaging']
        record = imaging[view['imaging_id']]
        children = [dict(imaging[i], id=i) for i in imaging if imaging[i].get('parent') == view['imaging_id']]
        figs = [f for f in content['modality_figures'] if f['modality'] == key]
        seen = {}
        for section in ('anatomy', 'lesions'):
            for level in ('direct', 'limited'):
                seen[(section, level)] = sorted((i for i in items.values() if i['section'] == section
                                                 and i['obs'].get(key) == level), key=lambda i: i['order'])
        measures = [f for f in atlas['features'].values() if f['role'] == 'measurement'
                    and any(modality_of(i) == key for i in f['imaging'])]
        return {'view': view, 'record': record, 'children': children, 'figures': figs, 'seen': seen,
                'measures': measures}

    @app.get('/imaging/')
    def modality_index():
        cards = [modality_summary(key) for key, _ in MODALITIES]
        others = [dict(v, id=k) for k, v in atlas['imaging'].items()
                  if v['level'] == 'modality' and not any(c['view']['imaging_id'] == k for c in cards)]
        return render_template('modality_index.html', active='imaging', title='영상 종류', cards=cards,
                               others=others, bands=DEPTH_BANDS)

    @app.get('/imaging/<key>/')
    def modality_page(key):
        if key not in MODALITY_VIEWS:
            abort(404)
        info = modality_summary(key)
        by_target = {}
        for f in info['measures']:
            by_target.setdefault(f['target'], []).append(f)
        groups = sorted(((items[t], fs) for t, fs in by_target.items() if t in items),
                        key=lambda pair: (pair[0]['section'] != 'anatomy', pair[0]['order']))
        loose = [f for t, fs in by_target.items() if t not in items for f in fs]
        return render_template('modality.html', active='imaging', title=info['record']['name'], bands=DEPTH_BANDS,
                               groups=groups, loose=loose, **info)

    @app.get('/modality-figures/<name>')
    def modality_figure(name):
        if name not in content['modality_files']:
            abort(404)
        target = modality_root / name
        if not target.is_file():
            abort(503)
        return send_file(target, conditional=True, max_age=3600)

    @app.get('/measurements/')
    def measurement_index():
        level = request.args.get('level', '')
        allowed = {key for key, _, _ in IMPL_LEVELS} | {'ready'}
        level = level if level in allowed else ''

        kind = request.args.get('kind', '')
        kind = kind if kind in {'qualitative', 'quantitative'} else ''
        img = request.args.get('img', '')
        img = img if img in MODALITY_VIEWS else ''

        def modalities_of(feature):
            return {modality_of(i) for i in feature['imaging']} - {''}

        def keep(feature):
            if feature['role'] != 'measurement' or (kind and feature['type'] != kind):
                return False
            if img and img not in modalities_of(feature):
                return False
            if not level:
                return True
            return feature['impl']['level'] in READY_LEVELS if level == 'ready' else feature['impl']['level'] == level

        by_target = {}
        for feature in features.values():
            by_target.setdefault(feature['target'], []).append(feature)

        def block(targets):
            rows = []
            for item in targets:
                fs = [f for f in by_target.get(item['id'], []) if keep(f)]
                if fs:
                    rows.append((item, fs))
            return rows

        anatomy = sorted((i for i in items.values() if i['section'] == 'anatomy'), key=lambda i: i['order'])
        lesions = sorted((i for i in items.values() if i['section'] == 'lesions'), key=lambda i: i['order'])
        sections = []
        for key, label, note in MAP_AXES:
            rows = block([i for i in anatomy if i.get('axis') == key])
            if rows:
                sections.append({'key': 'a-' + key, 'label': label, 'kind': '해부 구조', 'note': note, 'rows': rows})
        for key, label, note, groups in LESION_CATEGORIES:
            rows = block([i for i in lesions if i['group'] in groups])
            if rows:
                sections.append({'key': 'l-' + key, 'label': label, 'kind': '병변', 'note': note, 'rows': rows})
        common = [f for t_id in ('les_generic', 'ana_generic_layer') for f in by_target.get(t_id, []) if keep(f)]
        image = [f for f in features.values() if f['target'].startswith('img_') and keep(f)]
        by = request.args.get('by', '')
        by = by if by == 'imaging' else ''
        if by:
            pseudo = [({'name': '병변 공통 측정', 'abbr': '', 'pseudo': True}, ['les_generic']),
                      ({'name': '층 공통 측정', 'abbr': '', 'pseudo': True}, ['ana_generic_layer']),
                      ({'name': '영상 신호·품질', 'abbr': '', 'pseudo': True},
                       sorted({f['target'] for f in features.values() if f['target'].startswith('img_')}))]
            sections = []
            for key, short in MODALITIES:
                def with_mod(fs, key=key):
                    return [f for f in fs if keep(f) and key in modalities_of(f)]
                rows = [(item, with_mod(by_target.get(item['id'], []))) for item in anatomy + lesions]
                rows += [(head, with_mod([f for t in targets for f in by_target.get(t, [])])) for head, targets in pseudo]
                rows = [(item, fs) for item, fs in rows if fs]
                if rows:
                    sections.append({'key': 'm-' + key, 'label': atlas['imaging'][MODALITY_VIEWS[key]['imaging_id']]['name'],
                                     'kind': '영상', 'note': MODALITY_VIEWS[key]['summary'], 'rows': rows,
                                     'modality': key, 'short': short})
            common, image = [], []
        measures = [f for f in features.values() if f['role'] == 'measurement']
        all_levels = [f['impl']['level'] for f in measures]
        type_counts = {k: sum(1 for f in measures if f['type'] == k) for k in ('qualitative', 'quantitative')}
        summary = [(key, label, note, all_levels.count(key)) for key, label, note in IMPL_LEVELS]
        packaged = sum(1 for f in measures if f['impl'].get('package'))
        img_counts = [(key, label, sum(1 for f in measures if key in modalities_of(f)),
                       sum(1 for f in measures if key in modalities_of(f) and f['impl']['level'] in READY_LEVELS))
                      for key, label in MODALITIES]
        img_names = dict(MODALITIES)
        feature_mods = {f['id']: [k for k, _ in MODALITIES if k in modalities_of(f)] for f in measures}
        for s in sections:
            levels = [f['impl']['level'] for _, fs in s['rows'] for f in fs]
            s['count'] = len(levels)
            s['ready'] = sum(1 for lv in levels if lv in READY_LEVELS)
        example_of = {}
        for ex in content['measure_examples']:
            for layer in ex['layers']:
                for f in layer['features']:
                    example_of.setdefault(f['id'], ex['id'])
        code_links = {f['id']: code_index.links_for(f) for f in measures}
        pending = pending_by_modality(features, items, content['measure_examples'])
        return render_template('measurements.html', pending=pending, active='measurements', title='측정 목록', sections=sections,
                               examples=content['measure_examples'], example_of=example_of, code_links=code_links,
                               packages=[(k, PACKAGES[k]) for k in PACKAGES if k in code_index.available],
                               common=common, image=image, summary=summary, total=len(all_levels),
                               ready=sum(1 for lv in all_levels if lv in READY_LEVELS), level=level,
                               levels=IMPL_LEVELS, kind=kind, type_counts=type_counts, packaged=packaged,
                               img=img, img_counts=img_counts, img_names=img_names, feature_mods=feature_mods, by=by)

    @app.get('/figures/<name>')
    def masked_figure(name):
        if name not in content['masked_files']:
            abort(404)
        target = masked_root / name
        if not target.is_file():
            abort(503)
        return send_file(target, conditional=True, max_age=3600)

    @app.get('/measure-figures/<name>')
    def measure_figure(name):
        if name not in content['measure_files']:
            abort(404)
        target = measure_root / name
        if not target.is_file():
            abort(503)
        return send_file(target, conditional=True, max_age=3600)

    @app.get('/code/<package>.zip')
    def code_zip(package):
        if package not in code_index.available:
            abort(404)
        data, filename = code_index.zip_bytes(package)
        return Response(data, mimetype='application/zip',
                        headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    @app.get('/code/<package>/<path:rel>')
    def code_file(package, rel):
        target = code_index.safe_file(package, rel)
        if target is None:
            abort(404)
        headers = {}
        if request.args.get('download'):
            headers['Content-Disposition'] = f'attachment; filename="{target.name}"'
        return Response(target.read_text(encoding='utf-8'), mimetype='text/plain; charset=utf-8', headers=headers)

    @app.get('/measurements/code/<feature_id>/')
    def measurement_code(feature_id):
        feature = atlas['features'].get(feature_id)
        if not feature or feature['role'] != 'measurement':
            abort(404)
        links = code_index.links_for(feature)
        fn = code_index.function_source(links['function']) if links['function'] else None
        example = next((ex for ex in content['measure_examples']
                        if any(f['id'] == feature_id for la in ex['layers'] for f in la['features'])), None)
        return render_template('measure_code.html', active='measurements', title=f"{feature['name']} · 코드",
                               feature=feature, target=items.get(feature['target']), links=links, fn=fn,
                               example=example, packages=PACKAGES, available=code_index.available,
                               versions={k: code_index.version(k) for k in code_index.available})

    @app.get('/blueprint/')
    def blueprint():
        return render_template('blueprint.html', active='', title='설계 청사진', domains=catalog['domains'])

    @app.get('/fundus/')
    def fundus():
        return redirect('/images/', code=301)

    @app.get('/sources/')
    def sources():
        return render_template('sources.html', active='sources', title='출처와 라이선스')

    @app.get('/sample-images/<alias>')
    def sample_image(alias):
        if alias not in IMAGE_FILES:
            abort(404)
        target = image_root / IMAGE_FILES[alias]
        if not target.is_file():
            abort(503)
        return send_file(target, conditional=True, max_age=3600)

    @app.get('/health')
    def health():
        available = sum((image_root / name).is_file() for name in IMAGE_FILES.values())
        ready = available == len(IMAGE_FILES)
        return jsonify(status='ok' if ready else 'unavailable', site='retinal_atlas_web',
                       stage='atlas_v01', items=len(items), sample_images=available), 200 if ready else 503

    @app.errorhandler(404)
    @app.errorhandler(503)
    def unavailable(error):
        return render_template('error.html', active='', title='페이지를 표시할 수 없습니다',
                               code=error.code), error.code

    return app
