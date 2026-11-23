"""Build the pathology atlas images (prostate H&E): item figures and measurement examples.

Sources: PRECISE (CC BY 4.0, OME-TIFF pyramids with 7-class pixel masks, calibrated µm/px) and SICAPv2
(CC BY 4.0, 10× patches with Gleason-pattern masks, uncalibrated). Lesion overlays are the providers' expert
annotations; tissue, lumen and nucleus overlays are the service's automatic estimates (stated in captions).

    .venv/bin/python -B domains/pathology/code/build_pathology_figures.py
"""
from __future__ import annotations

import json
import math
import sys
import warnings

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

import pathology_atlas_registry as registry

sys.path.insert(0, str(registry.MEASURES_SRC))
from pathology_measures import glands, nuclei, texture, tissue  # noqa: E402

warnings.filterwarnings('ignore')
Image.MAX_IMAGE_PIXELS = None
TONES = {'blue': (56, 189, 248), 'yellow': (255, 211, 77), 'green': (74, 222, 128), 'red': (248, 113, 113),
         'magenta': (232, 121, 249), 'white': (255, 255, 255), 'orange': (251, 146, 60), 'cyan': (34, 211, 238)}
CLASS_TONE = {1: 'red', 2: 'green', 3: 'white', 4: 'orange', 5: 'magenta', 6: 'yellow', 7: 'blue'}
CLASS_KO = {1: '종양', 2: '양성 샘', 3: '인공물', 4: 'HGPIN', 5: '관내암', 6: '비정형 관내 증식', 7: '간질'}
PRECISE = registry.source_record('precise')
SICAP = registry.source_record('sicapv2')
SICAP_NOTE = 'SICAPv2 패치에는 화소 간격이 없어 길이·면적은 화소 단위입니다(10× 패치).'


# ------------------------------------------------------------------ drawing helpers

def _font(size):
    for name in ('NotoSansCJK-Regular.ttc', 'NanumGothic.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def resize_mask(mask, size):
    return np.asarray(Image.fromarray(np.asarray(mask, bool).astype(np.uint8) * 255).resize(size, Image.NEAREST)) > 127


def overlay(size, fills=(), outlines=(), dots=(), texts=(), lines=()):
    w, h = size
    canvas = np.zeros((h, w, 4), np.uint8)
    for mask, tone, alpha in fills:
        canvas[mask] = (*TONES[tone], alpha)
    for mask, tone, width in outlines:
        edge = mask & ~ndi.binary_erosion(mask, iterations=width)
        canvas[edge] = (*TONES[tone], 255)
    im = Image.fromarray(canvas, 'RGBA')
    d = ImageDraw.Draw(im)
    for p0, p1, tone, width in lines:
        d.line([p0, p1], fill=(*TONES[tone], 255), width=width)
    for (x, y), tone, r in dots:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*TONES[tone], 255))
    for (x, y), text, tone in texts:
        font = _font(15)
        box = d.textbbox((x, y), text, font=font)
        d.rectangle([box[0] - 4, box[1] - 3, box[2] + 4, box[3] + 3], fill=(15, 23, 42, 215))
        d.text((x, y), text, fill=(*TONES[tone], 255), font=font)
    return im


def fmt(value, unit):
    if value is None:
        return '—'
    if isinstance(value, bool):
        return '있음' if value else '없음'
    u = {'px': 'px', 'px2': 'px²', 'mm': 'mm', 'mm2': 'mm²', 'um2': 'µm²', '%': '%', 'count': '개', 'index': '',
         'ratio': '', 'OD': 'OD', 'presence': '', 'count/mm2': '/mm²', 'count/10^4 px2': '/10⁴px²',
         'count/10^6 px2': '/10⁶px²'}.get(unit, unit)
    if isinstance(value, float):
        text = f'{value:,.0f}' if abs(value) >= 1000 else (f'{value:,.1f}' if abs(value) >= 10 else f'{value:.3g}')
    else:
        text = f'{value:,}' if isinstance(value, int) else str(value)
    return f'{text} {u}'.strip()


def val(m, extra=''):
    text = fmt(m.value, m.unit) if m.status == 'ok' else {'not_observed': '관찰 안 됨', 'not_evaluable': '계산 불가'}[m.status]
    return {'id': m.feature_id, 'value': text + (f' · {extra}' if extra else ''), 'status': m.status}


def reading(fid, text):
    return {'id': fid, 'value': text, 'status': 'reading'}


def save(im, directory, name, jpg=False):
    if jpg:
        im.convert('RGB').save(directory / name, quality=88, optimize=True)
    else:
        im.save(directory / name, optimize=True)
    return name


# ------------------------------------------------------------------ inputs

def precise_window(image_name, cls, level=1, side=1400, rank=0):
    """RGB, label map and µm/px of a window at ``level`` centred on the ``rank``-th largest component of ``cls``."""
    coarse = registry.precise_level(image_name, 4, 'mask')
    labels, n = ndi.label(coarse == cls)
    if n == 0:
        raise ValueError(f'{image_name}: no class {cls}')
    sizes = np.bincount(labels.ravel())[1:]
    k = int(np.argsort(sizes)[::-1][min(rank, n - 1)]) + 1
    cy, cx = ndi.center_of_mass(labels == k)
    f = 2 ** (4 - level)
    H, W = registry.precise_level_shape(image_name, level)[:2]
    r0 = int(min(max(cy * f - side / 2, 0), H - side))
    c0 = int(min(max(cx * f - side / 2, 0), W - side))
    win = (r0, r0 + side, c0, c0 + side)
    rgb = registry.precise_level(image_name, level, 'image', win)[..., :3]
    lab = registry.precise_level(image_name, level, 'mask', win)
    return rgb, lab, registry.precise_mpp(image_name) * (2 ** level), win


def meta(image_name):
    r = registry.precise_participants()[image_name]
    return r.get('Gleason_score', ''), r.get('ISUP_Grade_Group_', ''), r.get('SLIDE_DIAGNOSIS', '')


def display(rgb, max_side=760):
    im = Image.fromarray(rgb)
    s = min(max_side / im.width, max_side / im.height, 2.0)
    size = (int(im.width * s), int(im.height * s))
    return im.resize(size, Image.LANCZOS), size, s


# ------------------------------------------------------------------ records

def figure_record(fid, items, label, caption, base_name, ov_name, size, src, source_file, transform, legend=()):
    return {'id': fid, 'items': items, 'source': src['_id'], 'source_file': source_file, 'mask_label': label,
            'legend': list(legend), 'caption': caption, 'transform': transform, 'base': base_name, 'overlay': ov_name,
            'width': size[0], 'height': size[1], 'name': src['name'], 'credit': src['credit'], 'url': src['url'],
            'license': src['license'], 'license_url': src['license_url']}


def masked(fid, items, label, caption, base_im, mask, tone, src, source_file, transform, legend=(), outline_only=False):
    d = registry.MASKED_DIR
    base_name = save(base_im, d, f'{fid}.jpg', jpg=True)
    fills = [] if outline_only else [(mask, tone, 70)]
    ov = overlay(base_im.size, fills=fills, outlines=[(mask, tone, 2)])
    return figure_record(fid, items, label, caption, base_name, save(ov, d, f'{fid}_mask.png'), base_im.size, src,
                         source_file, transform, legend)


def example_head(eid, region, title, caption, base_im, src, source_file, builder):
    name = save(base_im, registry.EXAMPLE_DIR, f'{eid}.jpg', jpg=True)
    return {'id': eid, 'modality': 'he', 'modality_label': 'H&E', 'region': region, 'title': f'H&E · {title}',
            'source': src['_id'], 'source_file': source_file, 'caption': caption, 'builder': builder, 'base': name,
            'width': base_im.size[0], 'height': base_im.size[1], 'layers': [], 'credit': src['credit'],
            'url': src['url'], 'license': src['license'], 'license_url': src['license_url']}


def layer(ex, key, label, tone, function, how, features, im):
    name = save(im, registry.EXAMPLE_DIR, f"{ex['id']}_{key}.png")
    ex['layers'].append({'key': key, 'label': label, 'tone': tone, 'function': function, 'how': how,
                         'features': features, 'file': name})


SRC_P = dict(PRECISE, _id='precise')
SRC_S = dict(SICAP, _id='sicapv2')


# ------------------------------------------------------------------ PRECISE examples

def core_example():
    name = 'sub-23_ses-01'
    rgb = registry.precise_level(name, 4)[..., :3]
    lab = registry.precise_level(name, 4, 'mask')
    h, w = lab.shape
    rgb = rgb[:h, :w]
    mpp = registry.precise_mpp(name) * 16
    tis = tissue.tissue_mask(rgb, min_object_px=200)
    rows, cols = np.nonzero(tis | (lab > 0))
    pad = 30
    r0, r1, c0, c1 = max(rows.min() - pad, 0), min(rows.max() + pad, h), max(cols.min() - pad, 0), min(cols.max() + pad, w)
    rgb, lab, tis = rgb[r0:r1, c0:c1], lab[r0:r1, c0:c1], tis[r0:r1, c0:c1]
    base, size, s = display(rgb, 860)
    gs, isup, dx = meta(name)
    ex = example_head('ex_he_core', '생검 코어 전체', '생검 코어 전체',
                      f'PRECISE {name}(글리슨 {gs} · ISUP 등급군 {isup})의 생검 코어 전체입니다(1/16 축소 영상). 색 영역은 공급자 전문가 주석이고, '
                      '조직 범위는 서비스가 유리 배경과 색으로 가른 것입니다. 화소 간격은 OME 메타데이터를 써서 mm·mm²로 계산했습니다.',
                      base, SRC_P, f'{name}_h-e.ome.tif', 'core_example')
    t_d = resize_mask(tis, size)
    layer(ex, 'tissue', '조직 면적', 'blue', 'tissue.tissue_area', '채도·밝기로 유리 배경을 빼고 구멍을 채운 조직 범위',
          [val(tissue.tissue_area(tis, mpp))], overlay(size, fills=[(t_d, 'blue', 40)], outlines=[(t_d, 'blue', 2)]))
    fills = [(resize_mask(lab == k, size), CLASS_TONE[k], 130) for k in (2, 3, 4, 5, 6)]
    fills.append((resize_mask(lab == 1, size), 'red', 150))
    layer(ex, 'composition', '조직 구성 비율', 'green', 'tissue.tumor_fraction', '조직 면적을 분모로 한 주석 class별 면적 비율',
          [val(tissue.tumor_fraction(lab, tis)), val(tissue.benign_gland_fraction(lab, tis)),
           val(tissue.stroma_fraction(lab, tis)), val(tissue.artifact_fraction(lab, tis))], overlay(size, fills=fills))
    tum = lab == 1
    pts = np.argwhere(tum)
    lines = []
    if len(pts) > 2:
        from scipy.spatial import ConvexHull
        hull = pts[ConvexHull(pts).vertices]
        dd = np.sqrt(((hull[:, None] - hull[None]) ** 2).sum(-1))
        i, j = np.unravel_index(int(dd.argmax()), dd.shape)
        lines = [((hull[i][1] * s, hull[i][0] * s), (hull[j][1] * s, hull[j][0] * s), 'yellow', 3)]
    layer(ex, 'tumor', '종양 면적·최대 길이·초점 수', 'red', 'tissue.tumor_area', '종양 주석의 면적, 가장 먼 두 종양 화소 사이 거리, 100 µm 안의 조각을 합친 뒤 0.005 mm² 이상인 초점 수',
          [val(tissue.tumor_area(lab, mpp)), val(tissue.tumor_extent(lab, mpp)), val(tissue.lesion_count(tum, min_px=int(5000 / (mpp * mpp)), merge_px=int(100 / mpp)))],
          overlay(size, fills=[(resize_mask(tum, size), 'red', 150)], lines=lines))
    layer(ex, 'grade', '글리슨 점수·등급군(판독)', 'white', '', '공급자 임상표의 판정', [reading('ft_gleason_score', f'{gs} (공급자 판독)'),
          reading('ft_isup_grade_group', f'{isup} (공급자 판독)')], overlay(size, texts=[((10, 10), f'Gleason {gs} · ISUP {isup}', 'white')]))
    figs = [masked('core_tissue', ['ref_tissue_area', 'ana_prostate'], '조직 범위(자동 추정)', '전립선 생검 코어의 조직 범위입니다(서비스 자동 추정).',
                   base, t_d, 'blue', SRC_P, f'{name}_h-e.ome.tif', '1/16 축소 영상(level 4) 일부를 잘라 표시', outline_only=True),
            masked('core_tumor', ['les_adenocarcinoma'], '종양(전문가 주석)', f'생검 코어의 종양 주석입니다(글리슨 {gs}).',
                   base, resize_mask(tum, size), 'red', SRC_P, f'{name}_h-e.ome.tif', '1/16 축소 영상(level 4) 일부를 잘라 표시')]
    return ex, figs


def window_example(eid, name, cls, region, title, items, fig_id, fig_label, fig_caption, level=1, side=1400, rank=0,
                   nuclei_on=True, glands_on=False, reading_rows=()):
    rgb, lab, mpp, win = precise_window(name, cls, level, side, rank)
    tis = tissue.tissue_mask(rgb)
    base, size, s = display(rgb)
    gs, isup, dx = meta(name)
    ex = example_head(eid, region, title,
                      f'PRECISE {name}(진단 {dx} · 글리슨 {gs})의 {CLASS_KO[cls]} 부위입니다(화소 {mpp:.2f} µm). 색 영역은 공급자 전문가 주석이고, '
                      '내강·핵은 서비스 자동 추정입니다.', base, SRC_P, f'{name}_h-e.ome.tif', 'window_example')
    target = lab == cls
    t_d = resize_mask(target, size)
    layer(ex, 'lesion', f'{CLASS_KO[cls]} 범위', CLASS_TONE[cls], 'tissue.lesion_area', '공급자 주석 class의 면적과 창 안 조직 대비 비율',
          [val(tissue.presence(target)), val(tissue.lesion_area(target, mpp)), val(tissue.lesion_fraction(target, tis)),
           val(tissue.lesion_count(target, min_px=30))], overlay(size, fills=[(t_d, CLASS_TONE[cls], 90)], outlines=[(t_d, CLASS_TONE[cls], 2)]))
    if glands_on:
        lum = glands.lumen_mask(rgb, target, mpp=mpp)
        layer(ex, 'glands', '샘 개수·크기·모양', 'green', 'glands.mean_area', '주석 샘 성분별 면적·원형도와 조직 면적당 개수',
              [val(glands.count(target)), val(glands.gland_density(target, tis, mpp)), val(glands.mean_area(target, mpp)),
               val(glands.circularity(target))], overlay(size, outlines=[(t_d, 'green', 3)]))
        layer(ex, 'lumen', '내강 비율·샘당 내강 수', 'cyan', 'glands.lumen_fraction', '샘 안의 밝고 채도 낮은 닫힌 공간(40 µm² 이상, 슬라이드 바깥 유리와 이어진 곳 제외)을 내강으로 봄',
              [val(glands.lumen_fraction(rgb, target, mpp)), val(glands.lumina_per_gland(rgb, target, mpp=mpp))],
              overlay(size, fills=[(resize_mask(lum, size), 'cyan', 170)]))
    if nuclei_on:
        region_mask = target if target.sum() > 2000 else tis
        nu = nuclei.detect(rgb, region_mask, mpp)
        layer(ex, 'nuclei', '핵 밀도·크기·다양성', 'magenta', 'nuclei.density',
              '헤마톡실린을 색 분리해 세 단계 Otsu의 가장 짙은 단계·거리 변환 분할로 찾은 핵 후보(12–180 µm²)',
              [val(nuclei.density(nu)), val(nuclei.mean_area(nu)), val(nuclei.area_variation(nu)), val(nuclei.hematoxylin_od(rgb, region_mask))],
              overlay(size, fills=[(resize_mask(nu.labels > 0, size), 'magenta', 200)]))
        layer(ex, 'texture', '조직 질감 대비', 'orange', 'texture.glcm_contrast', 'GLCM 대비(32단계 · 거리 2px · 4방향 평균)',
              [val(texture.glcm_contrast(rgb, region_mask))], overlay(size, outlines=[(resize_mask(region_mask, size), 'orange', 2)]))
    if reading_rows:
        layer(ex, 'read', '판독', 'white', '', '공급자 주석 class를 판독 값으로 옮김', [reading(f, t) for f, t in reading_rows],
              overlay(size, texts=[((10, 10), ' · '.join(t for _, t in reading_rows), 'white')]))
    fig = masked(fig_id, items, fig_label, fig_caption + f' PRECISE {name} · 화소 {mpp:.2f} µm.', base, t_d, CLASS_TONE[cls], SRC_P,
                 f'{name}_h-e.ome.tif', f'level {level} 영상에서 ({win[2]},{win[0]})–({win[3]},{win[1]}) {side}×{side} 창을 잘라 {size[0]} px로 축소')
    extra = []
    if nuclei_on:
        nu = nuclei.detect(rgb, target if target.sum() > 2000 else tis, mpp)
        extra.append(masked(fig_id + '_nuclei', ['ana_nucleus'], '핵 후보(자동 추정)', '헤마톡실린 색 분리로 찾은 핵 후보입니다(서비스 자동 추정).',
                            base, resize_mask(nu.labels > 0, size), 'magenta', SRC_P, f'{name}_h-e.ome.tif', 'level 1 창 축소'))
    return ex, [fig] + extra


# ------------------------------------------------------------------ SICAPv2 examples

def sicap_pick(column, exclude=(), crib=False):
    table = registry.sicap_table()
    cribs = {r['image_name'] for r in registry.sicap_cribriform() if r['G4C'] == 1}
    best, frac = None, -1
    for r in table:
        if r[column] != 1 or any(r[c] == 1 for c in exclude):
            continue
        name = r['image_name'][:-4]
        if crib != (r['image_name'] in cribs):
            continue
        m = np.asarray(Image.open(registry.sicap_paths(name)['mask']))
        code = {'G3': 3, 'G4': 4, 'G5': 5}[column]
        f = float((m == code).mean())
        if 0.3 < f < 0.85 and f > frac:     # most of the patch, with some context
            best, frac = name, f
        if frac > 0.6:
            break
    return best


def sicap_example(eid, column, region, title, items, fig_id, fig_label, fig_caption, crib=False, exclude=()):
    patch = sicap_pick(column, exclude, crib)
    rgb = np.asarray(Image.open(registry.sicap_paths(patch)['image']).convert('RGB'))
    m = np.asarray(Image.open(registry.sicap_paths(patch)['mask']))
    if m.ndim == 3:
        m = m[..., 0]
    base, size, s = display(rgb, 640)
    tis = tissue.tissue_mask(rgb)
    tumor = m > 0
    ex = example_head(eid, region, title, f'SICAPv2 패치 {patch}입니다. 색 영역은 공급자 전문가의 글리슨 패턴 주석입니다. ' + SICAP_NOTE,
                      base, SRC_S, f'images/{patch}.jpg', 'sicap_example')
    tones = {3: 'green', 4: 'orange', 5: 'red'}
    fills = [(resize_mask(m == k, size), tones[k], 110) for k in (3, 4, 5)]
    layer(ex, 'patterns', '글리슨 패턴 비율', 'orange', 'tissue.pattern_percent', '종양(주석 값 3·4·5) 면적 중 패턴별 비율',
          [val(tissue.pattern_percent(m == 3, tumor, 3)), val(tissue.pattern_percent(m == 4, tumor, 4)),
           val(tissue.pattern_percent(m == 5, tumor, 5))], overlay(size, fills=fills))
    main = {'G3': 3, 'G4': 4, 'G5': 5}[column]
    gl = m == main
    if column != 'G5':
        lum = glands.lumen_mask(rgb, gl)
        layer(ex, 'lumen', '샘당 내강 수·내강 비율', 'cyan', 'glands.lumina_per_gland',
              '주석 영역의 성분을 샘으로 보고 그 안의 닫힌 밝은 공간(30 px 이상) 수를 셈(사상 샘은 한 성분에 내강이 많음)',
              [val(glands.lumina_per_gland(rgb, gl)), val(glands.lumen_fraction(rgb, gl)), val(glands.count(gl))],
              overlay(size, fills=[(resize_mask(lum, size), 'cyan', 190)], outlines=[(resize_mask(gl, size), 'orange', 2)]))
    nu = nuclei.detect(rgb, gl if gl.sum() > 500 else tis, None, smooth=1.0)
    layer(ex, 'nuclei', '핵 밀도·크기', 'magenta', 'nuclei.density', '헤마톡실린 색 분리 후 핵 후보(화소 단위)',
          [val(nuclei.density(nu)), val(nuclei.mean_area(nu)), val(nuclei.area_variation(nu))],
          overlay(size, fills=[(resize_mask(nu.labels > 0, size), 'magenta', 200)]))
    reads = [reading('ft_cribriform_presence', '있음 (SICAPv2 사상 표)' if crib else '없음 (SICAPv2 사상 표)')] if column == 'G4' else []
    if reads:
        layer(ex, 'read', '사상 패턴(판독)', 'white', '', 'SICAPv2 사상 패턴 표(G4C)', reads,
              overlay(size, texts=[((10, 10), reads[0]['value'], 'white')]))
    fig = masked(fig_id, items, fig_label, fig_caption + ' ' + SICAP_NOTE.split('(')[0].strip(), base, resize_mask(gl, size),
                 tones[main], SRC_S, f'images/{patch}.jpg', f'512×512 패치를 {size[0]} px로 확대')
    return ex, [fig]


def main() -> int:
    for d in (registry.MASKED_DIR, registry.EXAMPLE_DIR):
        d.mkdir(parents=True, exist_ok=True)
        for old in list(d.glob('*.jpg')) + list(d.glob('*.png')):
            old.unlink()
    examples, figs = [], []
    ex, f = core_example()
    examples.append(ex)
    figs += f
    for args, kw in [
        (('ex_he_benign', 'sub-01_ses-01', 2, '양성 샘', '양성 샘과 간질', ['ana_benign_gland', 'ana_secretory_cells'], 'benign_glands',
          '양성 샘(전문가 주석)', '굴곡진 큰 양성 샘들입니다.'), {'glands_on': True}),
        (('ex_he_tumor', 'sub-20_ses-01', 1, '종양', '종양(글리슨 4+5)', ['les_adenocarcinoma', 'les_gleason_pattern_4'], 'tumor_hpf',
          '종양(전문가 주석)', '글리슨 4+5 선암 부위입니다.'), {'level': 0, 'side': 1200}),
        (('ex_he_hgpin', 'sub-01_ses-03', 4, 'HGPIN', '고등급 PIN', ['les_hgpin'], 'hgpin', 'HGPIN(전문가 주석)',
          '기존 샘 안 상피가 이형 세포로 바뀐 고등급 PIN입니다.'), {'reading_rows': (('ft_lesion_generic_presence', 'HGPIN 있음 (공급자 주석)'),)}),
        (('ex_he_idc', 'sub-02_ses-01', 5, '관내암', '관내암', ['les_intraductal_carcinoma'], 'idc', '관내암(전문가 주석)',
          '기존 관을 이형 세포가 채운 관내암입니다.'), {'reading_rows': (('ft_idc_presence', '있음 (공급자 주석)'),)}),
        (('ex_he_aip', 'sub-05_ses-01', 6, '비정형 관내 증식', '비정형 관내 증식', ['les_atypical_intraductal_proliferation'], 'aip',
          '비정형 관내 증식(전문가 주석)', '관내암 기준에 못 미치는 비정형 관내 증식입니다.'), {'nuclei_on': False}),
    ]:
        ex, f = window_example(*args, **kw)
        examples.append(ex)
        figs += f
    rgb, lab, mpp, win = precise_window('sub-21_ses-01', 3, 2, 1000)
    base, size, s = display(rgb)
    figs.append(masked('artifact', ['les_tissue_artifact'], '인공물(전문가 주석)', '판독을 방해하는 조직 인공물입니다. PRECISE sub-21_ses-01.',
                       base, resize_mask(lab == 3, size), 'white', SRC_P, 'sub-21_ses-01_h-e.ome.tif', 'level 2 창 축소'))
    figs.append(masked('stroma', ['ana_stroma'], '간질(주석)', '샘 사이의 섬유근육 간질입니다(공급자 주석 · 자동 보충 포함 가능). PRECISE sub-21_ses-01.',
                       base, resize_mask(lab == 7, size), 'blue', SRC_P, 'sub-21_ses-01_h-e.ome.tif', 'level 2 창 축소'))
    for args, kw in [
        (('ex_he_gp3', 'G3', '글리슨 패턴 3', '글리슨 패턴 3', ['les_gleason_pattern_3'], 'gp3', '글리슨 패턴 3(전문가 주석)',
          '따로 떨어진 잘 형성된 암 샘(패턴 3)입니다.'), {'exclude': ('G4', 'G5')}),
        (('ex_he_gp4', 'G4', '글리슨 패턴 4', '글리슨 패턴 4', ['les_gleason_pattern_4', 'les_fused_glands'], 'gp4', '글리슨 패턴 4(전문가 주석)',
          '융합·불완전한 샘(패턴 4)입니다.'), {'exclude': ('G3', 'G5')}),
        (('ex_he_cribriform', 'G4', '사상 샘', '사상(체 모양) 샘', ['les_cribriform'], 'cribriform', '사상 패턴(전문가 주석)',
          '한 샘 안에 여러 구멍이 뚫린 사상 샘(패턴 4)입니다.'), {'crib': True}),
        (('ex_he_gp5', 'G5', '글리슨 패턴 5', '글리슨 패턴 5', ['les_gleason_pattern_5', 'les_solid_sheets'], 'gp5', '글리슨 패턴 5(전문가 주석)',
          '샘 없이 판·끈으로 자라는 패턴 5입니다.'), {'exclude': ('G3',)}),
    ]:
        ex, f = sicap_example(*args, **kw)
        examples.append(ex)
        figs += f
    for fig in figs:
        fig['base_sha256'] = registry.sha256(registry.MASKED_DIR / fig['base'])
        fig['overlay_sha256'] = registry.sha256(registry.MASKED_DIR / fig['overlay'])
    ids = [e['id'] for e in examples] + [f['id'] for f in figs]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate id')
    registry.WEB_DATA.mkdir(parents=True, exist_ok=True)
    (registry.WEB_DATA / 'masked_figures.json').write_text(json.dumps(
        {'generated_by': 'domains/pathology/code/build_pathology_figures.py', 'figures': figs}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (registry.WEB_DATA / 'measurement_examples.json').write_text(json.dumps(
        {'generated_by': 'domains/pathology/code/build_pathology_figures.py',
         'note': 'values computed by pathology-measures on PRECISE (µm-calibrated) and SICAPv2 (pixels)', 'examples': examples},
        ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'masked figures {len(figs)} · examples {len(examples)} · layers {sum(len(e["layers"]) for e in examples)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
