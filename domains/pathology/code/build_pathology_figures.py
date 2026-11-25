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
from pathology_measures import glands, ihc, nuclei, register, texture, tissue  # noqa: E402

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
         'count/10^6 px2': '/10⁶px²', 'category': '', 'count/100um': '개/100 µm'}.get(unit, unit)
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

def precise_window(image_name, cls, level=1, side=1400, rank=0, kind='image'):
    """RGB, label map and µm/px of a window at ``level`` centred on the ``rank``-th largest component of ``cls``."""
    mask_kind = 'ihc_mask' if kind == 'ihc' else 'mask'
    coarse = registry.precise_level(image_name, 4, mask_kind)
    labels, n = ndi.label(coarse == cls)
    if n == 0:
        raise ValueError(f'{image_name}: no class {cls}')
    sizes = np.bincount(labels.ravel())[1:]
    k = int(np.argsort(sizes)[::-1][min(rank, n - 1)]) + 1
    cy, cx = ndi.center_of_mass(labels == k)
    f = 2 ** (4 - level)
    H, W = registry.precise_level_shape(image_name, level, kind)[:2]
    r0 = int(min(max(cy * f - side / 2, 0), H - side))
    c0 = int(min(max(cx * f - side / 2, 0), W - side))
    win = (r0, r0 + side, c0, c0 + side)
    rgb = registry.precise_level(image_name, level, kind, win)[..., :3]
    lab = registry.precise_level(image_name, level, mask_kind, win)
    return rgb, lab, registry.precise_mpp(image_name, kind) * (2 ** level), win


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


def example_head(eid, region, title, caption, base_im, src, source_file, builder, modality='he'):
    name = save(base_im, registry.EXAMPLE_DIR, f'{eid}.jpg', jpg=True)
    label = {'he': 'H&E', 'ihc': 'IHC'}[modality]
    return {'id': eid, 'modality': modality, 'modality_label': label, 'region': region, 'title': f'{label} · {title}',
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
    if cls == 1:
        seg = glands.segment_glands(rgb, target, mpp)
        lpg = glands.lumina_per_gland(rgb, seg, min_px=int(150 / (mpp * mpp)), mpp=mpp)
        layer(ex, 'tumor_glands', '종양 샘 분할·크기·모양', 'green', 'glands.segment_glands',
              '종양 주석 안에서 헤마톡실린 밀도(6 µm 평활, 창 전체 조직 기준 Otsu)가 높은 상피와 그 안의 내강을 합쳐 샘 하나로 나눔 — 고형 판은 큰 덩어리 하나로 나옴(서비스 추정)',
              [val(glands.count(seg, int(150 / (mpp * mpp)))), val(glands.mean_area(seg, mpp, int(150 / (mpp * mpp)))),
               val(glands.circularity(seg, int(150 / (mpp * mpp)))), val(lpg)],
              overlay(size, outlines=[(resize_mask(seg, size), 'green', 2)],
                      fills=[(resize_mask(glands.lumen_mask(rgb, seg, mpp=mpp, min_um2=5.0), size), 'cyan', 190)]))
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


def sicap_example(eid, column, region, title, items, fig_id, fig_label, fig_caption, crib=False, exclude=(), patch=None):
    picked_by_eye = patch is not None
    patch = patch or sicap_pick(column, exclude, crib)
    rgb = np.asarray(Image.open(registry.sicap_paths(patch)['image']).convert('RGB'))
    m = np.asarray(Image.open(registry.sicap_paths(patch)['mask']))
    if m.ndim == 3:
        m = m[..., 0]
    base, size, s = display(rgb, 640)
    tis = tissue.tissue_mask(rgb)
    tumor = m > 0
    ex = example_head(eid, region, title, f'SICAPv2 패치 {patch}입니다. 색 영역은 공급자 전문가의 글리슨 패턴 주석입니다. '
                      + ('사상 표(G4C)에 표시된 패치 중 형태가 뚜렷한 것을 눈으로 골랐습니다. ' if picked_by_eye else '')
                      + '샘은 주석 영역 안에서 서비스가 나눈 추정입니다. ' + SICAP_NOTE,
                      base, SRC_S, f'images/{patch}.jpg', 'sicap_example')
    tones = {3: 'green', 4: 'orange', 5: 'red'}
    fills = [(resize_mask(m == k, size), tones[k], 110) for k in (3, 4, 5)]
    layer(ex, 'patterns', '글리슨 패턴 비율', 'orange', 'tissue.pattern_percent', '종양(주석 값 3·4·5) 면적 중 패턴별 비율',
          [val(tissue.pattern_percent(m == 3, tumor, 3)), val(tissue.pattern_percent(m == 4, tumor, 4)),
           val(tissue.pattern_percent(m == 5, tumor, 5))], overlay(size, fills=fills))
    main = {'G3': 3, 'G4': 4, 'G5': 5}[column]
    gl = m == main
    seg = glands.segment_glands(rgb, gl)
    lum = glands.lumen_mask(rgb, seg, min_px=20)
    lpg = glands.lumina_per_gland(rgb, seg, min_px=150)
    extra = f"최대 {lpg.detail.get('max', 0)}개 · 내강 3개 이상인 샘 {lpg.detail.get('glands_3plus', 0)}개" if lpg.status == 'ok' else ''
    layer(ex, 'glands', '샘 분할·개수·크기·모양', 'green', 'glands.segment_glands',
          '헤마톡실린 밀도(6 px 평활, 조직 전체 Otsu)가 높은 상피와 그 안의 내강을 합쳐 샘 하나로 나눔(서비스 추정) · 샘 수·평균 크기·원형도',
          [val(glands.count(seg, 150)), val(glands.mean_area(seg, None, 150)), val(glands.circularity(seg, 150))],
          overlay(size, outlines=[(resize_mask(seg, size), 'green', 2)]))
    layer(ex, 'lumen', '샘당 내강 수·내강 비율', 'cyan', 'glands.lumina_per_gland',
          '나눈 샘마다 그 안의 닫힌 밝은 공간(20 px 이상) 수를 셈 — 사상 샘은 한 샘에 내강이 많고, 패턴 5는 내강이 거의 없음',
          [val(lpg, extra), val(glands.lumen_fraction(rgb, seg))],
          overlay(size, fills=[(resize_mask(lum, size), 'cyan', 200)], outlines=[(resize_mask(seg, size), 'green', 1)]))
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


IHC_NOTE = ('HMWCK·AMACR 이중 염색입니다. 갈색은 기저세포(HMWCK), 분홍·적색은 AMACR입니다. 색 분리는 서비스 기준'
            '(갈색 DAB 광학밀도 0.03 초과 · 적색은 R≫G이고 B>G)이며 염색 차이에 따라 달라집니다.')


def ihc_example(eid, name, cls, region, title, items, fig_id, fig_label, fig_caption, reading_rows=()):
    rgb, lab, mpp, win = precise_window(name, cls, 1, 1200, 0, kind='ihc')
    base, size, s = display(rgb)
    gs, isup, dx = meta(name)
    ex = example_head(eid, region, title, f'PRECISE {name}(글리슨 {gs}) IHC 슬라이드의 {CLASS_KO[cls]} 부위입니다(같은 조직의 연속 절편 · 화소 {mpp:.2f} µm). '
                      + fig_caption + ' ' + IHC_NOTE + ' 영역 윤곽은 IHC 슬라이드의 공급자 주석입니다.', base, SRC_P, f'{name}_hmwck-amacr.ome.tif', 'ihc_example', 'ihc')
    g = lab == cls
    g_d = resize_mask(g, size)
    layer(ex, 'region', f'{CLASS_KO[cls]} 범위(주석)', CLASS_TONE[cls], 'tissue.lesion_area', 'IHC 슬라이드의 공급자 주석 면적',
          [val(tissue.presence(g)), val(tissue.lesion_area(g, mpp))], overlay(size, outlines=[(g_d, CLASS_TONE[cls], 3)]))
    cov = ihc.basal_coverage(rgb, g)
    rim = cov.detail.pop('rim', np.zeros(g.shape, bool))
    frag = ihc.basal_fragments(rgb, g, mpp)
    frag_mask = frag.detail.pop('fragment_mask', np.zeros(g.shape, bool))
    extra = f"샘 {frag.detail.get('glands', 0)}개 중 {frag.detail.get('glands_with_fragment', 0)}개에 조각" if frag.status == 'ok' else ''
    layer(ex, 'basal', '기저세포 조각·둘레 비율', 'cyan', 'ihc.basal_fragments',
          '샘 경계 ±7.5 µm 띠(흰색) 안의 갈색(HMWCK) 조각(노랑, 15 µm² 이상)을 셈 · 경계 100 µm당 0.35개 이상이면 있음 · 둘레 비율도 함께 표시',
          [val(frag, extra), val(ihc.basal_cell_presence(frag)), val(cov)],
          overlay(size, fills=[(resize_mask(rim, size), 'white', 70), (resize_mask(frag_mask, size), 'yellow', 240)]))
    fr = ihc.amacr_fraction(rgb, g)
    layer(ex, 'amacr', 'AMACR 양성 면적', 'magenta', 'ihc.amacr_fraction', '주석 영역 중 분홍·적색(AMACR) 화소 비율 · 5% 이상이면 양성',
          [val(fr), val(ihc.amacr_positivity(fr))], overlay(size, fills=[(resize_mask(ihc.red_mask(rgb) & g, size), 'green', 210)]))
    if reading_rows:
        layer(ex, 'read', '판독', 'white', '', '공급자 주석 class', [reading(f, t) for f, t in reading_rows],
              overlay(size, texts=[((10, 10), ' · '.join(t for _, t in reading_rows), 'white')]))
    fig = masked(fig_id, items, fig_label, fig_caption + f' PRECISE {name} IHC · 화소 {mpp:.2f} µm.', base,
                 resize_mask(frag_mask, size) if cls in (2, 4, 5) else resize_mask(ihc.red_mask(rgb) & g, size),
                 'cyan' if cls in (2, 4, 5) else 'green', SRC_P, f'{name}_hmwck-amacr.ome.tif', f'level 1 IHC 창({win[2]},{win[0]})–({win[3]},{win[1]}) 축소')
    return ex, [fig]



# ------------------------------------------------------------------ H&E with registered IHC

def _warp_rgb(img, shape, A, t):
    rr, cc = np.indices(shape, dtype=np.float32)
    sr = A[0, 0] * rr + A[0, 1] * cc + t[0]
    sc = A[1, 0] * rr + A[1, 1] * cc + t[1]
    return np.stack([ndi.map_coordinates(img[..., k].astype(np.float32), [sr, sc], order=1, cval=255)
                     for k in range(3)], -1).clip(0, 255).astype(np.uint8)


def registered_basal_example(name='sub-23_ses-01', side=1200):
    """H&E window with the serial IHC section aligned onto it (register.align, per-core rigid) — basal-cell
    fragments measured on the IHC and shown on the H&E."""
    L = 5
    reg = register.align(registry.precise_level(name, L, 'image')[..., :3], registry.precise_mpp(name) * 2 ** L,
                         registry.precise_level(name, L, 'ihc')[..., :3], registry.precise_mpp(name, 'ihc') * 2 ** L)
    mpp, mpp_i = registry.precise_mpp(name) * 2, registry.precise_mpp(name, 'ihc') * 2
    coarse = registry.precise_level(name, 4, 'mask')
    k = side // 8
    both = np.minimum(ndi.uniform_filter((coarse == 1).astype(float), k), ndi.uniform_filter((coarse == 2).astype(float), k))
    cy, cx = np.unravel_index(np.argmax(both), both.shape)
    H, W = registry.precise_level_shape(name, 1)[:2]
    r0 = int(min(max(cy * 8 - side / 2, 0), H - side))
    c0 = int(min(max(cx * 8 - side / 2, 0), W - side))
    win = (r0, r0 + side, c0, c0 + side)
    rgb = registry.precise_level(name, 1, 'image', win)[..., :3]
    lab = registry.precise_level(name, 1, 'mask', win)
    A_um, t_um = register.map_window(reg, (side, side), mpp, (r0 * mpp, c0 * mpp))
    A_px, t_px = A_um / mpp_i, t_um / mpp_i
    corners = np.array([[0, 0], [0, side], [side, 0], [side, side]], float)
    q = corners @ A_px.T + t_px
    Hi, Wi = registry.precise_level_shape(name, 1, 'ihc')[:2]
    q0 = np.maximum(np.floor(q.min(0)).astype(int) - 8, 0)
    q1 = np.minimum(np.ceil(q.max(0)).astype(int) + 8, [Hi, Wi])
    iwin = (int(q0[0]), int(q1[0]), int(q0[1]), int(q1[1]))
    irgb = registry.precise_level(name, 1, 'ihc', iwin)[..., :3]
    ilab = registry.precise_level(name, 1, 'ihc_mask', iwin)
    t_loc = t_px - q0
    frag_t = ihc.basal_fragments(irgb, ilab == 1, mpp_i)
    frag_b = ihc.basal_fragments(irgb, ilab == 2, mpp_i)
    fm_t = frag_t.detail.pop('fragment_mask', np.zeros(ilab.shape, bool))
    fm_b = frag_b.detail.pop('fragment_mask', np.zeros(ilab.shape, bool))
    fm = fm_t | fm_b
    warped = _warp_rgb(irgb, (side, side), A_px, t_loc)
    frag_on_he = register.warp_to(ndi.binary_dilation(fm, iterations=2), (side, side), A_px, t_loc)   # on the aligned IHC
    core = min(reg['cores'], key=lambda c: np.hypot(c['centre_um'][0] - (r0 + side / 2) * mpp, c['centre_um'][1] - (c0 + side / 2) * mpp)) if reg['cores'] else None
    dice = core['dice'] if core else reg['dice_global']
    base, size, s = display(rgb)
    gs, isup, dx = meta(name)
    ex = example_head('ex_he_basal_registered', '양성 샘과 종양', 'H&E 위의 기저세포(IHC 정합)',
                      f'PRECISE {name}(글리슨 {gs}) H&E 창과, 같은 생검의 연속 절편 HMWCK·AMACR IHC를 조직 조각 단위로 정합해 같은 자리로 옮긴 창입니다(이 조직 Dice {dice:.2f}). '
                      'H&E만으로는 기저세포를 확실히 가를 수 없어 기저세포는 IHC에서 잽니다. 두 절편은 떨어져 있어 샘 하나하나가 겹치지는 않습니다 — 같은 부위의 종양·양성 샘을 비교하는 용도입니다.',
                      base, SRC_P, f'{name}_h-e.ome.tif; {name}_hmwck-amacr.ome.tif', 'registered_example')
    tum, ben = resize_mask(lab == 1, size), resize_mask(lab == 2, size)
    layer(ex, 'lesion', '종양·양성 샘(H&E 주석)', 'red', 'tissue.lesion_area', 'H&E 슬라이드의 공급자 주석(빨강 종양 · 초록 양성 샘)',
          [val(tissue.lesion_area(lab == 1, mpp), '종양(빨강)')],
          overlay(size, outlines=[(tum, 'red', 2), (ben, 'green', 2)]))
    ihc_layer = Image.fromarray(warped).resize(size, Image.LANCZOS).convert('RGBA')
    ihc_layer.putalpha(235)
    layer(ex, 'ihc', '정합한 IHC 절편', 'white', 'register.align',
          f'IHC 슬라이드(0.18 µm/px)를 H&E 배율로 바꾸고 조직 조각마다 회전·이동을 맞춤(조직 마스크 Dice {dice:.2f}) · 켜면 같은 부위의 IHC가 보임(샘 단위 대응 아님)',
          [], ihc_layer)
    for key, label, fr, fmask, region_ko, tone in (('basal_benign', '양성 샘의 기저세포(정합한 IHC)', frag_b, fm_b, 'IHC 양성 샘 주석', 'green'),
                                                   ('basal_tumour', '종양의 기저세포(정합한 IHC)', frag_t, fm_t, 'IHC 종양 주석', 'red')):
        region_d = resize_mask(register.warp_to(ilab == (2 if key == 'basal_benign' else 1), (side, side), A_px, t_loc), size)
        on = resize_mask(register.warp_to(ndi.binary_dilation(fmask, iterations=2), (side, side), A_px, t_loc), size)
        im = overlay(size, fills=[(on, 'yellow', 235)], outlines=[(region_d, tone, 2)])   # transparent: use with the IHC layer
        layer(ex, key, label, 'yellow', 'ihc.basal_cell_presence',
              f'정합한 IHC에서 {region_ko}(윤곽) 안 샘 경계 100 µm당 갈색 기저세포 조각(노랑)을 셈 · 0.35 이상이면 있음 · 「정합한 IHC 절편」 층과 함께 보면 IHC 위, 끄면 H&E 위(같은 부위, 샘 단위 대응 아님)',
              [val(fr, region_ko), val(ihc.basal_cell_presence(fr), region_ko)], im)
    pair = Image.new('RGB', (size[0] * 2 + 12, size[1]), 'white')
    pair.paste(base.convert('RGB'), (0, 0))
    pair.paste(Image.fromarray(warped).resize(size, Image.LANCZOS), (size[0] + 12, 0))
    pmask = np.zeros((size[1], size[0] * 2 + 12), bool)
    pmask[:, :size[0]] = tum | ben
    pmask[:, size[0] + 12:] = resize_mask(frag_on_he, size)
    fig = masked('he_basal_registered', ['ana_basal_cell_layer', 'les_adenocarcinoma'], '같은 부위 H&E(왼쪽)와 정합한 IHC(오른쪽)',
                 'H&E(왼쪽, 윤곽은 종양·양성 샘 주석)와 같은 생검의 연속 절편 IHC를 조직 조각 단위로 정합해 같은 부위로 옮긴 그림(오른쪽, 노랑은 기저세포 조각)입니다. '
                 f'양성 샘 둘레에는 갈색 기저세포가 남고(경계 100 µm당 {frag_b.value}), 분홍 AMACR 종양 샘에는 거의 없습니다({frag_t.value}). 두 절편의 샘은 하나하나 겹치지 않습니다.'
                 f' PRECISE {name} · 화소 {mpp:.2f} µm.', pair, pmask, 'yellow', SRC_P,
                 f'{name}_h-e.ome.tif; {name}_hmwck-amacr.ome.tif', f'H&E level 1 창({c0},{r0}) {side}×{side} · IHC는 조직 조각 단위 강체 정합(Dice {dice:.2f})으로 옮김', outline_only=True)
    return ex, [fig]


def he_ihc_pair():
    name = 'sub-23_ses-01'
    he = registry.precise_level(name, 4)[..., :3]
    ih = registry.precise_level(name, 4, 'ihc')[..., :3]
    he_m = registry.precise_level(name, 4, 'mask')
    ih_m = registry.precise_level(name, 4, 'ihc_mask')
    tiles, masks = [], []
    for rgb, lab in ((he, he_m), (ih, ih_m)):
        h, w = lab.shape
        rgb = rgb[:h, :w]
        t = tissue.tissue_mask(rgb, min_object_px=200)
        rows, cols = np.nonzero(t | (lab > 0))
        r0, r1, c0, c1 = rows.min(), rows.max(), cols.min(), cols.max()
        tiles.append(Image.fromarray(rgb[r0:r1, c0:c1]))
        masks.append(lab[r0:r1, c0:c1] == 1)
    hgt = 640
    ims = [im.resize((max(int(im.width * hgt / im.height), 1), hgt), Image.LANCZOS) for im in tiles]
    gap = 14
    canvas = Image.new('RGB', (ims[0].width + gap + ims[1].width, hgt), (255, 255, 255))
    canvas.paste(ims[0], (0, 0))
    canvas.paste(ims[1], (ims[0].width + gap, 0))
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), 'H&E', fill=(40, 20, 60), font=_font(20))
    d.text((ims[0].width + gap + 10, 8), 'HMWCK·AMACR', fill=(40, 20, 60), font=_font(20))
    full = np.zeros((hgt, canvas.width), bool)
    full[:, :ims[0].width] = resize_mask(masks[0], ims[0].size)
    full[:, ims[0].width + gap:] = resize_mask(masks[1], ims[1].size)
    return masked('he_ihc_pair', ['les_adenocarcinoma', 'ana_basal_cell_layer'], '종양(전문가 주석, 두 슬라이드 각각)',
                  f'같은 생검의 연속 절편 H&E(왼쪽)와 HMWCK·AMACR IHC(오른쪽)입니다(PRECISE {name}, 글리슨 3+4). IHC에서 종양 샘은 분홍(AMACR)이고 '
                  '양성 샘 둘레에는 갈색 기저세포가 남아 있습니다. 두 절편은 정합하지 않았습니다.', canvas, full, 'red', SRC_P,
                  f'{name}_h-e.ome.tif; {name}_hmwck-amacr.ome.tif', '두 슬라이드의 1/16 축소 영상을 높이 640 px로 나란히 붙임', outline_only=True)


HPF_FIELD_NUMBER_MM = 22.0          # eyepiece field number of a common 10x eyepiece
HPF_OBJECTIVE = 40.0


def _label(dr, xy, text, tone='yellow', size=16):
    font = _font(size)
    box = dr.textbbox(xy, text, font=font)
    dr.rectangle([box[0] - 4, box[1] - 3, box[2] + 4, box[3] + 3], fill=(15, 23, 42, 215))
    dr.text(xy, text, fill=(*TONES[tone], 255), font=font)


def reference_figures():
    """Real-image figures for the gland lumen, the 40x high-power field and the pixel size (PRECISE, µm-calibrated)."""
    figs, d = [], registry.MASKED_DIR
    # gland lumen: service lumen estimate inside the provider's benign-gland annotation
    name = 'sub-24_ses-01'                           # large benign glands with closed lumens
    rgb, lab, mpp, win = precise_window(name, 2, level=1, side=1200)
    benign = lab == 2
    lum = glands.lumen_mask(rgb, benign, mpp=mpp)
    base, size, s = display(rgb)
    frac = glands.lumen_fraction(rgb, benign, mpp)
    ov = overlay(size, fills=[(resize_mask(lum, size), 'blue', 150)], outlines=[(resize_mask(benign, size), 'green', 2)])
    figs.append(figure_record(
        'gland_lumen', ['ana_gland_lumen'], '샘 내강(서비스 자동 추정)',
        f'양성 샘(초록 윤곽, 공급자 주석) 안의 비어 있는 내강(파랑)입니다. 내강은 서비스가 주석 샘 안의 밝고 채도 낮은 닫힌 공간을 '
        f'자동으로 찾은 것입니다(glands.lumen_mask). 이 창의 내강 비율 {fmt(frac.value, frac.unit)}. PRECISE {name} · 화소 {mpp:.2f} µm.',
        save(base, d, 'gland_lumen.jpg', jpg=True), save(ov, d, 'gland_lumen_mask.png'), size, SRC_P,
        f'{name}_h-e.ome.tif', f'level 1 창 {win[3] - win[2]}×{win[1] - win[0]} px 축소'))
    # high-power field: a 40x field drawn to scale on a calibrated tumour window
    name = 'sub-20_ses-01'
    rgb, lab, mpp, win = precise_window(name, 1, level=1, side=1400)
    base, size, s = display(rgb)
    diam_um = HPF_FIELD_NUMBER_MM / HPF_OBJECTIVE * 1000
    area_mm2 = math.pi * (diam_um / 2000) ** 2
    r = diam_um / mpp * s / 2
    cx, cy = size[0] / 2, size[1] / 2
    ov = overlay(size, outlines=[(resize_mask(lab == 1, size), 'red', 2)])
    dr = ImageDraw.Draw(ov)
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*TONES['yellow'], 255), width=4)
    dr.line([(cx - r, cy), (cx + r, cy)], fill=(*TONES['yellow'], 255), width=2)
    _label(dr, (cx - 70, cy + 8), f'지름 {diam_um / 1000:.2f} mm')
    _label(dr, (cx - 70, cy + 34), f'면적 {area_mm2:.2f} mm²')
    figs.append(figure_record(
        'hpf_field', ['ref_hpf'], '40× 고배율 시야(실제 축척)',
        f'노란 원은 시야수 {HPF_FIELD_NUMBER_MM:.0f} mm 접안렌즈와 {HPF_OBJECTIVE:.0f}× 대물렌즈로 보는 한 시야(지름 {diam_um / 1000:.2f} mm, '
        f'면적 {area_mm2:.2f} mm²)를 이 슬라이드의 화소 크기({mpp:.2f} µm)로 실제 축척에 맞춰 그린 것입니다. 시야수 20이면 0.20 mm², 26.5면 0.34 mm²로 '
        f'장비마다 다르므로 「HPF당 개수」는 mm²당으로 바꿔 비교합니다. 빨간 윤곽은 종양(공급자 주석, 글리슨 4+5). PRECISE {name}.',
        save(base, d, 'hpf_field.jpg', jpg=True), save(ov, d, 'hpf_field_mask.png'), size, SRC_P,
        f'{name}_h-e.ome.tif', f'level 1 창 {win[3] - win[2]}×{win[1] - win[0]} px 축소'))
    # pixel size: scale bar and an enlarged inset where single pixels are visible
    name = 'sub-01_ses-01'
    rgb, lab, mpp, win = precise_window(name, 2, level=0, side=560)
    base, size, s = display(rgb, max_side=760)
    ov = Image.new('RGBA', size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    bar_um = 50
    bar = bar_um / mpp * s
    x0, y0 = 24, size[1] - 34
    dr.rectangle([x0 - 8, y0 - 30, x0 + bar + 8, y0 + 14], fill=(15, 23, 42, 200))
    dr.rectangle([x0, y0, x0 + bar, y0 + 7], fill=(255, 255, 255, 255))
    dr.text((x0, y0 - 26), f'{bar_um} µm = {bar_um / mpp:.0f} px', fill=(255, 255, 255, 255), font=_font(16))
    n_px, cell = 12, 16                                  # 12x12 source pixels, each drawn as a 16-px cell
    lum_y = rgb.mean(-1)                             # inset on the highest-contrast spot near the centre (a nucleus edge)
    h0, w0 = rgb.shape[0] // 4, rgb.shape[1] // 4
    spread = ndi.maximum_filter(lum_y, n_px) - ndi.minimum_filter(lum_y, n_px)
    cr, cc = np.unravel_index(np.argmax(spread[h0:3 * h0, w0:3 * w0]), (2 * h0, 2 * w0))
    cr, cc = int(cr) + h0 - n_px // 2, int(cc) + w0 - n_px // 2
    crop = rgb[cr:cr + n_px, cc:cc + n_px]
    inset = Image.fromarray(crop).resize((n_px * cell, n_px * cell), Image.NEAREST).convert('RGBA')
    gd = ImageDraw.Draw(inset)
    for k in range(n_px + 1):
        gd.line([(k * cell, 0), (k * cell, n_px * cell)], fill=(255, 255, 255, 140), width=1)
        gd.line([(0, k * cell), (n_px * cell, k * cell)], fill=(255, 255, 255, 140), width=1)
    ix, iy = size[0] - n_px * cell - 20, 20
    sx, sy = cc * s, cr * s
    dr.line([(sx + n_px * s, sy), (ix, iy + n_px * cell)], fill=(*TONES['yellow'], 220), width=2)
    dr.rectangle([sx - 2, sy - 2, sx + n_px * s + 2, sy + n_px * s + 2], outline=(*TONES['yellow'], 255), width=2)
    ov.paste(inset, (ix, iy))
    dr.rectangle([ix - 1, iy - 1, ix + n_px * cell, iy + n_px * cell], outline=(*TONES['yellow'], 255), width=2)
    _label(dr, (ix, iy + n_px * cell + 8), f'한 칸 = 1 화소 = {mpp:.3f} µm', size=15)
    figs.append(figure_record(
        'pixel_size', ['ref_pixel_size'], '화소 크기(메타데이터 µm/px)',
        f'원 해상도(level 0) 창입니다. 슬라이드 메타데이터의 화소 크기 {mpp:.3f} µm로 바꾸면 흰 막대 {bar_um} µm는 '
        f'{bar_um / mpp:.0f} 화소입니다. 오른쪽 위는 노란 상자 안 {n_px}×{n_px} 화소를 확대해 한 칸이 화소 하나임을 보인 것입니다. '
        f'면적은 화소 수 × ({mpp:.3f} µm)²로 바꾸며, 화소 크기가 없는 영상(SICAPv2 패치)은 화소 단위로만 잽니다. PRECISE {name}.',
        save(base, d, 'pixel_size.jpg', jpg=True), save(ov, d, 'pixel_size_mask.png'), size, SRC_P,
        f'{name}_h-e.ome.tif', f'level 0 창 {win[3] - win[2]}×{win[1] - win[0]} px · 표시 {s:.2f}배'))

    # nucleolus: highest-resolution window inside the expert tumour annotation; nothing is marked on the nuclei
    name = 'sub-05_ses-01'
    rgb, lab, mpp, win = precise_window(name, 1, level=0, side=300)
    base, size, s = display(rgb, max_side=760)
    base = Image.fromarray(rgb).resize((750, 750), Image.LANCZOS)
    size, s = base.size, 750 / rgb.shape[1]
    ov = Image.new('RGBA', size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    bar_um = 10
    bar = bar_um / mpp * s
    x0, y0 = 24, size[1] - 34
    dr.rectangle([x0 - 8, y0 - 30, x0 + bar + 8, y0 + 14], fill=(15, 23, 42, 200))
    dr.rectangle([x0, y0, x0 + bar, y0 + 7], fill=(255, 255, 255, 255))
    dr.text((x0, y0 - 26), f'{bar_um} µm', fill=(255, 255, 255, 255), font=_font(16))
    gleason, _, _ = meta(name)
    figs.append(figure_record(
        'nucleolus_hpf', ['ana_nucleolus'], '종양 안 원 해상도 확대(표시 없음)',
        f'전문가가 종양으로 주석한 부위(글리슨 {gleason})를 원 해상도({mpp:.3f} µm/화소)에서 약 {300 * mpp:.0f} µm 폭으로 잘라 2.5배 키운 것입니다. '
        '보라색 핵 안의 더 진한 작은 점이 핵소체이며, 암세포에서는 핵이 커지고 핵소체가 뚜렷해집니다. 핵소체 하나하나는 표시하지 않았습니다'
        '(자동 핵소체 검출은 검증에서 판별력이 없어 쓰지 않음). 흰 막대는 10 µm입니다. PRECISE ' + name + '.',
        save(base, d, 'nucleolus_hpf.jpg', jpg=True), save(ov, d, 'nucleolus_hpf_mask.png'), size, SRC_P,
        f'{name}_h-e.ome.tif', f'level 0 창 {win[3] - win[2]}×{win[1] - win[0]} px · 표시 {s:.2f}배'))
    return figs


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
          '한 샘 안에 여러 구멍이 뚫린 사상 샘(패턴 4)입니다.'), {'crib': True, 'patch': '17B0017717_Block_Region_2_20_6_xini_12957_yini_65495'}),
        (('ex_he_gp5', 'G5', '글리슨 패턴 5', '글리슨 패턴 5', ['les_gleason_pattern_5', 'les_solid_sheets'], 'gp5', '글리슨 패턴 5(전문가 주석)',
          '샘 없이 판·끈으로 자라는 패턴 5입니다.'), {'exclude': ('G3',)}),
    ]:
        ex, f = sicap_example(*args, **kw)
        examples.append(ex)
        figs += f
    for args, kw in [
        (('ex_ihc_benign', 'sub-23_ses-01', 2, '양성 샘', '양성 샘(IHC)', ['ana_basal_cell_layer', 'ana_benign_gland'], 'ihc_basal',
          '기저세포(HMWCK 갈색)', '양성 샘 둘레의 갈색 기저세포입니다.'), {}),
        (('ex_ihc_tumor', 'sub-23_ses-01', 1, '종양', '종양(IHC)', ['les_adenocarcinoma'], 'ihc_amacr', 'AMACR 양성 종양 샘(분홍)',
          '기저세포 없이 AMACR(분홍)이 양성인 암 샘입니다.'), {}),
        (('ex_ihc_hgpin', 'sub-01_ses-03', 4, 'HGPIN', '고등급 PIN(IHC)', ['les_hgpin'], 'ihc_hgpin', 'HGPIN 둘레 기저세포(갈색)',
          'AMACR 양성이지만 둘레에 기저세포가 조각으로 남은 HGPIN입니다. 둘레 비율은 낮지만(약 2%) 기저세포 조각 수로 보면 침윤암(조각 없음)과 갈립니다.'), {'reading_rows': (('ft_lesion_generic_presence', 'HGPIN (공급자 주석)'),)}),
        (('ex_ihc_idc', 'sub-02_ses-01', 5, '관내암', '관내암(IHC)', ['les_intraductal_carcinoma'], 'ihc_idc', '관내암 둘레 기저세포(갈색)',
          '관을 채운 암세포 둘레에 기저세포가 남은 관내암입니다.'), {'reading_rows': (('ft_idc_presence', '있음 (공급자 주석)'),)}),
    ]:
        ex, f = ihc_example(*args, **kw)
        examples.append(ex)
        figs += f
    figs.append(he_ihc_pair())
    figs += reference_figures()
    ex, f = registered_basal_example()
    examples.append(ex)
    figs += f
    import build_pathology_grading as grading_build
    helpers_s = (overlay, resize_mask, save, val, reading, example_head, layer, masked, SRC_S)
    src_par = dict(registry.source_record('par'), _id='par')
    helpers_p = (overlay, resize_mask, save, val, reading, example_head, layer, masked, src_par)
    g_examples, g_figs, _ = grading_build.build(helpers_s, helpers_p)
    examples += g_examples
    figs += g_figs
    import build_pathology_paper_figures as paper_build
    figs += paper_build.build()
    for fig in figs:
        fig['base_sha256'] = registry.sha256(registry.MASKED_DIR / fig['base'])
        fig['overlay_sha256'] = registry.sha256(registry.MASKED_DIR / fig['overlay']) if fig['overlay'] else ''
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
