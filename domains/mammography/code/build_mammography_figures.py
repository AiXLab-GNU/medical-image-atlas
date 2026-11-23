"""Build the mammography atlas images from DMID (CC BY 4.0): item-page masked figures and measurement examples.

Masked figures pair a crop of the original image with a transparent overlay of the DMID expert ROI
(lesions) or of the service's automatic landmarks (anatomy, marked as service estimates in the caption).
Measurement examples run mammography-measures functions on the full-resolution image and save one
transparent layer per switch. Outputs:

  resources/datasets/mammography_atlas_masked_figures/*      + web data/masked_figures.json
  resources/datasets/mammography_atlas_measurement_examples/* + web data/measurement_examples.json

    .venv/bin/python -B domains/mammography/code/build_mammography_figures.py
"""
from __future__ import annotations

import json
import math
import sys
import warnings

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

import mammography_atlas_registry as registry

sys.path.insert(0, str(registry.MEASURES_SRC))
from mammography_measures import breast, calcification, distortion, location, mass  # noqa: E402

warnings.filterwarnings('ignore', category=FutureWarning)
Image.MAX_IMAGE_PIXELS = None
SOURCE = registry.source_record('dmid')
TONES = {'blue': (56, 189, 248), 'yellow': (255, 211, 77), 'green': (74, 222, 128), 'red': (248, 113, 113),
         'magenta': (232, 121, 249), 'white': (255, 255, 255), 'orange': (251, 146, 60), 'cyan': (34, 211, 238)}
PAIR = ('IMG015', 'IMG014')      # CC and MLO of the right breast (consecutive DMID numbers; same breast assumed)
PAIR_NOTE = ('DMID는 환자 번호를 주지 않아 연속 번호의 같은 쪽 CC·MLO(IMG015·IMG014)를 같은 유방으로 가정했습니다. '
             '같은 침상형 종괴(악성)가 두 영상에 표시되어 있습니다.')
VIEW_NOTE = 'CC는 표준 표시 방향(바깥쪽이 위)을 가정했습니다.'
PX_NOTE = 'DMID 영상에는 화소 간격 정보가 없어 길이·면적은 화소 단위입니다.'


# ----------------------------------------------------------------------------------------- inputs

def load(image_id):
    paths = registry.dmid_paths(image_id)
    img = np.asarray(Image.open(paths['image']).convert('L'), dtype=np.float32) / 255.0
    roi = np.asarray(Image.open(paths['roi']).convert('L')) > 127 if paths['roi'].is_file() else None
    return img, roi


def finding(image_id, cls, nth=0):
    rows = [f for f in registry.dmid_findings() if f['image'] == image_id and cls in f['classes']]
    return rows[nth]


def finding_mask(roi, f):
    """ROI components belonging to one DMID finding (centre within ~1.5 radius; y flipped if needed)."""
    labels, n = ndi.label(roi)
    if n == 0:
        raise ValueError(f"{f['image']}: empty ROI")
    cents = ndi.center_of_mass(roi, labels, range(1, n + 1))
    r = f['r'] if f['r'] and not math.isnan(f['r']) else 300.0
    for y in (f['y'], roi.shape[0] - f['y']):
        keep = [i + 1 for i, (cy, cx) in enumerate(cents) if math.hypot(cy - y, cx - f['x']) < max(1.5 * r, 200)]
        if keep:
            return np.isin(labels, keep)
    raise ValueError(f"{f['image']}: no ROI component near the listed centre")


# ----------------------------------------------------------------------------------------- drawing

def to_rgb(gray):
    g = (np.clip(gray, 0, 1) * 255).astype(np.uint8)
    return Image.merge('RGB', [Image.fromarray(g)] * 3)


def resize_mask(mask, size):
    return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize(size, Image.NEAREST)) > 127


def overlay(size, fills=(), outlines=(), lines=(), points=(), dots=(), texts=(), dashed=()):
    """Transparent RGBA layer. fills/outlines: (mask, tone, alpha); lines: (p0, p1, tone, width) as (x, y)."""
    w, h = size
    canvas = np.zeros((h, w, 4), np.uint8)
    for mask, tone, alpha in fills:
        canvas[mask] = (*TONES[tone], alpha)
    for mask, tone, width in outlines:
        edge = mask & ~ndi.binary_erosion(mask, iterations=width)
        canvas[edge] = (*TONES[tone], 255)
    im = Image.fromarray(canvas, 'RGBA')
    draw = ImageDraw.Draw(im)
    for p0, p1, tone, width in lines:
        draw.line([p0, p1], fill=(*TONES[tone], 255), width=width)
    for p0, p1, tone, width in dashed:
        n = max(int(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / 12), 1)
        for k in range(0, n, 2):
            a = (p0[0] + (p1[0] - p0[0]) * k / n, p0[1] + (p1[1] - p0[1]) * k / n)
            b = (p0[0] + (p1[0] - p0[0]) * (k + 1) / n, p0[1] + (p1[1] - p0[1]) * (k + 1) / n)
            draw.line([a, b], fill=(*TONES[tone], 255), width=width)
    for (x, y), tone, r in points:
        draw.ellipse([x - r, y - r, x + r, y + r], outline=(*TONES[tone], 255), width=2)
    for (x, y), tone, r in dots:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(*TONES[tone], 255))
    for (x, y), text, tone in texts:
        font = _font(15)
        box = draw.textbbox((x, y), text, font=font)
        draw.rectangle([box[0] - 4, box[1] - 3, box[2] + 4, box[3] + 3], fill=(15, 23, 42, 210))
        draw.text((x, y), text, fill=(*TONES[tone], 255), font=font)
    return im


def _font(size):
    for name in ('NotoSansCJK-Regular.ttc', 'NanumGothic.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def save_png(im, directory, name):
    im.save(directory / name, optimize=True)
    return name


def save_jpg(im, directory, name):
    im.save(directory / name, quality=88, optimize=True)
    return name


def crop_box(mask, shape, margin=0.7, min_side=420):
    rows, cols = np.nonzero(mask)
    r0, r1, c0, c1 = rows.min(), rows.max(), cols.min(), cols.max()
    side = max(r1 - r0, c1 - c0)
    pad = max(int(side * margin), (min_side - side) // 2, 60)
    cy, cx = (r0 + r1) // 2, (c0 + c1) // 2
    half = side // 2 + pad
    r0, r1 = max(cy - half, 0), min(cy + half, shape[0])
    c0, c1 = max(cx - half, 0), min(cx + half, shape[1])
    return r0, r1, c0, c1


def fmt(value, unit):
    if value is None:
        return '—'
    if isinstance(value, bool):
        return '있음' if value else '없음'
    unit_txt = {'px': 'px', 'px2': 'px²', 'mm': 'mm', 'mm2': 'mm²', '%': '%', '%p': '%p', 'deg': '°',
                'count': '개', 'index': '', 'ratio': '', 'category': '', 'presence': ''}.get(unit, unit)
    if isinstance(value, float):
        text = f'{value:,.0f}' if abs(value) >= 1000 else (f'{value:,.1f}' if abs(value) >= 10 else f'{value:.3g}')
    else:
        text = f'{value:,}' if isinstance(value, int) else str(value)
    return f'{text} {unit_txt}'.strip()


CATEGORY_KO = {'anterior': '앞 1/3', 'middle': '가운데 1/3', 'posterior': '뒤 1/3', 'lateral': '바깥쪽',
               'medial': '안쪽', 'upper': '위쪽', 'lower': '아래쪽', 'UOQ': '외상사분면', 'UIQ': '내상사분면',
               'LOQ': '외하사분면', 'LIQ': '내하사분면'}


def val(m, extra=''):
    status = m.status
    value = CATEGORY_KO.get(m.value, m.value) if isinstance(m.value, str) else m.value
    text = fmt(value, m.unit) if status == 'ok' else {'not_observed': '관찰 안 됨', 'not_evaluable': '계산 불가'}[status]
    return {'id': m.feature_id, 'value': text + (f' · {extra}' if extra else ''), 'status': status}


def reading(feature_id, text):
    return {'id': feature_id, 'value': text, 'status': 'reading'}


# ----------------------------------------------------------------------------------------- whole views

class View:
    """Full-resolution view with automatic landmarks and a display copy of fixed height."""

    def __init__(self, image_id, height=900):
        self.id = image_id
        self.meta = next(f for f in registry.dmid_findings() if f['image'] == image_id)
        self.img, self.roi = load(image_id)
        self.geo = breast.geometry(self.img, self.meta['view'])
        self.dense = breast.dense_tissue(self.img, self.geo.breast)
        full = self.geo.breast | (self.geo.pectoral if self.geo.pectoral is not None else False)
        rows, cols = np.nonzero(full)
        pad = int(0.03 * max(self.img.shape))
        self.win = (max(rows.min() - pad, 0), min(rows.max() + pad, self.img.shape[0]),
                    max(cols.min() - pad, 0), min(cols.max() + pad, self.img.shape[1]))
        r0, r1, c0, c1 = self.win
        self.s = height / (r1 - r0)
        self.size = (int(round((c1 - c0) * self.s)), height)
        crop = (self.img[r0:r1, c0:c1] * 255).astype(np.uint8)
        self.base = to_rgb(np.asarray(Image.fromarray(crop).resize(self.size, Image.LANCZOS)) / 255.0)

    def p(self, rc):
        return ((rc[1] - self.win[2]) * self.s, (rc[0] - self.win[0]) * self.s)

    def m(self, mask):
        r0, r1, c0, c1 = self.win
        return resize_mask(mask[r0:r1, c0:c1], self.size)


def thirds(view):
    """Display masks of the anterior/middle/posterior thirds along the posterior nipple line."""
    g = view.geo
    h, w = view.size[1], view.size[0]
    yy, xx = np.mgrid[0:h, 0:w]
    nip = np.array(view.p(g.nipple))
    foot = np.array(view.p(g.pnl_foot))
    axis = foot - nip
    t = ((xx - nip[0]) * axis[0] + (yy - nip[1]) * axis[1]) / max(axis @ axis, 1e-9)
    br = view.m(g.breast)
    return [(br & (t >= a) & (t < b)) for a, b in ((-1, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 9))]


def halves(view):
    g = view.geo
    h, w = view.size[1], view.size[0]
    yy, xx = np.mgrid[0:h, 0:w]
    nip = np.array(view.p(g.nipple))
    foot = np.array(view.p(g.pnl_foot))
    axis = foot - nip
    t = ((xx - nip[0]) * axis[0] + (yy - nip[1]) * axis[1]) / max(axis @ axis, 1e-9)
    line_y = nip[1] + t * axis[1]
    br = view.m(g.breast)
    return br & (yy < line_y), br & (yy >= line_y)


# ----------------------------------------------------------------------------------------- masked figures

def lesion_figure(fid, image_id, cls, nth, items, label, caption, tone='red', legend=None, judged=''):
    img, roi = load(image_id)
    f = finding(image_id, cls, nth)
    mask = finding_mask(roi, f)
    r0, r1, c0, c1 = crop_box(mask, img.shape)
    crop, cmask = img[r0:r1, c0:c1], mask[r0:r1, c0:c1]
    scale = min(760 / crop.shape[1], 760 / crop.shape[0], 2.5)
    size = (int(crop.shape[1] * scale), int(crop.shape[0] * scale))
    base = to_rgb(np.asarray(Image.fromarray((crop * 255).astype(np.uint8)).resize(size, Image.LANCZOS)) / 255.0)
    m = resize_mask(cmask, size)
    ov = overlay(size, fills=[(m, tone, 60)], outlines=[(m, tone, 3)])
    ctx_s = 240 / img.shape[0]
    ctx = to_rgb(np.asarray(Image.fromarray((img * 255).astype(np.uint8)).resize(
        (int(img.shape[1] * ctx_s), 240), Image.LANCZOS)) / 255.0)
    ImageDraw.Draw(ctx).rectangle([c0 * ctx_s, r0 * ctx_s, c1 * ctx_s, r1 * ctx_s], outline=(255, 211, 77), width=2)
    out = registry.MASKED_DIR
    sev = {'B': '양성', 'M': '악성', 'N': '양성·악성 미정'}.get(f['severity'], '')
    return {
        'id': fid, 'items': items, 'source': 'dmid', 'source_file': f'TIFF Images/{image_id}.tif',
        'mask_label': label, 'legend': legend or [],
        'caption': f"{caption} DMID {image_id} · {f['view']} {'오른쪽' if f['laterality'] == 'R' else '왼쪽'} · "
                   f"공급자 분류 {'+'.join(f['classes'])}{' · ' + sev if sev else ''}.{(' ' + judged) if judged else ''}",
        'transform': f'원본 {img.shape[1]}×{img.shape[0]}에서 ({c0},{r0})–({c1},{r1})을 잘라 {size[0]}×{size[1]}로 변환; '
                     f'공급자 ROI mask를 같은 비율로 겹침',
        'base': save_jpg(base, out, f'{fid}.jpg'), 'overlay': save_png(ov, out, f'{fid}_mask.png'),
        'context': save_jpg(ctx, out, f'{fid}_context.jpg'), 'width': size[0], 'height': size[1],
        'name': SOURCE['name'], 'credit': SOURCE['credit'], 'url': SOURCE['url'], 'license': SOURCE['license'],
        'license_url': SOURCE['license_url'],
    }


def anatomy_figure(fid, view, items, label, caption, fills=(), outlines=(), lines=(), points=(), legend=None):
    out = registry.MASKED_DIR
    ov = overlay(view.size, fills=fills, outlines=outlines, lines=lines, points=points)
    base_name = f'view_{view.id.lower()}.jpg'
    if not (out / base_name).is_file():
        save_jpg(view.base, out, base_name)
    m = view.meta
    return {
        'id': fid, 'items': items, 'source': 'dmid', 'source_file': f'TIFF Images/{view.id}.tif',
        'mask_label': label, 'legend': legend or [],
        'caption': f"{caption} DMID {view.id} · {m['view']} {'오른쪽' if m['laterality'] == 'R' else '왼쪽'}. "
                   '표시는 서비스의 자동 경계 추정입니다(전문가 분할 아님).',
        'transform': f"원본 {view.img.shape[1]}×{view.img.shape[0]}에서 유방 범위 ({view.win[2]},{view.win[0]})–({view.win[3]},{view.win[1]})을 잘라 높이 {view.size[1]} px로 축소; 자동 경계를 같은 비율로 겹침",
        'base': base_name, 'overlay': save_png(ov, out, f'{fid}_mask.png'), 'width': view.size[0],
        'height': view.size[1], 'name': SOURCE['name'], 'credit': SOURCE['credit'], 'url': SOURCE['url'],
        'license': SOURCE['license'], 'license_url': SOURCE['license_url'],
    }


def pair_figure(fid, cc, mlo, items, label, caption, pick):
    """CC and MLO side by side; ``pick(view) -> mask`` chooses the highlighted display region per view."""
    out = registry.MASKED_DIR
    gap = 16
    w = cc.size[0] + gap + mlo.size[0]
    h = max(cc.size[1], mlo.size[1])
    base_name = f'pair_{cc.id.lower()}_{mlo.id.lower()}.jpg'
    if not (out / base_name).is_file():
        canvas = Image.new('RGB', (w, h), (15, 23, 42))
        canvas.paste(cc.base, (0, 0))
        canvas.paste(mlo.base, (cc.size[0] + gap, 0))
        d = ImageDraw.Draw(canvas)
        d.text((10, 8), 'CC', fill=(255, 255, 255), font=_font(20))
        d.text((cc.size[0] + gap + 10, 8), 'MLO', fill=(255, 255, 255), font=_font(20))
        save_jpg(canvas, out, base_name)
    full = np.zeros((h, w), bool)
    full[: cc.size[1], : cc.size[0]] = pick(cc)
    full[: mlo.size[1], cc.size[0] + gap:] = pick(mlo)
    ov = overlay((w, h), fills=[(full, 'cyan', 80)], outlines=[(full, 'cyan', 2)])
    return {
        'id': fid, 'items': items, 'source': 'dmid', 'source_file': f'TIFF Images/{cc.id}.tif; {mlo.id}.tif',
        'mask_label': label, 'legend': [],
        'caption': f'{caption} {PAIR_NOTE} {VIEW_NOTE} 구역은 서비스의 자동 추정입니다.',
        'transform': f'두 영상의 유방 범위를 잘라 높이 {h} px로 축소해 나란히 붙임; 유두·후유두선 기준 구역을 겹침',
        'base': base_name, 'overlay': save_png(ov, out, f'{fid}_mask.png'), 'width': w, 'height': h,
        'name': SOURCE['name'], 'credit': SOURCE['credit'], 'url': SOURCE['url'], 'license': SOURCE['license'],
        'license_url': SOURCE['license_url'],
    }


def masked_figures(cc, mlo):
    figs = [
        lesion_figure('mass_circumscribed_1', 'IMG008', 'CIRC', 0, ['les_mass_circumscribed', 'les_mass'],
                      '경계가 분명한 종괴(전문가 ROI)', '경계 대부분이 매끈하게 구분되는 타원형 종괴입니다.'),
        lesion_figure('mass_circumscribed_2', 'IMG032', 'CIRC', 0, ['les_mass_circumscribed'],
                      '경계가 분명한 종괴(전문가 ROI)', '실질 안의 타원형 종괴입니다.'),
        lesion_figure('mass_spiculated_1', 'IMG063', 'SPIC', 0, ['les_mass_spiculated', 'les_mass'],
                      '침상형 종괴(전문가 ROI)', '중심 덩어리에서 가는 선이 사방으로 뻗습니다.'),
        lesion_figure('mass_spiculated_2', 'IMG015', 'SPIC', 0, ['les_mass_spiculated'],
                      '침상형 종괴(전문가 ROI)', '경계가 불규칙하고 침상선이 길게 뻗은 종괴입니다.'),
        lesion_figure('mass_indistinct_1', 'IMG104', 'MISC', 0, ['les_mass_indistinct', 'les_mass'],
                      '경계가 불분명한 종괴(전문가 ROI)', '경계 일부가 주변 실질과 섞여 구분이 어렵습니다.'),
        lesion_figure('mass_indistinct_2', 'IMG255', 'MISC', 0, ['les_mass_indistinct'],
                      '경계가 불분명한 종괴(전문가 ROI)', '치밀한 실질 안에서 경계가 흐린 종괴입니다.'),
        lesion_figure('calc_cluster_1', 'IMG029', 'CALC', 2, ['les_calcification'],
                      '석회화 범위(전문가 ROI)', '작은 석회화 여러 개가 모인 범위입니다.', tone='yellow'),
        lesion_figure('calc_rodlike_1', 'IMG024', 'CALC', 0, ['les_calc_large_rodlike', 'les_calcification'],
                      '석회화 범위(전문가 ROI)', '유관을 따라 유두 쪽으로 뻗은 굵고 매끈한 막대 모양 석회화입니다.',
                      tone='yellow', judged='형태(큰 막대 모양)는 서비스 판독이며 공급자 분류는 석회화(양성)입니다.'),
        lesion_figure('calc_popcorn_1', 'IMG092', 'CALC', 0, ['les_calc_coarse_popcorn'],
                      '석회화 범위(전문가 ROI)', '덩어리 모양의 거친 석회화입니다.', tone='yellow',
                      judged='형태(거친 팝콘 모양)는 서비스 판독이며 공급자 분류는 석회화(양성)입니다.'),
        lesion_figure('calc_rim_1', 'IMG029', 'CALC', 1, ['les_calc_rim', 'les_fat_containing_mass'],
                      '석회화 범위(전문가 ROI)', '안이 지방처럼 어둡고 테두리를 따라 석회화된 둥근 병변(기름 낭종 모양)입니다.',
                      tone='yellow', judged='형태(테두리 석회화·기름 낭종)는 서비스 판독이며 공급자 분류는 석회화(양성)입니다.'),
        lesion_figure('distortion_1', 'IMG024', 'ARCH', 0, ['les_architectural_distortion'],
                      '구조왜곡이 동반된 침상형 병변(전문가 ROI)', '실질이 한 점으로 당겨지며 침상선이 모입니다.',
                      tone='magenta'),
    ]
    g, s = mlo.geo, mlo
    br = s.m(g.breast)
    figs += [
        anatomy_figure('anat_breast_mlo', mlo, ['ana_breast'], '유방 조직(자동 경계)', 'MLO 영상의 유방 조직 범위입니다(대흉근 제외).',
                       fills=[(br, 'blue', 50)], outlines=[(br, 'blue', 2)]),
        anatomy_figure('anat_pectoralis', mlo, ['ana_pectoralis_major', 'ref_pectoral_edge'], '대흉근과 앞 경계선(자동 추정)',
                       'MLO 위쪽 뒤의 대흉근 삼각형과 그 앞 경계선입니다.',
                       fills=[(s.m(g.pectoral), 'cyan', 70)] if g.pectoral is not None else [],
                       lines=[(s.p(g.pectoral_line[0]), s.p(g.pectoral_line[1]), 'cyan', 3)] if g.pectoral_line else []),
        anatomy_figure('anat_dense_mlo', mlo, ['ana_fibroglandular_tissue'], '치밀(섬유선) 조직(자동 경계값)',
                       '지방보다 밝은 섬유선 조직을 표시했습니다.', fills=[(s.m(s.dense), 'yellow', 90)]),
        anatomy_figure('anat_dense_cc', cc, ['ana_fibroglandular_tissue', 'ana_breast'], '치밀(섬유선) 조직(자동 경계값)',
                       'CC 영상에서 섬유선 조직이 유두 뒤에 원뿔 모양으로 모여 있습니다.',
                       fills=[(cc.m(cc.dense), 'yellow', 90)], outlines=[(cc.m(cc.geo.breast), 'blue', 2)]),
        anatomy_figure('anat_pnl_mlo', mlo, ['ref_posterior_nipple_line', 'ref_nipple'], '유두와 후유두선(자동 추정)',
                       '유두에서 대흉근 앞 경계에 수직으로 그은 후유두선입니다.',
                       lines=[(s.p(g.nipple), s.p(g.pnl_foot), 'green', 3)] +
                             ([(s.p(g.pectoral_line[0]), s.p(g.pectoral_line[1]), 'cyan', 2)] if g.pectoral_line else []),
                       points=[(s.p(g.nipple), 'magenta', 12)]),
        anatomy_figure('anat_nipple_cc', cc, ['ana_nipple_areola', 'ref_nipple', 'ref_posterior_nipple_line'],
                       '유두 기준점과 후유두선(자동 추정)', 'CC 영상의 유두 기준점과 영상 뒤 끝까지의 후유두선입니다.',
                       lines=[(cc.p(cc.geo.nipple), cc.p(cc.geo.pnl_foot), 'green', 3)],
                       points=[(cc.p(cc.geo.nipple), 'magenta', 14)]),
    ]
    edge = cc.m(cc.geo.breast)
    skin = edge & ~ndi.binary_erosion(edge, iterations=4)
    sub = edge & ~ndi.binary_erosion(edge, iterations=40) & ~skin & ~cc.m(cc.dense)
    figs.append(anatomy_figure('anat_skin_fat_cc', cc, ['ana_skin', 'ana_subcutaneous_fat'], '피부 띠와 피하 지방(자동 추정)',
                               '유방 윤곽을 따라가는 피부 띠(분홍)와 그 안쪽 지방층(파랑)입니다.',
                               fills=[(sub, 'blue', 70), (skin, 'magenta', 220)],
                               legend=[{'cls': 'skin', 'label': '피부'}, {'cls': 'fat', 'label': '피하 지방'}]))
    t3 = thirds(cc)
    figs.append(anatomy_figure('zone_depth_cc', cc, ['zone_depth_thirds'], '깊이 3구역(자동 추정)',
                               '후유두선을 셋으로 나눈 앞(초록)·가운데(노랑)·뒤(주황) 깊이입니다.',
                               fills=[(t3[0], 'green', 70), (t3[1], 'yellow', 70), (t3[2], 'orange', 70)],
                               lines=[(cc.p(cc.geo.nipple), cc.p(cc.geo.pnl_foot), 'white', 2)],
                               legend=[{'cls': 'front', 'label': '앞 1/3'}, {'cls': 'mid', 'label': '가운데 1/3'},
                                       {'cls': 'back', 'label': '뒤 1/3'}]))
    up_cc, low_cc = halves(cc)
    up_mlo, low_mlo = halves(mlo)
    figs.append(pair_figure('zone_quadrant_halves', cc, mlo, ['zone_quadrants'], '사분면을 정하는 두 절반',
                            'CC에서는 유두선 위쪽(바깥쪽), MLO에서는 유두선 위쪽을 표시했습니다. 두 절반이 겹치는 곳이 외상사분면입니다.',
                            lambda v: halves(v)[0]))
    quads = {'ana_upper_outer_quadrant': ('외상사분면', 0, 0), 'ana_upper_inner_quadrant': ('내상사분면', 1, 0),
             'ana_lower_outer_quadrant': ('외하사분면', 0, 1), 'ana_lower_inner_quadrant': ('내하사분면', 1, 1)}
    for item, (name, cc_half, mlo_half) in quads.items():
        figs.append(pair_figure(f'zone_{item[4:]}', cc, mlo, [item], f'{name}(두 영상의 절반)',
                                f"{name}은 CC의 {'바깥쪽(위)' if cc_half == 0 else '안쪽(아래)'} 절반과 MLO의 "
                                f"{'위쪽' if mlo_half == 0 else '아래쪽'} 절반이 겹치는 곳입니다.",
                                lambda v, a=cc_half, b=mlo_half: halves(v)[a if v.meta['view'] == 'CC' else b]))

    def subareolar(v):
        h, w = v.size[1], v.size[0]
        yy, xx = np.mgrid[0:h, 0:w]
        nx, ny = v.p(v.geo.nipple)
        rad = 0.18 * math.hypot(*(np.array(v.p(v.geo.pnl_foot)) - np.array((nx, ny))))
        return v.m(v.geo.breast) & (np.hypot(xx - nx, yy - ny) < rad)
    figs.append(pair_figure('zone_subareolar', cc, mlo, ['ana_subareolar_region'], '유륜하 영역(자동 추정)',
                            '유두 바로 뒤 영역입니다(후유두선 길이의 약 1/5 반경).', subareolar))
    return figs


# ----------------------------------------------------------------------------------------- examples

def layer(ex, key, label, tone, function, how, features, im):
    name = f"{ex['id']}_{key}.png"
    im.save(registry.EXAMPLE_DIR / name, optimize=True)
    return {'key': key, 'label': label, 'tone': tone, 'function': function, 'how': how, 'features': features,
            'file': name}


def example_head(eid, region, title, caption, image_ids, base_im, builder):
    base = f'{eid}.jpg'
    base_im.save(registry.EXAMPLE_DIR / base, quality=88, optimize=True)
    return {'id': eid, 'modality': 'ffdm', 'modality_label': '2D 유방촬영', 'region': region,
            'title': f'2D 유방촬영 · {title}', 'source': 'dmid',
            'source_file': '; '.join(f'TIFF Images/{i}.tif' for i in image_ids), 'caption': caption,
            'builder': builder, 'base': base, 'width': base_im.size[0], 'height': base_im.size[1], 'layers': [],
            'credit': SOURCE['credit'], 'url': SOURCE['url'], 'license': SOURCE['license'],
            'license_url': SOURCE['license_url']}


def whole_view_example(v, eid, lesion_cls):
    g = v.geo
    comp = registry.dmid_composition(v.id)
    ex = example_head(eid, f"{v.meta['view']} 전체", f"{v.meta['view']} 전체 영상",
                      f"오른쪽 유방 {v.meta['view']} 영상입니다. 유방 경계·{'대흉근·' if g.pectoral is not None else ''}유두를 자동으로 찾고 "
                      f"mammography-measures 함수를 실행했습니다. 병변 위치는 공급자 ROI를 씁니다. {PX_NOTE}"
                      + (f' {VIEW_NOTE}' if v.meta['view'] == 'CC' else ''), [v.id], v.base, 'whole_view_example')
    br = v.m(g.breast)
    L = ex['layers']
    L.append(layer(ex, 'breast', '유방 경계·면적', 'blue', 'breast.breast_area',
                   'Otsu 경계값으로 배경과 유방을 가르고 가장 큰 덩어리의 구멍을 채움' + (' · 대흉근 제외' if g.pectoral is not None else ''),
                   [val(breast.breast_area(g))], overlay(v.size, fills=[(br, 'blue', 40)], outlines=[(br, 'blue', 2)])))
    if g.pectoral is not None:
        L.append(layer(ex, 'pectoral', '대흉근 면적·각도', 'cyan', 'breast.pectoral_area',
                       '위쪽 행마다 흉벽 쪽 첫 강한 어두워짐을 찾고 RANSAC 직선으로 앞 경계를 맞춤',
                       [val(breast.pectoral_area(g)), val(breast.pectoral_angle(g))],
                       overlay(v.size, fills=[(v.m(g.pectoral), 'cyan', 70)],
                               lines=[(v.p(g.pectoral_line[0]), v.p(g.pectoral_line[1]), 'cyan', 3)])))
    feats = [val(breast.pnl_length(g))]
    if g.pectoral is not None:
        feats.append(val(breast.pectoral_reaches_pnl(g)))
    L.append(layer(ex, 'pnl', '유두·후유두선', 'green', 'breast.pnl_length',
                   '윤곽의 국소 돌출부를 찾고 원영상의 어두운 유두 끝까지 보정한 뒤 ' + ('대흉근 앞 경계(자동 추정·검토 전)에 수직으로 내린 선' if g.pectoral is not None else '영상 뒤 끝까지 수평선'),
                   feats, overlay(v.size, lines=[(v.p(g.nipple), v.p(g.pnl_foot), 'green', 3)],
                                  points=[(v.p(g.nipple), 'magenta', 12)])))
    L.append(layer(ex, 'dense', '치밀 조직·밀도 백분율', 'yellow', 'breast.percent_density',
                   '피부 가장자리를 뺀 유방 안 밝기의 Otsu 경계값보다 밝은 화소(영상 처리 방식에 따라 달라짐)',
                   [val(breast.dense_area(v.dense)), val(breast.percent_density(v.dense, g.breast))],
                   overlay(v.size, fills=[(v.m(v.dense), 'yellow', 100)])))
    if comp:
        L.append(layer(ex, 'composition', '유방 구성 범주(판독)', 'white', '', '공급자 판독 보고서의 ACR 범주',
                       [reading('ft_breast_composition', f'{comp} (공급자 보고서 ACR {comp.upper()})')],
                       overlay(v.size, texts=[((12, 12), f'ACR {comp.upper()} (보고서)', 'white')],
                               dashed=[])))
    f = finding(v.id, lesion_cls)
    lm = finding_mask(v.roi, f)
    c = location.centroid(lm)
    t3 = thirds(v)
    feats = [val(location.distance_from_nipple(c, g.nipple)), val(location.depth_third(c, g.nipple, g.pnl_foot)),
             val(location.view_half(c, g.nipple, g.pnl_foot, v.meta['view']))]
    L.append(layer(ex, 'location', '병변 위치(유두 기준)', 'red', 'location.distance_from_nipple',
                   '병변 ROI 중심을 후유두선에 투영해 앞·가운데·뒤 1/3과 유두 거리 · 유두선 위아래로 절반 위치',
                   feats, overlay(v.size, fills=[(t3[0], 'green', 30), (t3[1], 'yellow', 30), (t3[2], 'orange', 30),
                                                (v.m(lm), 'red', 120)],
                                  outlines=[(v.m(lm), 'red', 2)],
                                  lines=[(v.p(g.nipple), v.p(c), 'red', 2), (v.p(g.nipple), v.p(g.pnl_foot), 'white', 1)])))
    return ex


def pair_example(cc, mlo):
    gap = 16
    w, h = cc.size[0] + gap + mlo.size[0], max(cc.size[1], mlo.size[1])
    base = Image.new('RGB', (w, h), (15, 23, 42))
    base.paste(cc.base, (0, 0))
    base.paste(mlo.base, (cc.size[0] + gap, 0))
    d = ImageDraw.Draw(base)
    d.text((10, 8), 'CC', fill=(255, 255, 255), font=_font(20))
    d.text((cc.size[0] + gap + 10, 8), 'MLO', fill=(255, 255, 255), font=_font(20))
    ex = example_head('ex_ffdm_pair', 'CC·MLO 짝', 'CC·MLO 두 영상', f'두 방향 영상을 짝지어야 계산되는 측정입니다. {PAIR_NOTE} {VIEW_NOTE} {PX_NOTE}',
                      [cc.id, mlo.id], base, 'pair_example')
    off = cc.size[0] + gap

    def shift(p, dx):
        return (p[0] + dx, p[1])

    masks, halves_, offsets = {}, {}, {}
    for v, dx in ((cc, 0), (mlo, off)):
        lm = finding_mask(v.roi, finding(v.id, 'SPIC'))
        c = location.centroid(lm)
        g = v.geo
        masks[v.meta['view']] = (v, lm, c, dx)
        halves_[v.meta['view']] = location.view_half(c, g.nipple, g.pnl_foot, v.meta['view']).value
        axis = np.array(g.pnl_foot) - np.array(g.nipple)
        perp = np.array([c[0] - g.nipple[0], c[1] - g.nipple[1]], float)
        t = perp @ axis / max(axis @ axis, 1e-9)
        offsets[v.meta['view']] = float(g.nipple[0] + t * axis[0] - c[0])      # + when above the nipple line
    canvas = np.zeros((h, w), bool)
    lines = []
    for view, (v, lm, c, dx) in masks.items():
        dm = v.m(lm)
        canvas[: dm.shape[0], dx: dx + dm.shape[1]] |= dm
        lines.append((shift(v.p(v.geo.nipple), dx), shift(v.p(v.geo.pnl_foot), dx), 'white', 2))
    q = location.quadrant(halves_['CC'], halves_['MLO'])
    clock = location.clock_position(offsets['CC'], offsets['MLO'], 'R')
    L = ex['layers']
    L.append(layer(ex, 'match', '두 방향에서 보임', 'red', '', '두 영상의 공급자 ROI가 같은 병변을 표시함(짝짓기는 가정)',
                   [reading('ft_lesion_two_view', '있음 (CC·MLO 모두 표시)')],
                   overlay((w, h), fills=[(canvas, 'red', 110)], outlines=[(canvas, 'red', 2)])))
    L.append(layer(ex, 'quadrant', '사분면·시계 방향', 'cyan', 'location.quadrant',
                   'CC의 위·아래(바깥·안) 절반과 MLO의 위·아래 절반을 합치고, 유두선에서 벗어난 거리로 시계 방향을 계산',
                   [val(q), val(clock)], overlay((w, h), fills=[(canvas, 'red', 60)], lines=lines,
                                                 texts=[((12, h - 34), f"{CATEGORY_KO.get(q.value, q.value)} · {clock.value}", 'cyan')])))
    diff = breast.pnl_cc_mlo_difference(cc.geo, mlo.geo)
    L.append(layer(ex, 'pnl', 'CC·MLO 후유두선 길이 차이', 'green', 'breast.pnl_cc_mlo_difference',
                   '두 영상의 후유두선 길이 차이(1 cm 이내면 CC가 뒤쪽까지 충분히 포함). 화소 간격이 없어 두 영상 배율이 같다고 가정',
                   [val(diff)], overlay((w, h), lines=[(shift(cc.p(cc.geo.nipple), 0), shift(cc.p(cc.geo.pnl_foot), 0), 'green', 3),
                                                       (shift(mlo.p(mlo.geo.nipple), off), shift(mlo.p(mlo.geo.pnl_foot), off), 'green', 3)])))
    return ex


def crop_view(image_id, cls, nth=0, margin=0.7, max_side=760):
    img, roi = load(image_id)
    f = finding(image_id, cls, nth)
    mask = finding_mask(roi, f)
    r0, r1, c0, c1 = crop_box(mask, img.shape, margin=margin)
    crop, cmask = img[r0:r1, c0:c1], mask[r0:r1, c0:c1]
    s = min(max_side / crop.shape[1], max_side / crop.shape[0], 2.5)
    size = (int(crop.shape[1] * s), int(crop.shape[0] * s))
    base = to_rgb(np.asarray(Image.fromarray((crop * 255).astype(np.uint8)).resize(size, Image.LANCZOS)) / 255.0)
    return f, crop, cmask, s, size, base


def mass_example(eid, image_id, cls, region, title, margin_text, nth=0):
    f, crop, cm, s, size, base = crop_view(image_id, cls, nth)
    sev = {'B': '양성', 'M': '악성', 'N': '미정'}.get(f['severity'], '')
    ex = example_head(eid, region, title,
                      f"DMID {image_id}({f['view']} · 공급자 분류 {'+'.join(f['classes'])} · {sev})의 종괴 부위입니다. "
                      f'공급자 전문가 ROI를 종괴 경계로 써서 mammography-measures 함수를 실행했습니다. {PX_NOTE}',
                      [image_id], base, 'mass_example')
    m = resize_mask(cm, size)
    L = ex['layers']
    L.append(layer(ex, 'outline', '종괴 경계·크기', 'red', 'mass.size', '전문가 ROI의 최대 지름(Feret)과 화소 면적',
                   [val(mass.size(cm)), val(mass.mass_area(cm)), val(distortion.presence(cm))],
                   overlay(size, outlines=[(m, 'red', 3)])))
    from skimage.morphology import convex_hull_image
    hull = resize_mask(convex_hull_image(cm), size)
    rs = mass.radial_sd(cm)
    L.append(layer(ex, 'shape', '모양(원형도·볼록도·반지름 변동)', 'orange', 'mass.circularity',
                   '4π·면적/둘레², 면적/볼록 껍질 면적, 중심–경계 거리의 변동(점선=볼록 껍질)',
                   [val(mass.circularity(cm)), val(mass.solidity(cm)), val(rs)],
                   overlay(size, fills=[(hull & ~m, 'orange', 90)], outlines=[(hull, 'orange', 2)])))
    sp = mass.spiculation_index(crop, cm)
    pts = [((p[1] * s, p[0] * s), 'magenta', 1.6) for p in sp.detail.get('ridge_points', [])]
    band = resize_mask(ndi.binary_dilation(cm, iterations=max(int(sp.detail.get('band_px', 10)), 1)) & ~cm, size)
    L.append(layer(ex, 'spicule', '침상 지수', 'magenta', 'mass.spiculation_index',
                   '경계 바깥 띠에서 선 구조(Sato 필터 상위 10%) 중 방향이 종괴 중심을 향하는 것의 비율(점=중심을 향한 선)',
                   [val(sp)], overlay(size, fills=[(band, 'magenta', 35)], dots=pts)))
    inner = resize_mask(cm & ~ndi.binary_erosion(cm, iterations=max(int(0.2 * math.sqrt(cm.sum() / math.pi)), 1)), size)
    outer = resize_mask(ndi.binary_dilation(cm, iterations=max(int(0.5 * math.sqrt(cm.sum() / math.pi)), 2)) & ~cm, size)
    L.append(layer(ex, 'margin', '경계 선명도·대비', 'cyan', 'mass.margin_sharpness',
                   '경계의 밝기 기울기를 안팎 밝기 차이로 나눔 · 안쪽(초록)과 바깥 띠(파랑) 밝기 차이',
                   [val(mass.margin_sharpness(crop, cm)), val(mass.contrast(crop, cm))],
                   overlay(size, fills=[(inner, 'green', 80), (outer, 'blue', 50)])))
    L.append(layer(ex, 'margin_read', '종괴 경계 서술(판독)', 'white', '', '공급자 분류(DMID 이상 유형)를 BI-RADS 경계 서술로 옮김',
                   [reading('ft_mass_margin', margin_text)], overlay(size, texts=[((12, 12), margin_text, 'white')])))
    return ex


def calc_example(eid, image_id, nth, region, title, morphology_text=''):
    f, crop, cm, s, size, base = crop_view(image_id, 'CALC', nth, margin=0.4)
    sev = {'B': '양성', 'M': '악성', 'N': '미정'}.get(f['severity'], '')
    ex = example_head(eid, region, title,
                      f"DMID {image_id}({f['view']} · 공급자 분류 {'+'.join(f['classes'])} · {sev})의 석회화 부위입니다. "
                      f'전문가 ROI 안에서 top-hat 변환으로 석회화 점을 찾고 mammography-measures 함수를 실행했습니다. '
                      f'화소 간격이 없어 top-hat 반경은 7 px로 두었습니다. {PX_NOTE}', [image_id], base, 'calc_example')
    c = calcification.detect(crop, cm)
    spots = resize_mask(c.labels > 0, size)
    roi_m = resize_mask(cm, size)
    L = ex['layers']
    L.append(layer(ex, 'spots', '석회화 검출·개수', 'yellow', 'calcification.count',
                   'ROI(점선) 안 white top-hat이 중앙값 + 4·MAD를 넘는 점',
                   [val(calcification.count(c)), val(calcification.spot_size(c)), val(calcification.spot_contrast(c))],
                   overlay(size, fills=[(ndi.binary_dilation(spots, iterations=2), 'yellow', 230)], outlines=[(roi_m, 'white', 1)])))
    cen = [(p.centroid[1] * s, p.centroid[0] * s) for p in c.props]
    lines = []
    if len(cen) >= 2:
        arr = np.array(cen)
        d = np.sqrt(((arr[:, None] - arr[None]) ** 2).sum(-1))
        i, j = np.unravel_index(int(d.argmax()), d.shape)
        lines.append((tuple(arr[i]), tuple(arr[j]), 'cyan', 3))
    L.append(layer(ex, 'extent', '범위·밀집도', 'cyan', 'calcification.extent', '가장 먼 두 석회화 중심 사이 거리 · 탐색 범위 면적당 개수',
                   [val(calcification.extent(c)), val(calcification.density(c))],
                   overlay(size, lines=lines, dots=[(p, 'cyan', 3) for p in cen])))
    nn_lines = []
    if len(cen) >= 3:
        from scipy.spatial import cKDTree
        arr = np.array(cen)
        _, idx = cKDTree(arr).query(arr, k=2)
        nn_lines = [(tuple(arr[a]), tuple(arr[b]), 'green', 2) for a, b in enumerate(idx[:, 1])]
    L.append(layer(ex, 'arrangement', '배열(선형성·최근접 거리)', 'green', 'calcification.linearity',
                   '석회화 중심 분산의 방향 치우침 · 가장 가까운 석회화까지 거리(선)',
                   [val(calcification.linearity(c)), val(calcification.nn_distance(c))], overlay(size, lines=nn_lines)))
    big = [p for p in c.props if p.area >= 6]
    elong = np.zeros(c.labels.shape, bool)
    for p in c.props:
        if p.eccentricity > 0.9:
            elong[c.labels == p.label] = True
    L.append(layer(ex, 'shape', '크기 다양성·길쭉함·분지', 'orange', 'calcification.size_variation',
                   '석회화 면적의 변동계수 · 이심률 0.9 초과 비율(주황=길쭉한 점) · 골격 갈림점 비율',
                   [val(calcification.size_variation(c)), val(calcification.elongation(c)), val(calcification.branching(c))],
                   overlay(size, fills=[(ndi.binary_dilation(resize_mask(elong, size), iterations=2), 'orange', 240)])))
    if morphology_text:
        L.append(layer(ex, 'morph_read', '석회화 형태(판독)', 'white', '', '서비스 판독(공급자는 형태를 분류하지 않음)',
                       [reading('ft_calc_morphology', morphology_text)], overlay(size, texts=[((12, 12), morphology_text, 'white')])))
    del big
    return ex


def distortion_example():
    image_id = 'IMG024'
    f, crop, cm, s, size, base = crop_view(image_id, 'ARCH', 0, margin=1.0)
    ex = example_head('ex_ffdm_distortion', '구조왜곡 확대', '구조왜곡 부위',
                      f"DMID {image_id}({f['view']} · 공급자 분류 {'+'.join(f['classes'])} · 악성)의 부위입니다. "
                      f'전문가 ROI 중심을 기준으로 둘레 띠의 선 구조가 중심으로 모이는 정도를 계산했습니다. {PX_NOTE}',
                      [image_id], base, 'distortion_example')
    cy, cx = ndi.center_of_mass(cm)
    radius = 1.6 * math.sqrt(cm.sum() / math.pi)
    ci = distortion.convergence_index(crop, (cy, cx), radius)
    h, w = size[1], size[0]
    yy, xx = np.mgrid[0:h, 0:w]
    rr = np.hypot(yy - cy * s, xx - cx * s)
    ring = (rr > 0.25 * radius * s) & (rr < radius * s)
    pts = [((p[1] * s, p[0] * s), 'magenta', 1.6) for p in ci.detail.get('points', [])]
    L = ex['layers']
    L.append(layer(ex, 'converge', '침상선 수렴 지수', 'magenta', 'distortion.convergence_index',
                   '중심 둘레 띠(보라)에서 선 구조 중 중심을 향하는 것의 비율(무작위 배열이면 약 0.25)',
                   [val(ci)], overlay(size, fills=[(ring, 'magenta', 30)], dots=pts)))
    m = resize_mask(cm, size)
    L.append(layer(ex, 'extent', '범위', 'red', 'distortion.distortion_extent', '전문가 ROI의 최대 지름',
                   [val(distortion.distortion_extent(cm)), val(distortion.lesion_count(cm))],
                   overlay(size, outlines=[(m, 'red', 3)])))
    return ex


def main() -> int:
    registry.MASKED_DIR.mkdir(parents=True, exist_ok=True)
    registry.EXAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    for directory in (registry.MASKED_DIR, registry.EXAMPLE_DIR):
        for old in list(directory.glob('*.jpg')) + list(directory.glob('*.png')):
            old.unlink()
    cc, mlo = View(PAIR[0]), View(PAIR[1])
    figs = masked_figures(cc, mlo)
    for fig in figs:
        fig['base_sha256'] = registry.sha256(registry.MASKED_DIR / fig['base'])
        fig['overlay_sha256'] = registry.sha256(registry.MASKED_DIR / fig['overlay'])
    examples = [
        whole_view_example(mlo, 'ex_ffdm_mlo', 'SPIC'),
        whole_view_example(cc, 'ex_ffdm_cc', 'SPIC'),
        pair_example(cc, mlo),
        mass_example('ex_ffdm_mass_circumscribed', 'IMG008', 'CIRC', '경계 분명 종괴', '경계가 분명한 종괴',
                     '경계 분명 (DMID CIRC)'),
        mass_example('ex_ffdm_mass_spiculated', 'IMG063', 'SPIC', '침상형 종괴', '침상형 종괴', '침상 (DMID SPIC)'),
        mass_example('ex_ffdm_mass_indistinct', 'IMG104', 'MISC', '경계 불분명 종괴', '경계가 불분명한 종괴',
                     '불분명 (DMID MISC · 기타 경계)'),
        calc_example('ex_ffdm_calc_cluster', 'IMG029', 2, '석회화 군집', '작은 석회화 군집'),
        calc_example('ex_ffdm_calc_rodlike', 'IMG024', 0, '막대 모양 석회화', '큰 막대 모양 석회화',
                     '큰 막대 모양 (서비스 판독)'),
        distortion_example(),
    ]
    from build_mammography_paper_examples import build as paper_build
    paper_examples, paper_figs = paper_build()
    examples += paper_examples
    for fig in paper_figs:
        fig['base_sha256'] = registry.sha256(registry.MASKED_DIR / fig['base'])
        fig['overlay_sha256'] = registry.sha256(registry.MASKED_DIR / fig['overlay'])
    figs += paper_figs
    ids = [e['id'] for e in examples]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate example id')
    registry.WEB_DATA.mkdir(parents=True, exist_ok=True)
    (registry.WEB_DATA / 'masked_figures.json').write_text(json.dumps(
        {'generated_by': 'domains/mammography/code/build_mammography_figures.py', 'figures': figs},
        ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (registry.WEB_DATA / 'measurement_examples.json').write_text(json.dumps(
        {'generated_by': 'domains/mammography/code/build_mammography_figures.py',
         'note': 'values computed by mammography-measures on DMID and CC BY 4.0 paper figures; pixels, not calibrated', 'examples': examples},
        ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'masked figures {len(figs)} · examples {len(examples)} · layers {sum(len(e["layers"]) for e in examples)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
