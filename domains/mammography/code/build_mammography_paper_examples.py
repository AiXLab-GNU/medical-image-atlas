"""DBT and CEM item figures and measurement examples from CC BY paper figures (CC BY 2.0 or later).

Provider files live once in ``resources/datasets/mammography_atlas_provider_figures/`` under their original names,
pinned by SHA-256 in ``g_provider_figures``. Panels are cut by fixed boxes. Reader marks are found from the figure
itself: yellow circles (Amir 2026), blue arrows (Eren 2026) and the red ROI tint (Favati 2022). Lesion outlines
are service estimates (bright region inside the reader circle or next to the arrow tip) unless the author drew them.
Called from ``build_mammography_figures.py``.
"""
from __future__ import annotations

import csv
import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

import mammography_atlas_registry as registry
from build_mammography_figures import (CATEGORY_KO, _font, layer, overlay, reading, resize_mask, save_jpg, save_png,
                                       val)
from mammography_measures import calcification, distortion, enhancement, mass

PROVIDER_DIR = registry.DATASETS / 'mammography_atlas_provider_figures'
PX = '논문 그림은 화소 간격을 알 수 없어 길이·면적은 화소 단위입니다.'


def provider():
    with (registry.CATALOG / 'g_provider_figures_v01.csv').open(encoding='utf-8', newline='') as handle:
        rows = {r['file']: r for r in csv.DictReader(handle)}
    for name, row in rows.items():
        if registry.sha256(PROVIDER_DIR / name) != row['sha256']:
            raise ValueError(f'provider file changed: {name}')
    return rows


def panel(name, box, scale):
    """(grey float crop, RGB crop, display size) of one panel; box = (x0, y0, x1, y1) in provider pixels."""
    rgb = Image.open(PROVIDER_DIR / name).convert('RGB').crop(box)
    grey = unmark(rgb)
    size = (int(rgb.size[0] * scale), int(rgb.size[1] * scale))
    return grey, rgb, size


def unmark(rgb):
    """Grey image for measurement with reader marks (yellow circles, blue arrows) replaced by the nearest unmarked pixel."""
    a = np.asarray(rgb).astype(int)
    marks = ((a[..., 0] > 150) & (a[..., 1] > 110) & (a[..., 2] < 100)) | ((a[..., 2] - a[..., 0] > 60) & (a[..., 2] > 120))
    marks = ndi.binary_dilation(marks, iterations=2)
    grey = np.asarray(rgb.convert('L'), dtype=np.float32) / 255.0
    if marks.any():
        _, (ri, ci) = ndi.distance_transform_edt(marks, return_indices=True)
        grey = grey[ri, ci]
    return grey


def source(source_id, fig_label):
    s = registry.source_record(source_id)
    return dict(s, credit=f"{s['credit']}, {fig_label}")


def head(eid, modality, label, region, title, caption, src, file, base):
    base_name = f'{eid}.jpg'
    base.save(registry.EXAMPLE_DIR / base_name, quality=90, optimize=True)
    return {'id': eid, 'modality': modality, 'modality_label': label, 'region': region, 'title': f'{label} · {title}',
            'source': src['_id'], 'source_file': file, 'caption': caption, 'builder': 'paper_examples',
            'base': base_name, 'width': base.size[0], 'height': base.size[1], 'layers': [],
            'credit': src['credit'], 'url': src['url'], 'license': src['license'], 'license_url': src['license_url']}


def up(rgb, size):
    return rgb.resize(size, Image.LANCZOS)


def disk_mask(shape, centre, r):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return np.hypot(yy - centre[0], xx - centre[1]) <= r


# ------------------------------------------------------------------ DBT

def dbt_mass():
    name, box, s = 'diagnostics-16-02321-g004.jpg', (176, 6, 340, 370), 3
    grey, rgb, size = panel(name, box, s)
    src = dict(source('eren2026', 'Fig. 4B'), _id='eren2026')
    tip = (185 - box[1], 207 - box[0])                       # blue arrow tip (row, col) in the panel
    centre = (tip[0] + 11, tip[1] + 9)
    m = enhancement.enhancing_region(grey, centre, 16, quantile=0.55)
    ex = head('ex_dbt_mass', 'dbt', 'DBT', '침상형 종괴', 'DBT 단면의 침상형 종괴',
              'DBT 단면에서 2D 영상에 가려졌던 종괴의 침상·분엽 경계가 드러난 예입니다(저자: 삼중음성 유방암, ACR D). '
              '종괴 경계는 저자 화살표 끝의 밝은 영역을 서비스가 추정한 것입니다. ' + PX, src, name, up(rgb, size))
    md = resize_mask(m, size)
    L = ex['layers']
    L.append(layer(ex, 'outline', '종괴 경계·크기(추정)', 'red', 'mass.size', '화살표 끝 반경 16 px 안에서 밝은 영역(상위 45%)을 잇고 구멍을 채운 서비스 추정 경계',
                   [val(mass.size(m)), val(mass.mass_area(m)), val(distortion.presence(m)), val(distortion.lesion_size(m))],
                   overlay(size, outlines=[(md, 'red', 3)])))
    L.append(layer(ex, 'shape', '모양(원형도·볼록도·반지름 변동)', 'orange', 'mass.circularity', '추정 경계의 4π·면적/둘레², 볼록도, 반지름 변동',
                   [val(mass.circularity(m)), val(mass.solidity(m)), val(mass.radial_sd(m))],
                   overlay(size, fills=[(md, 'orange', 70)])))
    sp = mass.spiculation_index(grey, m)
    pts = [((p[1] * s, p[0] * s), 'magenta', 2) for p in sp.detail.get('ridge_points', [])]
    L.append(layer(ex, 'spicule', '침상 지수', 'magenta', 'mass.spiculation_index', '경계 바깥 띠의 선 구조 중 종괴 중심을 향하는 것의 비율',
                   [val(sp)], overlay(size, dots=pts, outlines=[(md, 'red', 1)])))
    L.append(layer(ex, 'read', '모양·경계·구성(저자 판독)', 'white', '', '원 논문 그림 설명의 서술',
                   [reading('ft_mass_margin', '침상 · 분엽 윤곽 (저자 서술)'), reading('ft_mass_shape', '불규칙 (저자: 분엽형 윤곽)'),
                    reading('ft_breast_composition', 'd (저자: ACR Type D)')],
                   overlay(size, texts=[((10, 10), '침상·분엽 경계 · ACR D (저자)', 'white')])))
    fig = masked(ex, md, 'mass_spiculated_dbt', ['les_mass_spiculated', 'les_mass'], 'DBT 침상형 종괴(서비스 추정 경계)', 'red',
                 'DBT 재구성 단면에서 침상·분엽 경계가 드러난 종괴입니다(2D 영상에서는 가려져 있었음).', src, name, box,
                 '파란 화살표는 원 저자의 표시이고, 빨간 경계는 서비스 추정입니다.')
    return ex, fig


def dbt_distortion():
    name, box, s = 'diagnostics-16-02321-g005.jpg', (384, 8, 745, 612), 1.3
    grey, rgb, size = panel(name, box, s)
    src = dict(source('eren2026', 'Fig. 5B'), _id='eren2026')
    tip = (314 - box[1], 478 - box[0])                       # blue arrow tip; the arrow points along (0.5, 0.87)
    centre = (tip[0] + 6, tip[1] + 10)                       # 12 px beyond the tip
    radius = 45
    grid = [distortion.convergence_index(grey, (centre[0] + dy, centre[1] + dx), radius) for dy in (-8, 0, 8) for dx in (-8, 0, 8)]
    values = [g.value for g in grid]
    ci = grid[4]
    ci.value = round(float(np.median(values)), 3)
    ci.note = f'화살표 끝 주변 3×3 중심(±8 px)의 중앙값 · 범위 {min(values):.2f}–{max(values):.2f} · 무작위 배열이면 약 0.25'
    pts = np.array(grid[4].detail.get('points', []))
    region = np.zeros(grey.shape, bool)
    if len(pts):
        region[pts[:, 0].astype(int), pts[:, 1].astype(int)] = True
        region = ndi.binary_closing(ndi.binary_dilation(region, iterations=3), iterations=6)
    ex = head('ex_dbt_distortion', 'dbt', 'DBT', '구조왜곡', 'DBT 단면의 구조왜곡',
              'DBT 단면에서 드러난 구조왜곡입니다(저자: 방사상 흉터, ACR C). 저자 화살표 끝 주변에서 둘레 띠의 선 구조가 '
              '중심으로 모이는 정도를 계산했습니다. 이 그림의 해상도에서는 값이 무작위 수준(약 0.25)과 비슷해, 이 간이 지수로는 '
              '저자가 본 구조왜곡이 드러나지 않습니다(한계를 보여 주는 예). ' + PX, src, name, up(rgb, size))
    h, w = size[1], size[0]
    yy, xx = np.mgrid[0:h, 0:w]
    rr = np.hypot(yy - centre[0] * s, xx - centre[1] * s)
    ring = (rr > 0.25 * radius * s) & (rr < radius * s)
    L = ex['layers']
    L.append(layer(ex, 'converge', '침상선 수렴 지수', 'magenta', 'distortion.convergence_index',
                   '중심 둘레 띠(보라)에서 선 구조 중 중심을 향하는 것의 비율. 중심 위치에 민감해 화살표 끝 주변 9개 중심의 중앙값을 씀',
                   [val(ci, f'9점 중앙값 · 범위 {min(values):.2f}–{max(values):.2f}')], overlay(size, fills=[(ring, 'magenta', 30)], dots=[((p[1] * s, p[0] * s), 'magenta', 1.6) for p in pts])))
    L.append(layer(ex, 'extent', '범위', 'red', 'distortion.distortion_extent', '중심을 향하는 선 구조 점들을 이은 범위의 최대 지름',
                   [val(distortion.distortion_extent(region))], overlay(size, outlines=[(resize_mask(region, size), 'red', 2)])))
    L.append(layer(ex, 'read', '구조왜곡 유무·구성(저자 판독)', 'white', '', '원 논문 그림 설명의 서술',
                   [reading('ft_ad_presence', '있음 (저자 서술 · 방사상 흉터)'), reading('ft_breast_composition', 'c (저자: ACR Type C)')],
                   overlay(size, texts=[((10, 10), '구조왜곡 · ACR C (저자)', 'white')])))
    fig = masked(ex, resize_mask(disk_mask(grey.shape, centre, radius), size), 'distortion_dbt', ['les_architectural_distortion'],
                 'DBT 구조왜곡 부위(저자 화살표 중심 원)', 'magenta',
                 'DBT 재구성 단면에서 드러난 구조왜곡입니다(저자: 방사상 흉터).', src, name, box,
                 '파란 화살표는 원 저자의 표시이고, 보라 원은 화살표가 가리키는 점을 중심으로 서비스가 그린 범위입니다.')
    return ex, fig


def dbt_calcifications():
    name, s = 'diagnostics-12-00771-g001.jpg', 1.1
    rgb = Image.open(PROVIDER_DIR / name).convert('RGB')
    a = np.asarray(rgb).astype(np.float32)
    roi = ndi.binary_fill_holes(ndi.binary_opening((a[..., 0] - a[..., 1]) > 25, iterations=2))
    inner = ndi.binary_erosion(roi, iterations=4)
    ring = ndi.binary_dilation(roi, iterations=8) & ~ndi.binary_dilation(roi, iterations=3)
    grey = a[..., 1].copy()                                   # green channel, rescaled inside the tinted ROI
    grey[roi] *= np.median(grey[ring]) / np.median(grey[inner])
    grey /= 255.0
    size = (int(rgb.size[0] * s), int(rgb.size[1] * s))
    src = dict(source('favati2022', 'Fig. 1'), _id='favati2022')
    c = calcification.detect(grey, inner, tophat_px=3, k=16.0, min_px=5)
    ex = head('ex_dbt_calc', 'dbt', 'DBT', '석회화', 'DBT 단면의 석회화',
              'BI-RADS 4 석회화의 DBT 단면입니다. 빨간 영역은 원 저자의 ROI이고, 그 안에서 top-hat으로 석회화 점을 찾았습니다. '
              '석회화 군집은 여러 단면에 흩어지므로 한 단면의 개수는 전체보다 적을 수 있습니다. ' + PX, src, name, up(rgb, size))
    spots = resize_mask(c.labels > 0, size)
    cen = [(p.centroid[1] * s, p.centroid[0] * s) for p in c.props]
    lines = []
    if len(cen) >= 2:
        arr = np.array(cen)
        d = np.sqrt(((arr[:, None] - arr[None]) ** 2).sum(-1))
        i, j = np.unravel_index(int(d.argmax()), d.shape)
        lines.append((tuple(arr[i]), tuple(arr[j]), 'cyan', 3))
    L = ex['layers']
    L.append(layer(ex, 'spots', '석회화 검출·개수', 'yellow', 'calcification.count', '저자 ROI(빨강 틴트를 녹색 채널 비율로 되돌림) 안 white top-hat(반경 3 px)이 중앙값 + 16·MAD를 넘고 5 px 이상인 점. 그림 JPEG 잡음을 피하려 경계값을 높임',
                   [val(calcification.count(c)), val(calcification.spot_size(c))],
                   overlay(size, fills=[(ndi.binary_dilation(spots, iterations=2), 'yellow', 240)],
                           outlines=[(resize_mask(roi, size), 'white', 1)])))
    L.append(layer(ex, 'extent', '범위', 'cyan', 'calcification.extent', '가장 먼 두 석회화 중심 사이 거리',
                   [val(calcification.extent(c))], overlay(size, lines=lines, dots=[(p, 'cyan', 3) for p in cen])))
    fig = masked(ex, resize_mask(roi, size), 'calc_dbt', ['les_calcification'], '석회화 범위(원 저자 ROI)', 'yellow',
                 'DBT 단면에서 본 BI-RADS 4 석회화입니다.', src, name, None,
                 '빨간 영역은 원 저자의 ROI(그림에 들어 있음)이고, 노란 겹침은 같은 범위를 다시 표시한 것입니다.')
    return ex, fig


# ------------------------------------------------------------------ CEM

def find_circles(name):
    a = np.asarray(Image.open(PROVIDER_DIR / name).convert('RGB')).astype(int)
    yel = (a[..., 0] > 170) & (a[..., 1] > 130) & (a[..., 2] < 90)
    lab, n = ndi.label(ndi.binary_dilation(yel, iterations=2))
    out = []
    for k in range(1, n + 1):
        ys, xs = np.nonzero(lab == k)
        if len(ys) >= 80:
            out.append(((ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2, (xs.max() - xs.min()) / 2))
    return out


def circle_in(circles, box):
    return next((cy - box[1], cx - box[0], r) for cy, cx, r in circles if box[0] <= cx <= box[2] and box[1] <= cy <= box[3])


def cem_lesion(eid, name, box, s, fig_label, region, title, caption, conspicuity, pattern=None, nme=None, items=(),
               fig_id=None, mask_label=''):
    grey, rgb, size = panel(name, box, s)
    cy, cx, r = circle_in(find_circles(name), box)
    inner = r - 4                                                    # stay inside the yellow ring
    m = enhancement.enhancing_region(grey, (cy, cx), inner, quantile=0.8 if not pattern else 0.7)
    if pattern:                                                      # rim enhancement: fill the ring's hole
        m = ndi.binary_fill_holes(ndi.binary_closing(m, iterations=4))
    src = dict(source('amir2026', fig_label), _id='amir2026')
    ex = head(eid, 'cem', 'CEM', region, title, caption + ' 증강 범위는 저자 원 안의 밝은 영역을 서비스가 추정한 것입니다. ' + PX,
              src, name, up(rgb, size))
    md = resize_mask(m, size)
    L = ex['layers']
    ir = enhancement.intensity_ratio(grey, m)
    radius = math.sqrt(max(m.sum(), 1) / math.pi)
    band = ndi.binary_dilation(m, iterations=max(int(1.5 * radius), 2)) & ~ndi.binary_dilation(m, iterations=max(int(0.5 * radius), 1)) & (grey > 0.03)
    L.append(layer(ex, 'enh', '증강 강도 비', 'cyan', 'enhancement.intensity_ratio', '추정 증강 범위(빨강)의 평균 밝기 ÷ 둘레 띠(파랑)의 평균 밝기',
                   [val(ir)], overlay(size, fills=[(md, 'red', 90), (resize_mask(band, size), 'blue', 60)])))
    feats = [val(distortion.presence(m))]
    if nme:
        feats.append(val(enhancement.nme_extent(m)))
    else:
        feats.append(val(distortion.lesion_size(m)))
    L.append(layer(ex, 'outline', '증강 범위·크기(추정)', 'red', 'enhancement.nme_extent' if nme else 'distortion.lesion_size',
                   '저자 원 안에서 밝은 영역을 잇고 구멍을 채운 서비스 추정 범위의 최대 지름', feats, overlay(size, outlines=[(md, 'red', 3)])))
    reads = [reading('ft_lesion_conspicuity', f'{conspicuity} (저자 서술)')]
    if pattern:
        reads.append(reading('ft_enh_pattern', f'{pattern} (저자 서술)'))
    if nme:
        reads.append(reading('ft_nme_distribution', f'{nme} (저자 서술)'))
    label = ' · '.join([f'뚜렷함 {conspicuity}'] + ([pattern] if pattern else []) + ([nme] if nme else []))
    L.append(layer(ex, 'read', '뚜렷함·양상(저자 판독)', 'white', '', '원 논문 그림 설명의 서술', reads,
                   overlay(size, texts=[((10, 10), label + ' (저자)', 'white')],
                           points=[((cx * s, cy * s), 'yellow', r * s)])))
    fig = masked(ex, md, fig_id, list(items), mask_label, 'red', caption, src, name, box,
                 '노란 원은 원 저자의 표시이고, 빨간 범위는 서비스 추정입니다.') if fig_id else None
    return ex, fig


def cem_bpe():
    name, s = 'cureus-0018-00000107590-i03.jpg', 0.9
    rgb = Image.open(PROVIDER_DIR / name).convert('RGB')
    size = (int(rgb.size[0] * s), int(rgb.size[1] * s))
    src = dict(source('hoon2026', 'Fig. 3'), _id='hoon2026')
    grey = np.asarray(rgb.convert('L'), dtype=np.float32) / 255.0
    ex = head('ex_cem_bpe', 'cem', 'CEM', '배경 실질 증강', '배경 실질 증강(BPE) 비교',
              '같은 유방의 CEM 재조합 영상입니다. 치료 전(A) 중등도 BPE가 선행 항암 치료 뒤(B) 최소 BPE로 줄었습니다(저자 판독). '
              '두 영상의 유방 안 평균 밝기를 함께 보였습니다(같은 그림 안 비교용 참고값).', src, name, up(rgb, size))
    halves = [(0, 365), (378, 750)]
    texts, fills = [], []
    for (x0, x1), lab in zip(halves, ('A 중등도', 'B 최소')):
        part = np.zeros(grey.shape, bool)
        part[:, x0:x1] = True
        br = ndi.binary_fill_holes(ndi.binary_closing(part & (filters_gauss(grey) > 0.03), iterations=8))
        lab, n = ndi.label(br)
        if n:
            br = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
        fills.append((resize_mask(br & ~ndi.binary_erosion(br, iterations=3), size), 'yellow', 220))
        texts.append(((x0 * s + 10, 12), f"{lab} · 평균 {grey[br].mean():.2f}", 'white'))
    ex['layers'].append(layer(ex, 'bpe', '배경 실질 증강 정도(저자 판독)', 'yellow', '', '원 논문 그림 설명의 판독(최소·경도·중등도·고도)',
                              [reading('ft_bpe_level', 'A 중등도 → B 최소 (저자 판독)')], overlay(size, fills=fills, texts=texts)))
    fig = masked(ex, resize_mask(grey > 0.04, size), 'bpe_cem', ['ana_fibroglandular_tissue'], '배경 실질 증강(재조합 영상)', 'yellow',
                 '같은 유방의 CEM 재조합 영상에서 배경 실질 증강이 치료 전(중등도)보다 치료 후(최소) 줄었습니다.', src, name, None)
    return ex, fig


def filters_gauss(img):
    return ndi.gaussian_filter(img, 4)


def masked(ex, mask_display, fid, items, label, tone, caption, src, name, box, marks=''):
    base = Image.open(registry.EXAMPLE_DIR / ex['base'])
    save_jpg(base, registry.MASKED_DIR, f'{fid}.jpg')
    ov = overlay(base.size, fills=[(mask_display, tone, 55)], outlines=[(mask_display, tone, 2)])
    return {'id': fid, 'items': items, 'source': src['_id'], 'source_file': name, 'mask_label': label, 'legend': [],
            'caption': caption + (' ' + marks if marks else ''),
            'transform': (f'원 그림에서 패널 {box}을 잘라 ' if box else '원 그림 전체를 ') + f'{base.size[0]}×{base.size[1]}로 변환; 표시를 같은 비율로 겹침',
            'base': f'{fid}.jpg', 'overlay': save_png(ov, registry.MASKED_DIR, f'{fid}_mask.png'),
            'width': base.size[0], 'height': base.size[1], 'name': src['name'], 'credit': src['credit'], 'url': src['url'],
            'license': src['license'], 'license_url': src['license_url']}


def modality_figure():
    """DBT vs 2D comparison (Eren 2026 Fig. 1) as a whole-figure masked figure for the DBT page."""
    name = 'diagnostics-16-02321-g001.jpg'
    rgb = Image.open(PROVIDER_DIR / name).convert('RGB')
    src = dict(source('eren2026', 'Fig. 1'), _id='eren2026')
    save_jpg(rgb, registry.MASKED_DIR, 'dbt_vs_2d.jpg')
    ov = overlay(rgb.size, points=[((390, 322), 'cyan', 26)])
    return {'id': 'dbt_vs_2d', 'items': ['les_mass_spiculated'], 'source': 'eren2026', 'source_file': name,
            'mask_label': '저자 화살표가 가리키는 종괴', 'legend': [],
            'caption': '같은 유방의 2D 유방촬영(A)과 DBT 단면(B)입니다. 2D에서는 치밀 실질에 가려 보이지 않던 침상형 종괴가 DBT에서 드러납니다(저자: 2등급 침윤성 유관암, ACR D). 화살표는 원 저자의 표시입니다.',
            'transform': f'원 그림 전체 {rgb.size[0]}×{rgb.size[1]}; 화살표 끝에 원을 겹침',
            'base': 'dbt_vs_2d.jpg', 'overlay': save_png(ov, registry.MASKED_DIR, 'dbt_vs_2d_mask.png'),
            'width': rgb.size[0], 'height': rgb.size[1], 'name': src['name'], 'credit': src['credit'], 'url': src['url'],
            'license': src['license'], 'license_url': src['license_url']}


# Plain paper panels: shown as published (the arrows/circles are the authors'); the finding is the author's caption.
# id, items, source_id, file, box (None = whole figure), panel label, Korean caption, author caption
PAPER_PANELS = [
    ('paper_axillary_adenopathy', ['les_axillary_adenopathy', 'ana_axilla'], 'khoo2025', 'cureus-0017-00000100096-i01.jpg', None,
     'Figure 1', '양쪽 MLO 영상에서 액와 림프절이 커지고 지방문 없이 하얗게 보입니다(화살표, 전이 의심). 왼쪽(B)의 림프절이 특히 큽니다.',
     'Mammogram demonstrating bilateral axillary lymphadenopathy suspicious for metastasis as indicated by arrows.'),
    ('paper_biopsy_clip', ['les_biopsy_marker'], 'weaver2021', '13244_2021_1136_Fig4_HTML.jpg', (397, 298, 784, 555),
     'Fig. 4d', '정위 조직검사 뒤 CC 영상입니다. 원 안의 작은 금속이 조직검사 표지자(클립)이고, 화살표는 초음파 유도 조직검사 때 넣은 리본 모양 클립입니다.',
     'Post-procedure CC mammogram demonstrating a stereotactic biopsy clip in appropriate position, with a minimal hematoma '
     'and no sign of clip migration (circle). ... A ribbon-shaped clip was placed (arrow).'),
    ('paper_focal_asymmetry', ['les_focal_asymmetry', 'les_asymmetry'], 'cohen2026', 'cureus-0018-00000114224-i01.webp', None,
     'Figure 1', '선별 검사 CC(A)와 MLO(B) 두 영상 모두에서 내하사분면에 같은 국소 비대칭(흰 원)이 보입니다. 두 방향에서 보이고 종괴의 볼록한 경계는 없습니다.',
     'Craniocaudal (A) and mediolateral oblique (B) digital mammographic views of the right breast for screening demonstrate '
     'an abnormal focal asymmetry (open white circles) in the lower inner quadrant.'),
    ('paper_coarse_heterogeneous', ['les_calc_coarse_heterogeneous', 'les_calc_fine_pleomorphic'], 'wang2026', 'fonc-16-1966376-g001.webp',
     (150, 66, 372, 740), 'Figure 1A',
     '왼쪽 MLO 영상의 크고 밀도가 높은 종괴 안에 거친 불균질 석회화와 미세 다형성 석회화가 있습니다(저자: 엽상종양). 그림 해상도가 낮아 석회화 하나하나는 잘 보이지 않습니다.',
     'Left mediolateral oblique mammogram showing a large high-density central breast mass with internal coarse heterogeneous '
     'and regional fine pleomorphic calcifications.'),
    ('paper_breast_implant', ['les_breast_implant'], 'kanavou2023', 'diagnostics-13-03186-g008.jpg', (0, 0, 166, 392), 'Figure 8a',
     '유방 절제 뒤 실리콘 보형물로 재건한 오른쪽 유방의 MLO 영상입니다. 보형물이 경계가 매끈한 타원형의 아주 밝은(방사선 비투과) 덩어리로 보입니다.',
     'In the MLO view, the implant appears as a homogenous radiopaque oval mass with smooth borders.'),
    ('paper_dystrophic_calc', ['les_calc_dystrophic', 'les_postsurgical_scar'], 'gigli2026', 'life-16-00701-g004.jpg', (0, 0, 743, 592),
     'Figure 4a,b', '수술·방사선 치료 1년 뒤 CC(a)와 MLO(b) 영상입니다. 수술 부위의 어두운(지방) 영역 둘레에 가는 이영양성 석회화가 생긴 지방괴사이며, 짧은 흰 선은 수술 클립입니다.',
     'Features consistent with fat necrosis are present, characterized mammographically by a radiolucent area with thin, '
     'peripheral dystrophic calcifications (a,b).'),
    ('paper_developing_asymmetry', ['les_developing_asymmetry', 'les_asymmetry'], 'shamir2024', 'bioengineering-11-00451-g001a.jpg',
     (80, 30, 700, 526), 'Figure 1A,B',
     '기준 선별 검사(A)와 17개월 뒤 추적 검사(B)의 네 방향 영상입니다. 왼쪽 유방에 이전에 없던 비대칭이 아주 미묘하게 새로 생겼습니다(저자: 맨눈으로 알아보기 어려움, 조직검사로 침윤성 암 확인).',
     'Between the baseline screening mammogram (A) and the follow-up screening mammogram 17 months later (B), there has been '
     'a very subtle development of left breast asymmetry that is difficult to perceive with the naked eye.'),
    ('paper_global_asymmetry', ['les_global_asymmetry', 'les_asymmetry'], 'sudo2024', 'PMC11388040/gr1.jpg', None, 'Fig. 1',
     '오른쪽(A)과 왼쪽(B) 유방을 비교하면 왼쪽의 섬유선 조직이 넓은 범위에서 더 많습니다. 원 그림의 대비가 낮습니다.',
     'Mammography showed global asymmetry between the right (A) and left (B) breasts.'),
    ('paper_axillary_tail', ['ana_axillary_tail'], 'schonour2025', 'PMC12546409/gr1.jpg', (0, 0, 791, 1330), 'Fig. 1A',
     '오른쪽 MLO 영상에서 유방 위쪽 뒤로 겨드랑이를 향해 뻗은 액와 꼬리 부위에 둥근 종괴(빨간 원)가 있습니다(저자: 이소성 유방 조직의 섬유선종).',
     'Diagnostic mammography (MLO C-view) demonstrates the presence of a 2.4 × 1.9 cm round, circumscribed, high-density mass in '
     'the right axillary tail (circled, A).'),
    ('paper_retromammary_fat', ['ana_retromammary_fat', 'ana_fibroglandular_tissue'], 'jabbour2025', 'diagnostics-15-02528-g005.jpg',
     (262, 5, 756, 378), 'Figure 5b,c',
     '왼쪽 유방 MLO(b)와 CC(c) 영상에서 밝은 섬유선 조직 뒤쪽 경계(노란 화살표)와 그 뒤의 어두운 유방후 지방층입니다.',
     'The junction between the fibroglandular tissue and the retromammary fat ... seen on mediolateral oblique (MLO) (b) and '
     'craniocaudal (CC) (c) views of the left breast (yellow arrows).'),
    ('paper_inframammary_fold', ['ana_inframammary_fold', 'ref_posterior_nipple_line', 'ana_pectoralis_major'], 'karic2026',
     'diagnostics-16-01218-g001.jpg', None, 'Figure 1',
     '잘 찍은 오른쪽 MLO 영상입니다. 아래쪽 화살촉이 유방하주름, 점선이 후유두선, 파란 선이 대흉근 앞 경계입니다.',
     'The posterior nipple line (PNL) is indicated by the dotted line. The pectoralis muscle ... (blue line) ... The '
     'inframammary fold (arrow head) must be clearly visualized, without overlapping skin folds or air gaps.'),
    ('paper_cooper_ligaments', ['ana_cooper_ligaments'], 'gharaibeh2023', 'fmed-10-1276434-g002.jpg', None, 'Figure 2',
     '2D 유방촬영(A)에서 비대칭처럼 보인 부위가 DBT 단면(B)에서는 서로 겹친 쿠퍼 인대와 섬유선 조직(화살표)으로 풀립니다.',
     'There is a symmetry that is seen in the right upper breast in the MLO view of 2D mammography (A). (B) DBT image detects '
     'crossing cooper ligaments and fibro-glandular tissue (arrow) with no associated mass or speculation.'),
    ('paper_dilated_duct', ['les_solitary_dilated_duct', 'ana_ducts'], 'pitarch2025', '13244_2025_1947_Fig4_HTML.jpg', (0, 0, 356, 300),
     'Fig. 4a', '내하사분면에 관 모양 음영(화살촉)으로 보이는 확장된 유관입니다(저자: 유관 확장을 동반한 관내 유두종, 장액성 유두 분비).',
     'Intraductal papilloma with duct dilatation. ... a Mammogram showing tubular structures in the lower inner quadrant (arrowheads).'),
    ('paper_trabecular_thickening', ['les_trabecular_thickening', 'les_skin_thickening'], 'almohawes2023', 'bjrcr.20220160.g001.jpg', None,
     'Figure 1', '오른쪽 유방(a MLO · c CC)은 피하 지방 사이 섬유 격벽이 굵어져 그물 모양이 짙고(소주 비후) 피부도 두껍습니다(부종). 왼쪽(b · d)은 비교용 반대쪽입니다.',
     'Digital mammography of the right breast, (a) CC and (c) MLO views, shows diffuse subcutaneous fat infiltration associated with '
     'increased trabeculation and dermal thickening are consistent with oedema ... Left breast (b, d) ...'),
    ('paper_skin_lesion', ['les_skin_lesion'], 'park2026', 'PMC12934220/gr2.jpg', None, 'Fig. 2',
     '만져지는 곳에 피부 표지자(작은 둥근 금속, BB)를 붙이고 찍은 접선 MLO 영상입니다. 피부와 이어진 작은 표재성 종괴들(화살표)이 피부 병변임을 보여 줍니다.',
     'Diagnostic left tangential MLO mammogram obtained after placement of a BB skin marker at the area of palpable lump in the low '
     'axilla demonstrates several small superficial masses in continuity with the skin.'),
    ('paper_tdlu_histology', ['ana_tdlu'], 'debel2022', '41523_2021_378_Fig1_HTML.jpg', (0, 0, 330, 652), 'Fig. 1a,c',
     '말단 유관 소엽 단위는 유방촬영에서 따로 보이지 않아 조직(H&E) 사진으로 보입니다. 위(a)는 소엽 하나, 아래(c)는 간질 속에 흩어진 여러 소엽입니다(막대 200·400 µm).',
     'The top view (a, b) shows a single TDLU ... The bottom view gives a broad overview (c, d).'),
    ('paper_milk_of_calcium', ['les_calc_milk_of_calcium'], 'nalawade2009', 'IJRI-19-282-g005.jpg', None, 'Figure 5',
     '옆(측면) 영상입니다. 작은 낭종 안에 가라앉은 칼슘이 아래쪽에 반달·찻잔 모양으로 층을 이룹니다(화살표). 위쪽의 흐린 둥근 점들도 같은 석회화를 다른 각도에서 본 것입니다.',
     'Lateral mammogram shows milk of calcium with layering (arrow).'),
    ('paper_skin_calc', ['les_calc_skin'], 'nalawade2009', 'IJRI-19-282-g006.jpg', (0, 0, 364, 335), 'Figure 6A',
     '가운데가 투명한 작은 고리 모양 석회화(화살표)로, 피부 석회화의 전형적인 모습입니다.',
     'Mammogram (A) shows a lucent-centered focus (arrow) of dermal calcification.'),
]


def paper_panel(fid, items, source_id, name, box, label, caption, original):
    rgb = Image.open(PROVIDER_DIR / name).convert('RGB')
    crop = rgb.crop(box) if box else rgb
    if crop.width < 460:
        k = 460 / crop.width
        crop = crop.resize((460, round(crop.height * k)), Image.LANCZOS)
    src = source(source_id, label)
    save_jpg(crop, registry.MASKED_DIR, f'{fid}.jpg')
    ov = overlay(crop.size, texts=[((10, 10), '논문 그림 · 저자 표시', 'white')])
    return {'id': fid, 'kind': 'paper', 'items': items, 'source': source_id, 'source_file': name, 'panel': label,
            'mask_label': '논문 그림 · 저자 판정', 'legend': [], 'caption': caption + ' 화살표·원·선은 원 저자의 표시입니다.',
            'original_caption': original,
            'transform': (f'패널 {label} 잘라냄 (x {box[0]}–{box[2]}, y {box[1]}–{box[3]})' if box else f'원 그림 전체 {label}')
                         + f', {crop.size[0]}×{crop.size[1]}',
            'base': f'{fid}.jpg', 'overlay': save_png(ov, registry.MASKED_DIR, f'{fid}_mask.png'),
            'width': crop.size[0], 'height': crop.size[1], 'name': src['name'], 'credit': src['credit'], 'url': src['url'],
            'license': src['license'], 'license_url': src['license_url']}


def build():
    provider()
    examples, figures = [], []
    for fn in (dbt_mass, dbt_distortion, dbt_calcifications):
        ex, fig = fn()
        examples.append(ex)
        figures.append(fig)
    for args in (
        ('ex_cem_mass', '330_2026_12660_Fig5_HTML.webp', (8, 8, 246, 384), 2.0, 'Fig. 5a', '증강 종괴', '뚜렷하게 증강되는 종괴',
         'CEM 재조합 MLO 영상에서 뚜렷하게 증강되는 종괴입니다(저자: 침윤성 유방암, 저에너지 영상에도 대응 소견).', '높음', None, None,
         ['les_enhancing_mass'], 'enhancing_mass_cem', '증강 종괴(서비스 추정 범위)'),
        ('ex_cem_rim', '330_2026_12660_Fig6_HTML.webp', (218, 6, 418, 470), 2.0, 'Fig. 6b', '테두리 증강', '테두리가 증강되는 종괴',
         'CEM 재조합 영상에서 테두리가 증강되는 종괴입니다(저자: 종괴 절제 부위의 지방괴사, MRI에서 가운데 지방 확인).', '높음', '테두리 증강', None,
         ['les_enhancing_mass'], None, ''),
        ('ex_cem_nme', '330_2026_12660_Fig4_HTML.webp', (5, 6, 276, 470), 2.0, 'Fig. 4a', '비종괴 증강', '국소 비종괴 증강',
         'CEM 재조합 CC 영상의 국소 비종괴 증강입니다(저자: 중간 뚜렷함, 침윤성 유방암, 저에너지 영상에는 대응 소견 없음).', '중간', None, '국소(focal)',
         ['les_non_mass_enhancement'], 'nme_cem', '비종괴 증강(서비스 추정 범위)'),
    ):
        ex, fig = cem_lesion(*args[:10], nme=args[10], items=args[11], fig_id=args[12], mask_label=args[13])
        examples.append(ex)
        if fig:
            figures.append(fig)
    ex, fig = cem_bpe()
    examples.append(ex)
    figures.append(fig)
    figures.append(modality_figure())
    figures += [paper_panel(*p) for p in PAPER_PANELS]
    return examples, figures
