"""Build the measurement-list display examples: one real image per modality × region with toggleable layers.

Each example runs the public ``retinal-measures`` functions on provider/expert masks (or a simple
documented tracer) and writes a base image, one RGBA overlay per measurement layer and the computed
values. The atlas web service shows them with a checkbox per layer (on = overlay and value shown).

Output: ``resources/datasets/retinal_atlas_measurement_examples/`` (images + source_manifest.json)
and ``packages/retinal-atlas-web/src/retinal_atlas_web/data/measurement_examples.json``.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'packages/retinal-measures/src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_atlas_masked_figures as atlas_fig  # noqa: E402  (shared dataset paths, layer tracer, sources)
import retinal_atlas_registry as registry  # noqa: E402  (canonical source / checksum tables)
from retinal_measures import atrophy, lesions, oct_layers, oct_lesions, octa, optic_disc, vessels  # noqa: E402

ROOT = PROJECT.parents[1]
OUTPUT = ROOT / 'resources/datasets/retinal_atlas_measurement_examples'
MANIFEST = PROJECT / 'packages/retinal-atlas-web/src/retinal_atlas_web/data/measurement_examples.json'
WIDTH = 900
COLOURS = {'blue': (56, 189, 248), 'yellow': (255, 211, 77), 'green': (74, 222, 128), 'red': (248, 113, 113),
           'magenta': (232, 121, 249), 'white': (255, 255, 255), 'orange': (251, 146, 60), 'cyan': (34, 211, 238)}


def fmt_number(v):
    if isinstance(v, bool):
        return '예' if v else '아니요'
    if isinstance(v, (int, np.integer)):
        return f'{int(v):,}'
    if isinstance(v, float):
        if math.isnan(v):
            return '—'
        return f'{v:,.0f}' if abs(v) >= 100 else f'{v:.3g}'
    return str(v)


UNIT_KO = {'px2': 'px²', 'px': 'px', 'ratio': '', 'DD': 'DD', 'deg': '°', 'index': '', 'count': '개',
           'presence': '', 'category': '', 'count/10k px': '/10⁴px', 'px/px2': 'px/px²', 'dimensionless': '', 'mm2': 'mm²',
           'mm': 'mm', 'um': 'µm', 'bits': '비트', 'score': '', 'intensity': '', 'dB': 'dB', 'clock hour': '시',
           'px3': 'px³', 'voxel': '복셀', 'px/year': 'px/년', 'px2/year': 'px²/년', 'length': 'px', 'area': 'px²', 'mm3': 'mm³'}
WORD_KO = {'follows': 'ISNT 순서 따름', 'violated': 'ISNT 순서 어긋남', 'pit': '정상 함요', 'shallow': '얕음',
           'inverted': '볼록', 'superotemporal': '위귀', 'superonasal': '위코', 'inferotemporal': '아래귀',
           'inferonasal': '아래코', 'vertical': '수직', 'horizontal': '수평', 'min': '최소', 'median': '중앙',
           'branch_points': '분지점', 'end_points': '끝점', 'depth': '깊이', 'width': '폭', 'max_slope': '최대 경사',
           'inferior': '아래(I)', 'multifocal': '다초점', 'unifocal': '단일 초점', 'foci': '초점 수', 'superior': '위(S)',
           'nasal': '코(N)', 'temporal': '귀(T)', 'rms': '불규칙(RMS)', 'max_elevation': '최대 융기',
           'preserved_fraction': '보존 비율', 'gap_count': '끊김 수', 'max_gap': '최대 끊김', 'ordered_fraction': '순서 유지 비율',
           'continuous': '연속', 'disrupted': '끊김 있음', 'absent': '대부분 소실', 'preserved': '보존', 'disorganised': '뒤섞임',
           'mean': '평균', 'p90': '90백분위', 'max': '최대', 'cv': '변동계수', 'std': '표준편차', 'circularity': '원형도',
           'eccentricity': '이심률', 'solidity': '충실도', 'row': '세로 위치', 'col': '가로 위치', 'entropy': '엔트로피',
           'dominance': '최빈 방향 비율', 'upper': '위', 'lower': '아래', 'left': '왼쪽', 'right': '오른쪽', 'ring1': '안쪽 고리',
           'ring2': '가운데 고리', 'ring3': '바깥 고리', 'mean_distance': '평균 거리', 'near_fraction': '혈관 10px 이내 비율',
           'clustered': '모여 있음', 'random': '무작위', 'dispersed': '흩어짐', 'clark_evans_R': 'Clark–Evans R', 'new': '새로 생김',
           'disappeared': '사라짐', 'axis_ratio': '장단축비', 'orientation_deg': '긴축 각도', 'max_min_ratio': '최대/최소 폭',
           'mean_cv': '평균 변동계수', 'sub_rpe': 'RPE 아래(1형)', 'subretinal': '망막하(2형)', 'intraretinal': '망막내(3형)',
           'hyporeflective': '저반사', 'mixed': '혼합 반사', 'hyperreflective': '고반사', 'contrast': '대비', 'homogeneity': '균질도',
           'energy': '에너지', 'correlation': '상관', 'lbp_entropy': 'LBP 엔트로피', 'sharpness': '선명도', 'before': '이전',
           'after': '이후', 'total': '합계', 'segments': '분절 수', 'largest_component_fraction': '최대 연결 비율',
           'components': '연결 성분 수', 'branch_end_ratio': '분지/끝점 비', 'normalised': '정규화(유리체 0·RPE 1)',
           'ratio_to_reference': 'RPE 대비 비', 'fd_count': '결손 수', 'mean_fd_size': '평균 결손 크기', 'luminal_px': '내강 화소',
           'total_px': '전체 화소', 'rate_per_year': '연간', 'raw_rate': '면적 기준 연간', 'pixels': '화소 수',
           'skeleton': '중심선', 'vessel': '혈관', 'skeleton_density': '중심선 밀도', 'detail': '세부'}
UNITLESS_KEYS = {'segments', 'cv', 'near_fraction', 'components', 'largest_component_fraction', 'branch_end_ratio', 'gap_count',
                 'preserved_fraction', 'ordered_fraction', 'circularity', 'eccentricity', 'solidity', 'row', 'col', 'entropy',
                 'dominance', 'fd_count', 'mean_cv', 'max_min_ratio', 'axis_ratio'}
NOTE_KO = {'x, y and z spacing required': '깊이(z) 화소 크기가 공개되지 않아 부피(mm³)를 낼 수 없음'}
READING = 'reading'   # status for qualitative items that have no computation code: the layer shows where to read


def value_text(m) -> str:
    """Readable value of a Measurement (status first: never shows missing evidence as 0)."""
    if m.status == 'not_evaluable':
        return f'계산 불가 · {NOTE_KO.get(m.note, m.note)}'
    if m.status == 'not_observed' and m.value in (None, 0, 0.0, False):
        return '관찰 안 됨'
    unit = UNIT_KO.get(m.unit, m.unit)
    v = m.value
    if isinstance(v, dict):
        return ' · '.join(f'{WORD_KO.get(k, k)} {fmt_number(x)}'
                          f'{unit if isinstance(x, (int, float)) and not isinstance(x, bool) and k not in UNITLESS_KEYS else ""}'
                          for k, x in v.items() if x is not None)
    if isinstance(v, str):
        text = WORD_KO.get(v, v)
        if m.detail and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in m.detail.values()):
            text += ' (' + ' · '.join(f'{WORD_KO.get(k, k)} {fmt_number(x)}' for k, x in m.detail.items()) + ')'
        return text
    if m.unit == 'ratio' and isinstance(v, float) and v <= 1:
        return f'{v:.3f}'
    return f'{fmt_number(v)} {unit}'.strip()


class Canvas:
    """Display-resolution canvas: masks/points are given in source pixels and scaled once."""

    def __init__(self, image: Image.Image, width=WIDTH):
        self.scale = min(1.0, width / image.width)
        self.size = (round(image.width * self.scale), round(image.height * self.scale))
        self.base = image.convert('RGB').resize(self.size, Image.LANCZOS)

    def layer(self):
        return Image.new('RGBA', self.size, (0, 0, 0, 0))

    def mask(self, mask, colour, fill=110, edge=255, layer=None):
        layer = layer or self.layer()
        m = Image.fromarray((np.asarray(mask) > 0).astype(np.uint8) * 255).resize(self.size, Image.NEAREST)
        arr = np.asarray(m) > 0
        from scipy import ndimage
        rim = arr & ~ndimage.binary_erosion(arr, iterations=2)
        rgba = np.zeros((*arr.shape, 4), np.uint8)
        rgba[..., :3] = colour
        rgba[..., 3] = np.where(rim, edge, np.where(arr, fill, 0))
        return Image.alpha_composite(layer, Image.fromarray(rgba, 'RGBA'))

    def p(self, rc):  # (row, col) source → (x, y) display
        return (rc[1] * self.scale, rc[0] * self.scale)

    def draw(self, layer):
        return ImageDraw.Draw(layer)


def _builder_name() -> str:
    """Top-level builder that produced the example (the function main() called), for the registry tables."""
    import inspect
    names = [f.function for f in inspect.stack()[2:]]
    return names[names.index('main') - 1] if 'main' in names else names[0]


def write_example(ex: dict, canvas: Canvas, layers: list[dict]) -> dict:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    ex = dict(ex, builder=_builder_name())
    base_name = f"{ex['id']}.jpg"
    canvas.base.save(OUTPUT / base_name, quality=88)
    out_layers = []
    for layer in layers:
        name = f"{ex['id']}_{layer['key']}.png"
        layer.pop('image').save(OUTPUT / name, optimize=True)
        out_layers.append(dict(layer, file=name))
    return dict(ex, base=base_name, width=canvas.size[0], height=canvas.size[1], layers=out_layers)


def L(key, label, image, features, function, how, colour):
    """Layer record; ``features`` = [(feature_id, Measurement[, display text])]."""
    out = []
    for f in features:
        fid, m = f[0], f[1]
        out.append({'id': fid, 'value': f[2] if len(f) > 2 else value_text(m), 'status': m.status})
    return dict(key=key, label=label, image=image, tone=colour, function=function, how=how, features=out)


def R(key, label, image, fid, reading, how, colour):
    """Reading layer for a qualitative item without computation code: shows where and what to read."""
    return dict(key=key, label=label, image=image, tone=colour, function='', how=how,
                features=[{'id': fid, 'value': reading, 'status': READING}])


# ---------------------------------------------------------------- examples

def fundus_disc() -> dict:
    stem = 'IMG_4198'
    root = atlas_fig.CHAKSU
    img = ImageOps.exif_transpose(Image.open(root / '1.0_Original_Fundus_Images/Remidio' / f'{stem}.JPG'))
    disc = np.asarray(Image.open(root / '5.0_OD_OC_Mean_Median_Majority_STAPLE/Remidio/Disc/STAPLE' / f'{stem}.png').convert('L')) > 127
    cup = np.asarray(Image.open(root / '5.0_OD_OC_Mean_Median_Majority_STAPLE/Remidio/Cup/STAPLE' / f'{stem}.png').convert('L')) > 127
    ys, xs = np.where(disc)
    cy, cx, r = int(ys.mean()), int(xs.mean()), int(1.25 * max(np.ptp(ys), np.ptp(xs)))
    box = (cx - r, cy - r, cx + r, cy + r)
    crop = img.crop(box)
    disc, cup = disc[box[1]:box[3], box[0]:box[2]], cup[box[1]:box[3], box[0]:box[2]]
    c = Canvas(crop, 720)
    layers = []
    layers.append(L('disc', '유두 경계·면적', c.mask(disc, COLOURS['blue'], 60), [('ft_disc_area', optic_disc.disc_area(disc))],
                    'optic_disc.disc_area', '전문가 합의 유두 mask의 화소 수', 'blue'))
    m = optic_disc.disc_diameter(disc)
    lay = c.layer(); d = c.draw(lay)
    (r0, c0, r1, c1) = __import__('skimage.measure', fromlist=['regionprops']).regionprops(disc.astype(int))[0].bbox
    mid_r, mid_c = (r0 + r1) / 2, (c0 + c1) / 2
    d.line([c.p((r0, mid_c)), c.p((r1, mid_c))], fill=COLOURS['blue'] + (255,), width=3)
    d.line([c.p((mid_r, c0)), c.p((mid_r, c1))], fill=COLOURS['blue'] + (255,), width=3)
    layers.append(L('disc_diameter', '유두 수직·수평 직경', lay, [('ft_disc_diameter', m)], 'optic_disc.disc_diameter',
                    '유두 mask 외접 상자의 높이·폭', 'blue'))
    layers.append(L('cup', '컵 면적', c.mask(cup, COLOURS['yellow'], 80), [('ft_cup_area', optic_disc.cup_area(cup))],
                    'optic_disc.cup_area', '전문가 합의 컵 mask의 화소 수', 'yellow'))
    lay = c.layer(); d = c.draw(lay)
    from skimage import measure as skm
    cr0, _, cr1, _ = skm.regionprops(cup.astype(int))[0].bbox
    x = c1 + 0.08 * (c1 - c0)
    d.line([c.p((r0, x)), c.p((r1, x))], fill=COLOURS['blue'] + (255,), width=5)
    d.line([c.p((cr0, x + 0.06 * (c1 - c0))), c.p((cr1, x + 0.06 * (c1 - c0)))], fill=COLOURS['yellow'] + (255,), width=5)
    layers.append(L('cdr', '수직 컵/유두비', lay, [('ft_cdr_vertical', optic_disc.cup_disc_ratio(disc, cup))],
                    'optic_disc.cup_disc_ratio', '컵 높이(노랑) ÷ 유두 높이(하늘색)', 'yellow'))
    layers.append(L('rim', '신경망막 테 면적', c.mask(disc & ~cup, COLOURS['green'], 90), [('ft_rim_area', optic_disc.rim_area(disc, cup))],
                    'optic_disc.rim_area', '유두 mask − 컵 mask', 'green'))
    lay = c.layer(); d = c.draw(lay)
    centre = np.argwhere(disc).mean(0)
    rad = 0.55 * max(r1 - r0, c1 - c0)
    for deg in (45, 135, 225, 315):
        t = math.radians(deg)
        d.line([c.p(centre), c.p((centre[0] - rad * math.sin(t), centre[1] + rad * math.cos(t)))], fill=COLOURS['white'] + (230,), width=2)
    for name, deg in (('S', 90), ('I', 270), ('N', 0), ('T', 180)):   # right eye assumed: nasal = image right
        t = math.radians(deg)
        x, y = c.p((centre[0] - 0.62 * rad * math.sin(t), centre[1] + 0.62 * rad * math.cos(t)))
        d.text((x - 4, y - 6), name, fill=(255, 255, 255, 255))
    layers.append(L('isnt', 'ISNT 순서(테 두께)', lay, [('ft_isnt_pattern', optic_disc.isnt_pattern(disc, cup, eye='OD'))],
                    'optic_disc.isnt_pattern', '4개 부채꼴의 평균 테 폭(px) 비교; 눈 방향 정보가 없어 오른눈으로 가정', 'white'))
    from skimage import measure as skm2
    p = skm2.regionprops(disc.astype(int))[0]
    lay = c.layer(); d = c.draw(lay)
    cy0, cx0 = p.centroid
    for length, ang in ((p.major_axis_length, p.orientation), (p.minor_axis_length, p.orientation + math.pi / 2)):
        dy, dx = math.cos(ang) * length / 2, math.sin(ang) * length / 2
        d.line([c.p((cy0 - dy, cx0 - dx)), c.p((cy0 + dy, cx0 + dx))], fill=COLOURS['orange'] + (255,), width=3)
    rr = np.linspace(0, 2 * math.pi, 180)
    a, b = p.major_axis_length / 2, p.minor_axis_length / 2
    pts = [c.p((cy0 + a * math.cos(t) * math.cos(p.orientation) - b * math.sin(t) * math.sin(p.orientation),
                cx0 + a * math.cos(t) * math.sin(p.orientation) + b * math.sin(t) * math.cos(p.orientation))) for t in rr]
    d.line(pts + pts[:1], fill=COLOURS['orange'] + (200,), width=2)
    layers.append(L('shape', '유두 형태(타원 근사)', lay, [('ft_disc_shape', optic_disc.disc_shape(disc))],
                    'optic_disc.disc_shape', '유두 mask에 같은 2차 모멘트의 타원(주황)을 맞춰 장단축비·원형도·이심률 계산', 'orange'))
    profile = optic_disc.rim_width_profile(disc, cup, eye='OD')
    med = float(np.median(list(profile.values())))
    lay = c.layer(); d = c.draw(lay)
    for ang_deg, w in profile.items():
        t = math.radians(ang_deg)
        tip = (centre[0] - rad * 0.95 * math.sin(t), centre[1] + rad * 0.95 * math.cos(t))
        col = COLOURS['red'] if w < 0.5 * med else COLOURS['green']
        d.line([c.p((centre[0] - rad * 0.8 * math.sin(t), centre[1] + rad * 0.8 * math.cos(t))), c.p(tip)], fill=col + (255,), width=3)
    layers.append(L('notch', '테 노치', lay, [('ft_cupping_notch', optic_disc.rim_notch(disc, cup, eye='OD'))],
                    'optic_disc.rim_notch', '5° 간격 방향별 테 폭 막대: 중앙값의 절반 미만이면 빨강(노치 후보), 아니면 초록', 'green'))
    layers.append(R('color', '유두 색', c.mask(disc & ~cup, COLOURS['magenta'], 0), 'ft_disc_color',
                    '판독 항목(계산 코드 없음) · 테(자홍 윤곽)의 분홍빛을 보고 판정; 이 영상은 정상 분홍색으로 보임',
                    '테 부분의 색을 판독자가 봄(창백 = 흰빛). 자동 판정 코드는 없음', 'magenta'))
    lay = c.layer(); d = c.draw(lay)
    x, y = c.p(centre); rr2 = 0.62 * max(r1 - r0, c1 - c0) * c.scale
    d.ellipse((x - rr2, y - rr2, x + rr2, y + rr2), outline=COLOURS['white'] + (200,), width=2)
    d.ellipse((x - rr2 * 0.75, y - rr2 * 0.75, x + rr2 * 0.75, y + rr2 * 0.75), outline=COLOURS['white'] + (120,), width=1)
    layers.append(R('margin', '유두 경계 선명도', lay, 'ft_disc_margin',
                    '판독 항목(계산 코드 없음) · 흰 고리 사이 띠에서 경계가 또렷한지 판정; 이 영상은 경계가 선명함',
                    '유두 가장자리(두 흰 고리 사이)를 판독자가 봄(흐림 = 부종 의심). 자동 판정 코드는 없음', 'white'))
    ex = dict(id='ex_fundus_disc', modality='cfp', modality_label='안저', region='시신경유두',
              title='안저 · 시신경유두', source='chaksu', source_file=f'Test/1.0_Original_Fundus_Images/Remidio/{stem}.JPG',
              caption='정상 눈의 유두입니다. 안과 전문의 5명의 합의 경계(유두·컵)를 입력으로 retinal-measures 함수를 실행했습니다. '
                      '장비 보정 정보가 없어 길이·면적은 화소 단위입니다.')
    return write_example(ex, c, layers)


def fundus_vessels() -> dict:
    name = '005_N'
    img = Image.open(atlas_fig.AVSEG / f'OrginalImages/Org/{name}.png').convert('RGB')
    lab = np.array(Image.open(atlas_fig.AVSEG / f'Fundus-AVSeg-7C-Mask/Labels/Org/{name}.png'))
    A = atlas_fig.AVSEG_LABELS
    artery = (lab == A['artery']) | (lab == A['crossing'])
    vein = (lab == A['vein']) | (lab == A['crossing'])
    vessel = artery | vein
    fov = lab > 0
    disc = lab == A['disc']
    dc = np.argwhere(disc).mean(0)
    dr = math.sqrt(disc.sum() / math.pi)
    fovea = np.argwhere(lab == A['fovea']).mean(0)
    c = Canvas(img)
    layers = [L('vessel', '혈관 면적 점유율', c.mask(vessel, COLOURS['cyan'], 150, 150), [('ft_vessel_area_density', vessels.area_density(vessel, fov=fov))],
                'vessels.area_density', '혈관 mask 화소 ÷ 촬영 시야 화소', 'cyan')]
    from skimage import morphology
    skel = morphology.skeletonize(vessel)
    lay = c.mask(morphology.binary_dilation(skel, morphology.disk(2)), COLOURS['red'], 230, 230)
    layers.append(L('skeleton', '혈관 중심선(길이 밀도·구불거림·프랙탈)', lay,
                    [('ft_vessel_length_density', vessels.length_density(vessel, fov=fov)),
                     ('ft_vessel_tortuosity', vessels.tortuosity(vessel)),
                     ('ft_fractal_dimension', vessels.fractal_dimension(vessel))],
                    'vessels.length_density · tortuosity · fractal_dimension', '혈관 mask를 1화소 중심선으로 가늘게 만든 뒤 계산', 'red'))
    from scipy import ndimage
    nb = ndimage.convolve(skel.astype(int), np.ones((3, 3)), mode='constant') - 1
    lay = c.layer(); d = c.draw(lay)
    for (r, q), col in ((p, COLOURS['yellow']) for p in np.argwhere(skel & (nb >= 3))[::3]):
        x, y = c.p((r, q)); d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=col + (255,))
    for r, q in np.argwhere(skel & (nb == 1)):
        x, y = c.p((r, q)); d.ellipse((x - 3, y - 3, x + 3, y + 3), outline=COLOURS['white'] + (255,), width=2)
    layers.append(L('topology', '분지점(노랑)·끝점(흰 테)', lay, [('ft_vessel_topology', vessels.topology(vessel, fov=fov))],
                    'vessels.topology', '중심선 화소의 이웃 수: 3 이상 = 분지점, 1 = 끝점', 'yellow'))
    radius = np.hypot(*(np.indices(lab.shape) - dc[:, None, None])) / dr
    zone = (radius >= 2) & (radius <= 3)
    lay = c.mask(artery & zone, COLOURS['red'], 220, 220)
    lay = c.mask(vein & zone, COLOURS['blue'], 220, 220, layer=lay)
    d = c.draw(lay)
    for k in (2, 3):
        x, y = c.p(dc); rr = k * dr * c.scale
        d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=COLOURS['white'] + (230,), width=2)
    layers.append(L('crae', '동·정맥 굵기(CRAE·CRVE·AVR)', lay,
                    [('ft_crae', vessels.crae(artery, dc, dr)), ('ft_crve', vessels.crve(vein, dc, dr)),
                     ('ft_avr', vessels.avr(artery, vein, dc, dr))],
                    'vessels.crae · crve · avr', '유두 경계에서 0.5–1 유두지름 고리(흰 원) 안 동맥(빨강)·정맥(파랑) 폭을 Knudtson 식으로 합침', 'red'))
    dd = 2 * dr
    lay = c.layer(); d = c.draw(lay)
    d.line([c.p(dc), c.p(fovea)], fill=COLOURS['magenta'] + (255,), width=3)
    for pt in (dc, fovea):
        x, y = c.p(pt); d.ellipse((x - 6, y - 6, x + 6, y + 6), outline=COLOURS['magenta'] + (255,), width=3)
    dist, ang = optic_disc.disc_fovea_geometry(dc, fovea, disc_diameter_px=dd)
    layers.append(L('disc_fovea', '유두–중심와 거리·각도', lay, [('ft_disc_fovea_distance', dist), ('ft_disc_fovea_angle', ang)],
                    'optic_disc.disc_fovea_geometry', '공급자 유두 중심과 중심와 점 사이 거리(유두지름 단위)와 수평선 대비 각도', 'magenta'))
    layers += vessel_detail_layers(c, img, vessel, artery, vein, fov, dc, dr, fovea)
    ex = dict(id='ex_fundus_vessels', modality='cfp', modality_label='안저', region='망막 혈관',
              title='안저 · 망막 혈관', source='fundus_avseg_7c', source_file=f'OrginalImages/Org/{name}.png',
              caption='정상 눈입니다. 공급자 전문가 동·정맥 mask를 입력으로 혈관 측정 함수를 실행했습니다. 길이 단위는 화소입니다.')
    return write_example(ex, c, layers)


def fundus_lesions() -> dict:
    image_id = 'IDRiD_31'
    lab = np.array(Image.open(atlas_fig.REFINED / f'Labels/{image_id}_vessel.png'))
    suffix = 'png' if (atlas_fig.REFINED / f'Images/{image_id}.png').exists() else 'jpg'
    img = Image.open(atlas_fig.REFINED / f'Images/{image_id}.{suffix}').convert('RGB')
    ma, hem, ex_, cws = lab == 255, lab == 127, lab == 63, lab == 191
    fovea = np.argwhere(lab == 16).mean(0)
    disc_m = lab == 32
    disc = np.argwhere(disc_m).mean(0)
    ys, xs = np.where(disc_m)
    dd = float(max(np.ptp(ys), np.ptp(xs)))
    c = Canvas(img)
    from scipy import ndimage
    lay = c.layer(); d = c.draw(lay)
    for comp in ndimage.find_objects(ndimage.label(ma)[0]):
        r = (comp[0].start + comp[0].stop) / 2; q = (comp[1].start + comp[1].stop) / 2
        x, y = c.p((r, q)); d.ellipse((x - 7, y - 7, x + 7, y + 7), outline=COLOURS['red'] + (255,), width=2)
    layers = [L('ma', '미세동맥류 개수', lay, [('ft_ma_count', lesions.count(ma)),
                                         ('ft_ma_distance_fovea', lesions.fovea_distance(ma, fovea, disc_diameter_px=dd))],
                'lesions.count · fovea_distance', '공급자 미세동맥류 mask의 연결 성분(빨간 원)', 'red')]
    lay = c.mask(hem, COLOURS['orange'], 120)
    d = c.draw(lay)
    axis = (disc - fovea) / np.linalg.norm(disc - fovea)
    normal = np.array([-axis[1], axis[0]])
    for v in (axis, normal):
        d.line([c.p(fovea - 3000 * v), c.p(fovea + 3000 * v)], fill=COLOURS['white'] + (220,), width=2)
    layers.append(L('hem', '출혈 면적·사분면별 개수', lay,
                    [('ft_hem_area', lesions.area(hem)), ('ft_hem_count_quadrant', lesions.quadrant_counts(hem, fovea, disc))],
                    'lesions.area · quadrant_counts', '공급자 출혈 mask; 사분면은 중심와를 지나는 유두–중심와 축(흰 선)으로 나눔', 'orange'))
    lay = c.mask(ex_, COLOURS['yellow'], 150)
    d = c.draw(lay)
    pts = np.argwhere(ex_)
    near = pts[np.argmin(np.hypot(*(pts - fovea).T))]
    d.line([c.p(fovea), c.p(near)], fill=COLOURS['cyan'] + (255,), width=3)
    x, y = c.p(fovea); d.ellipse((x - 6, y - 6, x + 6, y + 6), outline=COLOURS['cyan'] + (255,), width=3)
    layers.append(L('ex', '경성삼출물 면적·중심와 거리', lay,
                    [('ft_he_area', lesions.area(ex_)), ('ft_he_distance_fovea', lesions.fovea_distance(ex_, fovea, disc_diameter_px=dd))],
                    'lesions.area · fovea_distance', '공급자 경성삼출물 mask; 하늘색 선 = 중심와에서 가장 가까운 삼출물(유두지름 단위)', 'yellow'))
    layers.append(L('cws', '면화반 개수·면적', c.mask(cws, COLOURS['white'], 120),
                    [('ft_cws_count', lesions.count(cws)), ('ft_cws_area', lesions.area(cws))],
                    'lesions.count · area', '공급자 면화반 mask의 연결 성분과 화소 수', 'white'))
    ex = dict(id='ex_fundus_lesions', modality='cfp', modality_label='안저', region='황반·후극부 병변',
              title='안저 · 당뇨망막병증 병변', source='refined_idrid', source_file=f'Train/Images/{image_id}.{suffix}',
              caption='당뇨망막병증 눈입니다. 공급자 전문가 병변 mask(미세동맥류·출혈·경성삼출물·면화반)와 중심와·유두 위치를 '
                      '입력으로 병변 측정 함수를 실행했습니다. 거리는 유두지름(DD), 면적은 화소 단위입니다.')
    return write_example(ex, c, layers)


def fundus_atrophy() -> dict:
    import pandas as pd
    name = 'P0004'
    img = Image.open(atlas_fig.PALM / f'Images/{name}.jpg').convert('RGB')
    atr = np.array(Image.open(atlas_fig.PALM / f'Lesion Masks/Atrophy/{name}.bmp').convert('L')) < 128
    fx, fy = pd.read_excel(atlas_fig.PALM / 'Fovea Localization.xlsx').set_index('imgName').loc[f'{name}.jpg']
    fovea = (float(fy), float(fx))
    c = Canvas(img)
    layers = [L('area', '위축 면적', c.mask(atr, COLOURS['yellow'], 90), [('ft_atrophy_area', atrophy.area(atr))],
                'atrophy.area', '공급자 위축 mask 화소 수', 'yellow')]
    from scipy import ndimage
    labels, n = ndimage.label(atr)
    lay = c.layer(); d = c.draw(lay)
    palette = [COLOURS[k] for k in ('cyan', 'magenta', 'green', 'orange', 'blue')]
    for k in range(1, n + 1):
        lay = c.mask(labels == k, palette[(k - 1) % len(palette)], 70, layer=lay)
    layers.append(L('focality', '위축 초점 수', lay, [('ft_atrophy_focality', atrophy.focality(atr))],
                    'atrophy.focality', '서로 떨어진 위축 조각(색별)의 수', 'cyan'))
    lay = c.layer(); d = c.draw(lay)
    x, y = c.p(fovea); d.ellipse((x - 9, y - 9, x + 9, y + 9), outline=COLOURS['red'] + (255,), width=3)
    d.line((x - 16, y, x + 16, y), fill=COLOURS['red'] + (255,), width=2); d.line((x, y - 16, x, y + 16), fill=COLOURS['red'] + (255,), width=2)
    layers.append(L('fovea', '중심와 침범', lay, [('ft_atrophy_foveal_involvement', atrophy.foveal_involvement(atr, fovea))],
                    'atrophy.foveal_involvement', '공급자 중심와 좌표(빨간 표적)가 위축 안에 있는지', 'red'))
    ex = dict(id='ex_fundus_atrophy', modality='cfp', modality_label='안저', region='황반 위축',
              title='안저 · 근시성 황반 위축', source='palm', source_file=f'Training/Images/{name}.jpg',
              caption='병적 근시 눈입니다. 공급자 전문가 위축 mask와 중심와 좌표를 입력으로 위축 측정 함수를 실행했습니다.')
    return write_example(ex, c, layers)


def oct_layer_example() -> dict:
    rel = 'TREX DME/Monthly/0222MOS/V26/OS/TREX_DME_000024.tif'
    g = np.asarray(Image.open(atlas_fig.OLIVES / rel).convert('L'), dtype=float)
    t = atlas_fig._trace_layers(g)
    top, bottom = 40, 340
    crop = Image.fromarray(g.astype(np.uint8)).crop((0, top, g.shape[1], bottom))
    shift = lambda v: np.asarray(v, float) - top
    surf = {'ILM': shift(t['ilm'])[None], 'BM': shift(t['bm'])[None], 'OPL_ONL': shift(t['opl'] + 3)[None],
            'ELM': shift(t['ez'] - 6)[None], 'EZ': shift(t['ez'])[None]}
    band = lambda a, b: atlas_fig._band(crop.size[::-1], a[0], b[0])
    c = Canvas(crop, 1000)
    layers = [L('retina', '전체 망막 두께(ILM–BM)', c.mask(band(surf['ILM'], surf['BM']), COLOURS['cyan'], 60, 0),
                [('ft_layer_thickness_generic', oct_layers.layer_thickness(surf, 'retina'))],
                'oct_layers.layer_thickness', '열마다 브루크막 깊이 − 내경계막 깊이의 평균(축 방향 px)', 'cyan'),
              L('onl', '외핵층 두께', c.mask(band(surf['OPL_ONL'], surf['ELM']), COLOURS['magenta'], 80, 0),
                [('ft_onl_thickness', oct_layers.layer_thickness(surf, 'onl'))],
                'oct_layers.layer_thickness', '외망상층 아래 ~ 외경계막 사이 평균 두께', 'magenta')]
    ilm = surf['ILM'][0]
    pit = oct_layers.foveal_pit(ilm)
    lay = c.layer(); d = c.draw(lay)
    d.line([c.p((y, x)) for x, y in enumerate(ilm)], fill=COLOURS['yellow'] + (255,), width=3)
    q = len(ilm) // 4
    fc = q + int(np.nanargmax(ilm[q:len(ilm) - q]))
    half = len(ilm) // 4
    rl = fc - half + int(np.nanargmin(ilm[fc - half:fc + 1])); rr = fc + int(np.nanargmin(ilm[fc:fc + half + 1]))
    d.line([c.p((ilm[rl], rl)), c.p((ilm[rr], rr))], fill=COLOURS['white'] + (230,), width=2)
    d.line([c.p(((ilm[rl] + ilm[rr]) / 2, fc)), c.p((ilm[fc], fc))], fill=COLOURS['red'] + (255,), width=3)
    layers.append(L('pit', '중심와 함요 깊이·폭', lay, [('ft_foveal_pit_shape', pit), ('ft_foveal_contour', oct_layers.foveal_contour(ilm))],  # px (no spacing)
                    'oct_layers.foveal_pit · foveal_contour', '내경계막 선(노랑)에서 양쪽 테 꼭대기를 잇는 선(흰색)과 가장 깊은 점 사이 거리(빨강)', 'yellow'))
    ez_vis = np.ones((1, crop.size[0]), bool)
    lay = c.layer(); d = c.draw(lay)
    d.line([c.p((y, x)) for x, y in enumerate(surf['EZ'][0])], fill=COLOURS['green'] + (255,), width=3)
    _, frac, gap = oct_layers.ez_preserved(ez_vis)
    layers.append(L('ez', '타원체대(EZ) 보존 비율', lay, [('ft_ez_preserved_fraction', frac), ('ft_ez_disruption_width', gap)],
                    'oct_layers.ez_preserved', '추적한 EZ 선(초록)이 끊기지 않은 A-scan 비율과 가장 긴 끊김 폭', 'green'))
    layers += oct_layer_extra_layers(c, np.asarray(crop, float), surf, t, top)
    ex = dict(id='ex_oct_layers', modality='oct', modality_label='OCT', region='황반 망막층',
              title='OCT · 황반 망막층', source='olives', source_file=rel,
              caption='바이오마커 라벨이 모두 0인 중심와 B-scan입니다. 경계면은 열마다 밝기 변화로 자동 추적한 서비스 추정이며, '
                      '이를 입력으로 층 측정 함수를 실행했습니다. 두께는 축 방향 화소 단위입니다.')
    return write_example(ex, c, layers)


def oct_lesion_example() -> dict:
    pal = atlas_fig.AMD_PALETTE
    best, best_path = -1, None
    for path in sorted(atlas_fig.AMD_SD.glob('images/*/*.png'), key=lambda p: (int(p.parent.name), p.stem)):
        rgb = np.array(Image.open(path).convert('RGB'))
        mrgb = rgb[:, rgb.shape[1] // 2:].astype(int)
        areas = [int(np.all(np.abs(mrgb - pal[k]) < 40, axis=2).sum()) for k in ('IRF', 'SRF', 'PED', 'SHRM')]
        score = min(areas[:3]) + (10 ** 6 if areas[3] > 50 and min(areas[:3]) > 0 else 0)   # prefer scans that also carry SHRM
        if score > best:
            best, best_path = score, path
    rgb = np.array(Image.open(best_path).convert('RGB'))
    half = rgb.shape[1] // 2
    img, mrgb = Image.fromarray(rgb[:, :half]), rgb[:, half:].astype(int)
    m = {k: np.all(np.abs(mrgb - pal[k]) < 40, axis=2) for k in ('IRF', 'SRF', 'PED')}
    c = Canvas(img, 900)
    layers = [L('irf', '망막내액 단면 면적', c.mask(m['IRF'], COLOURS['green'], 120),
                [('ft_irf_bscan_area', oct_lesions.bscan_area(m['IRF'])),
                 ('ft_lesion_generic_count', oct_lesions.lesion_count(m['IRF'], feature_id='ft_lesion_generic_count'))],
                'oct_lesions.bscan_area · lesion_count', '공급자 망막내액 mask의 화소 수와 연결 성분 수', 'green')]

    def height_layer(key, label, mask, colour, fid_h, fid_w=None):
        lay = c.mask(mask, COLOURS[colour], 110)
        d = c.draw(lay)
        h = oct_lesions.height(mask, feature_id=fid_h)
        col = h.detail.get('ascan_index')
        feats = [(fid_h, h)]
        if col is not None:
            rows = np.where(mask[:, col])[0]
            d.line([c.p((rows.min(), col)), c.p((rows.max(), col))], fill=COLOURS['white'] + (255,), width=3)
        if fid_w:
            w = oct_lesions.lateral_diameter(mask, feature_id=fid_w)
            cols = np.where(mask.any(0))[0]
            r = np.where(mask.any(1))[0].max() + 4
            d.line([c.p((r, cols.min())), c.p((r, cols.max()))], fill=COLOURS['white'] + (255,), width=3)
            feats.append((fid_w, w))
        return L(key, label, lay, feats, 'oct_lesions.height' + (' · lateral_diameter' if fid_w else ''),
                 '가장 두꺼운 A-scan의 세로 길이(흰 세로선)' + (', mask 전체의 가장 넓은 가로 폭(흰 가로선; 떨어진 작은 조각도 포함)' if fid_w else ''), colour)

    layers.append(height_layer('srf', '망막하액 최대 높이', m['SRF'], 'red', 'ft_srf_height'))
    layers.append(height_layer('ped', '색소상피박리 높이·기저 직경', m['PED'], 'blue', 'ft_ped_height', 'ft_ped_diameter'))
    shrm = np.all(np.abs(mrgb - pal['SHRM']) < 40, axis=2)
    layers += amd_sd_bscan_layers(c, img, m, shrm)
    ex = dict(id='ex_oct_lesions', modality='oct', modality_label='OCT', region='황반 병변',
              title='OCT · 황반 병변(액체·PED)', source='amd_sd', source_file=f'images/{best_path.parent.name}/{best_path.name}',
              caption='나이관련황반변성 B-scan입니다. 공급자 병변 mask(망막내액·망막하액·색소상피박리)를 입력으로 OCT 병변 측정 '
                      '함수를 실행했습니다. 길이는 화소 단위입니다.')
    return write_example(ex, c, layers)


def octa_example() -> dict:
    img = Image.open(atlas_fig.ARTICLE_FIGURES / 'octa_scp.jpg').convert('L')
    g = np.asarray(img, dtype=float)
    flow = octa.binarize(g, method='phansalkar', window=15)
    from scipy import ndimage
    sm = ndimage.gaussian_filter(g, 3)
    h, w = g.shape
    win = sm[h // 2 - 40:h // 2 + 40, w // 2 - 40:w // 2 + 40]
    dy, dx = np.unravel_index(win.argmin(), win.shape)
    centre = (h // 2 - 40 + dy, w // 2 - 40 + dx)   # darkest point near the slab centre
    faz = octa.faz_detect(g, centre, max_radius_px=min(g.shape) / 5)
    c = Canvas(img.convert('RGB'), 700)
    layers = [L('vd', '표층 혈관 밀도', c.mask(flow, COLOURS['red'], 140, 140), [('ft_octa_vessel_density_scp', octa.vessel_density(flow))],
                'octa.vessel_density', 'Phansalkar 국소 임계값으로 이진화한 혈류 화소 ÷ 전체 화소', 'red'),
              L('faz', 'FAZ 면적·원형도', c.mask(faz, COLOURS['yellow'], 90),
                [('ft_faz_area', octa.faz_area(faz)), ('ft_faz_circularity', octa.faz_shape(faz))],
                'octa.faz_detect · faz_area · faz_shape', '슬랩 가운데 가장 어두운 점에서 이어진 혈류 없는 영역(Otsu 이진화 후 닫힘, 반지름 제한)', 'yellow')]
    ex = dict(id='ex_octa_scp', modality='octa', modality_label='OCTA', region='황반 표층 모세혈관망',
              title='OCTA · 황반 표층 혈관망', source='feng2024', source_file='retinal_atlas_modality_figures/octa_scp.jpg',
              caption='OCTA 표층 슬랩입니다. 혈류 이진화와 FAZ 검출(단순 규칙)을 거쳐 OCTA 측정 함수를 실행했습니다. 화소 단위입니다.')
    return write_example(ex, c, layers)


# ---------------------------------------------------------------- shared helpers for the extended examples

from scipy import ndimage  # noqa: E402
from skimage import morphology as skmorph  # noqa: E402
from retinal_measures import choroid, image as rm_image  # noqa: E402
from retinal_measures._common import Spacing  # noqa: E402

MASKED = ROOT / 'resources/datasets/retinal_atlas_masked_figures'
PROVIDER = atlas_fig.ARTICLE_FIGURES / 'provider_figures'
OCT3D = ROOT / 'resources/datasets/public_amd/amd_dme_3d_oct/extracted/AMD_DME_3D_Dataset'
CC_BY = {'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/'}
EXTRA_SOURCES = registry.source_records()     # g_image_sources_v01.csv (modality figures are added on the fly)
NEW_PROVIDER = {name: row['sha256']             # g_provider_figures_v01.csv
                for name, row in registry.provider_figures_for('measurement_examples').items()}


def provider(name: str) -> Image.Image:
    if name in NEW_PROVIDER:
        if atlas_fig.sha256(PROVIDER / name) != NEW_PROVIDER[name]:
            raise ValueError(f'provider figure changed: {name}')
        return Image.open(PROVIDER / name).convert('RGB')
    return atlas_fig._paper_source(name)


def masked(fig_id: str):
    """Published atlas masked figure (base image, mask = overlay alpha > 0) reused as measurement input."""
    base = Image.open(MASKED / f'{fig_id}.jpg').convert('RGB')
    alpha = np.asarray(Image.open(MASKED / f'{fig_id}_mask.png').convert('RGBA'))[..., 3] > 0
    return base, alpha


def masked_source(fig_id: str) -> tuple[str, str]:
    rec = next(f for f in json.loads((PROJECT / 'packages/retinal-atlas-web/src/retinal_atlas_web/data/masked_figures.json')
                                     .read_text(encoding='utf-8'))['figures'] if f['id'] == fig_id)
    return rec['source'], rec['source_file']


def dot(d, xy, r, colour, width=3, fill=False):
    x, y = xy
    if fill:
        d.ellipse((x - r, y - r, x + r, y + r), fill=colour + (255,))
    else:
        d.ellipse((x - r, y - r, x + r, y + r), outline=colour + (255,), width=width)


def poly(c, d, rows, colour, width=3, alpha=255, x0=0):
    pts = [c.p((r, x0 + i)) for i, r in enumerate(rows) if not np.isnan(r)]
    if len(pts) > 1:
        d.line(pts, fill=colour + (alpha,), width=width)


def surface_line(mask_line):
    """Per-column first row of a thin line mask (NaN where absent)."""
    m = np.asarray(mask_line, bool)
    rows = np.argmax(m, axis=0).astype(float)
    rows[~m.any(0)] = np.nan
    return rows


def trace_ilm_rpe(g, top=0, bottom=None, smooth=(2, 4), ilm_frac=0.35):
    """Simple per-column ILM (first strong rise) and RPE (brightest row) on a grayscale B-scan."""
    s = ndimage.gaussian_filter(np.asarray(g, float), smooth)
    bottom = bottom or s.shape[0]
    band = s[top:bottom]
    rpe = top + np.argmax(band, axis=0)
    rpe = ndimage.median_filter(rpe, 15).astype(float)
    thr = band.min(0) + ilm_frac * (band.max(0) - band.min(0))
    ilm = np.array([top + int(np.argmax(band[:, x] > thr[x])) for x in range(band.shape[1])], float)
    ilm = ndimage.median_filter(ilm, 9).astype(float)
    return ilm, rpe


def vessel_detail_layers(c, img, vessel, artery, vein, fov, dc, dr, fovea):
    """Extra vessel-geometry and whole-image layers on the AVSeg normal eye."""
    layers = []
    skel = skmorph.skeletonize(vessel)
    lay = c.mask(vessel, COLOURS['blue'], 90, 90)
    lay = c.mask(skmorph.binary_dilation(skel, skmorph.disk(1)), COLOURS['white'], 255, 255, layer=lay)
    layers.append(L('pixels', '혈관·중심선 화소 수', lay, [('ft_vessel_pixel_count', vessels.pixel_count(vessel))],
                    'vessels.pixel_count', '혈관 mask 화소(파랑)와 1화소 중심선 화소(흰색)의 원시 개수', 'blue'))
    lay = c.layer(); d = c.draw(lay)
    m = vessels.regional_density(vessel, fovea)
    rmax = float(np.hypot(*np.maximum(np.abs(np.array([0, 0]) - fovea), np.abs(np.array(vessel.shape) - fovea))))
    for k in (0.33, 0.66):
        x, y = c.p(fovea); rr = k * rmax * c.scale
        d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=COLOURS['yellow'] + (230,), width=2)
    x, y = c.p(fovea)
    d.line((0, y, c.size[0], y), fill=COLOURS['yellow'] + (230,), width=2); d.line((x, 0, x, c.size[1]), fill=COLOURS['yellow'] + (230,), width=2)
    lay = c.mask(vessel, COLOURS['cyan'], 110, 110, layer=lay)
    layers.append(L('regional', '구역별 혈관 점유율', lay, [('ft_vessel_regional_density', m)], 'vessels.regional_density',
                    '중심와를 지나는 노란 십자로 위·아래·왼쪽·오른쪽, 노란 고리로 안·가운데·바깥 구역을 나눠 혈관 비율 계산', 'yellow'))
    labels, n = ndimage.label(vessel, structure=np.ones((3, 3)))
    sizes = np.bincount(labels.ravel()); sizes[0] = 0
    big = labels == sizes.argmax()
    lay = c.mask(big, COLOURS['green'], 160, 160)
    lay = c.mask(vessel & ~big, COLOURS['red'], 230, 230, layer=lay)
    layers.append(L('connect', '혈관 연결성', lay, [('ft_vessel_connectivity', vessels.connectivity(vessel))],
                    'vessels.connectivity', '가장 큰 연결 덩어리(초록)와 떨어진 조각(빨강), 분지점/끝점 비', 'green'))
    lay = c.layer(); d = c.draw(lay)
    sk = skel.astype(float)
    gr = ndimage.sobel(ndimage.gaussian_filter(sk, 1.5), 0); gc = ndimage.sobel(ndimage.gaussian_filter(sk, 1.5), 1)
    hues = [COLOURS[k] for k in ('red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'magenta', 'red')]
    for r, q in np.argwhere(skel)[::6]:
        theta = (math.degrees(math.atan2(gr[r, q], gc[r, q])) + 90) % 180
        col = hues[int(theta / 180 * 7)]
        t = math.radians(theta); dx, dy = 4 * math.cos(t), 4 * math.sin(t)
        x, y = c.p((r, q)); d.line((x - dx, y - dy, x + dx, y + dy), fill=col + (255,), width=2)
    layers.append(L('orient', '혈관 방향 분포', lay, [('ft_vessel_orientation', vessels.orientation(vessel))], 'vessels.orientation',
                    '중심선 각 점의 진행 방향(0–180°)을 색으로 표시; 12구간 분포의 엔트로피와 최빈 방향 비율', 'orange'))
    segments, _, _ = vessels._segments(skel)
    lay = c.layer(); d = c.draw(lay)
    for i, seg in enumerate(s for s in segments if len(s) >= 5):
        col = (COLOURS['magenta'], COLOURS['cyan'], COLOURS['yellow'])[i % 3]
        for r, q in seg[::2]:
            x, y = c.p((r, q)); d.point((x, y), fill=col + (255,))
        x, y = c.p(seg[len(seg) // 2]); d.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill=col + (255,))
    lay = Image.fromarray(np.asarray(lay)).filter(__import__('PIL.ImageFilter', fromlist=['MaxFilter']).MaxFilter(3))
    layers.append(L('path', '혈관 경로 길이', lay, [('ft_vessel_path_length', vessels.path_length(vessel))], 'vessels.path_length',
                    '분지점 사이 중심선 분절(색을 번갈아 표시)마다 길이를 재어 평균·합계', 'magenta'))
    nb = vessels._neighbour_count(skel)
    lay = c.layer(); d = c.draw(lay)
    jl, nj = ndimage.label(skel & (nb >= 3), structure=np.ones((3, 3)))
    for k in range(1, nj + 1):
        r, q = np.argwhere(jl == k).mean(0)
        dot(d, c.p((r, q)), 5, COLOURS['yellow'], 2)
    layers.append(L('branch', '분지각', lay, [('ft_branching_angle', vessels.branching_angle(vessel))], 'vessels.branching_angle',
                    '분지점(노란 원)마다 중심선을 따라 8 px 떨어진 세 가지 끝을 잇는 각 중 딸가지 사이 각', 'yellow'))
    dist = ndimage.distance_transform_edt(vessel)
    width = np.where(skel, 2 * dist - 1, 0)
    lay = c.layer(); d = c.draw(lay)
    wmax = np.percentile(width[skel], 95)
    for r, q in np.argwhere(skel)[::2]:
        t = min(width[r, q] / wmax, 1)
        col = (int(56 + t * 192), int(189 - t * 76), int(248 - t * 135))
        x, y = c.p((r, q)); d.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill=col + (255,))
    layers.append(L('caliber', '혈관 국소 폭·폭 변동', lay, [('ft_vessel_caliber', vessels.caliber(vessel)),
                                                       ('ft_vessel_caliber_variability', vessels.caliber_variability(vessel))],
                    'vessels.caliber · caliber_variability', '중심선 각 점에서 경계까지 거리 × 2 − 1 = 국소 폭(가는 하늘색 → 굵은 빨강); 표준편차/평균 = 변동', 'red'))
    rgb = np.asarray(img)
    lay = c.mask(fov, COLOURS['white'], 0, 230)
    layers.append(L('image', '영상 색·품질·질감', lay,
                    [('ft_image_color_stats', rm_image.color_stats(rgb, fov=fov),
                      ' · '.join(f"{k.upper()} 평균 {v['mean']:.0f}" for k, v in rm_image.color_stats(rgb, fov=fov).value.items())),
                     ('ft_image_quality', rm_image.quality(rgb, fov=fov),
                      '선명도 {sharpness:.4f} · 대비 {contrast:.3f} · 조명 변동 {illumination_cv:.3f} · 어두움 {dark_fraction:.1%} · 과노출 {bright_fraction:.1%}'
                      .format(**rm_image.quality(rgb, fov=fov).detail)),
                     ('ft_image_texture', rm_image.texture(rgb, fov=fov))],
                    'image.color_stats · quality · texture', '촬영 시야(흰 윤곽) 전체의 채널 평균, 라플라시안 분산(선명도), GLCM 질감', 'white'))
    lay = c.layer(); d = c.draw(lay)
    dot(d, c.p(fovea), 0.35 * dr * c.scale, COLOURS['yellow'], 2)
    layers.append(R('reflex', '중심와 반사', lay, 'ft_foveal_reflex',
                    '판독 항목(계산 코드 없음) · 노란 원 안 작은 반짝임이 있는지 판정; 이 영상에서는 희미하게 보임',
                    '중심와 한가운데의 반사점을 판독자가 봄(소실 = 부종·위축 의심). 자동 판정 코드는 없음', 'yellow'))
    lay = c.layer(); d = c.draw(lay)
    for k in (1.0, 2.5):
        x, y = c.p(dc); rr = k * dr * c.scale
        d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=COLOURS['green'] + (220,), width=2)
    layers.append(R('striation', '신경섬유 줄무늬', lay, 'ft_rnfl_striation',
                    '판독 항목(계산 코드 없음) · 초록 고리 사이(유두 둘레)에서 밝은 줄무늬가 고르게 보이는지 판정',
                    '유두 둘레의 가는 밝은 줄(신경섬유층 반사)을 판독자가 봄(쐐기 모양 소실 = 결손). 자동 판정 코드는 없음', 'green'))
    return layers


# ---------------------------------------------------------------- fundus: common lesion measures (IDRiD_31 hemorrhage)

def idrid31():
    image_id = 'IDRiD_31'
    lab = np.array(Image.open(atlas_fig.REFINED / f'Labels/{image_id}_vessel.png'))
    suffix = 'png' if (atlas_fig.REFINED / f'Images/{image_id}.png').exists() else 'jpg'
    img = Image.open(atlas_fig.REFINED / f'Images/{image_id}.{suffix}').convert('RGB')
    fovea = np.argwhere(lab == 16).mean(0)
    disc_m = lab == 32
    disc = np.argwhere(disc_m).mean(0)
    ys, xs = np.where(disc_m)
    dd = float(max(np.ptp(ys), np.ptp(xs)))
    return dict(lab=lab, img=img, suffix=suffix, fovea=fovea, disc=disc, dd=dd, hem=lab == 127, ma=lab == 255,
                ex=lab == 63, vessel=lab == 24, fov=lab > 0, image_id=image_id)


def lesion_shape_example() -> dict:
    s = idrid31()
    c = Canvas(s['img'])
    hem, ma = s['hem'], s['ma']
    layers = [L('presence', '병변 존재·개수(출혈·미세동맥류)', c.mask(ma, COLOURS['red'], 200, 255, layer=c.mask(hem, COLOURS['orange'], 90)),
                [('ft_lesion_generic_presence', lesions.presence(hem)), ('ft_ma_presence', lesions.presence(ma, feature_id='ft_ma_presence')),
                 ('ft_lesion_generic_count', lesions.count(hem))],
                'lesions.presence · count', '공급자 mask에 연결 성분이 하나라도 있으면 "예"(주황 = 출혈, 빨강 = 미세동맥류); 출혈 연결 성분 수', 'orange'),
              L('area', '병변 면적(출혈)', c.mask(hem, COLOURS['orange'], 120), [('ft_lesion_generic_area', lesions.area(hem))],
                'lesions.area', '출혈 mask 화소 수', 'orange')]
    labels, n = ndimage.label(hem)
    sizes = ndimage.sum(hem, labels, range(1, n + 1))
    order = np.argsort(sizes)
    lay = c.layer()
    for rank, k in enumerate(order):
        t = rank / max(n - 1, 1)
        col = (int(56 + t * 192), int(189 - t * 76), int(248 - t * 135))
        lay = c.mask(labels == k + 1, col, 170, 255, layer=lay)
    layers.append(L('sizes', '병변 크기 분포', lay, [('ft_lesion_size_distribution', lesions.size_distribution(hem))],
                    'lesions.size_distribution', '출혈 조각별 면적(작은 하늘색 → 큰 빨강)의 평균·중앙·90백분위·최대·변동계수', 'cyan'))
    from skimage import measure as skm
    lay = c.mask(hem, COLOURS['magenta'], 60)
    d = c.draw(lay)
    for p in skm.regionprops(labels):
        if p.area < 5:
            continue
        r0, c0, r1, c1 = p.bbox
        d.rectangle([c.p((r0, c0)), c.p((r1, c1))], outline=COLOURS['magenta'] + (230,), width=1)
    layers.append(L('shape', '병변 형태', lay, [('ft_lesion_generic_shape', lesions.shape(hem))], 'lesions.shape',
                    '5 px 이상 조각마다 원형도(4πA/P²)·이심률·충실도를 면적 가중 평균', 'magenta'))
    best = max(skm.regionprops(labels), key=lambda p: p.feret_diameter_max)
    pts = np.argwhere(labels == best.label)
    from scipy.spatial import ConvexHull
    hv = pts[ConvexHull(pts).vertices]
    dmat = np.hypot(*(hv[:, None] - hv[None]).transpose(2, 0, 1))
    i, j = np.unravel_index(dmat.argmax(), dmat.shape)
    lay = c.mask(labels == best.label, COLOURS['yellow'], 120)
    d = c.draw(lay)
    d.line([c.p(hv[i]), c.p(hv[j])], fill=COLOURS['white'] + (255,), width=3)
    layers.append(L('extent', '병변 범위 길이', lay, [('ft_lesion_generic_extent', lesions.extent(hem))], 'lesions.extent',
                    '조각마다 최대 Feret 지름(가장 먼 두 점 거리) 중 최댓값 — 흰 선', 'yellow'))
    layers.append(R('depth', '출혈 깊이', c.mask(hem, COLOURS['red'], 0, 230), 'ft_hem_depth',
                    '판독 항목(계산 코드 없음) · 둥근 점·얼룩 모양 = 깊은 층, 화염 모양 = 신경섬유층; 이 영상은 대부분 점·얼룩 출혈',
                    '출혈 모양(빨강 윤곽)으로 판독자가 층을 추정; 확정은 OCT. 자동 판정 코드는 없음', 'red'))
    layers.append(R('he_pattern', '삼출물 배열', c.mask(s['ex'], COLOURS['yellow'], 120), 'ft_he_pattern',
                    '판독 항목(계산 코드 없음) · 흩어짐/고리(윤상)/별 모양 배열을 판정; 이 영상은 황반 주위에 흩어진 무리',
                    '경성삼출물(노랑)의 배열을 판독자가 봄. 자동 판정 코드는 없음', 'yellow'))
    lay = c.mask(hem, COLOURS['orange'], 80)
    lay = c.mask(ma, COLOURS['red'], 200, layer=lay)
    lay = c.mask(s['ex'], COLOURS['yellow'], 110, layer=lay)
    layers.append(R('grade', '소견 정도(공통)', lay, 'ft_lesion_generic_grade',
                    '판독 항목(계산 코드 없음) · 표준 사진과 비교해 경도/중등도/고도로 판정',
                    '병변 전체(출혈·미세동맥류·삼출물)를 판독자가 표준 사진과 비교. 자동 판정 코드는 없음', 'orange'))
    ex = dict(id='ex_fundus_lesion_shape', modality='cfp', modality_label='안저', region='병변 크기·형태(공통)',
              title='안저 · 병변 크기·형태(공통)', source='refined_idrid', source_file=f"Train/Images/{s['image_id']}.{s['suffix']}",
              caption='당뇨망막병증 눈의 공급자 출혈 mask를 "병변"의 예로 써서 여러 병변에 공통으로 쓰는 크기·형태 함수를 실행했습니다. '
                      '같은 함수가 다른 병변 mask에도 그대로 쓰입니다. 화소 단위입니다.')
    return write_example(ex, c, layers)


def lesion_place_example() -> dict:
    s = idrid31()
    c = Canvas(s['img'])
    hem, fovea, disc, dd = s['hem'], s['fovea'], s['disc'], s['dd']
    layers = []
    lay = c.mask(hem, COLOURS['orange'], 80)
    d = c.draw(lay)
    rows, cols = np.nonzero(hem)
    x, y = c.p((rows.mean(), cols.mean()))
    d.line((x - 14, y, x + 14, y), fill=COLOURS['white'] + (255,), width=3); d.line((x, y - 14, x, y + 14), fill=COLOURS['white'] + (255,), width=3)
    layers.append(L('position', '병변 위치 좌표', lay, [('ft_lesion_generic_position', lesions.position(hem))], 'lesions.position',
                    '출혈 mask 무게중심(흰 십자)을 영상 높이·너비에 대한 비율로', 'white'))
    lay = c.mask(hem, COLOURS['orange'], 80)
    d = c.draw(lay)
    for k in (1, 2, 3):
        x, y = c.p(fovea); rr = k * dd * c.scale
        d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=COLOURS['cyan'] + (200,), width=2)
    pts = np.argwhere(hem)
    near = pts[np.argmin(np.hypot(*(pts - fovea).T))]
    d.line([c.p(fovea), c.p(near)], fill=COLOURS['white'] + (255,), width=3)
    layers.append(L('radial', '중심와 기준 거리', lay, [('ft_lesion_radial_position', lesions.radial_position(hem, fovea, disc_diameter_px=dd)),
                                                   ('ft_lesion_fovea_distance', lesions.fovea_distance(hem, fovea, disc_diameter_px=dd))],
                    'lesions.radial_position · fovea_distance', '하늘색 고리 = 중심와에서 1·2·3 유두지름; 흰 선 = 가장 가까운 출혈. 평균·최소·중앙 거리(DD)', 'cyan'))
    lay = c.mask(hem & (np.hypot(*(np.indices(hem.shape) - fovea[:, None, None])) <= 2 * dd), COLOURS['green'], 170)
    lay = c.mask(hem & (np.hypot(*(np.indices(hem.shape) - fovea[:, None, None])) > 2 * dd), COLOURS['orange'], 80, layer=lay)
    d = c.draw(lay); x, y = c.p(fovea); rr = 2 * dd * c.scale
    d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=COLOURS['green'] + (230,), width=3)
    layers.append(L('regional', '구역별 병변 비율', lay, [('ft_lesion_regional_fraction', lesions.regional_fraction(hem, fovea, 2 * dd))],
                    'lesions.regional_fraction', '출혈 면적 중 중심와 2 유두지름 원(초록) 안에 든 비율', 'green'))
    axis = (disc - fovea) / np.linalg.norm(disc - fovea)
    normal = np.array([-axis[1], axis[0]])
    q = lesions.quadrant_of(np.argwhere(hem), fovea, disc)
    lay = c.layer()
    for name, col in zip(lesions.QUADRANTS, (COLOURS['cyan'], COLOURS['magenta'], COLOURS['yellow'], COLOURS['green'])):
        m = np.zeros_like(hem); pts = np.argwhere(hem)[q == name]
        m[tuple(pts.T)] = True
        lay = c.mask(m, col, 200, 255, layer=lay)
    d = c.draw(lay)
    for v in (axis, normal):
        d.line([c.p(fovea - 3000 * v), c.p(fovea + 3000 * v)], fill=COLOURS['white'] + (220,), width=2)
    layers.append(L('quadrant', '사분면 분산·침범 수', lay,
                    [('ft_lesion_spatial_dispersion', lesions.spatial_dispersion(hem, fovea, disc)),
                     ('ft_vascular_change_extent', lesions.quadrant_occupancy(hem, fovea, disc))],
                    'lesions.spatial_dispersion · quadrant_occupancy', '유두–중심와 축(흰 선)으로 나눈 네 사분면별 출혈(색별): 면적 비율의 엔트로피(0–2비트)와 병변 있는 사분면 수', 'magenta'))
    from skimage import measure as skm
    labels = skm.label(hem)
    props = skm.regionprops(labels)
    cent = np.array([p.centroid for p in props])
    dm = np.hypot(*(cent[:, None] - cent[None]).transpose(2, 0, 1)); np.fill_diagonal(dm, np.inf)
    lay = c.layer(); d = c.draw(lay)
    for i, j in enumerate(dm.argmin(1)):
        d.line([c.p(cent[i]), c.p(cent[j])], fill=COLOURS['yellow'] + (230,), width=2)
    for p in cent:
        dot(d, c.p(p), 3, COLOURS['orange'], fill=True)
    layers.append(L('distribution', '병변 분포 양상', lay, [('ft_lesion_generic_distribution', lesions.distribution_pattern(hem, fov=s['fov']))],
                    'lesions.distribution_pattern', '조각 중심(주황 점)마다 가장 가까운 이웃(노란 선) 거리의 평균 ÷ 무작위 기대값 = Clark–Evans R', 'yellow'))
    near = ndimage.distance_transform_edt(~s['vessel']) <= 10
    lay = c.mask(s['vessel'], COLOURS['cyan'], 120, 120)
    lay = c.mask(hem & near, COLOURS['red'], 220, layer=lay)
    lay = c.mask(hem & ~near, COLOURS['orange'], 90, layer=lay)
    layers.append(L('vessel', '병변–혈관 거리', lay, [('ft_lesion_vessel_relation', lesions.vessel_relation(hem, s['vessel']))],
                    'lesions.vessel_relation', '공급자 혈관 mask(하늘색)까지 출혈 화소의 평균 거리, 10 px 이내(빨강) 비율', 'cyan'))
    ex = dict(id='ex_fundus_lesion_place', modality='cfp', modality_label='안저', region='병변 위치·분포(공통)',
              title='안저 · 병변 위치·분포(공통)', source='refined_idrid', source_file=f"Train/Images/{s['image_id']}.{s['suffix']}",
              caption='같은 당뇨망막병증 눈의 공급자 출혈 mask와 중심와·유두·혈관 라벨로 병변 공통 위치·분포 함수를 실행했습니다. '
                      '거리는 유두지름(DD) 단위입니다.')
    return write_example(ex, c, layers)


# ---------------------------------------------------------------- fundus: proliferative changes (Refined IDRiD)

def fundus_nv_example() -> dict:
    image_id = 'IDRiD_27'
    lab = np.array(Image.open(atlas_fig.REFINED / f'Labels/{image_id}_vessel.png'))
    suffix = 'png' if (atlas_fig.REFINED / f'Images/{image_id}.png').exists() else 'jpg'
    img = Image.open(atlas_fig.REFINED / f'Images/{image_id}.{suffix}').convert('RGB')
    nv = ndimage.binary_closing(lab == 166, iterations=2) | (lab == 166)
    disc_m = lab == 32
    ys, xs = np.where(disc_m)
    dd = float(max(np.ptp(ys), np.ptp(xs)))
    dist = ndimage.distance_transform_edt(~disc_m)
    labels, n = ndimage.label(nv)
    nvd = np.isin(labels, [k for k in range(1, n + 1) if dist[labels == k].min() <= dd])
    nve = nv & ~nvd
    c = Canvas(img)
    ring = c.mask((dist > 0) & (dist <= dd), COLOURS['white'], 0, 200)
    layers = [L('nvd', 'NVD 범위·존재', c.mask(nvd, COLOURS['red'], 150, layer=ring),
                [('ft_nvd_area', lesions.area(nvd, feature_id='ft_nvd_area')), ('ft_nvd_presence', lesions.presence(nvd, feature_id='ft_nvd_presence'))],
                'lesions.area · presence', '공급자 신생혈관 mask 중 유두 경계에서 1 유두지름(흰 윤곽) 안에 닿는 조각', 'red'),
              L('nve', 'NVE 범위·존재', c.mask(nve, COLOURS['magenta'], 150, layer=ring),
                [('ft_nve_area', lesions.area(nve, feature_id='ft_nve_area')), ('ft_nve_presence', lesions.presence(nve, feature_id='ft_nve_presence'))],
                'lesions.area · presence', '같은 mask에서 1 유두지름 밖 조각', 'magenta')]
    ex = dict(id='ex_fundus_nv', modality='cfp', modality_label='안저', region='신생혈관(NVD·NVE)',
              title='안저 · 증식성 신생혈관', source='refined_idrid', source_file=f'Train/Images/{image_id}.{suffix}',
              caption='증식 당뇨망막병증 눈입니다. 공급자 전문가 신생혈관 mask를 유두에서의 거리(1 유두지름)로 NVD·NVE로 나눠 '
                      '면적·존재 함수를 실행했습니다. 화소 단위입니다.')
    return write_example(ex, c, layers)


def fundus_irma_example() -> dict:
    image_id = 'IDRiD_17'
    lab = np.array(Image.open(atlas_fig.REFINED / f'Labels/{image_id}_vessel.png'))
    suffix = 'png' if (atlas_fig.REFINED / f'Images/{image_id}.png').exists() else 'jpg'
    img = Image.open(atlas_fig.REFINED / f'Images/{image_id}.{suffix}').convert('RGB')
    irma = ndimage.binary_closing(lab == 96, iterations=2) | (lab == 96)
    vh = ndimage.binary_closing(lab == 4, iterations=2) | (lab == 4)
    fovea = np.argwhere(lab == 16).mean(0) if (lab == 16).any() else None
    disc = np.argwhere(lab == 32).mean(0)
    c = Canvas(img)
    lay = c.mask(irma, COLOURS['yellow'], 170)
    d = c.draw(lay)
    for comp in ndimage.find_objects(ndimage.label(irma)[0]):
        r = (comp[0].start + comp[0].stop) / 2; q = (comp[1].start + comp[1].stop) / 2
        dot(d, c.p((r, q)), 14, COLOURS['yellow'], 3)
    if fovea is not None:
        axis = (disc - fovea) / np.linalg.norm(disc - fovea); normal = np.array([-axis[1], axis[0]])
        for v in (axis, normal):
            d.line([c.p(fovea - 3000 * v), c.p(fovea + 3000 * v)], fill=COLOURS['white'] + (200,), width=2)
    layers = [L('irma', 'IRMA 존재·침범 사분면', lay,
                [('ft_irma_presence', lesions.presence(irma, feature_id='ft_irma_presence')),
                 ('ft_irma_quadrants', lesions.quadrant_occupancy(irma, fovea, disc, feature_id='ft_irma_quadrants'))],
                'lesions.presence · quadrant_occupancy', '공급자 IRMA mask(노란 원); 유두–중심와 축(흰 선)으로 나눈 사분면 중 IRMA가 있는 수', 'yellow'),
              R('vh', '유리체 출혈 가림 정도', c.mask(vh, COLOURS['red'], 90), 'ft_vh_obscuration',
                f'판독 항목(계산 코드 없음) · 출혈(빨강)이 혈관·유두를 얼마나 가리는지 판정; 공급자 mask는 촬영 시야의 {vh.sum() / (lab > 0).sum():.0%}',
                '공급자 유리체 출혈 mask를 보여 줌; 가림 정도(가벼움/중간/심함) 판정 코드는 없음', 'red')]
    ex = dict(id='ex_fundus_irma', modality='cfp', modality_label='안저', region='IRMA·유리체 출혈',
              title='안저 · IRMA·유리체 출혈', source='refined_idrid', source_file=f'Train/Images/{image_id}.{suffix}',
              caption='증식 당뇨망막병증 눈입니다. 공급자 전문가 IRMA·유리체 출혈 mask와 중심와·유두 라벨을 입력으로 썼습니다.')
    return write_example(ex, c, layers)


def fundus_vb_example() -> dict:
    base, ring = masked('paper_venous_beading')
    g = np.asarray(base, float)[..., 1]
    ys, xs = np.nonzero(ring)
    cy, cx = ys.mean(), xs.mean()
    rr = np.hypot(ys - cy, xs - cx).max()
    yy, xx = np.indices(g.shape)
    roi = np.hypot(yy - cy, xx - cx) <= rr * 1.6
    bh = skmorph.black_tophat(ndimage.gaussian_filter(g, 1.2), skmorph.disk(9))
    vein = (bh > np.percentile(bh[roi], 82)) & roi
    vein = skmorph.remove_small_objects(skmorph.binary_closing(vein, skmorph.disk(1)), 60)
    labels, n = ndimage.label(vein)
    if n:
        sizes = ndimage.sum(vein, labels, range(1, n + 1)); vein = labels == (sizes.argmax() + 1)
    sm = ndimage.gaussian_filter(g, 15)
    disc = np.unravel_index(sm.argmax(), sm.shape)
    band = sm.copy(); band[:, :int(disc[1]) + 150] = np.inf; band[:, int(disc[1]) + 420:] = np.inf
    band[:int(disc[0]) - 120] = np.inf; band[int(disc[0]) + 120:] = np.inf
    fovea = np.unravel_index(band.argmin(), band.shape)
    c = Canvas(base)
    lay = c.mask(vein, COLOURS['cyan'], 170)
    d = c.draw(lay)
    dot(d, c.p((cy, cx)), rr * 1.6 * c.scale, COLOURS['white'], 2)
    lay2 = c.mask(vein, COLOURS['magenta'], 170)
    d2 = c.draw(lay2)
    axis = (np.array(disc) - fovea) / np.linalg.norm(np.array(disc) - fovea); normal = np.array([-axis[1], axis[0]])
    for v in (axis, normal):
        d2.line([c.p(np.array(fovea) - 3000 * v), c.p(np.array(fovea) + 3000 * v)], fill=COLOURS['white'] + (200,), width=2)
    dot(d2, c.p(disc), 10, COLOURS['yellow'], 3); dot(d2, c.p(fovea), 10, COLOURS['red'], 3)
    layers = [L('caliber', '정맥 구경 변동', lay, [('ft_vb_caliber_variation', vessels.caliber_variation(vein))], 'vessels.caliber_variation',
                '저자 화살표 2번 둘레(흰 원)의 정맥을 녹색 채널 블랙햇으로 분할(하늘색, 서비스 추정); 분절별 최대/최소 폭과 변동계수', 'cyan'),
              L('quadrant', '정맥 구슬모양 침범 사분면', lay2, [('ft_vb_quadrants', lesions.quadrant_occupancy(vein, fovea, disc, feature_id='ft_vb_quadrants'))],
                'lesions.quadrant_occupancy', '유두(노랑)·중심와(빨강, 가장 어두운 점으로 추정)를 잇는 축으로 나눈 사분면 중 표시 정맥이 있는 수', 'magenta')]
    src, file = masked_source('paper_venous_beading')
    ex = dict(id='ex_fundus_vb', modality='cfp', modality_label='안저', region='정맥 구슬모양 변화',
              title='안저 · 정맥 구슬모양 변화', source=src, source_file=file,
              caption='저자가 정맥 구슬모양 변화로 표시한 자리(2번 화살표)의 정맥을 서비스가 분할해 구경 변동 함수를 실행했습니다. '
                      '분할·중심와 위치는 서비스 추정이며 화소 단위입니다(표시용 2배 확대 그림 기준).')
    return write_example(ex, c, layers)


def fundus_small_examples() -> list[dict]:
    """One-photo examples for single lesions shown in published CC BY figures (masks reused from the atlas)."""
    out = []
    # disc hemorrhage location
    base, hem = masked('paper_disc_hemorrhage')
    disc = (165.0, 200.0)   # vessel convergence point read on the figure (service estimate)
    c = Canvas(base, 600)
    lay = c.mask(hem, COLOURS['red'], 110)
    d = c.draw(lay)
    x, y = c.p(disc)
    rr = 120 * c.scale
    for h in range(12):
        t = math.radians(h * 30)
        d.line((x + 0.85 * rr * math.sin(t), y - 0.85 * rr * math.cos(t), x + rr * math.sin(t), y - rr * math.cos(t)), fill=COLOURS['white'] + (230,), width=2)
    d.text((x - 5, y - rr - 14), '12', fill=(255, 255, 255, 255))
    rows, cols = np.nonzero(hem)
    d.line([c.p(disc), c.p((rows.mean(), cols.mean()))], fill=COLOURS['yellow'] + (255,), width=3)
    dot(d, c.p(disc), 5, COLOURS['white'], fill=True)
    src, file = masked_source('paper_disc_hemorrhage')
    out.append(write_example(dict(id='ex_fundus_disc_hem', modality='cfp', modality_label='안저', region='유두 출혈',
                                  title='안저 · 유두 출혈 위치', source=src, source_file=file,
                                  caption='유두와 그 둘레 출혈입니다. 출혈은 서비스 색 규칙 mask(아틀라스 그림과 같음), 유두 중심은 혈관이 모이는 점으로 서비스가 읽었습니다. '
                                          '눈 방향 정보가 없어 오른눈으로 가정했습니다.'), c,
                             [L('clock', '유두 출혈 위치(시계 방향)', lay, [('ft_disc_hem_location', lesions.clock_hour(hem, disc))], 'lesions.clock_hour',
                                '유두 중심(흰 점)에서 출혈 무게중심(노란 선) 방향을 시계 시각으로(12시 = 위)', 'red')]))
    # flame hemorrhages
    base, flame = masked('paper_flame_hemorrhage')
    c = Canvas(base)
    m = lesions.count(flame, min_area_px=20, feature_id='ft_flame_hem_count')
    src, file = masked_source('paper_flame_hemorrhage')
    out.append(write_example(dict(id='ex_fundus_flame', modality='cfp', modality_label='안저', region='화염상 출혈',
                                  title='안저 · 화염상 출혈', source=src, source_file=file,
                                  caption='망막정맥폐쇄 눈의 신경섬유층 출혈입니다. 출혈 mask는 서비스 색 규칙(빨강/녹색 비) 추정이라 붙은 출혈이 한 덩어리로 셀 수 있습니다.'), c,
                             [L('count', '화염상 출혈 개수', c.mask(flame, COLOURS['orange'], 110), [('ft_flame_hem_count', m)], 'lesions.count',
                                '출혈 mask의 20 px 이상 연결 성분 수(주황)', 'orange')]))
    # laser scars
    base, scar = masked('paper_laser_scar')
    c = Canvas(base)
    src, file = masked_source('paper_laser_scar')
    out.append(write_example(dict(id='ex_fundus_laser', modality='cfp', modality_label='안저', region='레이저 반흔',
                                  title='안저 · 범망막 광응고 반흔', source=src, source_file=file,
                                  caption='범망막 광응고 뒤 반흔입니다. 반흔 mask는 서비스 톱햇 규칙 추정입니다.'), c,
                             [L('scar', '레이저 반흔 범위', c.mask(scar, COLOURS['yellow'], 150),
                                [('ft_laser_scar_extent', lesions.count(scar, feature_id='ft_laser_scar_extent')),
                                 ('ft_lesion_generic_area', lesions.area(scar), f'면적 {int(scar.sum()):,} px²')],
                                'lesions.count', '반흔 점(노랑)의 연결 성분 수; 면적 합도 함께 표시', 'yellow')]))
    # preretinal hemorrhage on UWF
    base, prh = masked('uwf_preretinal')
    c = Canvas(base)
    src, file = masked_source('uwf_preretinal')
    out.append(write_example(dict(id='ex_uwf_prh', modality='uwf', modality_label='광각 안저', region='망막앞 출혈',
                                  title='광각 안저 · 망막앞 출혈', source=src, source_file=file,
                                  caption='증식 당뇨망막병증 광각 영상의 큰 출혈입니다. 출혈 mask는 서비스 영역 확장 추정입니다.'), c,
                             [L('prh', '망막앞 출혈 면적', c.mask(prh, COLOURS['red'], 120), [('ft_prh_area', lesions.area(prh, feature_id='ft_prh_area'))],
                                'lesions.area', '출혈 mask 화소 수', 'red')]))
    return out


def fundus_rd_example() -> dict:
    import pandas as pd
    name = 'P0058'
    img = Image.open(atlas_fig.PALM / f'Images/{name}.jpg').convert('RGB')
    rd = np.array(Image.open(atlas_fig.PALM / f'Lesion Masks/Detachment/{name}.bmp').convert('L')) < 128
    fx, fy = pd.read_excel(atlas_fig.PALM / 'Fovea Localization.xlsx').set_index('imgName').loc[f'{name}.jpg']
    fovea = (float(fy), float(fx))
    fov = rm_image.fov_mask(np.asarray(img))
    c = Canvas(img)
    lay = c.mask(rd, COLOURS['cyan'], 100)
    lay = c.mask(fov, COLOURS['white'], 0, 160, layer=lay)
    lay2 = c.mask(rd, COLOURS['cyan'], 60)
    d = c.draw(lay2); x, y = c.p(fovea)
    dot(d, (x, y), 9, COLOURS['red'], 3)
    d.line((x - 16, y, x + 16, y), fill=COLOURS['red'] + (255,), width=2); d.line((x, y - 16, x, y + 16), fill=COLOURS['red'] + (255,), width=2)
    layers = [L('extent', '박리 범위', lay, [('ft_rd_extent', lesions.field_fraction(rd, fov=fov))], 'lesions.field_fraction',
                '공급자 박리 mask(하늘색) ÷ 촬영 시야(흰 윤곽)', 'cyan'),
              L('macula', '황반 침범', lay2, [('ft_rd_macula_status', lesions.involves_point(rd, fovea, feature_id='ft_rd_macula_status'))],
                'lesions.involves_point', '공급자 중심와 좌표(빨간 표적)가 박리 mask 안에 있는지', 'red')]
    ex = dict(id='ex_fundus_rd', modality='cfp', modality_label='안저', region='망막박리',
              title='안저 · 망막박리', source='palm', source_file=f'Training/Images/{name}.jpg',
              caption='병적 근시 눈의 망막박리입니다. 공급자 전문가 박리 mask와 중심와 좌표를 입력으로 썼습니다.')
    return write_example(ex, c, layers)


def fundus_myopic_disc_example() -> dict:
    name = 'P0054'
    img = Image.open(atlas_fig.PALM / f'Images/{name}.jpg').convert('RGB')
    disc = np.array(Image.open(atlas_fig.PALM / f'Disc Masks/{name}.bmp').convert('L')) < 128
    atr = np.array(Image.open(atlas_fig.PALM / f'Lesion Masks/Atrophy/{name}.bmp').convert('L')) < 128
    dist = ndimage.distance_transform_edt(~disc)
    dr = math.sqrt(disc.sum() / math.pi)
    labels, n = ndimage.label(atr & ~disc)
    ppa = np.isin(labels, [k for k in range(1, n + 1) if dist[labels == k].min() <= 0.2 * dr])
    ys, xs = np.nonzero(disc | ppa)
    pad = int(2.2 * dr)
    box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, img.width), min(ys.max() + pad, img.height))
    crop = img.crop(box)
    disc, ppa = disc[box[1]:box[3], box[0]:box[2]], ppa[box[1]:box[3], box[0]:box[2]]
    c = Canvas(crop, 700)
    from skimage import measure as skm
    p = skm.regionprops(disc.astype(int))[0]
    lay = c.mask(disc, COLOURS['blue'], 60)
    d = c.draw(lay)
    cy0, cx0 = p.centroid
    for length, ang in ((p.major_axis_length, p.orientation), (p.minor_axis_length, p.orientation + math.pi / 2)):
        dy, dx = math.cos(ang) * length / 2, math.sin(ang) * length / 2
        d.line([c.p((cy0 - dy, cx0 - dx)), c.p((cy0 + dy, cx0 + dx))], fill=COLOURS['orange'] + (255,), width=3)
    layers = [L('tilt', '유두 장단축비·회전', lay, [('ft_disc_tilt_ratio', optic_disc.tilt_ratio(disc))], 'optic_disc.tilt_ratio',
                '공급자 유두 mask(파랑)에 맞춘 타원의 긴 축 ÷ 짧은 축(주황 선)과 긴 축 각도', 'orange'),
              L('ppa', '유두주위 위축 면적', c.mask(ppa, COLOURS['yellow'], 120), [('ft_ppa_area', optic_disc.ppa_area(ppa))], 'optic_disc.ppa_area',
                '공급자 위축 mask 중 유두 경계에 닿는(0.2 반지름 이내) 조각(노랑)의 화소 수', 'yellow')]
    ex = dict(id='ex_fundus_myopic_disc', modality='cfp', modality_label='안저', region='근시성 유두',
              title='안저 · 근시성 기울어진 유두', source='palm', source_file=f'Training/Images/{name}.jpg',
              caption='병적 근시 눈의 기울어진 유두입니다. 공급자 전문가 유두·위축 mask를 입력으로 썼습니다(유두 둘레만 잘라 표시).')
    return write_example(ex, c, layers)


def fundus_drusen_example() -> dict:
    name = '061_A'
    img = Image.open(atlas_fig.AVSEG / f'OrginalImages/Org/{name}.png').convert('RGB')
    lab = np.array(Image.open(atlas_fig.AVSEG / f'Fundus-AVSeg-7C-Mask/Labels/Org/{name}.png'))
    _, dru = masked('fundus_drusen_large')
    fovea = np.argwhere(lab == atlas_fig.AVSEG_LABELS['fovea']).mean(0)
    disc = lab == atlas_fig.AVSEG_LABELS['disc']
    dd = 2 * math.sqrt(skmorph.convex_hull_image(disc).sum() / math.pi)
    near = np.hypot(*(np.indices(dru.shape) - fovea[:, None, None])) <= 2 * dd
    c = Canvas(img)
    lay = c.mask(dru & near, COLOURS['yellow'], 170)
    lay = c.mask(dru & ~near, COLOURS['yellow'], 60, 120, layer=lay)
    d = c.draw(lay); x, y = c.p(fovea); rr = 2 * dd * c.scale
    d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=COLOURS['white'] + (220,), width=2)
    layers = [L('area', '드루젠 면적·최대 크기', lay,
                [('ft_drusen_area', lesions.area(dru & near, feature_id='ft_drusen_area')),
                 ('ft_drusen_max_size', lesions.extent(dru & near, feature_id='ft_drusen_max_size'))],
                'lesions.area · extent', '중심와 2 유두지름 원(흰색) 안 드루젠(진한 노랑)의 화소 수와 가장 큰 조각의 최대 지름', 'yellow')]
    ex = dict(id='ex_fundus_drusen', modality='cfp', modality_label='안저', region='드루젠',
              title='안저 · 드루젠', source='fundus_avseg_7c', source_file=f'OrginalImages/Org/{name}.png',
              caption='나이관련황반변성 눈입니다. 드루젠 mask는 서비스 톱햇 규칙 추정(아틀라스 그림과 같음), 중심와·유두는 공급자 라벨입니다.')
    return write_example(ex, c, layers)


def fa_widefield_example() -> dict:
    base, np_mask = masked('paper_nonperfusion')
    g = np.asarray(base.convert('L'), float)
    fov = ndimage.binary_fill_holes(ndimage.gaussian_filter(g, 4) > 12)
    fov = ndimage.binary_erosion(fov, iterations=6)
    c = Canvas(base)
    lay = c.mask(np_mask & fov, COLOURS['blue'], 120)
    lay = c.mask(fov, COLOURS['white'], 0, 170, layer=lay)
    area, index = octa.nonperfusion(np_mask, fov=fov)
    leak = ndimage.gaussian_filter(g, 3) > np.percentile(g[fov], 99.3)
    leak = skmorph.remove_small_objects(leak, 40)
    layers = [L('np', '무관류 면적·허혈 지수', lay, [('ft_nonperfusion_area', area), ('ft_ischemic_index', index)], 'octa.nonperfusion',
                '서비스 무관류 mask(파랑) 화소 수와, 그것이 판독 가능한 시야(흰 윤곽)에서 차지하는 비율', 'blue'),
              R('leak', '신생혈관 누출', c.mask(leak, COLOURS['yellow'], 0, 255), 'ft_nv_leakage',
                '판독 항목(계산 코드 없음) · 노란 윤곽의 흐릿하게 번지는 과형광이 후기에 커지는지 판정',
                '가장 밝은 0.7 % 영역을 위치 안내로만 표시; 누출 판정은 초기·후기 비교로 판독자가 함. 자동 판정 코드는 없음', 'yellow')]
    src, file = masked_source('paper_nonperfusion')
    ex = dict(id='ex_fa_widefield', modality='fa', modality_label='형광안저혈관조영', region='광각 무관류·누출',
              title='FA · 광각 무관류와 누출', source=src, source_file=file,
              caption='증식 당뇨망막병증 광각 형광안저혈관조영입니다. 무관류 mask는 서비스 밝기 규칙 추정(아틀라스 그림과 같음)이며 화소 단위입니다.')
    return write_example(ex, c, layers)


def fa_mnv_example() -> dict:
    late = Image.open(atlas_fig.ARTICLE_FIGURES / 'fa_late.jpg').convert('L')
    early = Image.open(atlas_fig.ARTICLE_FIGURES / 'fa_early.jpg').convert('L').resize(late.size)
    g = np.asarray(late, float); e = np.asarray(early, float)
    h, w = g.shape
    sm = ndimage.gaussian_filter(g, 2)
    yy, xx = np.indices(g.shape)
    roi = np.hypot(yy - 0.545 * h, xx - 0.565 * w) < 0.09 * w
    thr = np.percentile(sm[roi], 80)
    mnv = (sm > thr) & roi
    mnv = skmorph.remove_small_objects(skmorph.binary_closing(mnv, skmorph.disk(2)), 30)
    c = Canvas(late.convert('RGB'))
    mean_e, mean_l = float(e[mnv].mean()), float(g[mnv].mean())
    layers = [L('area', 'MNV 병변 면적', c.mask(mnv, COLOURS['magenta'], 110), [('ft_mnv_lesion_area', oct_lesions.enface_area(mnv[:, None, :], feature_id='ft_mnv_lesion_area'))],
                'oct_lesions.enface_area', '저자 삼각형 둘레 후기 과형광(상위 20 %)을 서비스가 분할(자홍)한 화소 수', 'magenta'),
              R('activity', 'MNV 활동성 징후', c.mask(mnv, COLOURS['yellow'], 0, 255), 'ft_mnv_activity',
                f'판독 항목(계산 코드 없음) · 초기→후기 과형광이 커지고 흐려지면 누출(활동성); 이 영역 평균 밝기 초기 {mean_e:.0f} → 후기 {mean_l:.0f}',
                '같은 눈 초기·후기 사진에서 같은 영역의 밝기 변화를 참고로 보여 줌; 활동성 판정은 판독자(OCT 액체 포함). 자동 판정 코드는 없음', 'yellow')]
    ex = dict(id='ex_fa_mnv', modality='fa', modality_label='형광안저혈관조영', region='황반 신생혈관',
              title='FA · 황반 신생혈관', source=_figure_source('fa_late.jpg'), source_file='retinal_atlas_modality_figures/fa_late.jpg',
              caption='황반 신생혈관 눈의 형광안저혈관조영 후기 사진입니다. 병변 분할은 서비스 밝기 규칙 추정이며 화소 단위입니다.')
    return write_example(ex, c, layers)


def _figure_source(file: str) -> str:
    """Source key for a modality figure (registered on the fly from its manifest record)."""
    rec = next(r for r in json.loads((atlas_fig.ARTICLE_FIGURES / 'source_manifest.json').read_text(encoding='utf-8')) if r['file'] == file)
    key = 'modality:' + file
    EXTRA_SOURCES[key] = {'name': rec['credit'], 'credit': rec['credit'] + f" {rec.get('panel', '')}".rstrip(), 'url': rec['article_url'],
                          'license': rec['license'], 'license_url': rec['license_url']}
    return key


def redfree_rnfl_example() -> dict:
    base, _ = masked('paper_rnfl_defect')
    g = np.asarray(base.convert('L'), float)
    sm = ndimage.gaussian_filter(g, 6)
    sub = sm.copy(); sub[:200] = 0; sub[420:] = 0; sub[:, :120] = 0; sub[:, 260:] = 0
    disc = np.array(np.unravel_index(sub.argmax(), sub.shape), float)
    radius = 55
    n = 360
    ang = np.radians(np.arange(n))
    rows = disc[0] - radius * np.sin(ang); cols = disc[1] + radius * np.cos(ang)
    gs = ndimage.gaussian_filter(g, 2)
    prof = ndimage.map_coordinates(gs, [rows, cols], order=1)
    prof = ndimage.uniform_filter1d(prof, 9, mode='wrap')
    ref = ndimage.uniform_filter1d(prof, 91, mode='wrap')      # broad (±45°) trend of the same eye as the reference
    m = optic_disc.rnfl_defect_angle(prof, normal_um=ref, fraction=0.9)
    c = Canvas(base)
    lay = c.layer(); d = c.draw(lay)
    low = prof < 0.9 * ref
    for k in range(n):
        col = COLOURS['red'] if low[k] else COLOURS['green']
        x, y = c.p((rows[k], cols[k])); d.ellipse((x - 2.5, y - 2.5, x + 2.5, y + 2.5), fill=col + (255,))
    dot(d, c.p(disc), 4, COLOURS['white'], fill=True)
    src, file = masked_source('paper_rnfl_defect')
    ex = dict(id='ex_redfree_rnfl', modality='cfp', modality_label='안저', region='신경섬유층 결손',
              title='무적색 안저 · 신경섬유층 결손', source=src, source_file=file,
              caption='무적색(red-free) 사진의 쐐기 모양 신경섬유층 결손입니다(저자 화살표). 함수는 원래 OCT 원형 두께(µm)를 받지만, 여기서는 '
                      '유두 둘레 고리의 밝기를 대신 넣어 같은 규칙을 보여 줍니다. 유두 중심·반지름은 서비스 추정입니다.')
    return write_example(ex, c, [L('defect', 'RNFL 결손 각도', lay, [('ft_rnfl_defect_angle', m)], 'optic_disc.rnfl_defect_angle',
                                   '유두 중심에서 반지름 55 px 고리의 밝기(1° 간격)가 ±45° 이동 평균의 90 % 미만(빨강)으로 이어진 가장 긴 호의 각도(가는 혈관 그림자도 짧은 빨강으로 잡힘)', 'red')])


def faf_example() -> dict:
    img = provider('iovs-67-8-46-f002.jpg').crop((642, 0, 800, 156))
    img = img.resize((img.width * 4, img.height * 4), Image.LANCZOS)
    g = ndimage.gaussian_filter(np.asarray(img.convert('L'), float), 3)
    yy, xx = np.indices(g.shape)
    field = (xx > 220) & ~((xx < 330) & (yy < 90))
    dark = (g < np.percentile(g[field], 22)) & field
    dark = skmorph.remove_small_objects(skmorph.binary_opening(dark, skmorph.disk(3)), 400)
    border = dark ^ ndimage.binary_dilation(dark, iterations=18)
    c = Canvas(img, 640)
    layers = [R('pattern', '자가형광 양상', c.mask(dark, COLOURS['blue'], 70), 'ft_faf_pattern',
                '판독 항목(계산 코드 없음) · 저하(검게) 영역(파랑 표시)과 주변 증가 반점을 보고 양상 분류; 저자 분류: 미만성 저하(DDAF)',
                '어두운 영역 표시는 위치 안내용 서비스 밝기 규칙(하위 22 %); 양상 분류 코드는 없음', 'blue'),
              R('junction', '위축 가장자리 자가형광 양상', c.mask(border, COLOURS['yellow'], 90), 'ft_faf_junctional_pattern',
                '판독 항목(계산 코드 없음) · 위축 가장자리 띠(노랑)의 증가 자가형광 모양(없음/띠/반점/미만)을 판정',
                '어두운 영역 바깥 18 px 띠를 판독 위치로 표시; 가장자리 양상 분류 코드는 없음', 'yellow')]
    ex = dict(id='ex_faf_pattern', modality='faf', modality_label='자가형광', region='위축 가장자리',
              title='FAF · 위축 가장자리 양상', source='corradetti2026_faf', source_file='provider_figures/iovs-67-8-46-f002.jpg',
              caption='나이관련황반변성 위축 눈의 청색광 자가형광(저자 패널 E, 4배 확대)입니다. 두 항목 모두 판독 항목으로, 계산 코드 없이 볼 위치만 표시합니다.')
    return write_example(ex, c, layers)


def nir_change_example() -> dict:
    fig = provider('iovs-67-8-46-f001.jpg')

    def lesion(box):
        im = fig.crop(box)
        a = np.asarray(im, float)
        gray = a.mean(2)
        greenish = a[..., 1] > a[..., 0] + 25
        yellowish = (a[..., 0] > 150) & (a[..., 1] > 130) & (a[..., 2] < 110)
        sm = ndimage.gaussian_filter(gray, 1)
        yy, xx = np.indices(gray.shape)
        m = (sm > 175) & ~greenish & ~ndimage.binary_dilation(yellowish, iterations=2) & (xx > 8) & (yy > 8)
        m = skmorph.remove_small_objects(skmorph.binary_closing(m, skmorph.disk(1)), 6)
        return im, m
    a_img, a = lesion((2, 190, 116, 298))
    b_img, b = lesion((390, 190, 504, 298))
    k = 4
    pair = Image.new('RGB', (a_img.width * 2 + 6, a_img.height), 'black')
    pair.paste(a_img, (0, 0)); pair.paste(b_img, (a_img.width + 6, 0))
    pair = pair.resize((pair.width * k, pair.height * k), Image.LANCZOS)
    both = np.zeros((a_img.height, a_img.width * 2 + 6), bool)
    both[:, :a_img.width] = a; both[:, a_img.width + 6:] = b
    both = np.kron(both, np.ones((k, k), bool))
    c = Canvas(pair, 900)
    growth = atrophy.growth_rate(a, b, interval_years=1.5)
    change = lesions.change(a, b, interval_years=1.5)
    lay = c.mask(both, COLOURS['yellow'], 120)
    layers = [L('growth', '위축 확장률', lay, [('ft_atrophy_growth_rate', growth)], 'atrophy.growth_rate',
                '두 시점 밝은 병변(노랑) 면적의 제곱근 차이 ÷ 1.5년(원 그림 화소 기준)', 'yellow'),
              L('change', '병변 변화량', c.mask(both, COLOURS['orange'], 120), [('ft_lesion_generic_change', change)], 'lesions.change',
                '기준(왼쪽) → 18개월(오른쪽) 병변 면적 차이와 연간 변화', 'orange')]
    ex = dict(id='ex_nir_change', modality='nir', modality_label='근적외선', region='두 시점 병변 변화',
              title='근적외선 · 18개월 병변 변화', source='corradetti2026', source_file='provider_figures/iovs-67-8-46-f001.jpg',
              caption='같은 눈의 기준(왼쪽)과 18개월 뒤(오른쪽) 근적외선 사진입니다(저자 Figure 1 둘째 줄, 4배 확대). 밝은 위축성 병변은 서비스 밝기 규칙 추정이며 '
                      '두 영상은 정합하지 않아 면적만 비교합니다. 자가형광 대신 근적외선을 쓴 예입니다.')
    return write_example(ex, c, layers)


def ma_turnover_example() -> dict:
    fig = provider('antioxidants-14-00244-g001.jpg')
    boxes = [(6, 40, 250, 196), (256, 40, 500, 196)]
    panels, marks, discs = [], [], []
    for box in boxes:
        im = fig.crop(box)
        a = np.asarray(im, float)
        white = (a.min(2) > 185)
        lab, n = ndimage.label(white)
        pts = []
        for k in range(1, n + 1):
            p = np.argwhere(lab == k)
            touches = p[:, 0].min() == 0 or p[:, 1].min() == 0 or p[:, 0].max() == a.shape[0] - 1 or p[:, 1].max() == a.shape[1] - 1
            if 4 <= len(p) <= 40 and not touches:
                tip = p[np.argmax(p[:, 0] - p[:, 1])]     # arrows point down-left: tip = lowest-left pixel
                pts.append(tip)
        yellow = (a[..., 0] > 150) & (a[..., 1] > 150) & (a[..., 2] < 120)
        sm = ndimage.gaussian_filter(yellow.astype(float), 3)
        sm[:, :40] = 0; sm[:, -40:] = 0; sm[:25] = 0
        discs.append(np.array(np.unravel_index(sm.argmax(), sm.shape), float))
        panels.append(im); marks.append(np.array(pts, float))
    shift = discs[1] - discs[0]
    shape = panels[0].size[::-1]

    def mask_of(points, offset):
        m = np.zeros(shape, bool)
        for r, q in points - offset:
            rr, cc = int(round(r)), int(round(q))
            if 0 <= rr < shape[0] and 0 <= cc < shape[1]:
                m[rr, cc] = True
        return ndimage.binary_dilation(m, iterations=4)
    before, after = mask_of(marks[0], 0), mask_of(marks[1], shift)
    m = lesions.turnover(before, after)
    k = 3
    pair = Image.new('RGB', (shape[1] * 2 + 6, shape[0]), 'black')
    pair.paste(panels[0], (0, 0)); pair.paste(panels[1], (shape[1] + 6, 0))
    pair = pair.resize((pair.width * k, pair.height * k), Image.LANCZOS)
    c = Canvas(pair, 1000)
    lay = c.layer(); d = c.draw(lay)
    for (r, q) in marks[0]:
        hit = after[min(int(r), shape[0] - 1), min(int(q), shape[1] - 1)] if 0 <= r < shape[0] and 0 <= q < shape[1] else False
        dot(d, c.p((r * k, q * k)), 6, COLOURS['green'] if hit else COLOURS['blue'], 3)
    for (r, q) in marks[1]:
        rr, cc = r - shift[0], q - shift[1]
        hit = before[int(rr), int(cc)] if 0 <= rr < shape[0] and 0 <= cc < shape[1] else False
        dot(d, c.p((r * k, (q + shape[1] + 6) * k)), 6, COLOURS['green'] if hit else COLOURS['red'], 3)
    for i, dsc in enumerate(discs):
        dot(d, c.p((dsc[0] * k, (dsc[1] + i * (shape[1] + 6)) * k)), 9, COLOURS['yellow'], 2)
    ex = dict(id='ex_cfp_ma_turnover', modality='uwf', modality_label='광각 안저', region='미세혈관 병변 생성·소실',
              title='광각 안저 · 미세혈관 병변 생성·소실', source='burggraaf2025', source_file='provider_figures/antioxidants-14-00244-g001.jpg',
              caption='같은 눈(대조군)의 기준(왼쪽)과 12개월 뒤(오른쪽) 광각 사진입니다. 저자가 흰 화살표로 표시한 미세혈관 병변 위치를 점 mask로 삼고, '
                      '유두(노란 원) 위치 차이만큼 옮겨 맞춘 뒤 비교했습니다. 정합은 평행 이동만 쓴 서비스 추정이고, 저자는 병변의 일부만 화살표로 표시했으므로 값은 함수 동작을 보여 주는 예시입니다.')
    return write_example(ex, c, [L('turnover', '미세동맥류 생성·소실', lay, [('ft_ma_turnover', m)], 'lesions.turnover',
                                   '두 시점 모두 있음 = 초록, 기준에만 = 파랑(사라짐), 12개월에만 = 빨강(새로 생김); 반지름 4 px 점의 30 % 겹침 기준', 'green')])


def octa_extra_examples() -> list[dict]:
    out = []
    img = Image.open(atlas_fig.ARTICLE_FIGURES / 'octa_dcp.jpg').convert('L')
    g = np.asarray(img, float)
    flow = octa.binarize(g, method='phansalkar', window=15)
    c = Canvas(img.convert('RGB'), 700)
    out.append(write_example(dict(id='ex_octa_dcp', modality='octa', modality_label='OCTA', region='황반 심층 모세혈관망',
                                  title='OCTA · 황반 심층 혈관망', source=_figure_source('octa_dcp.jpg'), source_file='retinal_atlas_modality_figures/octa_dcp.jpg',
                                  caption='OCTA 심층 슬랩입니다. Phansalkar 이진화 뒤 혈관 밀도 함수를 실행했습니다.'), c,
                             [L('vd', '심층 혈관 밀도', c.mask(flow, COLOURS['red'], 140, 140),
                                [('ft_octa_vessel_density_dcp', octa.vessel_density(flow, feature_id='ft_octa_vessel_density_dcp'))],
                                'octa.vessel_density', 'Phansalkar 국소 임계값으로 이진화한 혈류 화소 ÷ 전체 화소', 'red')]))
    img = Image.open(atlas_fig.ARTICLE_FIGURES / 'octa_cc.jpg').convert('L')
    g = np.asarray(img, float)
    yy, xx = np.indices(g.shape)
    fov = ~((xx < 0.25 * g.shape[1]) & (yy > 0.7 * g.shape[0]))   # exclude the panel letter
    m = octa.flow_deficit(g, fov=fov)
    deficit = (g <= octa.phansalkar_threshold(g, window=15)) & fov
    c = Canvas(img.convert('RGB'), 700)
    out.append(write_example(dict(id='ex_octa_cc', modality='octa', modality_label='OCTA', region='맥락막모세혈관',
                                  title='OCTA · 맥락막모세혈관층', source=_figure_source('octa_cc.jpg'), source_file='retinal_atlas_modality_figures/octa_cc.jpg',
                                  caption='OCTA 맥락막모세혈관 슬랩입니다(패널 글자 부분 제외). 화소 단위입니다.'), c,
                             [L('fd', '맥락막모세혈관 혈류 결손', c.mask(deficit, COLOURS['blue'], 130, 130), [('ft_cc_flow_deficit', m)],
                                'octa.flow_deficit', 'Phansalkar 국소 임계값 이하 화소(파랑) 비율, 결손 수·평균 크기', 'blue')]))
    base, _ = masked('paper_rpc')
    g = np.asarray(base.convert('L'), float)
    big = skmorph.white_tophat(g, skmorph.disk(7)) > 32
    big = ndimage.binary_dilation(skmorph.remove_small_objects(big, 80), iterations=2)
    a = np.asarray(base, float)
    lines = (np.abs(a[..., 0] - a[..., 1]) > 40) | (np.abs(a[..., 1] - a[..., 2]) > 40)
    flow = octa.binarize(g, method='phansalkar', window=15) & ~big & ~ndimage.binary_dilation(lines, iterations=2)
    centre = (205.0, 190.0)   # author cross-hair intersection = disc centre
    yy, xx = np.indices(g.shape)
    disc = np.hypot(yy - centre[0], xx - centre[1]) <= 45
    m = octa.rpc_density(flow, disc, outer_px=130)
    ring = (np.hypot(yy - centre[0], xx - centre[1]) > 45) & (np.hypot(yy - centre[0], xx - centre[1]) <= 175)
    c = Canvas(base, 600)
    lay = c.mask(flow & ring, COLOURS['red'], 170, 170)
    lay = c.mask(ring, COLOURS['white'], 0, 200, layer=lay)
    src, file = masked_source('paper_rpc')
    out.append(write_example(dict(id='ex_octa_rpc', modality='octa', modality_label='OCTA', region='유두주위 모세혈관',
                                  title='OCTA · 유두주위 방사상 모세혈관', source=src, source_file=file,
                                  caption='유두 둘레 OCTA 슬랩입니다(3배 확대). 유두 중심은 저자 십자선 교차점, 유두 반지름은 서비스 가정(45 px)입니다. 큰 혈관과 저자 선은 뺐습니다.'), c,
                             [L('rpc', '유두주위 모세혈관 밀도', lay, [('ft_rpc_density', m)], 'octa.rpc_density',
                                '유두 경계부터 130 px 고리(흰 윤곽) 안, 큰 혈관을 뺀 Phansalkar 혈류 화소(빨강) 비율', 'red')]))
    fig = provider('40942_2022_406_Fig2_HTML.jpg')
    w = fig.width / 4
    hpan = 465
    a_img = fig.crop((0, 0, int(w) - 6, hpan)); d_img = fig.crop((int(3 * w) + 6, 0, fig.width, hpan))
    d_img = d_img.resize(a_img.size)

    def faz_of(im):
        gg = np.asarray(im.convert('L'), float)
        s2 = ndimage.gaussian_filter(gg, 2)
        flow = skmorph.remove_small_objects(s2 > octa.phansalkar_threshold(s2, window=31), 30)
        non = ~ndimage.binary_dilation(flow, iterations=3)
        h, w2 = gg.shape
        sm = ndimage.gaussian_filter(gg, 8)
        win = sm[h // 2 - 90:h // 2 + 90, w2 // 2 - 90:w2 // 2 + 90]
        dy, dx = np.unravel_index(win.argmin(), win.shape)
        lab, _ = ndimage.label(non)
        faz = lab == lab[h // 2 - 90 + dy, w2 // 2 - 90 + dx]
        faz = ndimage.binary_dilation(faz, iterations=3) & ~flow
        return ndimage.binary_fill_holes(skmorph.binary_closing(faz, skmorph.disk(5)))
    fa, fd = faz_of(a_img), faz_of(d_img)
    pair = Image.new('RGB', (a_img.width * 2 + 8, a_img.height), 'black')
    pair.paste(a_img, (0, 0)); pair.paste(d_img, (a_img.width + 8, 0))
    both_a = np.zeros(pair.size[::-1], bool); both_a[:, :a_img.width] = fa
    both_d = np.zeros(pair.size[::-1], bool); both_d[:, a_img.width + 8:] = fd
    c = Canvas(pair, 1000)
    lay = c.mask(both_a, COLOURS['yellow'], 100)
    lay = c.mask(both_d, COLOURS['orange'], 100, layer=lay)
    m = octa.faz_enlargement(fa, fd, interval_years=0.5)
    out.append(write_example(dict(id='ex_octa_faz_change', modality='octa', modality_label='OCTA', region='FAZ 변화',
                                  title='OCTA · 6개월 FAZ 변화', source='bromeo2022', source_file='provider_figures/40942_2022_406_Fig2_HTML.jpg',
                                  caption='항VEGF 치료 중인 당뇨황반부종 눈의 같은 표층 슬랩, 기준(왼쪽)과 6개월(오른쪽)입니다. FAZ는 단순 규칙 검출(서비스 추정)이고 '
                                          '원 그림 화소 단위입니다. 부종 때문에 기준 FAZ 경계가 흐립니다.'), c,
                             [L('faz', 'FAZ 확대', lay, [('ft_faz_enlargement', m)], 'octa.faz_enlargement',
                                '두 시점 FAZ(노랑 → 주황: 중심 가까운 가장 어두운 점에서 이어진 무혈류 영역, Phansalkar 이진화) 면적 차이 ÷ 0.5년', 'orange')]))
    return out


def icga_nir_examples() -> list[dict]:
    out = []
    base, ring = masked('paper_polypoidal')
    g = ndimage.gaussian_filter(np.asarray(base.convert('L'), float), 2)
    ys, xs = np.nonzero(ring)
    cy, cx, rr = ys.mean(), xs.mean(), np.hypot(ys - ys.mean(), xs - xs.mean()).max()
    yy, xx = np.indices(g.shape)
    roi = np.hypot(yy - cy, xx - cx) <= rr
    polyp = (g > np.percentile(g[roi], 90)) & roi
    polyp = skmorph.remove_small_objects(polyp, 20)
    c = Canvas(base)
    lay = c.mask(polyp, COLOURS['red'], 160)
    d = c.draw(lay); dot(d, c.p((cy, cx)), rr * c.scale, COLOURS['white'], 2)
    src, file = masked_source('paper_polypoidal')
    out.append(write_example(dict(id='ex_icga_polyp', modality='icga', modality_label='ICGA', region='결절성 병변',
                                  title='ICGA · 결절성 맥락막혈관병증', source=src, source_file=file,
                                  caption='인도시아닌그린혈관조영의 결절 모양 과형광입니다(3배 확대). 저자 화살표 둘레(흰 원)에서 가장 밝은 10 %를 결절로 분할한 서비스 추정입니다.'), c,
                             [L('polyp', '결절 개수', lay, [('ft_polyp_count', oct_lesions.lesion_count(polyp, feature_id='ft_polyp_count'))],
                                'oct_lesions.lesion_count', '흰 원 안 밝은 결절(빨강)의 연결 성분 수', 'red')]))
    base, sdd = masked('paper_sdd')
    c = Canvas(base, 600)
    src, file = masked_source('paper_sdd')
    yy, xx = np.indices(sdd.shape)
    hull = skmorph.convex_hull_image(sdd) if sdd.any() else sdd
    out.append(write_example(dict(id='ex_nir_sdd', modality='nir', modality_label='근적외선', region='망막하 드루젠양 침착물',
                                  title='근적외선 · 망막하 드루젠양 침착물', source=src, source_file=file,
                                  caption='근적외선 사진의 그물 모양 밝은 점입니다. 점 mask는 서비스 톱햇 규칙 추정(아틀라스 그림과 같음)입니다.'), c,
                             [L('extent', 'SDD 침범 범위', c.mask(sdd, COLOURS['yellow'], 220, 220, layer=c.mask(hull, COLOURS['white'], 0, 160)),
                                [('ft_sdd_extent', lesions.area(sdd, feature_id='ft_sdd_extent')),
                                 ('ft_lesion_generic_area', lesions.area(hull), f'점들을 감싸는 범위(흰 윤곽) {int(hull.sum()):,} px²')],
                                'lesions.area', '밝은 점(노랑) 화소 수; 점들을 감싸는 볼록 껍질 면적도 함께', 'yellow'),
                              R('stage', 'SDD 단계', c.mask(sdd, COLOURS['magenta'], 0, 255), 'ft_sdd_stage',
                                '판독 항목(계산 코드 없음) · 단계(1–4)는 OCT B-scan에서 침착물이 EZ를 넘는지로 판정; 이 근적외선 사진만으로는 판정 불가',
                                '점 위치를 표시; 단계 판정은 같은 자리 OCT를 판독자가 봄. 자동 판정 코드는 없음', 'magenta')]))
    return out


# ---------------------------------------------------------------- OCT

def rnfl_defect_layer(c, t, ilm, cols, z_um):
    """RNFL defect arc on the circle-scan thickness profile (reference = the same eye's ±45° moving average)."""
    prof = np.interp(np.linspace(0, len(t) - 1, 360), np.arange(len(t)), t * z_um)
    ref = ndimage.uniform_filter1d(prof, 91, mode='wrap')
    m = optic_disc.rnfl_defect_angle(prof, normal_um=ref, fraction=0.7)
    lay = c.layer(); d = c.draw(lay)
    low = t * z_um < 0.7 * np.interp(np.arange(len(t)), np.linspace(0, len(t) - 1, 360), ref)
    for x in range(len(cols)):
        if not np.isnan(ilm[x]):
            d.line([c.p((ilm[x] * 4 - 14, x * 4 + 2)), c.p((ilm[x] * 4 - 4, x * 4 + 2))],
                   fill=(COLOURS['red'] if low[x] else COLOURS['green']) + (255,), width=4)
    return L('defect', 'RNFL 결손 각도', lay, [('ft_rnfl_defect_angle', m)], 'optic_disc.rnfl_defect_angle',
             '두께 곡선(360°)이 같은 눈 ±45° 이동 평균의 70 % 미만(빨강)으로 이어진 가장 긴 호; 부종 눈이라 결손 해석은 제한적(혈관 그림자도 잡힘)', 'red')


def onh_oct_examples() -> list[dict]:
    out = []
    fig = provider('gr4.jpg')
    box = (46, 306, 300, 474)
    im = fig.crop(box)
    a = np.asarray(im, float)
    red = (a[..., 0] > 170) & (a[..., 1] < 110) & (a[..., 2] < 110)
    cyan = (a[..., 1] > 150) & (a[..., 2] > 150) & (a[..., 0] < 120)
    cols = np.arange(0, 236)                      # right edge carries the 'ILM'/'RNFL' labels
    ilm = np.array([np.argwhere(red[:, x]).mean() if red[:, x].any() else np.nan for x in cols])
    rnfl = np.array([np.argwhere(cyan[:, x]).mean() if cyan[:, x].any() else np.nan for x in cols])
    bar = np.asarray(fig.crop((46, 440, 70, 474)).convert('L'), float) > 200
    bar_px = int(bar.any(1).sum())               # 200 µm vertical scale bar
    z_um = 200.0 / bar_px
    t = rnfl - ilm
    ok = ~np.isnan(t)
    t = np.interp(np.arange(len(t)), np.where(ok)[0], t[ok])
    n = len(t)
    size = 201
    centre = (100.0, 100.0)
    radius = 80.0
    spacing = Spacing(x_mm=1.73 / radius, y_mm=1.73 / radius, z_um=z_um)
    # Spectralis circle scans run TMP→SUP→NAS→INF→TMP for the right eye; place each A-scan back on its circle point.
    surf_ilm = np.full((size, size), np.nan); surf_rnfl = np.full((size, size), np.nan)
    angles = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    for th in angles:
        k = int(th / (2 * np.pi) * n) % n
        r = int(round(centre[0] - radius * np.sin(th))); q = int(round(centre[1] - radius * np.cos(th)))
        surf_ilm[r, q] = 0.0; surf_rnfl[r, q] = t[k]
    m = oct_layers.rnfl_peripapillary({'ILM': surf_ilm, 'RNFL_GCL': surf_rnfl}, centre, spacing=spacing, eye='OD')
    quad = m.detail['quadrants']
    text = f"평균 {m.value:.0f} µm · " + ' · '.join(f"{WORD_KO.get(k, k)} {v:.0f}" for k, v in
                                               (('superior', quad['S']), ('inferior', quad['I']), ('nasal', quad['N']), ('temporal', quad['T'])))
    edema = Measurement('ft_disc_edema_rnfl', m.value, 'um', detail=m.detail)
    big = im.resize((im.width * 4, im.height * 4), Image.LANCZOS)
    c = Canvas(big, 1000)
    lay = c.layer(); d = c.draw(lay)
    for x in range(len(cols)):
        if not np.isnan(ilm[x]) and not np.isnan(rnfl[x]):
            d.line([c.p((ilm[x] * 4, x * 4 + 2)), c.p((rnfl[x] * 4, x * 4 + 2))], fill=COLOURS['yellow'] + (150,), width=3)
    out.append(write_example(dict(id='ex_oct_peripapillary', modality='oct', modality_label='OCT', region='유두주위 원형 스캔',
                                  title='OCT · 유두주위 RNFL 원형 스캔', source='markowitz2026', source_file='provider_figures/gr4.jpg',
                                  caption='유두 부종을 동반한 망막혈관염(IRVAN) 증례의 오른눈 3.5 mm 원형 B-scan입니다(4배 확대). 장비가 그린 ILM(빨강)·RNFL(청록) 경계선을 '
                                          '읽어 두께를 재고, 200 µm 눈금으로 µm로 바꿨습니다. 저자 보고값은 120 µm입니다. 오른쪽 끝 글자 구간은 뺐습니다.'), c,
                             [L('rnfl', '유두주위 RNFL 두께(부종 눈)', lay, [('ft_rnfl_thickness_peripapillary', m, text), ('ft_disc_edema_rnfl', edema, text)],
                                'oct_layers.rnfl_peripapillary', '열마다 ILM–RNFL 경계 거리(노란 막대)를 원 둘레 위치에 되돌려 놓고 평균·사분면 평균 계산', 'yellow'),
                              rnfl_defect_layer(c, t, ilm, cols, z_um)]))
    # BMO minimum rim width on the published radial ONH B-scan (device ILM trace + author BMO line)
    box = (205, 485, 1100, 900)
    im = provider('12886_2026_5473_Fig1_HTML.webp').crop(box)
    a = np.asarray(im, float)
    yy, xx = np.indices(a.shape[:2])
    green = (a[..., 1] - a[..., 0] > 30) & (a[..., 1] - a[..., 2] > 30) & (yy > 280) & (yy < 305)
    gys, gxs = np.nonzero(green)
    gy = int(np.bincount(gys).argmax())
    bmo = [(gy, int(gxs.min())), (gy, int(gxs.max()))]            # ends of the author BMO reference line
    gray = ndimage.gaussian_filter(a.mean(2), 2)
    gray[:, :48] = 0
    gray[:120] = 0                                                # above: the device reference line
    gray[green | ndimage.binary_dilation(green, iterations=3)] = 0
    ilm_rows = np.full(a.shape[1], np.nan)
    for x in range(48, a.shape[1]):
        col = gray[:, x]
        hit = np.nonzero(col > 70)[0]
        if hit.size:
            ilm_rows[x] = hit[0]
    ilm_rows = ndimage.median_filter(np.nan_to_num(ilm_rows, nan=np.nanmax(ilm_rows)), 9)
    ilm_pts = np.array([(ilm_rows[x], x) for x in range(48, a.shape[1])], float)
    m = optic_disc.bmo_mrw(bmo, [ilm_pts, ilm_pts])
    c = Canvas(im, 900)
    lay = c.layer(); d = c.draw(lay)
    poly(c, d, ilm_rows[48:], COLOURS['orange'], 2, x0=48)
    for b in bmo:
        j = np.argmin(np.hypot(ilm_pts[:, 0] - b[0], ilm_pts[:, 1] - b[1]))
        d.line([c.p(b), c.p(ilm_pts[j])], fill=COLOURS['yellow'] + (255,), width=4)
        dot(d, c.p(b), 6, COLOURS['green'], fill=True)
    out.append(write_example(dict(id='ex_oct_bmo', modality='oct', modality_label='OCT', region='시신경유두 단면',
                                  title='OCT · 시신경유두 방사 단면', source='oyur2026', source_file='provider_figures/12886_2026_5473_Fig1_HTML.webp',
                                  caption='시신경유두를 지나는 OCT 방사 단면입니다. 저자 BMO 기준선(초록) 양 끝과, 서비스가 밝기로 추적한 ILM(주황, 장비 점선과 같은 자리)을 썼습니다. '
                                          '눈금 정보가 없어 화소 단위입니다(가로·세로 화소 크기가 같다고 가정).'), c,
                             [L('mrw', 'BMO 최소 테 폭', lay, [('ft_bmo_mrw', m, f'{m.value:.1f} px (눈금이 없어 화소; 함수 기본 표기는 µm)')], 'optic_disc.bmo_mrw',
                                'BMO 양 끝(초록 점)에서 ILM까지 가장 짧은 거리(노란 선)의 평균', 'yellow')]))
    return out


from retinal_measures._common import Measurement  # noqa: E402


def oct_layer_extra_layers(c, crop, surf, t, top):
    """More single-B-scan layer measures on the OLIVES label-free foveal scan."""
    g = np.asarray(crop, float)
    h, w = g.shape
    rpe = np.asarray(t['rpe'], float) - top
    sm = ndimage.gaussian_filter(g, (1, 4))
    surf = dict(surf, RPE=rpe[None], OS_RPE=(rpe - 2)[None])
    layers = []
    band = lambda a, b: atlas_fig._band((h, w), a, b)  # noqa: E731
    lay = c.mask(band(surf['EZ'][0], surf['OS_RPE'][0]), COLOURS['yellow'], 150, 0)
    lay = c.mask(band(surf['RPE'][0], surf['BM'][0]), COLOURS['red'], 150, 0, layer=lay)
    layers.append(L('outer', '외절 길이·RPE–BM 두께', lay, [('ft_os_length', oct_layers.layer_thickness(surf, 'os')),
                                                      ('ft_rpe_bm_thickness', oct_layers.layer_thickness(surf, 'rpe_bm'))],
                    'oct_layers.layer_thickness', 'EZ~RPE 꼭대기 = 외절(노랑), RPE 최대 밝기~브루크막 = RPE–BM(빨강)', 'yellow'))
    elm = surf['ELM'][0]
    elm_vis = np.array([sm[int(elm[x]) - 1:int(elm[x]) + 2, x].mean() > sm[int(elm[x]) - 6:int(elm[x]) - 3, x].mean() + 2 for x in range(w)])
    ez_vis = np.array([sm[int(surf['EZ'][0][x]), x] > np.percentile(sm[:, x], 85) for x in range(w)])
    lay = c.layer(); d = c.draw(lay)
    for x in range(w):
        col = COLOURS['green'] if elm_vis[x] else COLOURS['red']
        d.point(c.p((elm[x], x)), fill=col + (255,))
        x0, y0 = c.p((elm[x], x)); d.ellipse((x0 - 1.5, y0 - 1.5, x0 + 1.5, y0 + 1.5), fill=col + (255,))
        col2 = COLOURS['cyan'] if ez_vis[x] else COLOURS['red']
        x0, y0 = c.p((surf['EZ'][0][x], x)); d.ellipse((x0 - 1.5, y0 - 1.5, x0 + 1.5, y0 + 1.5), fill=col2 + (255,))
    layers.append(L('continuity', '층 연속성(ELM·EZ)', lay,
                    [('ft_elm_continuity', oct_layers.layer_continuity(elm_vis, feature_id='ft_elm_continuity')),
                     ('ft_ez_continuity', oct_layers.layer_continuity(ez_vis, feature_id='ft_ez_continuity')),
                     ('ft_layer_continuity_generic', oct_layers.layer_continuity(elm_vis & ez_vis))],
                    'oct_layers.layer_continuity', '열마다 ELM(초록)·EZ(하늘색) 띠가 주변보다 밝으면 보임, 아니면 빨강; 보임 비율과 끊김 수', 'green'))
    rows = {k: v[0] for k, v in surf.items()}
    lay = c.mask(band(surf['OPL_ONL'][0], surf['ELM'][0]), COLOURS['magenta'], 120, 0)
    refl = oct_layers.layer_reflectivity(g, rows, 'onl')
    layers.append(L('reflect', '층 반사 신호(외핵층)', lay, [('ft_layer_reflectivity_generic', refl,
                                                        f"평균 밝기 {refl.value:.0f} · 정규화 {refl.detail['normalised']:.2f}")],
                    'oct_layers.layer_reflectivity', '외핵층(자홍) 평균 밝기; 유리체 = 0, RPE = 1로 정규화한 값도 함께', 'magenta'))
    lay = c.layer(); d = c.draw(lay)
    order = ['ILM', 'OPL_ONL', 'ELM', 'EZ', 'RPE', 'BM']
    palette = ['yellow', 'magenta', 'white', 'cyan', 'red', 'blue']
    for name, col in zip(order, palette):
        poly(c, d, surf[name][0], COLOURS[col], 2)
    layers.append(L('order', '층 배열 보존', lay, [('ft_layer_order', oct_layers.layer_order(surf))], 'oct_layers.layer_order',
                    '추적한 경계면 6개(색별)가 열마다 위→아래 순서를 지키는 비율', 'white'))
    lay = c.layer(); d = c.draw(lay)
    poly(c, d, rpe, COLOURS['red'], 3)
    x = np.arange(w); base = np.polyval(np.polyfit(x, rpe, 2), x)
    poly(c, d, base, COLOURS['white'], 2, 200)
    layers.append(L('rpe', 'RPE 윤곽', lay, [('ft_rpe_contour', oct_layers.surface_contour(rpe))], 'oct_layers.surface_contour',
                    'RPE 선(빨강)과 2차 곡선 기준선(흰색)의 차이: RMS와 최대 융기', 'red'))
    lay = c.mask(np.ones((h, w), bool) & (np.arange(h)[:, None] < h // 10), COLOURS['white'], 60, 0)
    layers.append(L('signal', 'OCT 신호 강도', lay, [('ft_oct_signal_strength', rm_image.oct_signal(g))], 'image.oct_signal',
                    '영상 99백분위 밝기와 위쪽 10 % 배경(흰 띠) 잡음의 비(dB)', 'white'))
    return layers


def oct_inner_example() -> dict:
    """Inner retinal layers on the high-resolution published parafoveal B-scan (Bringmann 2022 Fig 2C)."""
    im = provider('pone.0266968.g002.jpg').convert('L').crop((37, 598, 328, 718))
    g = np.asarray(im, float)
    h, w = g.shape
    s = ndimage.gaussian_filter(g, (1.2, 5))
    gr = np.gradient(s, axis=0)
    ilm, r1, r2 = np.full(w, np.nan), np.full(w, np.nan), np.full(w, np.nan)
    for x in range(w):
        col = s[:, x]
        top = np.nonzero(col > 0.5 * col[:40].max())[0]
        if not top.size:
            continue
        i0 = int(top[0]); ilm[x] = i0
        nfl = i0 + int(np.argmax(col[i0:i0 + 10]))
        gcl = nfl + int(np.argmin(col[nfl:nfl + 12]))
        r1[x] = nfl + int(np.argmin(gr[nfl:gcl + 1, x]))
        ipl = gcl + int(np.argmax(col[gcl:gcl + 14]))
        inl = ipl + int(np.argmin(col[ipl:ipl + 16]))
        r2[x] = ipl + int(np.argmin(gr[ipl:inl + 1, x]))
    ilm, r1, r2 = (ndimage.median_filter(v, 9) for v in (ilm, r1, r2))
    surf = {'ILM': ilm[None], 'RNFL_GCL': r1[None], 'IPL_INL': r2[None]}
    k = 3
    big = im.resize((w * k, h * k), Image.LANCZOS).convert('RGB')
    c = Canvas(big, 900)
    up = lambda v: v * k  # noqa: E731
    band = atlas_fig._band((h * k, w * k), np.repeat(up(ilm), k), np.repeat(up(r1), k))
    band2 = atlas_fig._band((h * k, w * k), np.repeat(up(r1), k), np.repeat(up(r2), k))
    layers = [L('rnfl', '황반 RNFL 두께', c.mask(band, COLOURS['green'], 110, 0), [('ft_rnfl_thickness_macular', oct_layers.layer_thickness(surf, 'rnfl'))],
                'oct_layers.layer_thickness', '내경계막 ~ 첫 밝은 띠(신경섬유층)가 끝나는 가장 가파른 밝기 하강(초록 띠)', 'green'),
              L('gcipl', 'GCIPL 두께', c.mask(band2, COLOURS['orange'], 110, 0), [('ft_gcipl_thickness', oct_layers.layer_thickness(surf, 'gcipl'))],
                'oct_layers.layer_thickness', 'RNFL 아래 ~ 내망상층(밝은 띠)이 내과립층(어두운 띠)으로 바뀌는 하강(주황 띠)', 'orange')]
    ex = dict(id='ex_oct_inner', modality='oct', modality_label='OCT', region='황반 내층',
              title='OCT · 황반 내층(RNFL·GCIPL)', source='bringmann2022', source_file='provider_figures/pone.0266968.g002.jpg',
              caption='층 구분이 또렷한 논문 고해상 B-scan(저자가 층 이름을 붙인 Fig 2C, 3배 확대)입니다. 열마다 밝기 곡선의 봉우리·골로 경계를 '
                      '서비스가 추적했으며, 눈금이 없어 원 그림 화소 단위입니다.')
    return write_example(ex, c, layers)


def oct_volume_examples() -> list[dict]:
    """DME 3D OCT volume with provider IRF masks: en-face maps, ETDRS grid, fluid volume; central B-scan with choroid."""
    import tifffile
    out = []
    vol = tifffile.imread(OCT3D / 'DME_labeled/input/DME0101.tif')
    irf = tifffile.imread(OCT3D / 'DME_labeled/label/DME0101_mask.tif') > 0
    nb, h, w = vol.shape
    ilm = np.zeros((nb, w)); bm = np.zeros((nb, w))
    for k in range(nb):
        s = ndimage.gaussian_filter(vol[k].astype(float), (3, 3))
        bright = np.argmax(s[40:h - 40], axis=0) + 40                    # RPE: brightest row
        thr = np.percentile(s, 60)
        top = np.array([int(np.argmax(s[:, x] > max(thr, 0.45 * s[bright[x], x]))) for x in range(w)])
        ilm[k] = ndimage.median_filter(top, 11); bm[k] = ndimage.median_filter(bright, 11) + 4
    ilm = ndimage.median_filter(ilm, (5, 5)); bm = ndimage.median_filter(bm, (5, 5))
    surf = {'ILM': ilm, 'BM': bm}
    spacing = Spacing(x_mm=6.0 / w, y_mm=6.0 / nb)              # assumed 6 × 6 mm field (provider gives no voxel size)
    thick = oct_layers.thickness_map(surf, 'retina')
    sm = ndimage.gaussian_filter(np.nan_to_num(thick, nan=np.nanmax(thick)), 6)
    cy, cx = nb // 2, w // 2
    win = sm[cy - nb // 6:cy + nb // 6, cx - w // 6:cx + w // 6]
    dy, dx = np.unravel_index(win.argmin(), win.shape)
    centre = (cy - nb // 6 + dy, cx - w // 6 + dx)
    tm = (thick - np.nanpercentile(thick, 2)) / (np.nanpercentile(thick, 98) - np.nanpercentile(thick, 2))
    from matplotlib import cm
    rgb = (cm.viridis(np.clip(np.nan_to_num(tm), 0, 1))[..., :3] * 255).astype(np.uint8)
    enface = Image.fromarray(rgb).resize((w, w), Image.BILINEAR)
    scale_r = w / nb
    c = Canvas(enface, 640)
    pc = lambda r, q: c.p((r * scale_r, q))  # noqa: E731
    lay = c.layer(); d = c.draw(lay)
    for rad_mm in (0.5, 1.5, 3.0):
        x, y = pc(*centre); rx = rad_mm / spacing.x_mm * c.scale; ry = rad_mm / spacing.y_mm * scale_r * c.scale
        d.ellipse((x - rx, y - ry, x + rx, y + ry), outline=COLOURS['white'] + (230,), width=2)
    for ang in (45, 135, 225, 315):
        t = math.radians(ang)
        x0, y0 = pc(centre[0] - 0.5 / spacing.y_mm * math.sin(t), centre[1] + 0.5 / spacing.x_mm * math.cos(t))
        x1, y1 = pc(centre[0] - 3.0 / spacing.y_mm * math.sin(t), centre[1] + 3.0 / spacing.x_mm * math.cos(t))
        d.line((x0, y0, x1, y1), fill=COLOURS['white'] + (230,), width=2)
    etdrs = oct_layers.etdrs_thickness(surf, centre, spacing=spacing)
    cst = oct_layers.central_subfield_thickness(surf, centre, spacing=spacing)
    mv = oct_layers.macular_volume(surf, centre, spacing=spacing)
    etxt = ' · '.join(f'{k} {v:.0f}' for k, v in etdrs.value.items()) + ' (축 방향 px)'
    layers = [L('etdrs', 'ETDRS 구역별·중심 두께', lay, [('ft_etdrs_subfield_thickness', etdrs, etxt), ('ft_central_subfield_thickness', cst),
                                                    ('ft_macular_volume', mv)],
                'oct_layers.etdrs_thickness · central_subfield_thickness · macular_volume',
                '볼륨 전 B-scan의 ILM–BM 두께 지도(바탕색)에 ETDRS 1·3·6 mm 격자(흰색, 가장 얇은 점 중심); 깊이 화소 크기가 없어 부피는 계산 불가', 'white')]
    proj = irf.any(axis=1)
    proj_img = np.kron(proj, np.ones((1, 1), bool))
    big = np.asarray(Image.fromarray(proj.astype(np.uint8) * 255).resize((w, w), Image.NEAREST)) > 0
    lay = c.mask(big, COLOURS['cyan'], 130)
    d = c.draw(lay); x, y = pc(*centre); rx = 0.5 / spacing.x_mm * c.scale; ry = 0.5 / spacing.y_mm * scale_r * c.scale
    d.ellipse((x - rx, y - ry, x + rx, y + ry), outline=COLOURS['red'] + (255,), width=3)
    layers.append(L('irf', '망막내액 부피·중심 침범', lay,
                    [('ft_irf_volume', oct_lesions.volume(irf, feature_id='ft_irf_volume')),
                     ('ft_lesion_generic_volume', oct_lesions.volume(irf)),
                     ('ft_irf_center_involvement', oct_lesions.center_involvement(irf, centre, spacing=spacing))],
                    'oct_lesions.volume · center_involvement', '공급자 3D 망막내액 mask의 복셀 수와 en face 투영(하늘색)이 중심 1 mm(빨간 원)에 닿는지', 'cyan'))
    out.append(write_example(dict(id='ex_oct_volume', modality='oct', modality_label='OCT', region='볼륨 두께 지도·액체',
                                  title='OCT 볼륨 · 두께 지도와 망막내액', source='amd_dme_3d', source_file='DME_labeled/input/DME0101.tif',
                                  caption=f'당뇨황반부종 눈의 OCT 볼륨(B-scan {nb}장)입니다. 바탕은 서비스가 B-scan마다 추적한 전체 망막 두께 지도입니다. '
                                          '공급자가 화소 크기를 밝히지 않아 촬영 범위를 6×6 mm로 가정해 격자를 그렸고, 두께는 축 방향 화소입니다. 망막내액은 공급자 3D mask입니다.'), c, layers))
    # central B-scan: retina layers, fluid layer, HRF, DRIL and choroid
    k = int(round(centre[0]))
    g = vol[k].astype(float)
    m2 = irf[k]
    s = ndimage.gaussian_filter(g, (2, 3))
    rpe = ndimage.median_filter(np.argmax(s[40:h - 40], axis=0) + 40, 11).astype(float)
    ilm_k = ilm[k].astype(float)
    bmk = np.array([rpe[x] + next((i for i in range(1, 30) if int(rpe[x]) + i >= h - 1 or s[int(rpe[x]) + i, x] < 0.5 * s[int(rpe[x]), x]), 4)
                    for x in range(w)], float)                     # BM: lower edge of the bright RPE band
    bmk = ndimage.median_filter(bmk, 11).astype(float)
    mu = ndimage.gaussian_filter(g, 6); sq = ndimage.gaussian_filter(g * g, 6)
    texture = ndimage.gaussian_filter(np.sqrt(np.clip(sq - mu * mu, 0, None)), (3, 15))
    csi = np.full(w, np.nan)
    for x in range(w):                                             # CSI: deepest row that still has vessel texture
        a0 = int(bmk[x]) + 8
        col = texture[a0:h - 5, x]
        if col.size > 60:
            idx = np.nonzero(col > 0.6 * np.percentile(col[:60], 90))[0]
            csi[x] = a0 + idx.max() if idx.size else np.nan
    csi = ndimage.median_filter(np.nan_to_num(csi, nan=np.nanmedian(csi)), 41).astype(float)
    opl = np.zeros(w)
    for x in range(w):
        a0, b0 = int(ilm_k[x] + 0.45 * (rpe[x] - ilm_k[x])), int(rpe[x]) - 12
        opl[x] = a0 + int(np.argmin(s[a0:b0, x])) if b0 > a0 + 3 else a0
    opl = ndimage.median_filter(opl, 21).astype(float)
    ez = np.array([int(rpe[x]) - 14 + int(np.argmax(s[int(rpe[x]) - 14:int(rpe[x]) - 4, x])) for x in range(w)], float)
    surf_b = {'ILM': ilm_k[None], 'OPL_ONL': opl[None], 'EZ': ez[None], 'RPE': rpe[None], 'BM': bmk[None], 'CSI': csi[None]}
    c = Canvas(Image.fromarray(vol[k]).convert('RGB'), 900)
    layers = []
    lay = c.mask(m2, COLOURS['cyan'], 140)
    d = c.draw(lay)
    for name, col in (('ILM', 'yellow'), ('OPL_ONL', 'magenta'), ('EZ', 'green'), ('RPE', 'red')):
        poly(c, d, surf_b[name][0], COLOURS[col], 2)
    layers.append(L('irf_layer', '액체 층 위치', lay, [('ft_irf_layer', oct_lesions.layer_location(m2[None], surf_b))],
                    'oct_lesions.layer_location', '공급자 망막내액(하늘색)이 서비스 추적 경계면(ILM 노랑·OPL 자홍·EZ 초록·RPE 빨강) 사이 어느 칸에 가장 많은지', 'cyan'))
    top_hat = skmorph.white_tophat(ndimage.gaussian_filter(g, 1), skmorph.disk(3))
    rows = np.arange(h)[:, None]
    retina = (rows > ilm_k[None] + 6) & (rows < ez[None] - 6) & ~ndimage.binary_dilation(m2, iterations=2)
    thr = np.percentile(top_hat[retina], 99.7)
    hrf = (top_hat > thr) & retina
    hrf = skmorph.remove_small_objects(hrf, 4)
    lay = c.layer(); d = c.draw(lay)
    for comp in ndimage.find_objects(ndimage.label(hrf)[0]):
        r = (comp[0].start + comp[0].stop) / 2; q = (comp[1].start + comp[1].stop) / 2
        dot(d, c.p((r, q)), 6, COLOURS['yellow'], 2)
    layers.append(L('hrf', '고반사 점 개수', lay, [('ft_hrf_count', oct_lesions.lesion_count(hrf, min_voxels=4))], 'oct_lesions.lesion_count',
                    '내경계막~EZ 사이(액체 제외) 백색 톱햇 상위 0.3 % 점(노란 원)의 연결 성분 수 — 서비스 추정', 'yellow'))
    inner = (rows > ilm_k[None] + 4) & (rows < opl[None])
    prof_std = np.array([s[int(ilm_k[x]) + 4:int(opl[x]), x].std() if opl[x] > ilm_k[x] + 10 else np.nan for x in range(w)])
    cmid = int(round(centre[1]))
    half = int(0.5 / spacing.x_mm)
    region = np.zeros(w, bool); region[max(cmid - half, 0):cmid + half] = True
    dril_cols = region & (prof_std < np.nanpercentile(prof_std, 25))
    dril = inner & dril_cols[None]
    lay = c.mask(dril, COLOURS['orange'], 110)
    d = c.draw(lay)
    x0, y0 = c.p((h - 20, cmid - half)); x1, y1 = c.p((h - 20, cmid + half))
    d.line((x0, y0, x1, y1), fill=COLOURS['white'] + (255,), width=3)
    layers.append(L('dril', 'DRIL 수평 범위', lay, [('ft_dril_extent', oct_lesions.lateral_diameter(dril, feature_id='ft_dril_extent'))],
                    'oct_lesions.lateral_diameter', '중심 1 mm(흰 막대, 6 mm 가정) 안에서 내층 밝기 변동이 하위 25 %라 층 구분이 흐린 열(주황) — 서비스 추정', 'orange'))
    ch = choroid.choroid_mask((h, w), bmk, csi)
    lumen = choroid.luminal_mask(g, ch)
    lay = c.mask(ch, COLOURS['magenta'], 50, 0)
    lay = c.mask(lumen, COLOURS['blue'], 140, 0, layer=lay)
    d = c.draw(lay)
    poly(c, d, bmk, COLOURS['red'], 2); poly(c, d, csi, COLOURS['yellow'], 2)
    x0, y0 = c.p((bmk[cmid], cmid)); x1, y1 = c.p((csi[cmid], cmid))
    d.line((x0, y0, x1, y1), fill=COLOURS['white'] + (255,), width=3)
    surf_c = {'BM': bmk[None], 'CSI': csi[None]}
    layers.append(L('choroid', '맥락막 두께·혈관성 지수', lay,
                    [('ft_choroid_thickness_subfoveal', oct_layers.subfoveal_choroid_thickness(surf_c, (0, cmid))),
                     ('ft_choroid_thickness_map', oct_layers.layer_thickness(surf_c, 'choroid')),
                     ('ft_choroidal_vascularity_index', choroid.vascularity_index(g, bmk, csi))],
                    'oct_layers.subfoveal_choroid_thickness · layer_thickness · choroid.vascularity_index',
                    '브루크막(빨강)~맥락막–공막 경계(노랑: 혈관 무늬가 끝나는 깊이, 서비스 추정) 사이: 중심와 아래 두께(흰 선), 단면 평균 두께, Niblack 어두운 내강(파랑) 비율', 'magenta'))
    outer = ch & (rows >= ((bmk + csi) / 2)[None])
    lum_o = lumen & outer
    dist = ndimage.distance_transform_edt(lum_o)
    r, q = np.unravel_index(dist.argmax(), dist.shape)
    lay = c.mask(lum_o, COLOURS['blue'], 120, 0)
    d = c.draw(lay); dot(d, c.p((r, q)), dist.max() * c.scale, COLOURS['white'], 3)
    layers.append(L('haller', '대혈관 직경', lay, [('ft_haller_vessel_diameter', choroid.large_vessel_diameter(g, bmk, csi))],
                    'choroid.large_vessel_diameter', '맥락막 바깥 절반의 어두운 내강(파랑) 중 가장 큰 내접원(흰 원)의 지름', 'blue'))
    out.append(write_example(dict(id='ex_oct_dme_bscan', modality='oct', modality_label='OCT', region='DME 중심 단면·맥락막',
                                  title='OCT · DME 중심 단면과 맥락막', source='amd_dme_3d', source_file=f'DME_labeled/input/DME0101.tif (B-scan {k})',
                                  caption='같은 볼륨에서 두께가 가장 얇은 점을 지나는 B-scan입니다. 망막내액은 공급자 mask이고, 경계면·고반사 점·DRIL·맥락막 경계는 '
                                          '서비스 추정입니다. 길이는 화소 단위입니다(맥락막까지 보이는 swept-source 영상).'), c, layers))
    return out


def amd_sd_volume_example() -> dict:
    pal = atlas_fig.AMD_PALETTE
    best, best_pid = -1, None
    for pid in sorted({p.parent.name for p in atlas_fig.AMD_SD.glob('images/*/*.png')}, key=int):
        files = sorted((atlas_fig.AMD_SD / 'images' / pid).glob('*.png'), key=lambda p: int(p.stem.split('_')[-1]))
        if len(files) < 15:
            continue
        tot = {k: 0 for k in ('SRF', 'PED', 'IS_OS')}
        for path in files[::3]:
            rgb = np.array(Image.open(path).convert('RGB'))
            mrgb = rgb[:, rgb.shape[1] // 2:].astype(int)
            for key in tot:
                tot[key] += int(np.all(np.abs(mrgb - pal[key]) < 40, axis=2).sum())
        score = min(tot.values())
        if score > best:
            best, best_pid = score, pid
    files = sorted((atlas_fig.AMD_SD / 'images' / best_pid).glob('*.png'), key=lambda p: int(p.stem.split('_')[-1]))
    vols = {k: [] for k in ('SRF', 'PED', 'IS_OS')}
    images = []
    for path in files:
        rgb = np.array(Image.open(path).convert('RGB'))
        half = rgb.shape[1] // 2
        images.append(rgb[:, :half].mean(2))
        mrgb = rgb[:, half:].astype(int)
        for key in vols:
            vols[key].append(np.all(np.abs(mrgb - pal[key]) < 40, axis=2))
    vols = {k: np.stack(v) for k, v in vols.items()}
    proj = {k: v.any(axis=1) for k, v in vols.items()}
    nb, wd = proj['SRF'].shape
    k_rep = int(np.argmax(vols['PED'].sum((1, 2)) + vols['SRF'].sum((1, 2))))
    bscan = Image.fromarray(images[k_rep].astype(np.uint8)).convert('RGB')
    rows_per = 12
    strip_h = nb * rows_per
    canvas_img = Image.new('RGB', (bscan.width, bscan.height + 10 + strip_h), 'black')
    canvas_img.paste(bscan, (0, 0))
    gray = np.stack([im.mean(0) for im in images])
    gray = (gray - gray.min()) / (np.ptp(gray) or 1) * 255
    enf = Image.fromarray(gray.astype(np.uint8)).resize((bscan.width, strip_h), Image.NEAREST).convert('RGB')
    canvas_img.paste(enf, (0, bscan.height + 10))
    c = Canvas(canvas_img, 760)
    oy = bscan.height + 10

    def enface_mask(p):
        big = np.zeros(canvas_img.size[::-1], bool)
        big[oy:oy + strip_h] = np.kron(p, np.ones((rows_per, 1), bool))[:, :bscan.width]
        return big

    def bscan_mask(m):
        big = np.zeros(canvas_img.size[::-1], bool); big[:bscan.height] = m; return big
    layers = []
    for key, fid, label, col in (('SRF', 'ft_srf_volume', '망막하액 부피', 'red'), ('PED', 'ft_ped_volume', 'PED 부피', 'blue')):
        lay = c.mask(enface_mask(proj[key]), COLOURS[col], 150)
        lay = c.mask(bscan_mask(vols[key][k_rep]), COLOURS[col], 130, layer=lay)
        layers.append(L(key.lower(), label, lay, [(fid, oct_lesions.volume(vols[key], feature_id=fid))], 'oct_lesions.volume',
                        f'공급자 {label[:-3]} mask를 B-scan {nb}장에 걸쳐 더한 복셀 수; 아래 띠 = en face 투영(한 줄 = B-scan 1장)', col))
    isos = vols['IS_OS']
    vis = isos.any(axis=1)
    cols = np.zeros_like(vis); cols[:, :] = True
    retina_cols = np.stack([np.asarray(im)[:, :].mean(0) > 8 for im in images])
    loss = retina_cols & ~vis
    lay = c.mask(enface_mask(vis), COLOURS['green'], 150)
    lay = c.mask(enface_mask(loss), COLOURS['red'], 150, layer=lay)
    lay = c.mask(bscan_mask(isos[k_rep]), COLOURS['green'], 150, layer=lay)
    area, frac, gap = oct_layers.ez_preserved(vis)
    layers.append(L('ez', 'EZ 보존·소실 면적', lay,
                    [('ft_ez_preserved_area', area), ('ft_ez_loss_area', oct_lesions.enface_area(loss[:, None, :], feature_id='ft_ez_loss_area'))],
                    'oct_layers.ez_preserved · oct_lesions.enface_area', '공급자 IS/OS(EZ) 띠가 있는 A-scan(초록)과 없는 A-scan(빨강)을 en face로 셈(화소 = A-scan × B-scan)', 'green'))
    ex = dict(id='ex_oct_amd_volume', modality='oct', modality_label='OCT', region='AMD 연속 단면 부피',
              title='OCT 연속 단면 · AMD 병변 부피', source='amd_sd', source_file=f'images/{best_pid}/ ({nb}장)',
              caption=f'나이관련황반변성 한 눈의 연속 B-scan {nb}장(공급자 병변 mask)입니다. 위는 대표 단면, 아래 띠는 B-scan마다 mask를 세로로 '
                      '투영한 en face 지도입니다. B-scan 간격을 몰라 부피는 복셀 수입니다.')
    return write_example(ex, c, layers)


def amd_sd_bscan_layers(c, img, m, shrm):
    """Extra lesion measures on the AMD-SD B-scan: presence, layer position, internal reflectivity, height."""
    g = np.asarray(img.convert('L'), float)
    h, w = g.shape
    s = ndimage.gaussian_filter(g, (2, 3))
    s4 = ndimage.gaussian_filter(g, 4)
    retina = skmorph.remove_small_objects(skmorph.binary_opening(s4 > 0.35 * np.percentile(s4, 99.5), skmorph.disk(3)), 2000)
    ilm = np.array([np.argmax(retina[:, x]) if retina[:, x].any() else np.nan for x in range(w)], float)
    ilm = ndimage.median_filter(np.nan_to_num(ilm, nan=np.nanmedian(ilm)), 15).astype(float)
    ped_bottom = np.array([np.nonzero(m['PED'][:, x])[0].max() if m['PED'][:, x].any() else np.nan for x in range(w)])
    ped_top = np.array([np.nonzero(m['PED'][:, x])[0].min() if m['PED'][:, x].any() else np.nan for x in range(w)])
    bright = np.argmax(s, axis=0).astype(float)
    rpe = np.where(np.isnan(ped_top), bright, ped_top - 1)
    bm = np.where(np.isnan(ped_bottom), bright + 4, ped_bottom + 1)
    rpe = ndimage.median_filter(rpe, 9); bm = ndimage.median_filter(bm, 9)
    srf_top = np.array([np.nonzero(m['SRF'][:, x])[0].min() if m['SRF'][:, x].any() else np.nan for x in range(w)])
    ez = np.where(np.isnan(srf_top), rpe - 8, srf_top - 1)
    opl = ilm + 0.55 * (ez - ilm)
    surf = {'ILM': ilm[None], 'OPL_ONL': opl[None], 'EZ': ez[None], 'RPE': rpe[None], 'BM': bm[None]}
    layers = []
    lay = c.mask(m['IRF'], COLOURS['green'], 110)
    lay = c.mask(m['SRF'], COLOURS['red'], 110, layer=lay)
    layers.append(L('presence', '액체 존재', lay, [('ft_irf_presence', oct_lesions.presence(m['IRF'], feature_id='ft_irf_presence')),
                                              ('ft_srf_presence', oct_lesions.presence(m['SRF'], feature_id='ft_srf_presence'))],
                    'oct_lesions.presence', '공급자 망막내액(초록)·망막하액(빨강) mask가 비어 있지 않은지', 'green'))
    lay = c.mask(m['PED'], COLOURS['blue'], 90)
    d = c.draw(lay)
    for name, col in (('ILM', 'yellow'), ('EZ', 'green'), ('RPE', 'red'), ('BM', 'white')):
        poly(c, d, surf[name][0], COLOURS[col], 2)
    layers.append(L('mnv_type', 'MNV 유형(깊이)', lay, [('ft_mnv_type', oct_lesions.depth_category(m['PED'][None], surf))], 'oct_lesions.depth_category',
                    'PED(파랑) 화소가 RPE(빨강) 아래·망막하·망막내 중 어디에 많은지; RPE·BM은 PED mask 위·아래 경계로 정함', 'blue'))
    rpe_band = np.zeros_like(g, bool)
    for x in range(w):
        if not np.isnan(rpe[x]):
            r = int(rpe[x]); rpe_band[max(r - 2, 0):r + 1, x] = True
    ref = float(g[rpe_band & ~m['PED']].mean()) if (rpe_band & ~m['PED']).any() else float(g[rpe_band].mean())
    lay = c.mask(m['PED'], COLOURS['orange'], 120)
    lay = c.mask(rpe_band, COLOURS['red'], 200, 200, layer=lay)
    layers.append(L('reflect', 'PED 내부 반사', lay, [('ft_ped_internal_reflectivity', oct_lesions.internal_reflectivity(g, m['PED'], reference=ref))],
                    'oct_lesions.internal_reflectivity', 'PED 내부(주황) 평균 밝기 ÷ RPE 띠(빨강) 평균: 0.33 미만 저반사, 0.66 미만 혼합, 이상 고반사', 'orange'))
    hgt = oct_lesions.height(m['IRF'])
    lay = c.mask(m['IRF'], COLOURS['green'], 90)
    d = c.draw(lay)
    col = hgt.detail.get('ascan_index')
    if col is not None:
        rows = np.where(m['IRF'][:, col])[0]
        d.line([c.p((rows.min(), col)), c.p((rows.max(), col))], fill=COLOURS['white'] + (255,), width=3)
    layers.append(L('height', '병변 높이(공통)', lay, [('ft_lesion_generic_height', hgt)], 'oct_lesions.height',
                    '망막내액 mask에서 가장 두꺼운 A-scan의 세로 길이(흰 선)', 'green'))
    if shrm.any():
        hs = oct_lesions.height(shrm, feature_id='ft_shrm_thickness')
        lay = c.mask(shrm, COLOURS['yellow'], 140)
        d = c.draw(lay); col = hs.detail.get('ascan_index')
        if col is not None:
            rows = np.where(shrm[:, col])[0]
            d.line([c.p((rows.min(), col)), c.p((rows.max(), col))], fill=COLOURS['white'] + (255,), width=3)
        layers.append(L('shrm', 'SHRM 두께', lay, [('ft_shrm_thickness', hs)], 'oct_lesions.height',
                        '공급자 망막하 고반사 물질 mask(노랑)의 가장 두꺼운 A-scan 높이', 'yellow'))
        lay = c.mask(shrm, COLOURS['red'], 0, 255); d = c.draw(lay)
        poly(c, d, rpe, COLOURS['white'], 2)
        layers.append(R('hem_depth', '출혈 깊이', lay, 'ft_hem_depth',
                        '판독 항목(계산 코드 없음) · 망막하 고반사 물질(빨간 윤곽)이 RPE(흰 선) 위·망막 아래에 있어 망막하 위치로 읽음',
                        'RPE 선과 물질 위치를 함께 표시; 층 판정은 판독자. 자동 판정 코드는 없음', 'red'))
    mid = slice(int(0.3 * w), int(0.7 * w))
    fc = int(np.argmax(ilm[mid])) + mid.start                     # foveal pit = deepest ILM point near the centre
    srf_cols = np.repeat(m['SRF'].any(0)[None], h, 0)
    lay = c.mask(m['SRF'], COLOURS['red'], 120); d = c.draw(lay)
    x, _ = c.p((0, fc)); d.line((x, 0, x, c.size[1]), fill=COLOURS['yellow'] + (255,), width=3)
    layers.append(L('macula', '황반 침범(망막하액)', lay,
                    [('ft_rd_macula_status', lesions.involves_point(srf_cols, (h // 2, fc), feature_id='ft_rd_macula_status'))],
                    'lesions.involves_point', '중심와 함요 열(노란 선)에 망막하액(빨강)이 걸리는지 — 장액 박리의 황반 침범 예', 'yellow'))
    lay = c.mask(m['IRF'], COLOURS['green'], 0, 255)
    lay = c.mask(m['SRF'], COLOURS['red'], 0, 255, layer=lay)
    layers.append(R('activity', 'MNV 활동성 징후', lay, 'ft_mnv_activity',
                    '판독 항목(계산 코드 없음) · 망막내액(초록)·망막하액(빨강)이 있으면 활동성 신생혈관으로 읽음; 이 단면은 액체 있음',
                    '공급자 액체 mask 윤곽을 판독 위치로 표시; 활동성 판정은 판독자(이전 검사와 비교). 자동 판정 코드는 없음', 'green'))
    return layers


def octid_examples() -> list[dict]:
    out = []
    # macular hole
    base, _ = masked('octid_mh_full')
    g = np.asarray(base.convert('L'), float)
    tissue = skmorph.binary_opening(ndimage.gaussian_filter(g, 1.5) > 65, skmorph.disk(2))
    centre_col = 365                                              # hole centre (same seed column as the atlas figure)
    hole = np.zeros_like(tissue)
    for r in range(100, 260):
        if tissue[r, centre_col]:
            if hole.any():
                break                                             # reached the RPE floor
            continue
        left, right = np.nonzero(tissue[r, :centre_col])[0], np.nonzero(tissue[r, centre_col:])[0]
        if left.size and right.size and centre_col - left.max() < 120 and right.min() < 120:
            hole[r, left.max() + 1:centre_col + right.min()] = True
    rows = np.where(hole.any(1))[0]
    widths = hole.sum(1)
    lower = rows[int(0.6 * len(rows)):]
    hole[lower[np.argmax(widths[lower])] + 1:] = False             # drop the sloping floor rows below the widest base row
    mn, base_d = oct_lesions.hole_diameters(hole)
    rows = np.where(hole.any(1))[0]
    widths = hole.sum(1)
    rmin = rows[np.argmin(widths[rows])]
    c = Canvas(base)
    lay = c.mask(hole, COLOURS['cyan'], 90)
    d = c.draw(lay)
    for r, col in ((rmin, COLOURS['yellow']), (rows[-1], COLOURS['red'])):
        q = np.nonzero(hole[r])[0]
        d.line([c.p((r, q.min())), c.p((r, q.max()))], fill=col + (255,), width=4)
    ilm, _ = trace_ilm_rpe(g, top=60, bottom=440)
    vit = np.full_like(ilm, np.nan)
    lay2 = c.layer(); d2 = c.draw(lay2)
    poly(c, d2, ilm, COLOURS['yellow'], 2)
    src, file = masked_source('octid_mh_full')
    out.append(write_example(dict(id='ex_oct_mh', modality='oct', modality_label='OCT', region='황반원공',
                                  title='OCT · 전층 황반원공', source=src, source_file=file,
                                  caption='전층 황반원공 B-scan입니다. 원공은 행마다 양쪽 망막 조직 가장자리 사이 빈 구간으로 서비스가 잡았으며(밝기 임계 65) 화소 단위입니다.'), c,
                             [L('diam', '원공 최소·기저 직경', lay, [('ft_mh_min_diameter', mn), ('ft_mh_base_diameter', base_d)], 'oct_lesions.hole_diameters',
                                '원공 영역(하늘색)에서 가장 좁은 가로 폭(노랑)과 가장 아래(RPE 쪽) 폭(빨강)', 'cyan'),
                              L('vmt', '원공의 견인 동반', lay2, [('ft_mh_vmt_status', oct_lesions.attachment_width(vit, ilm, feature_id='ft_mh_vmt_status'))],
                                'oct_lesions.attachment_width', '후유리체막이 ILM(노란 선)에 닿은 폭; 이 영상에서는 막이 보이지 않아 "관찰 안 됨"', 'yellow')]))
    # vitreomacular traction
    base, hyal = masked('octid_vmt')
    g = np.asarray(base.convert('L'), float)
    ilm, _ = trace_ilm_rpe(g, top=80, bottom=520)
    hy = surface_line(hyal)
    m = oct_lesions.attachment_width(hy, ilm, tolerance_px=4)
    touch = np.abs(ilm - hy) <= 4
    c = Canvas(base)
    lay = c.layer(); d = c.draw(lay)
    poly(c, d, hy, COLOURS['cyan'], 3); poly(c, d, ilm, COLOURS['yellow'], 2)
    for x in np.nonzero(touch)[0]:
        x0, y0 = c.p((ilm[x], x)); d.ellipse((x0 - 2, y0 - 2, x0 + 2, y0 + 2), fill=COLOURS['red'] + (255,))
    src, file = masked_source('octid_vmt')
    out.append(write_example(dict(id='ex_oct_vmt', modality='oct', modality_label='OCT', region='유리체황반 견인',
                                  title='OCT · 유리체황반 견인', source=src, source_file=file,
                                  caption='유리체황반 견인 B-scan입니다. 후유리체막(하늘색)과 ILM(노랑)은 서비스 밝기 추적입니다. 화소 단위입니다.'), c,
                             [L('attach', '유리체 부착 직경', lay, [('ft_vmt_attachment_width', m)], 'oct_lesions.attachment_width',
                                '후유리체막과 ILM이 4 px 이내로 붙은 가장 긴 구간(빨간 점)의 폭', 'red')]))
    # epiretinal membrane
    base, erm = masked('octid_erm')
    c = Canvas(base)
    src, file = masked_source('octid_erm')
    out.append(write_example(dict(id='ex_oct_erm', modality='oct', modality_label='OCT', region='망막전막',
                                  title='OCT · 망막전막', source=src, source_file=file,
                                  caption='망막전막 B-scan입니다. 막 표시는 서비스 밝기 추적(아틀라스 그림과 같음)입니다. B-scan 1장이라 en face 면적 대신 가로 범위(px)가 나옵니다.'), c,
                             [L('extent', '망막전막 범위', c.mask(erm, COLOURS['cyan'], 220, 220),
                                [('ft_erm_extent', oct_lesions.enface_area(erm, feature_id='ft_erm_extent'))], 'oct_lesions.enface_area',
                                '막 mask를 깊이 방향으로 투영한 화소 수(B-scan 1장 = 막이 덮는 A-scan 수)', 'cyan'),
                              R('traction', '망막전막 견인 징후', c.mask(erm, COLOURS['yellow'], 0, 255), 'ft_erm_traction_signs',
                                '판독 항목(계산 코드 없음) · 막 아래 주름·내층 끌림·중심와 함요 소실을 판정; 이 영상은 표면 주름과 망막 두꺼워짐이 보임',
                                '막(노랑) 아래 망막 모양을 판독자가 봄. 자동 판정 코드는 없음', 'yellow')]))
    # staphyloma
    base, line = masked('octid_staphyloma')
    bmline = surface_line(line)
    m = oct_layers.staphyloma_depth(bmline)
    valid = np.where(~np.isnan(bmline))[0]
    x0, x1 = valid[0], valid[-1]
    chord = bmline[x0] + (bmline[x1] - bmline[x0]) * (np.arange(len(bmline)) - x0) / (x1 - x0)
    k = int(np.nanargmax(bmline - chord))
    c = Canvas(base)
    lay = c.layer(); d = c.draw(lay)
    poly(c, d, bmline, COLOURS['red'], 3)
    d.line([c.p((bmline[x0], x0)), c.p((bmline[x1], x1))], fill=COLOURS['white'] + (230,), width=2)
    d.line([c.p((chord[k], k)), c.p((bmline[k], k))], fill=COLOURS['yellow'] + (255,), width=4)
    src, file = masked_source('octid_staphyloma')
    out.append(write_example(dict(id='ex_oct_staphyloma', modality='oct', modality_label='OCT', region='후포도종',
                                  title='OCT · 후포도종 굴곡', source=src, source_file=file,
                                  caption='고도근시 눈의 넓은 B-scan입니다. RPE/BM 선은 서비스 밝기 추적(아틀라스 그림과 같음)입니다. 화소 단위입니다.'), c,
                             [L('depth', '후포도종 깊이', lay, [('ft_staphyloma_depth', m)], 'oct_layers.staphyloma_depth',
                                'RPE/BM 선(빨강) 양 끝을 잇는 현(흰색)에서 가장 깊이 처진 거리(노랑)', 'red')]))
    # hypertransmission
    base, ht = masked('octid_hypertd')
    cols = ht.any(0)
    m = oct_lesions.transmission_width(cols[None, :])
    c = Canvas(base)
    lay = c.mask(ht, COLOURS['orange'], 110)
    d = c.draw(lay)
    q = np.nonzero(cols)[0]
    y = base.height - 30
    lab_, n = ndimage.label(cols)
    for i in range(1, n + 1):
        qq = np.nonzero(lab_ == i)[0]
        d.line([c.p((y, qq.min())), c.p((y, qq.max()))], fill=COLOURS['white'] + (255,), width=4)
    src, file = masked_source('octid_hypertd')
    out.append(write_example(dict(id='ex_oct_hypertd', modality='oct', modality_label='OCT', region='과투과 결손',
                                  title='OCT · 맥락막 과투과', source=src, source_file=file,
                                  caption='위축 부위 아래 맥락막이 밝게 보이는 과투과 B-scan입니다. 과투과 열은 서비스 밝기 규칙 추정(아틀라스 그림과 같음)입니다. '
                                          'B-scan 1장을 한 줄 en face로 보고 가장 긴 구간을 잽니다.'), c,
                             [L('width', '과투과 폭', lay, [('ft_hypertd_width', m)], 'oct_lesions.transmission_width',
                                '과투과 열(주황)을 가로 한 줄 mask로 만들어 가장 긴 연속 구간(흰 막대)의 길이', 'orange')]))
    # drusen on OCT
    base, dr = masked('octid_drusen')
    g = np.asarray(base.convert('L'), float)
    labels, n = ndimage.label(dr)
    sizes = ndimage.sum(dr, labels, range(1, n + 1))
    big = labels == (sizes.argmax() + 1)
    hd = oct_lesions.height(big, feature_id='ft_drusen_height')
    rpe_ref = float(np.percentile(g[ndimage.binary_dilation(dr, iterations=3) & ~dr], 90))
    c = Canvas(base)
    lay = c.mask(big, COLOURS['yellow'], 120)
    d = c.draw(lay); col = hd.detail.get('ascan_index')
    if col is not None:
        rows = np.where(big[:, col])[0]
        d.line([c.p((rows.min(), col)), c.p((rows.max(), col))], fill=COLOURS['white'] + (255,), width=3)
    src, file = masked_source('octid_drusen')
    out.append(write_example(dict(id='ex_oct_drusen', modality='oct', modality_label='OCT', region='드루젠',
                                  title='OCT · 드루젠', source=src, source_file=file,
                                  caption='드루젠이 있는 B-scan입니다. 드루젠 영역은 서비스 추정(아틀라스 그림과 같음)이며 화소 단위입니다. '
                                          'B-scan 1장이라 부피 함수는 단면 화소 수를 돌려줍니다.'), c,
                             [L('height', '드루젠 높이', lay, [('ft_drusen_height', hd)], 'oct_lesions.height', '가장 큰 드루젠(노랑)의 가장 두꺼운 A-scan(흰 선)', 'yellow'),
                              L('reflect', '드루젠 내부 반사', c.mask(dr, COLOURS['orange'], 110),
                                [('ft_drusen_reflectivity', oct_lesions.internal_reflectivity(g, dr, reference=rpe_ref, feature_id='ft_drusen_reflectivity'))],
                                'oct_lesions.internal_reflectivity', '드루젠 내부(주황) 평균 밝기 ÷ 둘레 RPE 띠 밝기(90백분위)', 'orange'),
                              L('volume', '드루젠 부피(단면)', c.mask(dr, COLOURS['cyan'], 110), [('ft_drusen_volume', oct_lesions.volume(dr, feature_id='ft_drusen_volume'))],
                                'oct_lesions.volume', '드루젠 mask 화소 합(볼륨이면 복셀 합)', 'cyan')]))
    return out


# ---------------------------------------------------------------- shared suites for the per-modality examples
# The same lesion / vessel / landmark functions are run on another image type so that every measurement that
# applies to that type has an image there. Inputs are provider masks where they exist, otherwise service
# estimates that each caption names.

def lesion_suite(c, mask, *, fovea, disc=None, dd=None, fov=None, vessel=None, what='병변', ring_dd=2.0):
    """Common lesion measures (presence … vessel relation) on one lesion mask; returns layers."""
    from skimage import measure as skm
    from scipy.spatial import ConvexHull
    layers = []
    mask = np.asarray(mask, bool)
    labels, n = ndimage.label(mask)
    layers.append(L('presence', f'{what} 존재·개수', c.mask(mask, COLOURS['orange'], 120),
                    [('ft_lesion_generic_presence', lesions.presence(mask)), ('ft_lesion_generic_count', lesions.count(mask))],
                    'lesions.presence · count', f'{what} mask(주황)에 연결 성분이 있는지와 그 개수', 'orange'))
    sizes = ndimage.sum(mask, labels, range(1, n + 1))
    lay = c.layer()
    for rank, k in enumerate(np.argsort(sizes)):
        t = rank / max(n - 1, 1)
        lay = c.mask(labels == k + 1, (int(56 + t * 192), int(189 - t * 76), int(248 - t * 135)), 170, 255, layer=lay)
    layers.append(L('sizes', f'{what} 면적·크기 분포', lay,
                    [('ft_lesion_generic_area', lesions.area(mask)), ('ft_lesion_size_distribution', lesions.size_distribution(mask))],
                    'lesions.area · size_distribution', '전체 화소 수와 조각별 면적(작은 하늘색 → 큰 빨강)의 평균·중앙·90백분위·최대', 'cyan'))
    props = [p for p in skm.regionprops(labels) if p.area >= 3]
    lay = c.mask(mask, COLOURS['magenta'], 60); d = c.draw(lay)
    pts = np.argwhere(labels == max(props, key=lambda p: p.area).label) if props else np.zeros((0, 2))
    if len(pts) >= 3:
        try:
            hv = pts[ConvexHull(pts).vertices]
            dm = np.hypot(*(hv[:, None] - hv[None]).transpose(2, 0, 1))
            i, j = np.unravel_index(dm.argmax(), dm.shape)
            d.line([c.p(hv[i]), c.p(hv[j])], fill=COLOURS['white'] + (255,), width=3)
        except Exception:   # degenerate (collinear) component
            pass
    layers.append(L('shape', f'{what} 형태·범위 길이', lay,
                    [('ft_lesion_generic_shape', lesions.shape(mask)), ('ft_lesion_generic_extent', lesions.extent(mask))],
                    'lesions.shape · extent', '조각마다 원형도·이심률·충실도(면적 가중)와 최대 Feret 지름 중 최댓값(흰 선)', 'magenta'))
    lay = c.mask(mask, COLOURS['orange'], 70); d = c.draw(lay)
    rows, cols = np.nonzero(mask)
    x, y = c.p((rows.mean(), cols.mean()))
    d.line((x - 14, y, x + 14, y), fill=COLOURS['white'] + (255,), width=3); d.line((x, y - 14, x, y + 14), fill=COLOURS['white'] + (255,), width=3)
    layers.append(L('position', f'{what} 위치 좌표', lay, [('ft_lesion_generic_position', lesions.position(mask))], 'lesions.position',
                    f'{what} 무게중심(흰 십자)을 영상 높이·너비에 대한 비율로', 'white'))
    lay = c.mask(mask, COLOURS['orange'], 70); d = c.draw(lay)
    unit = dd or 1.0
    for k in (1, 2, 3):
        x, y = c.p(fovea); rr = k * unit * c.scale
        d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=COLOURS['cyan'] + (200,), width=2)
    pts_all = np.argwhere(mask)
    near = pts_all[np.argmin(np.hypot(*(pts_all - np.asarray(fovea)).T))]
    d.line([c.p(fovea), c.p(near)], fill=COLOURS['white'] + (255,), width=3)
    layers.append(L('radial', f'중심와에서 {what}까지 거리', lay,
                    [('ft_lesion_radial_position', lesions.radial_position(mask, fovea, disc_diameter_px=dd)),
                     ('ft_lesion_fovea_distance', lesions.fovea_distance(mask, fovea, disc_diameter_px=dd))],
                    'lesions.radial_position · fovea_distance',
                    ('하늘색 고리 = 중심와에서 1·2·3 유두지름' if dd else '하늘색 고리 = 중심와에서 1·2·3 px 단위') + '; 흰 선 = 가장 가까운 병변', 'cyan'))
    radius = ring_dd * (dd or 50)
    inside = np.hypot(*(np.indices(mask.shape) - np.asarray(fovea, float)[:, None, None])) <= radius
    lay = c.mask(mask & inside, COLOURS['green'], 170)
    lay = c.mask(mask & ~inside, COLOURS['orange'], 70, layer=lay)
    d = c.draw(lay); x, y = c.p(fovea); rr = radius * c.scale
    d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=COLOURS['green'] + (230,), width=3)
    layers.append(L('regional', f'구역별 {what} 비율', lay, [('ft_lesion_regional_fraction', lesions.regional_fraction(mask, fovea, radius))],
                    'lesions.regional_fraction', f'{what} 면적 중 중심와 {"%g 유두지름" % ring_dd if dd else "%d px" % radius} 원(초록) 안 비율', 'green'))
    if disc is not None:
        axis = (np.asarray(disc, float) - fovea) / np.linalg.norm(np.asarray(disc, float) - fovea)
        normal = np.array([-axis[1], axis[0]])
        q = lesions.quadrant_of(np.argwhere(mask), fovea, disc)
        lay = c.layer()
        for name, col in zip(lesions.QUADRANTS, (COLOURS['cyan'], COLOURS['magenta'], COLOURS['yellow'], COLOURS['green'])):
            m = np.zeros_like(mask); p = np.argwhere(mask)[q == name]
            m[tuple(p.T)] = True
            lay = c.mask(m, col, 200, 255, layer=lay)
        d = c.draw(lay)
        for v in (axis, normal):
            d.line([c.p(np.asarray(fovea) - 3000 * v), c.p(np.asarray(fovea) + 3000 * v)], fill=COLOURS['white'] + (220,), width=2)
        layers.append(L('quadrant', '사분면 분산·침범 수', lay,
                        [('ft_lesion_spatial_dispersion', lesions.spatial_dispersion(mask, fovea, disc)),
                         ('ft_vascular_change_extent', lesions.quadrant_occupancy(mask, fovea, disc))],
                        'lesions.spatial_dispersion · quadrant_occupancy',
                        f'유두–중심와 축(흰 선)으로 나눈 네 사분면별 {what}(색별): 면적 비율 엔트로피와 병변 있는 사분면 수', 'magenta'))
    cent = np.array([p.centroid for p in props])
    lay = c.layer(); d = c.draw(lay)
    if len(cent) > 1:
        dm = np.hypot(*(cent[:, None] - cent[None]).transpose(2, 0, 1)); np.fill_diagonal(dm, np.inf)
        for i, j in enumerate(dm.argmin(1)):
            d.line([c.p(cent[i]), c.p(cent[j])], fill=COLOURS['yellow'] + (230,), width=2)
    for p in cent:
        dot(d, c.p(p), 3, COLOURS['orange'], fill=True)
    layers.append(L('distribution', f'{what} 분포 양상', lay, [('ft_lesion_generic_distribution', lesions.distribution_pattern(mask, fov=fov))],
                    'lesions.distribution_pattern', '조각 중심(주황 점)마다 가장 가까운 이웃(노란 선) 거리의 평균 ÷ 무작위 기대값 = Clark–Evans R', 'yellow'))
    if vessel is not None:
        near = ndimage.distance_transform_edt(~vessel) <= 10
        lay = c.mask(vessel, COLOURS['cyan'], 90, 90)
        lay = c.mask(mask & near, COLOURS['red'], 220, layer=lay)
        lay = c.mask(mask & ~near, COLOURS['orange'], 90, layer=lay)
        layers.append(L('vessel', f'{what}–혈관 거리', lay, [('ft_lesion_vessel_relation', lesions.vessel_relation(mask, vessel))],
                        'lesions.vessel_relation', f'혈관 mask(하늘색)까지 {what} 화소의 평균 거리와 10 px 이내(빨강) 비율', 'cyan'))
    return layers


def landmark_layer(c, disc, fovea, dd, how):
    distance, angle = optic_disc.disc_fovea_geometry(disc, fovea, disc_diameter_px=dd)
    lay = c.layer(); d = c.draw(lay)
    d.line([c.p(disc), c.p(fovea)], fill=COLOURS['yellow'] + (255,), width=3)
    d.line([c.p(disc), (c.p(fovea)[0], c.p(disc)[1])], fill=COLOURS['white'] + (200,), width=2)
    dot(d, c.p(disc), dd / 2 * c.scale, COLOURS['green'], 3)
    dot(d, c.p(fovea), 6, COLOURS['red'], fill=True)
    return L('landmark', '유두–중심와 거리·각도', lay, [('ft_disc_fovea_distance', distance), ('ft_disc_fovea_angle', angle)],
             'optic_disc.disc_fovea_geometry', how + '; 노란 선 길이 ÷ 유두지름, 흰 수평선과의 각(아래가 +)', 'yellow')


def texture_layer(c, gray, fov, how):
    return L('texture', '영상 질감', c.mask(fov, COLOURS['white'], 0, 220), [('ft_image_texture', rm_image.texture(gray, fov=fov))],
             'image.texture', how, 'white')


def vessel_suite(c, vessel, centre, *, fov=None, colour='red', keys=None):
    """Vessel-map measures on one binary vessel / flow mask; ``keys`` limits the layers."""
    skel = skmorph.skeletonize(vessel)
    out = []
    want = (lambda k: keys is None or k in keys)
    if want('density'):
        lay = c.mask(vessel, COLOURS[colour], 120, 120)
        lay = c.mask(skmorph.binary_dilation(skel, skmorph.disk(1)), COLOURS['white'], 255, 255, layer=lay)
        out.append(L('density', '혈관 면적·길이 밀도', lay,
                     [('ft_vessel_area_density', vessels.area_density(vessel, fov=fov)), ('ft_vessel_length_density', vessels.length_density(vessel, fov=fov)),
                      ('ft_vessel_pixel_count', vessels.pixel_count(vessel))],
                     'vessels.area_density · length_density · pixel_count', '혈관 화소 ÷ 영역(면적 밀도), 1화소 중심선(흰색) 길이 ÷ 영역(길이 밀도), 원시 화소 수', colour))
    if want('fractal'):
        lay = c.mask(vessel, COLOURS['cyan'], 150, 150); d = c.draw(lay)
        h, w = vessel.shape
        for s in (h // 8, h // 4):
            for y0 in range(0, h, s):
                d.line([c.p((y0, 0)), c.p((y0, w))], fill=COLOURS['white'] + (90,), width=1)
            for x0 in range(0, w, s):
                d.line([c.p((0, x0)), c.p((h, x0))], fill=COLOURS['white'] + (90,), width=1)
        out.append(L('fractal', '프랙탈 차원', lay, [('ft_fractal_dimension', vessels.fractal_dimension(vessel))], 'vessels.fractal_dimension',
                     '상자 크기를 바꿔 가며 혈관이 걸친 상자 수를 세어 log–log 기울기(상자 세기)', 'cyan'))
    if want('tortuosity'):
        segments, _, _ = vessels._segments(skel)
        lay = c.layer(); d = c.draw(lay)
        for seg in segments:
            if len(seg) < 20:
                continue
            path = vessels._ordered_path(seg)
            length = np.hypot(*np.diff(path, axis=0).T).sum(); chord = np.hypot(*(path[-1] - path[0]))
            t = min((length / max(chord, 1) - 1) / 0.3, 1)
            col = (int(74 + t * 174), int(222 - t * 109), int(128 - t * 15))
            d.line([c.p(p) for p in path[::2]], fill=col + (255,), width=3)
        out.append(L('tortuosity', '혈관 구불거림', lay, [('ft_vessel_tortuosity', vessels.tortuosity(vessel))], 'vessels.tortuosity',
                     '20 px 이상 분절마다 경로 길이 ÷ 양 끝 직선거리(곧음 초록 → 구불 빨강)', 'green'))
    if want('branch'):
        nb = vessels._neighbour_count(skel)
        lay = c.mask(vessel, COLOURS['blue'], 50, 50); d = c.draw(lay)
        jl, nj = ndimage.label(skel & (nb >= 3), structure=np.ones((3, 3)))
        for k in range(1, nj + 1):
            dot(d, c.p(np.argwhere(jl == k).mean(0)), 4, COLOURS['yellow'], 2)
        out.append(L('branch', '분지각', lay, [('ft_branching_angle', vessels.branching_angle(vessel))], 'vessels.branching_angle',
                     '분지점(노란 원)마다 8 px 떨어진 세 가지 끝 사이 각 중 딸가지 사이 각', 'yellow'))
    if want('topology'):
        nb = vessels._neighbour_count(skel)
        lay = c.layer(); d = c.draw(lay)
        rad = max(1.5, 2.5 * c.scale)
        for r, q in np.argwhere(skel & (nb >= 3))[::3]:
            dot(d, c.p((r, q)), rad, COLOURS['yellow'], fill=True)
        for r, q in np.argwhere(skel & (nb == 1))[::3]:
            dot(d, c.p((r, q)), rad, COLOURS['magenta'], fill=True)
        labels, _ = ndimage.label(vessel, structure=np.ones((3, 3)))
        sizes = np.bincount(labels.ravel()); sizes[0] = 0
        big = labels == sizes.argmax()
        lay = c.mask(vessel & ~big, COLOURS['red'], 200, 200, layer=lay)
        out.append(L('topology', '분지점·끝점·연결성', lay,
                     [('ft_vessel_topology', vessels.topology(vessel, fov=fov)), ('ft_vessel_connectivity', vessels.connectivity(vessel))],
                     'vessels.topology · connectivity', '분지점(노랑)·끝점(자홍, 3개 중 1개만 표시) 밀도, 가장 큰 연결 덩어리 비율(떨어진 조각 = 빨강)', 'yellow'))
    if want('path'):
        segments, _, _ = vessels._segments(skel)
        lay = c.layer(); d = c.draw(lay)
        for i, seg in enumerate(s for s in segments if len(s) >= 5):
            col = (COLOURS['magenta'], COLOURS['cyan'], COLOURS['yellow'])[i % 3]
            pts = [c.p(p) for p in vessels._ordered_path(seg)]
            if len(pts) > 1:
                d.line(pts, fill=col + (255,), width=2)
        out.append(L('path', '혈관 경로 길이', lay, [('ft_vessel_path_length', vessels.path_length(vessel))], 'vessels.path_length',
                     '분지점 사이 중심선 분절(색을 번갈아 표시)마다 길이; 평균·합계', 'magenta'))
    if want('regional'):
        lay = c.mask(vessel, COLOURS['cyan'], 110, 110); d = c.draw(lay)
        rmax = float(np.hypot(*np.maximum(np.abs(np.asarray(centre)), np.abs(np.array(vessel.shape) - centre))))
        for k in (0.33, 0.66):
            x, y = c.p(centre); rr = k * rmax * c.scale
            d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=COLOURS['yellow'] + (230,), width=2)
        x, y = c.p(centre)
        d.line((0, y, c.size[0], y), fill=COLOURS['yellow'] + (230,), width=2); d.line((x, 0, x, c.size[1]), fill=COLOURS['yellow'] + (230,), width=2)
        out.append(L('regional', '구역별 혈관 점유율', lay, [('ft_vessel_regional_density', vessels.regional_density(vessel, centre))],
                     'vessels.regional_density', '중심을 지나는 노란 십자로 위·아래·왼쪽·오른쪽, 노란 고리로 안·가운데·바깥 구역을 나눠 혈관 비율', 'yellow'))
    if want('beading'):
        dist = ndimage.distance_transform_edt(vessel)
        width = np.where(skel, 2 * dist - 1, 0)
        lay = c.layer(); d = c.draw(lay)
        wmax = np.percentile(width[skel], 95) if skel.any() else 1
        for r, q in np.argwhere(skel)[::2]:
            t = min(width[r, q] / wmax, 1)
            x, y = c.p((r, q)); d.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill=(int(56 + t * 192), int(189 - t * 76), int(248 - t * 135), 255))
        out.append(L('beading', '혈관 구경 변동', lay, [('ft_vb_caliber_variation', vessels.caliber_variation(vessel))], 'vessels.caliber_variation',
                     '30 px 이상 분절마다 중심선 국소 폭(가는 하늘색 → 굵은 빨강)의 최대/최소 비와 변동계수', 'red'))
    return out


def bright_vessels(g, radius=6, pct=88, min_size=60):
    """Service vessel map for angiograms / OCTA: white top-hat above a percentile, small specks removed."""
    th = skmorph.white_tophat(ndimage.gaussian_filter(g, 1), skmorph.disk(radius))
    v = th > np.percentile(th, pct)
    return skmorph.remove_small_objects(v, min_size)


def bright_spots(g, *, radius, pct, min_px, max_px=None, exclude=None):
    """Service spot detector: small white top-hat peaks (dots, leaks, atrophy) with area limits."""
    th = skmorph.white_tophat(ndimage.gaussian_filter(g, 1), skmorph.disk(radius))
    m = th > np.percentile(th, pct)
    if exclude is not None:
        m &= ~exclude
    m = skmorph.remove_small_objects(skmorph.binary_opening(m, skmorph.disk(1)), min_px)
    if max_px:
        lab, n = ndimage.label(m)
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = np.isin(lab, [k + 1 for k, s in enumerate(sizes) if s <= max_px])
    return m


def ring_disc(shape, centre, radius):
    yy, xx = np.indices(shape)
    return np.hypot(yy - centre[0], xx - centre[1]) <= radius


# ---------------------------------------------------------------- FA

def fa_macula_examples() -> list[dict]:
    out = []
    early = Image.open(atlas_fig.ARTICLE_FIGURES / 'fa_early.jpg').convert('L')
    late = Image.open(atlas_fig.ARTICLE_FIGURES / 'fa_late.jpg').convert('L').resize(early.size)
    g = np.asarray(early, float); gl = np.asarray(late, float)
    h, w = g.shape
    yy, xx = np.indices(g.shape)
    fov = ~((xx < 0.09 * w) & (yy < 0.11 * h))                 # panel letter
    vessel = bright_vessels(g, radius=7, pct=86) & fov
    sm = ndimage.gaussian_filter(g, 5)
    win = (slice(int(0.4 * h), int(0.75 * h)), slice(int(0.4 * w), int(0.7 * w)))
    r0, c0 = np.unravel_index(sm[win].argmin(), sm[win].shape)
    seed = (r0 + win[0].start, c0 + win[1].start)
    dark = (sm < np.percentile(sm, 4)) & ring_disc(g.shape, seed, 0.09 * w)
    lab, _ = ndimage.label(dark)
    fz = ndimage.binary_fill_holes(skmorph.binary_closing(lab == lab[seed], skmorph.disk(4)))
    fovea = tuple(np.argwhere(fz).mean(0))
    c = Canvas(early.convert('RGB'))
    layers = vessel_suite(c, vessel, fovea, fov=fov, colour='red', keys={'density', 'fractal', 'tortuosity', 'branch', 'beading'})
    layers.append(L('faz', 'FAZ 면적·원형도', c.mask(fz, COLOURS['yellow'], 110),
                    [('ft_faz_area', octa.faz_area(fz, feature_id='ft_faz_area')), ('ft_faz_circularity', octa.faz_shape(fz))],
                    'octa.faz_area · faz_shape', '중심 가까이 가장 어두운 점에서 이어진 어두운 영역(하위 4 %, 노랑)의 화소 수와 4πA/P²', 'yellow'))
    ex = dict(id='ex_fa_macula', modality='fa', modality_label='형광안저혈관조영', region='황반 혈관·FAZ',
              title='FA · 황반 혈관망과 FAZ', source=_figure_source('fa_early.jpg'), source_file='retinal_atlas_modality_figures/fa_early.jpg',
              caption='형광안저혈관조영 초기 사진입니다. 밝은 혈관을 톱햇 규칙으로 분할(서비스 추정)해 혈관 지도 함수를, 중심의 어두운 무혈관 구역으로 FAZ 함수를 '
                      '실행했습니다. 화소 단위입니다.')
    out.append(write_example(ex, c, layers))

    # leakage / staining spots: late-phase bright patches outside vessels, compared with the early frame
    diff = ndimage.gaussian_filter(gl, 3) - ndimage.gaussian_filter(g, 3)
    from skimage import measure as skm

    def blobs(img, extra):
        th = skmorph.white_tophat(ndimage.gaussian_filter(img, 2), skmorph.disk(25))
        m = (th > np.percentile(th[fov], 95)) & extra & ~ndimage.binary_dilation(vessel, iterations=2) & fov
        m = skmorph.remove_small_objects(skmorph.binary_opening(m, skmorph.disk(1)), 30)
        lab = skm.label(m)
        return np.isin(lab, [p.label for p in skm.regionprops(lab) if p.eccentricity < 0.95 and p.solidity > 0.5])
    leak_l = blobs(gl, diff > np.percentile(diff[fov], 90))
    leak_e = blobs(g, np.ones_like(fov)) & ndimage.binary_dilation(leak_l, iterations=15)
    c = Canvas(late.convert('RGB'))
    layers = lesion_suite(c, leak_l, fovea=fovea, fov=fov, vessel=vessel, what='과형광', ring_dd=1.0)
    layers = [la for la in layers if la['key'] != 'regional'] + [
        L('regional', '구역별 과형광 비율', c.mask(leak_l, COLOURS['green'], 150), [('ft_lesion_regional_fraction',
          lesions.regional_fraction(leak_l, fovea, 0.25 * w))], 'lesions.regional_fraction', '과형광 면적 중 중심와(FAZ 중심) 반지름 ¼ 영상폭 원 안 비율', 'green'),
        L('change', '초기 → 후기 과형광 변화', c.mask(leak_l, COLOURS['orange'], 110, layer=c.mask(leak_e, COLOURS['cyan'], 0, 255)),
          [('ft_lesion_generic_change', lesions.change(leak_e, leak_l))], 'lesions.change',
          '같은 방문 초기(하늘색 윤곽) → 후기(주황) 과형광 면적 차이; 시점 간격이 분 단위라 연간 변화율은 계산하지 않음', 'orange')]
    ex = dict(id='ex_fa_leak', modality='fa', modality_label='형광안저혈관조영', region='과형광 병변(공통)',
              title='FA · 과형광 병변(공통)', source=_figure_source('fa_late.jpg'), source_file='retinal_atlas_modality_figures/fa_late.jpg',
              caption='같은 눈의 후기 사진에서 초기보다 밝아진 혈관 밖 반점(누출·착색)을 서비스 규칙(후기−초기 차이 상위 10 %·톱햇)으로 분할해 병변 공통 함수를 실행했습니다. 중심와는 FAZ 중심, '
                      '유두는 사진 밖이라 사분면 항목은 광각 FA 예시에 있습니다. 화소 단위입니다.')
    out.append(write_example(ex, c, layers))
    return out


def fa_widefield_pdr_example() -> dict:
    base, _ = masked('paper_nonperfusion')
    g = np.asarray(base.convert('L'), float)
    fov = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.gaussian_filter(g, 4) > 12), iterations=6)
    disc, dd = (268.0, 195.0), 48.0          # leakage centre at the vessel convergence (service estimate), disc size assumed
    fovea = (300.0, 318.0)                   # ~2.5 DD temporal, darkest smoothed point in that window (service estimate)
    vessel = bright_vessels(g, radius=6, pct=85) & fov
    sm = ndimage.gaussian_filter(g, 5)
    th = skmorph.white_tophat(sm, skmorph.disk(25))
    leak = (th > np.percentile(th[fov], 96)) & fov & ~ndimage.binary_dilation(vessel & (ndimage.gaussian_filter(g, 1) > sm + 15), iterations=1)
    leak = skmorph.remove_small_objects(skmorph.binary_opening(leak, skmorph.disk(2)), 60)
    near_disc = ring_disc(g.shape, disc, dd)
    nvd, nve = leak & near_disc, leak & ~near_disc
    nvd = nvd | (leak & ndimage.binary_dilation(nvd, iterations=12) & ring_disc(g.shape, disc, 1.6 * dd))
    nve = nve & ~nvd
    c = Canvas(base)

    def ring_outline(lay, r, col):
        d = c.draw(lay); x, y = c.p(disc); rr = r * c.scale
        d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=col + (230,), width=2)
        return lay
    layers = [L('nvd', 'NVD 존재·범위', ring_outline(c.mask(nvd, COLOURS['red'], 130), dd, COLOURS['white']),
                [('ft_nvd_presence', lesions.presence(nvd, feature_id='ft_nvd_presence')), ('ft_nvd_area', lesions.area(nvd, feature_id='ft_nvd_area'))],
                'lesions.presence · area', '유두 1 DD 원(흰색) 안과 이어진 누출 과형광(빨강): 있음 여부와 화소 수', 'red'),
              L('nve', 'NVE 존재·범위', ring_outline(c.mask(nve, COLOURS['orange'], 130), dd, COLOURS['white']),
                [('ft_nve_presence', lesions.presence(nve, feature_id='ft_nve_presence')), ('ft_nve_area', lesions.area(nve, feature_id='ft_nve_area'))],
                'lesions.presence · area', '유두 1 DD 밖 누출 과형광(주황): 있음 여부와 화소 수', 'orange'),
              landmark_layer(c, disc, fovea, dd, '유두(누출 중심)와 중심와는 서비스 추정 위치')]
    layers += [la for la in lesion_suite(c, leak, fovea=fovea, disc=disc, dd=dd, fov=fov, what='누출')
               if la['key'] in ('quadrant', 'distribution', 'position')]
    src, file = masked_source('paper_nonperfusion')
    ex = dict(id='ex_fa_widefield_pdr', modality='fa', modality_label='형광안저혈관조영', region='광각 신생혈관',
              title='FA · 광각 신생혈관(NVD·NVE)', source=src, source_file=file,
              caption='증식 당뇨망막병증 광각 형광안저혈관조영입니다. 누출 과형광은 서비스 톱햇 규칙 추정, 유두 중심은 누출이 모이는 혈관 수렴점, '
                      '중심와는 유두에서 약 2.5 DD 귀쪽으로 서비스가 정했습니다. 화소 단위입니다.')
    return write_example(ex, c, layers)


# ---------------------------------------------------------------- FAF

def faf_lesion_examples() -> list[dict]:
    out = []
    base, dots = masked('paper_white_dots')
    g = np.asarray(base.convert('L'), float)
    fov = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.gaussian_filter(g, 4) > 25), iterations=8)
    yy, xx = np.indices(g.shape)
    fov &= ~((xx < 60) & (yy < 60))
    disc, fovea, dd = (281.0, 383.0), (291.0, 318.0), 34.0     # dark disc and foveal hypo-AF read on the figure (service estimate)
    c = Canvas(base)
    layers = lesion_suite(c, dots & fov, fovea=fovea, disc=disc, dd=dd, fov=fov, what='반점')
    layers.append(landmark_layer(c, disc, fovea, dd, '유두(어두운 원)와 중심와(어두운 점)는 그림에서 서비스가 읽은 위치'))
    layers.append(texture_layer(c, g, fov, '판독 가능한 시야(흰 윤곽) 안 회색조 GLCM 대비·균질도·에너지·상관과 LBP 엔트로피'))
    src, file = masked_source('paper_white_dots')
    out.append(write_example(dict(id='ex_faf_dots', modality='faf', modality_label='자가형광', region='다발 반점(공통)',
                                  title='FAF · 광각 다발 반점(공통)', source=src, source_file=file,
                                  caption='백점 증후군 눈의 광각 자가형광입니다. 반점 mask는 아틀라스 그림과 같은 서비스 추정이며, 이 mask로 병변 공통 함수를 실행했습니다. '
                                          '거리는 유두지름(DD) 단위입니다.'), c, layers))
    base, ring = masked('paper_bulls_eye')
    g = np.asarray(base.convert('L'), float)
    hull = ndimage.binary_fill_holes(ndimage.binary_closing(ring, iterations=3))
    sm2 = ndimage.gaussian_filter(g, 2)
    atr = hull & (sm2 < 0.55 * np.median(sm2[~hull & (sm2 > 40)]))
    atr = skmorph.remove_small_objects(atr, 30)
    fovea = tuple(np.argwhere(hull).mean(0))
    c = Canvas(base)
    lay = c.mask(atr, COLOURS['blue'], 120); d = c.draw(lay)
    dot(d, c.p(fovea), 7, COLOURS['red'], fill=True)
    layers = [L('area', '위축 면적·초점 수', c.mask(atr, COLOURS['blue'], 120),
                [('ft_atrophy_area', atrophy.area(atr)), ('ft_atrophy_focality', atrophy.focality(atr, min_area_px=30))],
                'atrophy.area · focality', '표시 영역 안에서 주변 배경 중앙값의 55 % 미만인 저자가형광(파랑) 화소 수와 30 px 이상 조각 수', 'blue'),
              L('fovea', '중심와 침범', lay, [('ft_atrophy_foveal_involvement', atrophy.foveal_involvement(atr, fovea))],
                'atrophy.foveal_involvement', '표시 영역 중심(빨간 점 = 중심와로 가정)이 위축 화소 위에 있는지; 소눈 모양이라 중심이 남아 있음', 'red')]
    src, file = masked_source('paper_bulls_eye')
    out.append(write_example(dict(id='ex_faf_atrophy', modality='faf', modality_label='자가형광', region='위축 면적',
                                  title='FAF · 소눈 모양 위축', source=src, source_file=file,
                                  caption='소눈(bull’s eye) 모양 황반병증의 자가형광입니다. 위축은 저자 표시 영역 안 어두운 부분을 서비스 밝기 규칙으로 분할했고, '
                                          '중심와는 그 영역의 중심으로 가정했습니다.'), c, layers))
    return out


# ---------------------------------------------------------------- NIR

def nir_examples() -> list[dict]:
    out = []
    img = Image.open(atlas_fig.ARTICLE_FIGURES / 'nir_widefield.jpg').convert('L')
    g = np.asarray(img, float)
    fov = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.gaussian_filter(g, 4) > 30), iterations=10)
    yy, xx = np.indices(g.shape)
    fov &= ~((xx < 110) & (yy < 110)) & ~((xx < 90) & (yy > 720))      # 'IR' label and scale bar
    disc, dd, fovea = (410.0, 526.0), 74.0, (410.0, 330.0)               # disc read on the figure; fovea ~2.6 DD temporal (service)
    discm = ring_disc(g.shape, disc, dd / 2)
    dots = bright_spots(g, radius=6, pct=97.0, min_px=6, max_px=400, exclude=ring_disc(g.shape, disc, 0.9 * dd) | ~fov)
    vessel = (skmorph.black_tophat(ndimage.gaussian_filter(g, 1.5), skmorph.disk(6)) > 14) & fov
    vessel = skmorph.remove_small_objects(vessel, 80)
    c = Canvas(img.convert('RGB'))
    layers = lesion_suite(c, dots, fovea=fovea, disc=disc, dd=dd, fov=fov, vessel=vessel, what='밝은 점')
    layers.append(landmark_layer(c, disc, fovea, dd, '유두는 그림에서 읽은 위치, 중심와는 유두에서 약 2.6 DD 귀쪽 어두운 황반 중심(서비스 추정)'))
    dist = ndimage.distance_transform_edt(~discm)
    sm = ndimage.gaussian_filter(g, 2)
    ppa = (dist > 1) & (dist < 0.35 * dd) & (sm > np.percentile(sm[(dist > dd) & (dist < 2 * dd)], 85)) & ~vessel
    ppa = skmorph.remove_small_objects(skmorph.binary_closing(ppa, skmorph.disk(2)), 40)
    layers.append(L('ppa', '유두주위 위축 면적', c.mask(ppa, COLOURS['yellow'], 150, layer=c.mask(discm, COLOURS['white'], 0, 200)),
                    [('ft_ppa_area', optic_disc.ppa_area(ppa))], 'optic_disc.ppa_area',
                    '유두 경계(흰 원) 바깥 0.35 DD 띠에서 주변보다 밝은 반달 부분(노랑)의 화소 수 — 서비스 밝기 규칙', 'yellow'))
    radius, n = 0.85 * dd, 360
    ang = np.radians(np.arange(n))
    rows = disc[0] - radius * np.sin(ang); cols = disc[1] + radius * np.cos(ang)
    prof = ndimage.uniform_filter1d(ndimage.map_coordinates(ndimage.gaussian_filter(g, 2), [rows, cols], order=1), 9, mode='wrap')
    ref = ndimage.uniform_filter1d(prof, 91, mode='wrap')
    m = optic_disc.rnfl_defect_angle(prof, normal_um=ref, fraction=0.9)
    lay = c.layer(); d = c.draw(lay)
    for k in range(n):
        x, y = c.p((rows[k], cols[k])); d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(COLOURS['red'] if prof[k] < 0.9 * ref[k] else COLOURS['green']) + (255,))
    layers.append(L('rnfl', 'RNFL 결손 각도', lay, [('ft_rnfl_defect_angle', m)], 'optic_disc.rnfl_defect_angle',
                    '유두 중심에서 0.85 DD 고리의 밝기가 ±45° 이동 평균의 90 % 미만(빨강)으로 이어진 가장 긴 호; 혈관 그림자도 짧게 잡힘', 'red'))
    layers.append(texture_layer(c, g, fov, '판독 가능한 시야(흰 윤곽) 안 GLCM 질감과 LBP 엔트로피'))
    out.append(write_example(dict(id='ex_nir_widefield', modality='nir', modality_label='근적외선', region='광각 밝은 점·유두(공통)',
                                  title='근적외선 · 광각 밝은 점과 유두 둘레', source=_figure_source('nir_widefield.jpg'),
                                  source_file='retinal_atlas_modality_figures/nir_widefield.jpg',
                                  caption='광각 근적외선 사진입니다. 흩어진 밝은 점을 서비스 톱햇 규칙으로 분할해 병변 공통 함수를, 유두 둘레에서 위축·결손 함수를 실행했습니다. '
                                          '화소 단위이며 유두 크기는 그림에서 읽은 값입니다.'), c, layers))
    fig = provider('iovs-67-8-46-f001.jpg')
    box = (0, 320, 118, 448)
    im = fig.crop(box)
    a = np.asarray(im, float); gray = a.mean(2)
    green = a[..., 1] > a[..., 0] + 20
    sm = ndimage.gaussian_filter(gray, 3)
    k = 5
    box_m = np.zeros_like(gray, bool); box_m[31:104, 27:97] = True     # inside the author's green scan box
    atr = (sm > np.percentile(sm[box_m], 78)) & ~ndimage.binary_dilation(green, iterations=1) & box_m
    atr = skmorph.remove_small_objects(atr, 25)
    fovea = (387 - 320, 61.5)            # centre of the author's green scan box (macular cube centred on the fovea)
    big = im.resize((im.width * k, im.height * k), Image.LANCZOS)
    up = lambda m: np.kron(m, np.ones((k, k), bool))
    c = Canvas(big, 700)
    fv = (fovea[0] * k, fovea[1] * k)
    lay = c.mask(up(atr), COLOURS['yellow'], 120); d = c.draw(lay); dot(d, c.p(fv), 8, COLOURS['red'], fill=True)
    layers = [L('area', '위축 면적·초점 수', c.mask(up(atr), COLOURS['yellow'], 120),
                [('ft_atrophy_area', atrophy.area(atr)), ('ft_atrophy_focality', atrophy.focality(atr, min_area_px=25))],
                'atrophy.area · focality', '저자 스캔 상자 안에서 밝은(상위 22 %) 창백한 위축(노랑)의 원 그림 화소 수와 25 px 이상 조각 수', 'yellow'),
              L('fovea', '중심와 침범', lay, [('ft_atrophy_foveal_involvement', atrophy.foveal_involvement(atr, fovea, radius_px=3))],
                'atrophy.foveal_involvement', '저자 스캔 상자 중심(빨간 점 = 중심와 가정) 반지름 3 px 안에 위축이 있는지', 'red')]
    out.append(write_example(dict(id='ex_nir_atrophy', modality='nir', modality_label='근적외선', region='위축 면적',
                                  title='근적외선 · 다발 위축', source='corradetti2026', source_file='provider_figures/iovs-67-8-46-f001.jpg',
                                  caption='나이관련황반변성 눈의 기준 근적외선 사진(저자 Figure 1 셋째 줄, 5배 확대)입니다. 밝은 위축 반점은 서비스 밝기 규칙 추정, '
                                          '중심와는 황반 스캔 상자의 중심으로 가정했습니다.'), c, layers))
    return out


# ---------------------------------------------------------------- ICGA

def icga_examples() -> list[dict]:
    out = []
    base, _ = masked('paper_choroidal_hyperpermeability')
    g = np.asarray(base.convert('L'), float)
    disc, dd, fovea = (268.0, 505.0), 120.0, (275.0, 255.0)     # dark disc at the right edge; fovea ~2 DD temporal (service)
    fov = ~ring_disc(g.shape, disc, 0.7 * dd)
    yy, xx = np.indices(g.shape); fov &= ~((xx < 30) & (yy > 500))
    vessel = skmorph.remove_small_objects(bright_vessels(g, radius=6, pct=93) & fov, 120)
    spots = bright_spots(g, radius=5, pct=98.6, min_px=4, max_px=600, exclude=ndimage.binary_dilation(vessel, iterations=2) | ~fov)
    c = Canvas(base)
    layers = lesion_suite(c, spots, fovea=fovea, disc=disc, dd=dd, fov=fov, vessel=vessel, what='과형광 점', ring_dd=1.0)
    src, file = masked_source('paper_choroidal_hyperpermeability')
    out.append(write_example(dict(id='ex_icga_spots', modality='icga', modality_label='ICGA', region='과형광 점(공통)',
                                  title='ICGA · 과형광 점(공통)', source=src, source_file=file,
                                  caption='맥락막 투과성 증가 눈의 인도시아닌그린혈관조영입니다. 혈관 밖 밝은 점을 서비스 톱햇 규칙으로 분할해 병변 공통 함수를 실행했습니다. '
                                          '유두는 오른쪽 가장자리의 어두운 원, 중심와는 약 2 DD 귀쪽으로 서비스가 정했습니다.'), c, layers))
    base, ring = masked('paper_polypoidal')
    psrc, pfile = masked_source('paper_polypoidal')
    gg = ndimage.gaussian_filter(np.asarray(base.convert('L'), float), 2)
    ys, xs = np.nonzero(ring)
    cy, cx = ys.mean(), xs.mean()
    roi = ring_disc(gg.shape, (cy, cx), 75)
    net = (gg > np.percentile(gg[roi], 75)) & roi
    net = skmorph.remove_small_objects(skmorph.binary_opening(net, skmorph.disk(1)), 25)
    c = Canvas(base)
    lay = c.mask(net, COLOURS['magenta'], 120); d = c.draw(lay); x, y = c.p((cy, cx)); rr = 75 * c.scale
    d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=COLOURS['white'] + (200,), width=2)
    out.append(write_example(dict(id='ex_icga_mnv', modality='icga', modality_label='ICGA', region='황반 신생혈관',
                                  title='ICGA · 결절·분지 혈관망 면적', source=psrc, source_file=pfile,
                                  caption='결절성 맥락막혈관병증 눈의 인도시아닌그린혈관조영입니다. 저자 화살표 둘레(흰 원) 안의 밝은 결절·분지 혈관망을 서비스 밝기 규칙(상위 25 %)으로 '
                                          '분할했습니다. 화소 단위입니다.'), c,
                             [L('area', 'MNV 병변·혈관망 면적', lay, [('ft_mnv_lesion_area', oct_lesions.enface_area(net[:, None, :], feature_id='ft_mnv_lesion_area'))],
                                'oct_lesions.enface_area', '흰 원 안 밝은 결절·혈관망(자홍)의 화소 수', 'magenta')]))
    return out


# ---------------------------------------------------------------- OCTA

def octa_vessel_examples() -> list[dict]:
    out = []
    base, flow = masked('octa_scp_flow')
    g = np.asarray(base.convert('L'), float)
    _, faz = masked('octa_faz')
    centre = tuple(np.argwhere(faz).mean(0)) if faz.any() else (g.shape[0] / 2, g.shape[1] / 2)
    yy, xx = np.indices(g.shape)
    fov = ~((xx < 0.33 * g.shape[1]) & (yy > 0.78 * g.shape[0]))
    flow = flow & fov
    c = Canvas(base, 700)
    layers = vessel_suite(c, flow, centre, fov=fov, colour='red', keys={'density', 'fractal', 'tortuosity', 'topology', 'path', 'regional'})
    src, file = masked_source('octa_scp_flow')
    out.append(write_example(dict(id='ex_octa_graph', modality='octa', modality_label='OCTA', region='표층 혈관 그래프',
                                  title='OCTA · 표층 혈관 그래프', source=src, source_file=file,
                                  caption='건강한 눈 OCTA 표층 슬랩의 혈류 mask(아틀라스 그림과 같은 서비스 이진화)로 혈관 지도 함수를 실행했습니다. '
                                          '구역 중심은 FAZ 중심입니다. 화소 단위입니다.'), c, layers))
    fig = provider('40942_2022_406_Fig2_HTML.jpg')
    im = fig.crop((0, 0, int(fig.width / 4) - 6, 465))
    gg = ndimage.gaussian_filter(np.asarray(im.convert('L'), float), 2)
    flow = skmorph.remove_small_objects(gg > octa.phansalkar_threshold(gg, window=31), 30)
    gap = octa.nonperfusion_from_vessels(flow, min_gap_px=6)
    h, w = gap.shape
    lab, _ = ndimage.label(gap)
    sm = ndimage.gaussian_filter(np.asarray(im.convert('L'), float), 8)
    win = sm[h // 2 - 90:h // 2 + 90, w // 2 - 90:w // 2 + 90]
    dy, dx = np.unravel_index(win.argmin(), win.shape)
    fazl = lab[h // 2 - 90 + dy, w // 2 - 90 + dx]
    np_mask = gap & (lab != fazl) if fazl else gap
    np_mask = skmorph.remove_small_objects(np_mask, 30)
    fov = np.ones_like(np_mask); fov[:28, :40] = False
    np_mask &= fov
    area, index = octa.nonperfusion(np_mask, fov=fov)
    c = Canvas(im, 600)
    out.append(write_example(dict(id='ex_octa_np', modality='octa', modality_label='OCTA', region='무관류 영역',
                                  title='OCTA · 모세혈관 무관류', source='bromeo2022', source_file='provider_figures/40942_2022_406_Fig2_HTML.jpg',
                                  caption='당뇨황반부종 눈의 OCTA 표층 슬랩(저자 Fig. 2A)입니다. 혈류 화소에서 6 px 넘게 떨어진 영역을 무관류 후보로, FAZ는 뺐습니다(서비스 추정). '
                                          '화소 단위입니다.'), c,
                             [L('np', '무관류 면적', c.mask(np_mask, COLOURS['blue'], 130, layer=c.mask(flow, COLOURS['white'], 40, 40)),
                                [('ft_nonperfusion_area', area)], 'octa.nonperfusion · nonperfusion_from_vessels',
                                '혈류(흰색)에서 6 px 넘게 떨어진 무관류 후보(파랑) 화소 수; FAZ 제외', 'blue')]))
    return out


# ---------------------------------------------------------------- UWF

def uwf_examples() -> list[dict]:
    out = []
    name = '5_359_2021-04-13_5_L.png'
    import zipfile
    with zipfile.ZipFile(atlas_fig.UWF_ZIP) as z:
        img = Image.open(z.open(next(n for n in z.namelist() if n.endswith('PDR512/' + name)))).convert('RGB')
    a = np.asarray(img, float)
    disc, fovea, dd = (250.0, 208.0), (253.0, 258.0), 15.0          # bright disc and dark fovea read on the image (service)
    gch = ndimage.gaussian_filter(a[..., 1], 1)
    fov = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.gaussian_filter(a.mean(2), 3) > 25), iterations=8)
    yy, xx = np.indices(gch.shape)
    fov &= (yy > 70) & (yy < 440) & (xx > 25) & (xx < 495) & ~((xx < 140) & (yy < 260) & (a[..., 1] > a[..., 0] + 40))
    bh = skmorph.black_tophat(gch, skmorph.disk(6))
    redness = a[..., 0] / (a[..., 1] + 1)
    vessel = skmorph.remove_small_objects((skmorph.black_tophat(gch, skmorph.disk(3)) > 9) & fov, 40)
    hem = (bh > np.percentile(bh[fov], 96)) & (redness > np.percentile(redness[fov], 55)) & fov & ~ndimage.binary_dilation(vessel, iterations=1)
    hem = skmorph.remove_small_objects(skmorph.binary_opening(hem, skmorph.disk(1)), 6) & ~ring_disc(gch.shape, disc, dd)
    c = Canvas(img, 800)
    q = lesions.quadrant_of(np.argwhere(hem), fovea, disc)
    lay = c.layer()
    for qn, col in zip(lesions.QUADRANTS, (COLOURS['cyan'], COLOURS['magenta'], COLOURS['yellow'], COLOURS['green'])):
        m = np.zeros_like(hem); p = np.argwhere(hem)[q == qn]; m[tuple(p.T)] = True
        lay = c.mask(m, col, 220, 255, layer=lay)
    axis = (np.asarray(disc) - fovea) / np.linalg.norm(np.asarray(disc) - fovea); normal = np.array([-axis[1], axis[0]])
    d = c.draw(lay)
    for v in (axis, normal):
        d.line([c.p(np.asarray(fovea) - 3000 * v), c.p(np.asarray(fovea) + 3000 * v)], fill=COLOURS['white'] + (200,), width=2)
    layers = [L('area', '출혈 면적', c.mask(hem, COLOURS['red'], 160), [('ft_hem_area', lesions.area(hem, feature_id='ft_hem_area'))], 'lesions.area',
                '녹색 채널 블랙햇 상위 4 %이면서 붉은 화소(빨강) 수 — 서비스 추정', 'red'),
              L('quadrant', '사분면별 출혈 개수·침범 사분면', lay,
                [('ft_hem_count_quadrant', lesions.quadrant_counts(hem, fovea, disc, min_area_px=6)),
                 ('ft_vascular_change_extent', lesions.quadrant_occupancy(hem, fovea, disc, min_area_px=6))],
                'lesions.quadrant_counts · quadrant_occupancy', '유두–중심와 축(흰 선)으로 나눈 사분면별(색별) 출혈 조각 수와 출혈 있는 사분면 수', 'magenta')]
    out.append(write_example(dict(id='ex_uwf_hem', modality='uwf', modality_label='광각 안저', region='사분면별 출혈',
                                  title='광각 안저 · 사분면별 출혈', source='uwf_dr_2026', source_file='PDR512/' + name,
                                  caption='증식 당뇨망막병증 눈(왼눈)의 광각 SLO 영상(512 px)입니다. 출혈은 서비스 색·블랙햇 규칙 추정이며 혈관 일부가 섞일 수 있습니다. '
                                          '유두·중심와는 영상에서 서비스가 읽은 위치입니다.'), c, layers))
    base, fvp = masked('uwf_fvp')
    a = np.asarray(base, float)
    disc, dd = (338.0, 345.0), 16.0                    # vessel convergence under the membrane (service estimate)
    nve = fvp & ~ring_disc(fvp.shape, disc, dd)
    c = Canvas(base, 800)
    lay = c.mask(nve, COLOURS['orange'], 130); d = c.draw(lay); x, y = c.p(disc); rr = dd * c.scale
    d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=COLOURS['white'] + (230,), width=2)
    field = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.gaussian_filter(a.mean(2), 4) > 30), iterations=25)
    src, file = masked_source('uwf_fvp')
    out.append(write_example(dict(id='ex_uwf_nve', modality='uwf', modality_label='광각 안저', region='섬유혈관 증식',
                                  title='광각 안저 · 유두 밖 신생혈관', source=src, source_file=file,
                                  caption='증식 당뇨망막병증 광각 영상의 섬유혈관 증식막입니다. 막 mask는 아틀라스 그림과 같은 서비스 색 규칙 추정이고, 유두 중심은 혈관 수렴점으로 '
                                          '서비스가 정했습니다.'), c,
                             [L('nve', 'NVE 존재·범위', lay, [('ft_nve_presence', lesions.presence(nve, feature_id='ft_nve_presence')),
                                                              ('ft_nve_area', lesions.area(nve, feature_id='ft_nve_area'))],
                                'lesions.presence · area', '유두 1 DD 원(흰색) 밖 증식막(주황)이 있는지와 화소 수', 'orange'),
                              R('vh', '유리체 출혈 가림 정도', c.mask(field, COLOURS['red'], 0, 200), 'ft_vh_obscuration',
                                '판독 항목(계산 코드 없음) · 망막 시야(빨간 윤곽) 안에서 출혈·혼탁으로 혈관이 안 보이는 범위를 보고 가림 정도(없음/일부/대부분)를 판정',
                                '시야 윤곽만 표시; 가림 정도 판정 코드는 없음', 'red')]))
    return out


# ---------------------------------------------------------------- OCT: atrophy over 18 months, polyp, drusen size

def oct_rora_example() -> dict:
    fig = provider('iovs-67-8-46-f001.jpg')
    boxes = [(123, 327, 360, 418), (511, 327, 748, 418)]      # B-scan panels without the label text

    def hyper(im):
        """Author's yellow ellipse (lesion extent) filled as the lesion mask; fovea = deepest ILM point."""
        a = np.asarray(im, float)
        yellow = (a[..., 0] > 150) & (a[..., 1] > 140) & (a[..., 2] < 110)
        yellow[:8] = False; yellow[:, :4] = False; yellow[:, -4:] = False      # panel frame
        mask = ndimage.binary_fill_holes(ndimage.binary_closing(yellow, iterations=2)) & ~yellow
        mask = skmorph.remove_small_objects(mask, 20)
        g = ndimage.gaussian_filter(a.mean(2), 1)
        h, w = g.shape
        ilm = np.array([int(np.argmax(g[12:, x] > g[12:, x].min() + 0.35 * np.ptp(g[12:, x]))) + 12 for x in range(w)])
        ilm = ndimage.median_filter(ilm, 15)
        mid = slice(int(0.3 * w), int(0.7 * w))
        fovea_col = int(np.argmax(ilm[mid])) + mid.start
        return g, mask, None, (float(ilm[fovea_col]) + 20, float(fovea_col))
    ims = [fig.crop(b) for b in boxes]
    (g0, m0, c0, fov0), (g1, m1, c1, fov1) = hyper(ims[0]), hyper(ims[1])
    k = 3
    pair = Image.new('RGB', (ims[0].width * 2 + 6, ims[0].height), 'black')
    pair.paste(ims[0], (0, 0)); pair.paste(ims[1], (ims[0].width + 6, 0))
    pair = pair.resize((pair.width * k, pair.height * k), Image.LANCZOS)
    W = ims[0].width

    def both(a, b):
        out = np.zeros((ims[0].height, W * 2 + 6), bool); out[:, :W] = a; out[:, W + 6:] = b
        return np.kron(out, np.ones((k, k), bool))
    c = Canvas(pair, 1000)
    f0 = (fov0[0] * k, fov0[1] * k); f1 = (fov1[0] * k, (fov1[1] + W + 6) * k)
    lay = c.mask(both(m0, m1), COLOURS['yellow'], 140); d = c.draw(lay)
    for f in (f0, f1):
        x, y = c.p(f); d.line((x, y - 40, x, y + 40), fill=COLOURS['red'] + (255,), width=3)
    layers = [L('atrophy', '위축 폭·초점 수·중심와 침범', lay,
                [('ft_atrophy_area', atrophy.area(m1)), ('ft_atrophy_focality', atrophy.focality(m1, min_area_px=20)),
                 ('ft_atrophy_foveal_involvement', atrophy.foveal_involvement(m1, fov1, radius_px=4))],
                'atrophy.area · focality · foveal_involvement',
                '저자가 노란 타원으로 표시한 병변 범위(안쪽, 노랑)를 위축 mask로 — 18개월 단면 기준 단면 면적·조각 수, 빨간 선 = 중심와 함요', 'yellow'),
              L('growth', '위축 확장률(18개월)', c.mask(both(m0, m1), COLOURS['orange'], 140), [('ft_atrophy_growth_rate', atrophy.growth_rate(m0, m1, interval_years=1.5))],
                'atrophy.growth_rate', '기준(왼쪽) → 18개월(오른쪽) 표시 범위 면적 제곱근 차이 ÷ 1.5년(원 그림 화소)', 'orange'),
              L('lesion', '병변 존재·면적·폭·변화', c.mask(both(m0, m1), COLOURS['cyan'], 120),
                [('ft_lesion_generic_presence', lesions.presence(m1)), ('ft_lesion_generic_area', oct_lesions.bscan_area(m1)),
                 ('ft_lesion_generic_extent', oct_lesions.lateral_diameter(m1)), ('ft_lesion_generic_change', lesions.change(m0, m1, interval_years=1.5))],
                'lesions.presence · oct_lesions.bscan_area · lateral_diameter · lesions.change', '같은 표시 범위를 병변으로 써서 18개월 단면의 존재·단면 면적·가로 폭과 두 시점 차이', 'cyan'),
              L('distance', '중심와까지 거리', c.mask(both(np.zeros_like(m0), m1), COLOURS['cyan'], 120),
                [('ft_lesion_fovea_distance', lesions.fovea_distance(m1, fov1))], 'lesions.fovea_distance',
                '18개월 단면에서 중심와 함요(빨간 선)부터 병변 화소까지 거리(px)', 'cyan'),
              texture_layer(c, g1, np.ones_like(g1, bool), '18개월 B-scan 전체의 GLCM 질감과 LBP 엔트로피')]
    ex = dict(id='ex_oct_rora', modality='oct', modality_label='OCT', region='위축(RORA) 18개월',
              title='OCT · 위축 18개월 변화', source='corradetti2026', source_file='provider_figures/iovs-67-8-46-f001.jpg',
              caption='같은 눈 같은 위치의 기준(iRORA, 왼쪽)과 18개월(cRORA, 오른쪽) B-scan입니다(저자 Figure 1 셋째 줄, 3배 확대). 병변 범위는 저자가 그린 노란 타원(iRORA→cRORA)을 그대로 썼고 '
                      '단면 하나라 면적은 단면 면적(px²)입니다.')
    return write_example(ex, c, layers)


def oct_small_examples() -> list[dict]:
    out = []
    base, ped = masked('paper_sharp_ped')
    c = Canvas(base)
    src, file = masked_source('paper_sharp_ped')
    out.append(write_example(dict(id='ex_oct_polyp', modality='oct', modality_label='OCT', region='결절(뾰족한 PED)',
                                  title='OCT · 뾰족한 색소상피박리(결절)', source=src, source_file=file,
                                  caption='결절성 맥락막혈관병증 눈의 B-scan에서 저자가 표시한 뾰족한 색소상피박리(결절)입니다. mask는 아틀라스 그림과 같습니다.'), c,
                             [L('count', '결절 개수', c.mask(ped, COLOURS['red'], 120), [('ft_polyp_count', oct_lesions.lesion_count(ped, feature_id='ft_polyp_count'))],
                                'oct_lesions.lesion_count', '뾰족한 PED mask(빨강)의 연결 성분 수', 'red')]))
    base, dr = masked('octid_drusen')
    c = Canvas(base)
    src, file = masked_source('octid_drusen')
    out.append(write_example(dict(id='ex_oct_drusen_size', modality='oct', modality_label='OCT', region='드루젠 크기',
                                  title='OCT · 드루젠 단면 크기', source=src, source_file=file,
                                  caption='드루젠 B-scan(OCTID)입니다. 드루젠 mask는 아틀라스 그림과 같은 서비스 추정이며, 단면 하나라 면적은 단면 면적(px²)입니다.'), c,
                             [L('size', '드루젠 면적·최대 크기', c.mask(dr, COLOURS['yellow'], 140),
                                [('ft_drusen_area', lesions.area(dr, feature_id='ft_drusen_area')), ('ft_drusen_max_size', oct_lesions.lateral_diameter(dr, feature_id='ft_drusen_max_size'))],
                                'lesions.area · oct_lesions.lateral_diameter', '드루젠(노랑) 단면 화소 수와 가장 넓은 가로 폭', 'yellow')]))
    return out


# ---------------------------------------------------------------- published CC BY figures for the remaining items



def arrow_tips(rgb, *, colour='yellow', min_px=15, prefer=None):
    """Author arrow heads: for each coloured component, the end of its long axis that carries more pixels."""
    a = np.asarray(rgb, float)
    if colour == 'yellow':
        m = (a[..., 0] > 170) & (a[..., 1] > 170) & (a[..., 0] - a[..., 2] > 50)
    else:
        m = (a[..., 0] > 150) & (a[..., 1] < 90) & (a[..., 2] < 90)
    lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=2))
    lab = lab * m
    tips = []
    for k in range(1, n + 1):
        p = np.argwhere(lab == k).astype(float)
        if len(p) < min_px:
            continue
        c0 = p.mean(0)
        u = np.linalg.svd(p - c0, full_matrices=False)[2][0]
        t = (p - c0) @ u
        ends = [p[t.argmin()], p[t.argmax()]]
        if prefer == 'down':
            tips.append(max(ends, key=lambda e: e[0]))
        elif prefer == 'left':
            tips.append(min(ends, key=lambda e: e[1]))
        else:
            heavy = [(np.hypot(*(p - e).T) < 5).sum() for e in ends]
            tips.append(ends[int(np.argmax(heavy))])
    if prefer in ('down', 'left'):                    # pieces of one broken arrow: keep the furthest tip
        axis = 1 if prefer == 'down' else 0
        tips = sorted(tips, key=lambda t: -t[1 - axis] if prefer == 'down' else t[1])
        kept = []
        for t in tips:
            if not any(abs(t[axis] - k[axis]) < 12 for k in kept):
                kept.append(t)
        tips = kept
    return tips, m


def disk_mask(shape, points, r):
    out = np.zeros(shape, bool)
    yy, xx = np.indices(shape)
    for y, x in points:
        out |= np.hypot(yy - y, xx - x) <= r
    return out


def magenta_surfaces(rgb):
    """Device segmentation lines drawn in magenta on an OCTA B-scan: upper = RPE, lower = BM (per column)."""
    a = np.asarray(rgb, float)
    m = (a[..., 0] > 140) & (a[..., 2] > 140) & (a[..., 1] < 110)
    lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=1))
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    m &= np.isin(lab, [k + 1 for k, sz in enumerate(sizes) if sz >= 8])      # dashed line pieces, not speckle
    h, w = m.shape
    ys, xs = np.nonzero(m)
    lower = np.array([[x, ys[xs == x].max()] for x in np.unique(xs)], float)
    coef = np.polyfit(lower[:, 0], lower[:, 1], 2)
    resid = lower[:, 1] - np.polyval(coef, lower[:, 0])
    keep = np.abs(resid) < 6                                  # BM: smooth lower dashed line
    coef = np.polyfit(lower[keep, 0], lower[keep, 1], 2)
    xs_all = np.arange(w)
    bot = np.polyval(coef, xs_all)
    top_pts = np.array([[x, ys[xs == x].min()] for x in np.unique(xs)], float)
    above = top_pts[:, 1] < np.polyval(coef, top_pts[:, 0]) - 4     # RPE pieces lifted off BM (PED dome)
    top = bot.copy()
    if above.any():
        xa, ya = top_pts[above, 0], top_pts[above, 1]
        span = (xs_all >= xa.min()) & (xs_all <= xa.max())
        top[span] = np.interp(xs_all[span], xa, ya)
    return ndimage.median_filter(top, 7), bot, m


def pcv_parts():
    fig = provider('ajoc-22-101057-gr4.jpg')
    e = fig.crop((0, 700, 340, 908))
    rpe, bm, lines = magenta_surfaces(e)
    h, w = lines.shape
    rows = np.arange(h)[:, None]
    lesion = (rows > rpe[None] + 2) & (rows < bm[None] - 1) & ((bm - rpe) > 6)[None]
    ilm = np.full(w, 5.0)
    surf = {'ILM': ilm[None], 'EZ': (rpe - 6)[None], 'RPE': rpe[None], 'BM': bm[None]}
    return fig, e, lesion, surf, rpe, bm


def stack(images, gap=6, vertical=True):
    if vertical:
        W = max(i.width for i in images); H = sum(i.height for i in images) + gap * (len(images) - 1)
        out = Image.new('RGB', (W, H), 'black'); y = 0
        offs = []
        for i in images:
            out.paste(i, (0, y)); offs.append((y, 0)); y += i.height + gap
    else:
        H = max(i.height for i in images); W = sum(i.width for i in images) + gap * (len(images) - 1)
        out = Image.new('RGB', (W, H), 'black'); x = 0
        offs = []
        for i in images:
            out.paste(i, (x, 0)); offs.append((0, x)); x += i.width + gap
    return out, offs


def place(shape, mask, off):
    out = np.zeros(shape, bool)
    out[off[0]:off[0] + mask.shape[0], off[1]:off[1] + mask.shape[1]] = mask
    return out


def mnv_type_card(ex_id, modality, label, panel_box, panel_name, caption):
    fig, e, lesion, surf, rpe, bm = pcv_parts()
    top = fig.crop(panel_box)
    comp, offs = stack([top, e])
    shape = (comp.height, comp.width)
    c = Canvas(comp, 700)
    lay = c.mask(place(shape, lesion, offs[1]), COLOURS['blue'], 110); d = c.draw(lay)
    for surf_rows, col in ((rpe, COLOURS['red']), (bm, COLOURS['white'])):
        poly(c, d, surf_rows + offs[1][0], col, 2)
    m = oct_lesions.depth_category(lesion[None], surf)
    return write_example(dict(id=ex_id, modality=modality, modality_label=label, region='MNV 유형(깊이)',
                              title=f'{panel_name} + OCT · MNV 유형', source='shen2021', source_file='provider_figures/ajoc-22-101057-gr4.jpg',
                              caption=caption), c,
                         [L('type', 'MNV 유형(깊이)', lay, [('ft_mnv_type', m)], 'oct_lesions.depth_category',
                            f'위 {panel_name}에서 본 병변을 아래 같은 날 OCT B-scan에서 깊이로 판정: 장비가 그린 자홍 선(위 = RPE 빨강, 아래 = BM 흰색) 사이(파랑)가 '
                            'RPE 아래면 1형', 'blue')])


def remaining_figure_examples() -> list[dict]:
    out = []
    # --- CFP: premacular haemorrhage before / after Nd:YAG hyaloidotomy
    fig = provider('cureus-0018-00000105301-i01.jpg')
    a_img, b_img = fig.crop((0, 0, 375, 375)), fig.crop((375, 0, 750, 375))

    def prh(im, centre):
        lum = ndimage.gaussian_filter(np.asarray(im, float).mean(2), 2)
        yy, xx = np.indices(lum.shape)
        dist = np.hypot(yy - centre[0], xx - centre[1])
        ref = np.median(lum[(dist > 90) & (dist < 140)])
        m = (lum < 0.8 * ref) & (dist < 85)
        m = ndimage.binary_fill_holes(skmorph.remove_small_objects(skmorph.binary_opening(m, skmorph.disk(2)), 150))
        return m
    ma, mb = prh(a_img, (205, 182)), prh(b_img, (210, 195))
    comp, offs = stack([a_img, b_img], vertical=False)
    shape = (comp.height, comp.width)
    c = Canvas(comp, 900)
    both = place(shape, ma, offs[0]) | place(shape, mb, offs[1])
    out.append(write_example(dict(id='ex_cfp_prh_change', modality='cfp', modality_label='안저', region='망막앞 출혈 변화',
                                  title='안저 · 망막앞 출혈 치료 전후', source='douillet2026', source_file='provider_figures/cureus-0018-00000105301-i01.jpg',
                                  caption='같은 눈의 망막앞(유리체막하) 출혈, Nd:YAG 레이저 막절개 전(왼쪽)·후(오른쪽) 안저 사진입니다. 출혈은 서비스 밝기 규칙 추정이며 '
                                          '두 사진의 간격은 원문에 일 단위로만 적혀 있어 연간 변화율은 계산하지 않았습니다. 화소 단위입니다.'), c,
                             [L('area', '망막앞 출혈 면적', c.mask(place(shape, ma, offs[0]), COLOURS['red'], 120),
                                [('ft_prh_area', lesions.area(ma, feature_id='ft_prh_area'))], 'lesions.area',
                                '치료 전 사진에서 둘레 고리 밝기의 80 % 미만인 황반 출혈(빨강)의 화소 수', 'red'),
                              L('change', '병변 변화량', c.mask(both, COLOURS['orange'], 120), [('ft_lesion_generic_change', lesions.change(ma, mb))],
                                'lesions.change', '치료 전(왼쪽) → 후(오른쪽) 출혈 면적 차이', 'orange')]))
    # --- OCTA (Guro 2026): microaneurysms, NVE, NVD, IRMA marked by the authors
    fig = provider('OVS2-103-e70090-g006.webp')
    im = fig.crop((620, 810, 1064, 1012))
    tips, arrows = arrow_tips(im, prefer='down')
    ma = disk_mask(arrows.shape, tips, 4)
    c = Canvas(im, 800)
    lay = c.mask(ma, COLOURS['red'], 150, 255)
    out.append(write_example(dict(id='ex_octa_ma', modality='octa', modality_label='OCTA', region='미세동맥류',
                                  title='OCTA · 미세동맥류', source='guro2026', source_file='provider_figures/OVS2-103-e70090-g006.webp',
                                  caption='중증 비증식 당뇨망막병증 눈의 광각 OCTA 일부(저자 Figure 1 오른쪽 아래)입니다. 저자가 노란 화살표로 가리킨 미세동맥류 무리의 '
                                          '화살표 끝을 병변 점으로 썼습니다(화살표가 없는 미세동맥류는 세지 않음).'), c,
                             [L('ma', '미세동맥류 존재·개수', lay, [('ft_ma_presence', lesions.presence(ma, feature_id='ft_ma_presence')),
                                                                   ('ft_ma_count', lesions.count(ma, feature_id='ft_ma_count'))],
                                'lesions.presence · count', '저자 화살표 끝(빨간 점, 반지름 4 px)의 개수 = 표시된 미세동맥류 무리 수', 'red')]))
    fig = provider('OVS2-103-e70090-g003.webp')
    im = fig.crop((870, 0, 1064, 330))
    g = ndimage.gaussian_filter(np.asarray(im.convert('L'), float), 1)
    nve = (g > np.percentile(g[:190], 80)) & disk_mask(g.shape, [(110, 88)], 13)
    nve = skmorph.remove_small_objects(nve, 6)
    c = Canvas(im, 520)
    out.append(write_example(dict(id='ex_octa_nve', modality='octa', modality_label='OCTA', region='망막 신생혈관(NVE)',
                                  title='OCTA · 유두 밖 신생혈관', source='guro2026', source_file='provider_figures/OVS2-103-e70090-g003.webp',
                                  caption='증식 당뇨망막병증 눈의 OCTA(저자 Figure 6F)입니다. 저자 화살표가 가리킨 고리 모양 혈관 묶음을 반지름 13 px 안 밝은 화소(상위 20 %)로 분할했고, '
                                          '아래 B-scan에서 혈류가 ILM 위로 솟아 있습니다(서비스 추정).'), c,
                             [L('nve', 'NVE 존재·범위', c.mask(nve, COLOURS['orange'], 160), [('ft_nve_presence', lesions.presence(nve, feature_id='ft_nve_presence')),
                                                                                             ('ft_nve_area', lesions.area(nve, feature_id='ft_nve_area'))],
                                'lesions.presence · area', '저자 화살표가 가리키는 혈관 묶음(주황)의 있음 여부와 화소 수', 'orange')]))
    fig = provider('OVS2-103-e70090-g007.webp')
    im = fig.crop((615, 290, 740, 388))
    big = im.resize((im.width * 4, im.height * 4), Image.LANCZOS)
    g = ndimage.gaussian_filter(np.asarray(big.convert('L'), float), 1)
    a = np.asarray(big, float)
    yel = (a[..., 0] > 170) & (a[..., 1] > 170) & (a[..., 2] < 110)
    nvd = (skmorph.white_tophat(g, skmorph.disk(5)) > 35) & disk_mask(g.shape, [(60, 290)], 60) & ~ndimage.binary_dilation(yel, iterations=3)
    nvd = skmorph.remove_small_objects(nvd, 15)
    c = Canvas(big, 520)
    out.append(write_example(dict(id='ex_octa_nvd', modality='octa', modality_label='OCTA', region='유두 신생혈관(NVD)',
                                  title='OCTA · 유두 신생혈관', source='guro2026', source_file='provider_figures/OVS2-103-e70090-g007.webp',
                                  caption='증식 당뇨망막병증 눈의 유두 OCT 영상(저자 Figure 7E 오른쪽 위, 4배 확대)입니다. 저자 화살표가 시작하는 유두 가장자리의 가는 밝은 혈관을 '
                                          '서비스 톱햇 규칙으로 분할했습니다. 원 그림 해상도가 낮아 범위는 대략적입니다.'), c,
                             [L('nvd', 'NVD 존재·범위', c.mask(nvd, COLOURS['red'], 170), [('ft_nvd_presence', lesions.presence(nvd, feature_id='ft_nvd_presence')),
                                                                                         ('ft_nvd_area', lesions.area(nvd, feature_id='ft_nvd_area'))],
                                'lesions.presence · area', '유두 가장자리 반지름 15 px(원 그림) 안 가는 밝은 혈관(빨강)의 있음 여부와 화소 수(4배 확대 화소)', 'red')]))
    fig = provider('OVS2-103-e70090-g004.webp')
    im = fig.crop((830, 505, 1064, 681))
    tips, arrows = arrow_tips(im, prefer='left')
    irma = disk_mask(arrows.shape, tips, 6)
    c = Canvas(im, 700)
    out.append(write_example(dict(id='ex_octa_irma', modality='octa', modality_label='OCTA', region='망막내 미세혈관 이상',
                                  title='OCTA · 망막내 미세혈관 이상', source='guro2026', source_file='provider_figures/OVS2-103-e70090-g004.webp',
                                  caption='중등도 비증식 당뇨망막병증 눈의 OCTA(저자 Figure 3I)입니다. 저자가 노란 화살표로 가리킨 IRMA 위치(화살표 끝)를 병변 점으로 썼습니다.'), c,
                             [L('irma', 'IRMA 존재', c.mask(irma, COLOURS['magenta'], 150, 255), [('ft_irma_presence', lesions.presence(irma, feature_id='ft_irma_presence'))],
                                'lesions.presence', '저자 화살표 끝(자홍 원)이 하나라도 있으면 "예"', 'magenta')]))
    # --- PCV (Shen 2021): OCTA MNV area at baseline / 7 months, MNV type on FA, ICGA and OCTA cards
    fig, e, lesion, surf, rpe, bm = pcv_parts()
    cpan, dpan = fig.crop((0, 350, 340, 680)), fig.crop((350, 350, 694, 680))

    def tangle(im, centre):
        g = ndimage.gaussian_filter(np.asarray(im.convert('L'), float), 1)
        m = (g > np.percentile(g, 93)) & disk_mask(g.shape, [centre], 60)
        return skmorph.remove_small_objects(skmorph.binary_closing(m, skmorph.disk(1)), 20)
    mc, md = tangle(cpan, (114, 165)), tangle(dpan, (175, 170))
    comp, offs = stack([fig.crop((0, 350, 694, 680)), e])
    shape = (comp.height, comp.width)
    c = Canvas(comp, 800)
    mnv_both = place(shape, mc, offs[0]) | place(shape, md, (offs[0][0], 350))
    lay = c.mask(place(shape, lesion, offs[1]), COLOURS['blue'], 110); d = c.draw(lay)
    poly(c, d, rpe + offs[1][0], COLOURS['red'], 2); poly(c, d, bm + offs[1][0], COLOURS['white'], 2)
    out.append(write_example(dict(id='ex_octa_mnv', modality='octa', modality_label='OCTA', region='황반 신생혈관',
                                  title='OCTA · 결절성 맥락막혈관병증 혈관망', source='shen2021', source_file='provider_figures/ajoc-22-101057-gr4.jpg',
                                  caption='결절성 맥락막혈관병증 눈의 SS-OCTA 바깥 망막 슬랩, 치료 전(왼쪽 위)과 7개월 뒤(오른쪽 위)와 치료 전 B-scan(아래)입니다(저자 Fig. 4C·D·E). '
                                          '혈관망은 밝기 상위 7 % 서비스 분할, 깊이는 장비가 그린 자홍 분할선을 썼습니다. 화소 단위입니다.'), c,
                             [L('area', 'MNV 병변·혈관망 면적', c.mask(mnv_both, COLOURS['magenta'], 150),
                                [('ft_mnv_lesion_area', oct_lesions.enface_area(md[:, None, :], feature_id='ft_mnv_lesion_area'))], 'oct_lesions.enface_area',
                                '7개월 슬랩(오른쪽 위)의 밝은 혈관망(자홍) 화소 수; 치료 전 혈관망도 함께 표시', 'magenta'),
                              L('type', 'MNV 유형(깊이)', lay, [('ft_mnv_type', oct_lesions.depth_category(lesion[None], surf))], 'oct_lesions.depth_category',
                                '아래 B-scan에서 장비 자홍 선(위 = RPE 빨강, 아래 = BM 흰색) 사이 병변(파랑)이 RPE 아래면 1형', 'blue')]))
    out.append(mnv_type_card('ex_fa_mnv_type', 'fa', '형광안저혈관조영', (0, 0, 340, 340), 'FA',
                             '결절성 맥락막혈관병증 눈의 형광안저혈관조영(위)과 같은 날 OCT B-scan(아래)입니다(저자 Fig. 4A·E). FA만으로는 깊이를 알 수 없어 '
                             'B-scan에서 유형을 판정합니다.'))
    out.append(mnv_type_card('ex_icga_mnv_type', 'icga', 'ICGA', (350, 0, 694, 340), 'ICGA',
                             '결절성 맥락막혈관병증 눈의 인도시아닌그린혈관조영(위)과 같은 날 OCT B-scan(아래)입니다(저자 Fig. 4B·E). ICGA만으로는 깊이를 알 수 없어 '
                             'B-scan에서 유형을 판정합니다.'))
    # --- FA microaneurysms (Videkar 2024)
    fig = provider('cureus-0016-00000073228-i07.jpg')
    im = fig.crop((0, 0, 750, 735))
    g = np.asarray(im.convert('L'), float)
    a = np.asarray(im, float)
    red = (a[..., 0] > 150) & (a[..., 1] < 90)
    vessel = bright_vessels(g, radius=6, pct=86)
    excl = ndimage.binary_dilation(vessel | red, iterations=2) | disk_mask(g.shape, [(250, 15)], 70)
    dots = bright_spots(g, radius=4, pct=98.0, min_px=4, max_px=60, exclude=excl)
    sm = ndimage.gaussian_filter(g, 6)
    win = sm[280:400, 330:460]
    fovea = tuple(np.array(np.unravel_index(win.argmin(), win.shape)) + (280, 330))
    c = Canvas(im, 800)
    lay = c.mask(dots, COLOURS['yellow'], 230, 255); d = c.draw(lay); dot(d, c.p(fovea), 6, COLOURS['red'], fill=True)
    out.append(write_example(dict(id='ex_fa_ma', modality='fa', modality_label='형광안저혈관조영', region='미세동맥류',
                                  title='FA · 미세동맥류', source='videkar2024', source_file='provider_figures/cureus-0016-00000073228-i07.jpg',
                                  caption='증식 당뇨망막병증 눈의 30° 형광안저혈관조영 초기 사진입니다. 혈관·유두·저자 화살표 밖의 작은 밝은 점을 서비스 톱햇 규칙으로 분할했고, '
                                          '중심와는 FAZ의 가장 어두운 점입니다. 화소 단위입니다.'), c,
                             [L('ma', '미세동맥류 존재·개수·중심와 거리', lay,
                                [('ft_ma_presence', lesions.presence(dots, feature_id='ft_ma_presence')), ('ft_ma_count', lesions.count(dots, feature_id='ft_ma_count')),
                                 ('ft_ma_distance_fovea', lesions.fovea_distance(dots, fovea, feature_id='ft_ma_distance_fovea'))],
                                'lesions.presence · count · fovea_distance', '4–60 px 밝은 점(노랑): 있음 여부, 개수, 중심와(빨간 점)까지 거리(px)', 'yellow')]))
    # --- ICGA: lesion change baseline → week 48 (Carta 2023)
    fig = provider('cureus-0015-00000047942-i02.jpg')
    d0, d1 = fig.crop((190, 175, 375, 358)), fig.crop((565, 175, 750, 358))

    def hypo(im):
        g = ndimage.gaussian_filter(np.asarray(im.convert('L'), float), 2)
        m = (g < 0.55 * np.median(g)) & disk_mask(g.shape, [(95, 95)], 70)
        m[:, 150:] = False                                   # optic disc at the right edge
        return skmorph.remove_small_objects(skmorph.binary_opening(m, skmorph.disk(2)), 40)
    m0, m1 = hypo(d0), hypo(d1)
    comp, offs = stack([d0, d1], vertical=False)
    shape = (comp.height, comp.width)
    c = Canvas(comp, 800)
    out.append(write_example(dict(id='ex_icga_change', modality='icga', modality_label='ICGA', region='병변 변화',
                                  title='ICGA · 48주 병변 변화', source='carta2023_icga', source_file='provider_figures/cureus-0015-00000047942-i02.jpg',
                                  caption='결절성 맥락막혈관병증 눈의 후기 인도시아닌그린혈관조영, 치료 전(왼쪽)과 48주(오른쪽)입니다(저자 Figure 2D·H). 황반의 어두운 '
                                          '저형광 병변을 서비스 밝기 규칙으로 분할했습니다. 화소 단위입니다.'), c,
                             [L('change', '병변 변화량', c.mask(place(shape, m0, offs[0]) | place(shape, m1, offs[1]), COLOURS['cyan'], 120),
                                [('ft_lesion_generic_change', lesions.change(m0, m1, interval_years=48 / 52))], 'lesions.change',
                                '치료 전 → 48주 저형광 병변(하늘색) 면적 차이와 연간 변화', 'cyan')]))
    # --- ICGA + EDI-OCT: large choroidal vessel diameter (Kitagawa 2021)
    fig = provider('12886_2021_2067_Fig1_HTML.jpg')
    bimg = fig.crop((303, 0, 709, 255))
    region = fig.crop((480, 0, 700, 150))                     # right of the PED, above the IR inset
    gb = np.asarray(region.convert('L'), float)
    h, w = gb.shape
    s = ndimage.gaussian_filter(gb, (2, 3))
    rpe = ndimage.median_filter(np.argmax(s[60:130], axis=0) + 60, 15).astype(float)
    bmk = ndimage.median_filter(np.array([rpe[x] + next((i for i in range(1, 25) if s[min(int(rpe[x]) + i, h - 1), x] < 0.5 * s[int(rpe[x]), x]), 4)
                                         for x in range(w)], float), 11)
    mu = ndimage.gaussian_filter(gb, 5); sq = ndimage.gaussian_filter(gb * gb, 5)
    tex = ndimage.gaussian_filter(np.sqrt(np.clip(sq - mu * mu, 0, None)), (3, 12))
    csi = np.full(w, np.nan)
    for x in range(w):
        a0 = int(bmk[x]) + 6
        col = tex[a0:h - 2, x]
        if col.size > 15:
            idx = np.nonzero(col > 0.6 * np.percentile(col[:15], 90))[0]
            csi[x] = a0 + idx.max() if idx.size else np.nan
    csi = ndimage.median_filter(np.nan_to_num(csi, nan=np.nanmedian(csi)), 31).astype(float)
    ex_icga = fig.crop((500, 258, 709, 512))
    comp, offs = stack([ex_icga.resize((int(ex_icga.width * 255 / ex_icga.height), 255)), bimg], vertical=False)
    shape = (comp.height, comp.width)
    c = Canvas(comp, 900)
    ch = place(shape, choroid.choroid_mask((h, w), bmk, csi), (offs[1][0], offs[1][1] + 177))
    lay = c.mask(ch, COLOURS['blue'], 40, 0); d = c.draw(lay)
    poly(c, d, bmk, COLOURS['red'], 2, x0=offs[1][1] + 177); poly(c, d, csi, COLOURS['yellow'], 2, x0=offs[1][1] + 177)
    m = choroid.large_vessel_diameter(gb, bmk, csi)
    out.append(write_example(dict(id='ex_icga_haller', modality='icga', modality_label='ICGA', region='대혈관층',
                                  title='ICGA + EDI-OCT · 맥락막 대혈관', source='kitagawa2021', source_file='provider_figures/12886_2021_2067_Fig1_HTML.jpg',
                                  caption='맥락막 비후를 동반한 결절성 맥락막혈관병증 눈의 ICGA(왼쪽, 저자 Fig. 1E)와 OCT(오른쪽, Fig. 1B; 저자 측정 맥락막 309 µm)입니다. '
                                          'ICGA에서 굵은 맥락막 혈관이 보이는 눈에서, 그 지름은 B-scan으로 잽니다. BM·맥락막–공막 경계는 서비스 추정이며 화소 단위입니다.'), c,
                             [L('haller', '대혈관 직경', lay, [('ft_haller_vessel_diameter', m)], 'choroid.large_vessel_diameter',
                                'PED 오른쪽·삽입 사진 위 구간에서 BM(빨강)~맥락막–공막 경계(노랑) 바깥 절반 어두운 내강의 가장 큰 내접원 지름', 'yellow')]))
    # --- UWF: laser scars (Panse 2023), IRMA quadrants (Guro 2026 wide-field red-free), ischemic index (wide-field FA)
    fig = provider('ajoc-32-101908-gr1.jpg')
    im = fig.crop((0, 0, 395, 330))
    a = np.asarray(im, float)
    fov = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.gaussian_filter(a.mean(2), 3) > 30), iterations=6)
    red = ndimage.gaussian_filter(a[..., 0], 1)
    scar = (skmorph.black_tophat(red, skmorph.disk(5)) > 28) & fov & ~disk_mask(red.shape, [(145, 215)], 14)
    scar = skmorph.remove_small_objects(skmorph.binary_opening(scar, skmorph.disk(1)), 6)
    c = Canvas(im, 800)
    out.append(write_example(dict(id='ex_uwf_laser', modality='uwf', modality_label='광각 안저', region='레이저 반흔',
                                  title='광각 안저 · 주변부 레이저 반흔', source='panse2023', source_file='provider_figures/ajoc-32-101908-gr1.jpg',
                                  caption='폐쇄성 혈관염 눈의 광각 영상(저자 Fig. 1A)입니다. 주변부 레이저 반흔을 적색 채널 블랙햇 규칙으로 분할했습니다(서비스 추정, 출혈 일부가 섞일 수 있음).'), c,
                             [L('scar', '레이저 반흔 범위', c.mask(scar, COLOURS['yellow'], 160),
                                [('ft_laser_scar_extent', lesions.count(scar, feature_id='ft_laser_scar_extent')),
                                 ('ft_lesion_generic_area', lesions.area(scar), f'면적 {int(scar.sum()):,} px²')],
                                'lesions.count', '어두운 반흔 점(노랑)의 연결 성분 수와 면적 합', 'yellow')]))
    fig = provider('OVS2-103-e70090-g004.webp')
    im = fig.crop((330, 0, 720, 300))
    a = np.asarray(im, float)
    redline = (a[..., 0] > 170) & (a[..., 1] < 90) & (a[..., 2] < 90)
    lab, n = ndimage.label(ndimage.binary_closing(redline, iterations=2))
    irma = np.zeros(redline.shape, bool)
    for k in range(1, n + 1):
        if (lab == k).sum() > 30:
            irma |= ndimage.binary_fill_holes(lab == k)
    disc, fovea = (150.0, 228.0), (165.0, 145.0)
    c = Canvas(im, 800)
    q = lesions.quadrant_occupancy(irma, fovea, disc, feature_id='ft_irma_quadrants')
    lay = c.mask(irma, COLOURS['magenta'], 110); d = c.draw(lay)
    axis = (np.asarray(disc) - fovea) / np.linalg.norm(np.asarray(disc) - fovea); normal = np.array([-axis[1], axis[0]])
    for v in (axis, normal):
        d.line([c.p(np.asarray(fovea) - 3000 * v), c.p(np.asarray(fovea) + 3000 * v)], fill=COLOURS['white'] + (200,), width=2)
    out.append(write_example(dict(id='ex_uwf_irma', modality='uwf', modality_label='광각 안저', region='IRMA 사분면',
                                  title='광각 무적색 · IRMA 침범 사분면', source='guro2026', source_file='provider_figures/OVS2-103-e70090-g004.webp',
                                  caption='중등도 비증식 당뇨망막병증 눈의 광각 무적색 사진(저자 Figure 3B)입니다. 저자가 IRMA 관심 영역으로 그린 빨간 타원을 IRMA mask로, '
                                          '유두·중심와는 서비스가 읽은 위치를 썼습니다.'), c,
                             [L('irma', 'IRMA 침범 사분면 수', lay, [('ft_irma_quadrants', q)], 'lesions.quadrant_occupancy',
                                '유두–중심와 축(흰 선)으로 나눈 사분면 중 저자 IRMA 타원(자홍)이 있는 사분면 수', 'magenta')]))
    base, np_mask = masked('paper_nonperfusion')
    g = np.asarray(base.convert('L'), float)
    fov = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.gaussian_filter(g, 4) > 12), iterations=6)
    area, index = octa.nonperfusion(np_mask, fov=fov)
    c = Canvas(base)
    src, file = masked_source('paper_nonperfusion')
    out.append(write_example(dict(id='ex_uwf_ischemic', modality='uwf', modality_label='광각 안저', region='허혈 지수',
                                  title='광각 FA · 허혈 지수', source=src, source_file=file,
                                  caption='광각(UWF) 형광안저혈관조영입니다(형광안저혈관조영 탭의 광각 예시와 같은 영상). 허혈 지수는 광각 영상 전체 시야를 분모로 씁니다.'), c,
                             [L('index', '허혈 지수', c.mask(fov, COLOURS['white'], 0, 170, layer=c.mask(np_mask & fov, COLOURS['blue'], 120)),
                                [('ft_ischemic_index', index)], 'octa.nonperfusion', '무관류(파랑) 화소 ÷ 판독 가능한 광각 시야(흰 윤곽)', 'blue')]))
    # --- FAF: PIC lesions at 2 months vs ~2 years (Bai 2026)
    t1 = provider('medi-105-e47893-g003.jpg').crop((165, 0, 335, 130))
    t2 = provider('medi-105-e47893-g005.jpg').crop((400, 0, 800, 245))
    disc1, dd1, disc2, dd2 = (68.0, 262.0 - 165), 20.0, (170.0, 590.0 - 400), 50.0
    k = dd2 / dd1
    t1s = t1.resize((round(t1.width * k), round(t1.height * k)), Image.LANCZOS)
    off = (int(round(disc2[0] - disc1[0] * k)), int(round(disc2[1] - disc1[1] * k)))
    canvas1 = Image.new('RGB', t2.size, 'black'); canvas1.paste(t1s, (off[1], off[0]))

    def spots(im, valid):
        g = ndimage.gaussian_filter(np.asarray(im.convert('L'), float), 1.5)
        m = (skmorph.black_tophat(g, skmorph.disk(9)) > 22) & valid & ~disk_mask(g.shape, [disc2], 0.62 * dd2)
        m &= disk_mask(g.shape, [disc2], 2.2 * dd2)
        m = skmorph.remove_small_objects(m, 12)
        from skimage import measure as skm
        lab = skm.label(m)
        return np.isin(lab, [p.label for p in skm.regionprops(lab) if p.eccentricity < 0.9 and p.area < 600])
    valid1 = np.zeros(t2.size[::-1], bool)
    valid1[max(off[0], 0):off[0] + t1s.height, max(off[1], 0):off[1] + t1s.width] = True
    valid1 = ndimage.binary_erosion(valid1, iterations=6)
    m1, m2 = spots(canvas1, valid1), spots(t2, valid1)
    comp, offs = stack([canvas1, t2], vertical=False)
    shape = (comp.height, comp.width)
    c = Canvas(comp, 900)
    both = place(shape, m1, offs[0]) | place(shape, m2, offs[1])
    out.append(write_example(dict(id='ex_faf_change', modality='faf', modality_label='자가형광', region='위축 변화',
                                  title='FAF · 유두 둘레 위축 반점 변화', source='bai2026_faf', source_file='provider_figures/medi-105-e47893-g005.jpg',
                                  caption='점상 내맥락막병증 눈의 자가형광, 첫 방문 2개월(왼쪽, 저자 Figure 3B를 유두 크기에 맞춰 확대)과 마지막 주사 2년 뒤(오른쪽, Figure 5B)입니다. '
                                          '유두를 기준으로 맞추고 유두 둘레 2.2 DD 안의 어두운 반점을 서비스 블랙햇 규칙으로 분할했습니다. 간격은 원문 기술로 약 2년 이상이라 2년으로 계산한 근사입니다.'), c,
                             [L('growth', '위축 확장률', c.mask(both, COLOURS['blue'], 140), [('ft_atrophy_growth_rate', atrophy.growth_rate(m1, m2, interval_years=2.0))],
                                'atrophy.growth_rate', '두 시점 저자가형광 반점(파랑) 면적 제곱근 차이 ÷ 2년(오른쪽 영상 화소)', 'blue'),
                              L('change', '병변 변화량', c.mask(both, COLOURS['orange'], 140), [('ft_lesion_generic_change', lesions.change(m1, m2, interval_years=2.0))],
                                'lesions.change', '두 시점 반점 면적 차이와 연간 변화', 'orange')]))
    # --- SDD on FAF and OCT (Li 2019)
    fig = provider('retina-39-802-g003.jpg')
    faf = fig.crop((0, 0, 395, 395))
    g = ndimage.gaussian_filter(np.asarray(faf.convert('L'), float), 1)
    a = np.asarray(faf, float)
    marks = (np.abs(a[..., 0] - a[..., 1]) > 35) | (np.abs(a[..., 1] - a[..., 2]) > 35)
    vessel = skmorph.remove_small_objects(skmorph.black_tophat(ndimage.gaussian_filter(g, 1.5), skmorph.disk(6)) > 18, 60)
    ga = skmorph.remove_small_objects(ndimage.gaussian_filter(g, 4) < np.percentile(g, 5), 200)
    roi = np.zeros(g.shape, bool); roi[150:370, 200:385] = True
    sdd = (skmorph.black_tophat(g, skmorph.disk(3)) > 14) & roi & ~ndimage.binary_dilation(vessel | marks | ga, iterations=3)
    sdd = skmorph.remove_small_objects(sdd, 3)
    from skimage import measure as skm
    lab = skm.label(sdd)
    sdd = np.isin(lab, [p.label for p in skm.regionprops(lab) if p.area <= 30 and (p.area < 6 or p.eccentricity < 0.9)])
    c = Canvas(faf, 700)
    out.append(write_example(dict(id='ex_faf_sdd', modality='faf', modality_label='자가형광', region='망막하 드루젠양 침착물',
                                  title='FAF · 망막하 드루젠양 침착물', source='li2019', source_file='provider_figures/retina-39-802-g003.jpg',
                                  caption='나이관련황반변성 눈의 자가형광(저자 Fig. 3A)입니다. 저자가 하늘색 화살표로 표시한 귀쪽 영역의 작은 저자가형광 점을 서비스 블랙햇 규칙으로 '
                                          '분할했습니다(혈관·지도모양위축·저자 표시 제외).'), c,
                             [L('sdd', 'SDD 침범 범위', c.mask(sdd, COLOURS['yellow'], 230, 255, layer=c.mask(roi, COLOURS['white'], 0, 150)),
                                [('ft_sdd_extent', lesions.area(sdd, feature_id='ft_sdd_extent'))], 'lesions.area',
                                '흰 상자 안 작은 어두운 점(노랑)의 화소 수', 'yellow')]))
    oct_img = fig.crop((405, 607, 631, 795))
    go = np.asarray(oct_img.convert('L'), float)
    h, w = go.shape
    so = ndimage.gaussian_filter(go, (2, 3))
    rpe = ndimage.median_filter(np.argmax(so[60:h - 10], axis=0) + 60, 15)
    dep = np.zeros(go.shape, bool)
    s1 = ndimage.gaussian_filter(go, 1)
    for x in range(w):
        band = slice(max(int(rpe[x]) - 12, 0), max(int(rpe[x]) - 3, 0))
        ref = np.median(s1[band, :])
        dep[band, x] = s1[band, x] > ref + 45
    a = np.asarray(oct_img, float)
    cyan = (a[..., 2] > 150) & (a[..., 0] < 120)
    near = np.zeros(w, bool)
    for x in np.unique(np.nonzero(cyan)[1]):
        near[max(x - 30, 0):x + 30] = True                    # around the author's SDD arrowheads
    dep &= ~ndimage.binary_dilation(cyan, iterations=4) & near[None]
    dep = skmorph.remove_small_objects(dep, 6)
    c = Canvas(oct_img, 700)
    lay = c.mask(dep, COLOURS['yellow'], 170); d = c.draw(lay); poly(c, d, rpe.astype(float), COLOURS['red'], 2)
    out.append(write_example(dict(id='ex_oct_sdd', modality='oct', modality_label='OCT', region='망막하 드루젠양 침착물',
                                  title='OCT · 망막하 드루젠양 침착물', source='li2019', source_file='provider_figures/retina-39-802-g003.jpg',
                                  caption='같은 눈의 B-scan(저자 Fig. 3 IV, 하늘색 화살촉 = SDD)입니다. RPE(빨강) 바로 위 3–12 px 띠에서 주변보다 밝은 침착물을 서비스 규칙으로 분할했습니다.'), c,
                             [L('sdd', 'SDD 침범 범위', lay, [('ft_sdd_extent', lesions.area(dep, feature_id='ft_sdd_extent'))], 'lesions.area',
                                '저자 화살촉 둘레 ±30 px, RPE 위 띠의 밝은 침착물(노랑) 단면 화소 수', 'yellow'),
                              R('stage', 'SDD 단계', c.mask(dep, COLOURS['magenta'], 0, 255), 'ft_sdd_stage',
                                '판독 항목(계산 코드 없음) · 침착물이 RPE 위에 고여 있고 EZ를 넘지 않으면 낮은 단계, EZ를 뚫고 올라가면 높은 단계로 판정',
                                '침착물 위치를 표시; 단계 판정은 판독자. 자동 판정 코드는 없음', 'magenta')]))
    # --- UWF rhegmatogenous detachment, macula sparing (Al-Saleh 2025)
    im = provider('cureus-0017-00000085709-i01.jpg')
    a = np.asarray(im, float)
    r, gch = ndimage.gaussian_filter(a[..., 0], 3), ndimage.gaussian_filter(a[..., 1], 3)
    lum = a.mean(2)
    mu = ndimage.gaussian_filter(lum, 6); sq = ndimage.gaussian_filter(lum ** 2, 6)
    tex = np.sqrt(np.clip(sq - mu * mu, 0, None))
    yy, xx = np.indices(lum.shape)
    fov = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.gaussian_filter(lum, 4) > 45), iterations=12)
    fov &= (yy > 40) & (yy < 470)
    rd = (gch > r * 1.25) & (tex < np.percentile(tex[fov], 50)) & fov & (xx > 480)
    rd = skmorph.remove_small_objects(skmorph.binary_opening(rd, skmorph.disk(4)), 800)
    rd = ndimage.binary_fill_holes(skmorph.binary_closing(rd, skmorph.disk(8))) & fov
    fovea = (265.0, 450.0)                     # macula temporal to the disc (service estimate)
    c = Canvas(im, 900)
    lay = c.mask(rd, COLOURS['cyan'], 100); lay = c.mask(fov, COLOURS['white'], 0, 160, layer=lay)
    lay2 = c.mask(rd, COLOURS['cyan'], 60); d = c.draw(lay2); x, y = c.p(fovea)
    dot(d, (x, y), 9, COLOURS['red'], 3)
    out.append(write_example(dict(id='ex_uwf_rd', modality='uwf', modality_label='광각 안저', region='망막박리',
                                  title='광각 안저 · 황반을 비낀 망막박리', source='alsaleh2025', source_file='provider_figures/cureus-0017-00000085709-i01.jpg',
                                  caption='2–4시 귀쪽 열공을 동반한 열공성 망막박리의 Optos 광각 영상입니다(저자 기술: 황반 보존). 박리 범위는 귀쪽의 초점이 흐린 녹색 융기 영역을 '
                                          '서비스 색·질감 규칙으로 추정했고, 중심와도 서비스가 정한 위치입니다.'), c,
                             [L('extent', '박리 범위', lay, [('ft_rd_extent', lesions.field_fraction(rd, fov=fov))], 'lesions.field_fraction',
                                '추정 박리 영역(하늘색) ÷ 판독 가능한 시야(흰 윤곽)', 'cyan'),
                              L('macula', '황반 침범', lay2, [('ft_rd_macula_status', lesions.involves_point(rd, fovea, feature_id='ft_rd_macula_status'))],
                                'lesions.involves_point', '중심와(빨간 원)가 박리 영역 안에 있는지 — 저자 기술과 같이 "아니요"면 황반 보존', 'red')]))
    # --- FAF laser scars 12 months after PRP (Higaki 2018)
    im = provider('JOPH2018-9371895.001.jpg').crop((5, 520, 360, 985))
    a = np.asarray(im, float); g = ndimage.gaussian_filter(a.mean(2), 2)
    box = (np.abs(a[..., 0] - a[..., 2]) < 12) & (a.mean(2) > 215)               # author's white dashed box
    vessel = skmorph.remove_small_objects(skmorph.black_tophat(g, skmorph.disk(5)) > 14, 80)
    scar = (skmorph.black_tophat(g, skmorph.disk(16)) > 18) & ~ndimage.binary_dilation(vessel | box, iterations=3)
    scar &= ~disk_mask(g.shape, [(100, 55)], 70)
    from skimage import measure as skm
    lab = skm.label(skmorph.binary_opening(scar, skmorph.disk(2)))
    scar = np.isin(lab, [p.label for p in skm.regionprops(lab) if p.area >= 60 and p.eccentricity < 0.85])
    c = Canvas(im, 600)
    out.append(write_example(dict(id='ex_faf_laser', modality='faf', modality_label='자가형광', region='레이저 반흔',
                                  title='FAF · 범망막 광응고 반흔(12개월)', source='higaki2018', source_file='provider_figures/JOPH2018-9371895.001.jpg',
                                  caption='범망막 광응고 12개월 뒤 자가형광(저자 Figure 1c)입니다. 둥근 저자가형광 반흔을 서비스 블랙햇·모양 규칙으로 분할했습니다(혈관·유두·저자 점선 상자 제외).'), c,
                             [L('scar', '레이저 반흔 범위', c.mask(scar, COLOURS['yellow'], 140),
                                [('ft_laser_scar_extent', lesions.count(scar, feature_id='ft_laser_scar_extent')),
                                 ('ft_lesion_generic_area', lesions.area(scar), f'면적 {int(scar.sum()):,} px²')],
                                'lesions.count', '둥근 어두운 반흔(노랑)의 연결 성분 수와 면적 합', 'yellow')]))
    # --- OCT: BMO margin on the SD-OCT infrared image (Choung 2021)
    im = provider('pone.0254889.g001.jpg').crop((240, 0, 500, 246))
    a = np.asarray(im, float)
    red = (a[..., 0] > 170) & (a[..., 1] < 90) & (a[..., 2] < 90)
    pts = np.array([p.mean(0) for p in (np.argwhere(lab_k) for lab_k in
                    [ndimage.label(red)[0] == k for k in range(1, ndimage.label(red)[1] + 1)]) if len(p) <= 30])
    cen = pts.mean(0)
    rim = pts[np.hypot(*(pts - cen).T) > 45]                                        # BMO dots, not the red angle labels
    from skimage.draw import polygon as skpoly
    order = np.argsort(np.arctan2(rim[:, 0] - cen[0], rim[:, 1] - cen[1]))
    bmo = np.zeros(red.shape, bool)
    rr, cc = skpoly(rim[order, 0], rim[order, 1], red.shape); bmo[rr, cc] = True
    c = Canvas(im, 600)
    lay = c.mask(bmo, COLOURS['cyan'], 70, 255)
    out.append(write_example(dict(id='ex_oct_bmo_area', modality='oct', modality_label='OCT', region='유두 면적(BMO)',
                                  title='OCT · BMO로 정한 유두 면적', source='choung2021', source_file='provider_figures/pone.0254889.g001.jpg',
                                  caption='SD-OCT 적외선 영상에 저자가 표시한 브루크막 개방(BMO) 가장자리 빨간 점(저자 Fig 1B)을 이어 유두 경계로 썼습니다. 화소 단위입니다.'), c,
                             [L('disc', '유두 면적', lay, [('ft_disc_area', optic_disc.disc_area(bmo))], 'optic_disc.disc_area',
                                '저자 BMO 점(빨강)을 각도 순으로 이은 다각형(하늘색) 안 화소 수', 'cyan')]))
    # --- FAF peripapillary atrophy in high myopia (Fonollosa 2026)
    im = provider('fmed-13-1745948-g004.jpg').crop((0, 180, 200, 370))
    a = np.asarray(im, float); g = ndimage.gaussian_filter(a.mean(2), 1.5)
    colour = (np.abs(a[..., 0] - a[..., 1]) > 40) | (np.abs(a[..., 1] - a[..., 2]) > 40)
    disc_c, disc_r = (70.0, 45.0), 15.0                                              # vessel convergence (service estimate)
    dark = (g < 0.45 * np.median(g)) & ~ndimage.binary_dilation(colour, iterations=2)
    lab, _ = ndimage.label(dark)
    blob = lab == lab[int(disc_c[0]), int(disc_c[1])] if lab[int(disc_c[0]), int(disc_c[1])] else np.zeros_like(dark)
    ppa = blob & ~disk_mask(g.shape, [disc_c], disc_r)
    c = Canvas(im, 600)
    lay = c.mask(ppa, COLOURS['yellow'], 120); d = c.draw(lay); dot(d, c.p(disc_c), disc_r * c.scale, COLOURS['white'], 2)
    out.append(write_example(dict(id='ex_faf_ppa', modality='faf', modality_label='자가형광', region='유두주위 위축',
                                  title='FAF · 고도근시 유두주위 위축', source='fonollosa2026', source_file='provider_figures/fmed-13-1745948-g004.jpg',
                                  caption='고도근시 눈의 자가형광(저자 Figure 4B)입니다. 유두에 이어진 어두운 저자가형광 영역에서 유두(흰 원, 서비스 추정 위치·크기)를 뺀 부분을 '
                                          '유두주위 위축으로 썼습니다.'), c,
                             [L('ppa', '유두주위 위축 면적', lay, [('ft_ppa_area', optic_disc.ppa_area(ppa))], 'optic_disc.ppa_area',
                                '유두와 이어진 저자가형광(중앙값의 45 % 미만)에서 유두 원을 뺀 화소 수(노랑)', 'yellow')]))
    return out




def more_figure_examples() -> list[dict]:
    out = []
    # --- wide-field FA: IRMA marked "e" by the authors (Yang 2022)
    im = provider('fendo-13-1079217-g005.jpg').crop((0, 285, 354, 570))
    tips, _ = arrow_tips(im, colour='red', prefer='left')
    tip = min(tips, key=lambda t: np.hypot(t[0] - 108, t[1] - 98))
    irma = disk_mask(np.asarray(im).shape[:2], [tip], 7)
    disc, fovea = (155.0, 185.0), (160.0, 105.0)
    c = Canvas(im, 800)
    lay = c.mask(irma, COLOURS['magenta'], 150, 255); d = c.draw(lay)
    axis = (np.asarray(disc) - fovea) / np.linalg.norm(np.asarray(disc) - fovea); normal = np.array([-axis[1], axis[0]])
    for v in (axis, normal):
        d.line([c.p(np.asarray(fovea) - 3000 * v), c.p(np.asarray(fovea) + 3000 * v)], fill=COLOURS['white'] + (180,), width=2)
    out.append(write_example(dict(id='ex_fa_irma', modality='fa', modality_label='형광안저혈관조영', region='IRMA',
                                  title='광각 FA · 망막내 미세혈관 이상', source='yang2022', source_file='provider_figures/fendo-13-1079217-g005.jpg',
                                  caption='증식 당뇨망막병증 오른눈의 광각 형광안저혈관조영(저자 Figure 5C)입니다. 저자가 "e"(IRMA) 화살표로 가리킨 위치를 병변 점으로, '
                                          '유두·중심와는 서비스가 읽은 위치를 썼습니다. 저자가 표시하지 않은 IRMA는 세지 않습니다.'), c,
                             [L('irma', 'IRMA 존재·침범 사분면', lay,
                                [('ft_irma_presence', lesions.presence(irma, feature_id='ft_irma_presence')),
                                 ('ft_irma_quadrants', lesions.quadrant_occupancy(irma, fovea, disc, feature_id='ft_irma_quadrants'))],
                                'lesions.presence · quadrant_occupancy', '저자 IRMA 화살표 끝(자홍 원)의 있음 여부와, 유두–중심와 축(흰 선) 사분면 중 그것이 있는 사분면 수', 'magenta')]))
    # --- OCT ONH B-scan: BMO line and cup volume cross-section (Driessen 2024)
    im = provider('tvst-13-12-5-f002.jpg').crop((0, 240, 545, 470))
    a = np.asarray(im, float)
    yellow = (a[..., 0] > 120) & (a[..., 1] > 110) & (a[..., 2] < 80)
    blue = (a[..., 2] > 150) & (a[..., 0] < 120)
    bcols = np.unique(np.nonzero(blue)[1])
    mid = a.shape[1] / 2
    left, right = bcols[bcols < mid].max(), bcols[bcols > mid].min()       # BMO = inner ends of the blue line
    ycols = np.unique(np.nonzero(yellow)[1])
    disc_d, cup_d = float(right - left), float(ycols.max() - ycols.min())
    size = int(disc_d) + 21
    yy, xx = np.indices((size, size)); cen = size / 2
    disc_m = np.hypot(yy - cen, xx - cen) <= disc_d / 2
    cup_m = np.hypot(yy - cen, xx - cen) <= cup_d / 2
    c = Canvas(im, 800)
    lay = c.mask(yellow, COLOURS['yellow'], 130); d = c.draw(lay)
    for x in (left, right):
        r = np.nonzero(blue[:, max(int(x) - 2, 0):int(x) + 3].any(1))[0].mean()
        dot(d, c.p((r, x)), 6, COLOURS['cyan'], fill=True)
    note = f'BMO 지름 {disc_d:.0f} px · 컵 지름 {cup_d:.0f} px(가로 단면)'
    out.append(write_example(dict(id='ex_oct_cup', modality='oct', modality_label='OCT', region='유두 컵·테',
                                  title='OCT · 유두 단면의 컵과 테', source='driessen2024', source_file='provider_figures/tvst-13-12-5-f002.jpg',
                                  caption='유두 중심을 지나는 OCT B-scan에 저자가 그린 BMO 연결선(파랑·흰색)과 컵(노랑)입니다(저자 Figure 2C). 단면 하나뿐이라 BMO와 컵을 '
                                          '각각 그 가로 지름의 원으로 가정해 면적·비를 계산했습니다(원형 가정, 수직 비 대신 가로 비). ISNT·노치는 둘레 전체가 필요해 계산하지 않습니다.'), c,
                             [L('cup', '컵 면적·테 면적·컵/유두비', lay,
                                [('ft_cup_area', optic_disc.cup_area(cup_m)), ('ft_rim_area', optic_disc.rim_area(disc_m, cup_m)),
                                 ('ft_cdr_vertical', optic_disc.cup_disc_ratio(disc_m, cup_m), f"{cup_d / disc_d:.2f} (가로 단면 · {note})")],
                                'optic_disc.cup_area · rim_area · cup_disc_ratio',
                                'BMO 두 끝(하늘색 점) 사이 거리와 저자 컵(노랑)의 가로 폭을 지름으로 하는 원으로 면적과 비 계산', 'yellow')]))
    # --- OCT en face: myopic temporal crescent (Hu 2024)
    im = provider('fneur-15-1366593-g002.jpg').crop((355, 0, 714, 300))
    g = ndimage.gaussian_filter(np.asarray(im.convert('L'), float), 3)
    dc, dr = (172.0, 545.0 - 355), 38.0
    yy, xx = np.indices(g.shape)
    dist = np.hypot(yy - dc[0], xx - dc[1])
    ring = (dist > dr) & (dist < dr + 110) & (xx < dc[1])
    ppa = ring & (g > np.percentile(g[ring], 70))
    lab, _ = ndimage.label(ppa)
    touch = np.unique(lab[(dist > dr) & (dist < dr + 6) & ppa])
    ppa = np.isin(lab, touch[touch > 0])
    c = Canvas(im, 700)
    lay = c.mask(ppa, COLOURS['yellow'], 120); d = c.draw(lay); dot(d, c.p(dc), dr * c.scale, COLOURS['white'], 2)
    out.append(write_example(dict(id='ex_oct_ppa', modality='oct', modality_label='OCT', region='유두주위 위축',
                                  title='OCT 표면 영상 · 근시성 반달', source='hu2024', source_file='provider_figures/fneur-15-1366593-g002.jpg',
                                  caption='고도근시 눈의 OCT 표면(en face) 영상(저자 Figure 2B)에서 귀쪽 흰 반달(β·γ 구역)을 서비스 밝기 규칙으로 분할했습니다. 유두 원(흰색)은 서비스 추정입니다.'), c,
                             [L('ppa', '유두주위 위축 면적', lay, [('ft_ppa_area', optic_disc.ppa_area(ppa))], 'optic_disc.ppa_area',
                                '유두 경계에 닿는 귀쪽 밝은 반달(노랑, 둘레 고리 상위 30 %) 화소 수', 'yellow')]))
    # --- NIR: idiopathic epiretinal membrane sheen (Vogt 2026)
    im = provider('40942_2026_849_Fig1_HTML.jpg').crop((0, 0, 135, 130))
    k = 5
    big = im.resize((im.width * k, im.height * k), Image.LANCZOS)
    g = ndimage.gaussian_filter(np.asarray(big.convert('L'), float), 3)
    fovea, disc_p = (55 * k, 88 * k), (45 * k, 12 * k)
    th = skmorph.white_tophat(g, skmorph.disk(30))
    roi = disk_mask(g.shape, [fovea], 50 * k) & ~disk_mask(g.shape, [disc_p], 25 * k)
    roi[:20 * k, :25 * k] = False                                               # panel letter
    erm = (th > np.percentile(th[roi], 80)) & roi
    erm = skmorph.remove_small_objects(skmorph.binary_closing(erm, skmorph.disk(4)), 200)
    c = Canvas(big, 650)
    out.append(write_example(dict(id='ex_nir_erm', modality='nir', modality_label='근적외선', region='망막전막',
                                  title='근적외선 · 특발 망막전막', source='vogt2026', source_file='provider_figures/40942_2026_849_Fig1_HTML.jpg',
                                  caption='특발 망막전막 눈의 수술 전 적외선 영상(저자 Fig. 1A, 5배 확대)입니다. 황반 둘레의 주름진 밝은 반사를 서비스 톱햇 규칙으로 분할했습니다(근사).'), c,
                             [L('erm', '망막전막 범위', c.mask(erm, COLOURS['cyan'], 110), [('ft_erm_extent', oct_lesions.enface_area(erm[:, None, :], feature_id='ft_erm_extent'))],
                                'oct_lesions.enface_area', '중심와 둘레의 밝은 주름 반사(하늘색, 톱햇 상위 20 %) 화소 수(확대 화소)', 'cyan')]))
    return out






def before_after_examples() -> list[dict]:
    """Same eye before and after PRP + bevacizumab (Lee 2023): FA and colour photographs, aligned by disc and fovea."""
    from skimage import measure as skm
    from skimage import transform as sktf
    out = []
    fig = provider('12886_2023_2788_Fig2_HTML.jpg')
    k = 3
    boxes = {'b': (354, 2, 706, 268), 'd': (354, 276, 706, 542)}
    marks = {'b': ((115, 30), (145, 170)), 'd': ((115, 55), (165, 185))}   # (disc, fovea) read on the panels

    def up(name):
        return fig.crop(boxes[name]).resize(((boxes[name][2] - boxes[name][0]) * k, (boxes[name][3] - boxes[name][1]) * k), Image.LANCZOS)

    def fa_dots(img):
        g = np.asarray(img.convert('L'), float)
        th = skmorph.white_tophat(ndimage.gaussian_filter(g, 1), skmorph.disk(6))
        lab = skm.label(th > 25)
        m = np.isin(lab, [p.label for p in skm.regionprops(lab) if 6 <= p.area <= 120 and p.eccentricity < 0.85])
        m[-40:, -200:] = False                                                      # device text
        return m

    def align(after_name, before_name, mask, shape):
        src = np.array([[x, y] for y, x in marks[after_name]], float) * k
        dst = np.array([[x, y] for y, x in marks[before_name]], float) * k
        t = sktf.SimilarityTransform(); t.estimate(src, dst)
        return sktf.warp(mask.astype(float), t.inverse, output_shape=shape, order=0) > 0.5

    # colour panels (a, c) were tried too: at this resolution red dots cannot be told from vessel and disc edges, so only FA is used
    for before, after, modality, label, ex_id, dots in (('b', 'd', 'fa', '형광안저혈관조영', 'ex_fa_ma_change', fa_dots),):
        i0, i1 = up(before), up(after)
        m0 = dots(i0); m1 = align(after, before, dots(i1), m0.shape)
        r0, r1 = ndimage.binary_dilation(m0, iterations=4), ndimage.binary_dilation(m1, iterations=4)
        turn = lesions.turnover(r0, r1, min_area_px=6)
        comp, offs = stack([i0, i1], vertical=False)
        c = Canvas(comp, 1000)
        lay = c.layer(); d = c.draw(lay)
        lab0 = skm.label(m0); lab1 = skm.label(dots(i1))
        for p in skm.regionprops(lab0):
            hit = r1[tuple(np.round(p.centroid).astype(int))]
            dot(d, c.p(p.centroid), 5, COLOURS['green'] if hit else COLOURS['blue'], 2)
        for p in skm.regionprops(lab1):
            q = np.round(p.centroid).astype(int)
            src = np.array([[q[1], q[0]]], float)
            dst = np.array([[x, y] for y, x in marks[before]], float) * k
            srcm = np.array([[x, y] for y, x in marks[after]], float) * k
            t = sktf.SimilarityTransform(); t.estimate(srcm, dst)
            xb, yb = t(src)[0]
            inside = 0 <= int(yb) < r0.shape[0] and 0 <= int(xb) < r0.shape[1]
            hit = r0[int(yb), int(xb)] if inside else False
            dot(d, c.p((p.centroid[0], p.centroid[1] + offs[1][1])), 5, COLOURS['green'] if hit else COLOURS['red'], 2)
        layers = [L('turnover', '미세동맥류 생성·소실', lay, [('ft_ma_turnover', turn)], 'lesions.turnover',
                    '두 시점 모두 = 초록, 치료 전에만 = 파랑(사라짐), 치료 후에만 = 빨강(새로 생김); 유두·중심와 두 점으로 맞춘 닮음 변환 뒤 비교', 'green')]
        if modality == 'fa':
            def faz(img, fov_pt):
                sm = ndimage.gaussian_filter(np.asarray(img.convert('L'), float), 6)
                roi = disk_mask(sm.shape, [fov_pt], 70)
                m = (sm < np.percentile(sm[roi], 15)) & roi
                lab, _ = ndimage.label(m)
                return ndimage.binary_fill_holes(lab == lab[int(fov_pt[0]), int(fov_pt[1])]) if lab[int(fov_pt[0]), int(fov_pt[1])] else m
            f0 = faz(i0, np.array(marks[before][1]) * k)
            f1_raw = faz(i1, np.array(marks[after][1]) * k)
            f1 = align(after, before, f1_raw, f0.shape)
            lay2 = c.mask(place((comp.height, comp.width), f0, offs[0]), COLOURS['yellow'], 110)
            lay2 = c.mask(place((comp.height, comp.width), f1_raw, offs[1]), COLOURS['orange'], 110, layer=lay2)
            layers.append(L('faz', 'FAZ 크기 변화', lay2, [('ft_faz_enlargement', octa.faz_enlargement(f0, f1))], 'octa.faz_enlargement',
                            '두 시점 중심와 주변 가장 어두운 15 % 영역(노랑 → 주황)을 같은 좌표로 맞춘 뒤 면적 차이(간격 미상이라 연간율 없음)', 'orange'))
        out.append(write_example(dict(id=ex_id, modality=modality, modality_label=label, region='치료 전후 미세동맥류',
                                      title=('FA' if modality == 'fa' else '안저') + ' · 치료 전후 미세동맥류 변화', source='lee2023',
                                      source_file='provider_figures/12886_2023_2788_Fig2_HTML.jpg',
                                      caption='증식 당뇨망막병증 왼눈의 범망막 광응고·베바시주맙 치료 전(왼쪽)과 후(오른쪽) ' + ('형광안저혈관조영' if modality == 'fa' else '안저 사진')
                                              + '입니다(저자 Fig. 2, 3배 확대; 저자 보고 FA 미세동맥류 437개 → 62개). 미세동맥류는 서비스 점 규칙 추정이고, 두 시점은 서비스가 읽은 '
                                              '유두·중심와 두 점으로 맞췄습니다. 원 그림 해상도가 낮아 값은 함수 동작을 보여 주는 예시입니다.'), c, layers))
    return out




def contour_mask(points, shape, *, bins=72):
    """Close a dashed / interrupted outline: median radius per angle bin around the centroid, gaps interpolated."""
    from skimage.draw import polygon as skpoly
    pts = np.asarray(points, float)
    c = pts.mean(0)
    ang = np.arctan2(pts[:, 0] - c[0], pts[:, 1] - c[1])
    rad = np.hypot(pts[:, 0] - c[0], pts[:, 1] - c[1])
    edges = np.linspace(-np.pi, np.pi, bins + 1)
    r = np.array([np.median(rad[(ang >= edges[i]) & (ang < edges[i + 1])]) if ((ang >= edges[i]) & (ang < edges[i + 1])).any() else np.nan
                  for i in range(bins)])
    mid = (edges[:-1] + edges[1:]) / 2
    ok = ~np.isnan(r)
    r = np.interp(mid, mid[ok], r[ok], period=2 * np.pi)
    ref = ndimage.median_filter(r, size=9, mode='wrap')
    ok = np.abs(r - ref) < 0.15 * ref                       # drop bins that hit a vessel or another mark instead of the outline
    r = np.interp(mid, mid[ok], r[ok], period=2 * np.pi)
    rr, cc = skpoly(c[0] + r * np.sin(mid), c[1] + r * np.cos(mid), shape)
    m = np.zeros(shape, bool); m[rr, cc] = True
    return m


def oct_onh_report_example() -> dict:
    """Cirrus ONH report (OD): device disc margin (black) and cup margin (red) on the en-face deviation map."""
    im = provider('cureus-0018-00000115500-i02.webp').crop((180, 610, 320, 750))
    k = 4
    big = im.resize((im.width * k, im.height * k), Image.LANCZOS)
    a = np.asarray(big, float)
    red = (a[..., 0] > 130) & (a[..., 0] - a[..., 1] > 55) & (a[..., 0] - a[..., 2] > 55)
    black = a.max(2) < 75
    black &= disk_mask(black.shape, [(black.shape[0] / 2, black.shape[1] / 2)], 0.42 * black.shape[0])   # disc margin, not the outer RNFL circle
    disc = contour_mask(np.argwhere(black), black.shape)
    cup = contour_mask(np.argwhere(red), red.shape)
    isnt = optic_disc.isnt_pattern(disc, cup, eye='OD')
    notch = optic_disc.rim_notch(disc, cup, eye='OD')
    c = Canvas(big, 560)
    lay = c.mask(disc & ~cup, COLOURS['green'], 90, 200); lay = c.mask(cup, COLOURS['yellow'], 90, 230, layer=lay)
    d = c.draw(lay)
    cy, cx = np.argwhere(disc).mean(0)
    for name, deg in (('superior', 90), ('nasal', 0), ('inferior', 270), ('temporal', 180)):     # right eye: nasal = image right
        t = math.radians(deg)
        y_dir, x_dir = -math.sin(t), math.cos(t)
        rr = np.arange(0, 400)
        ys, xs = (cy + rr * y_dir).astype(int), (cx + rr * x_dir).astype(int)
        ok = (ys >= 0) & (ys < disc.shape[0]) & (xs >= 0) & (xs < disc.shape[1])
        ys, xs = ys[ok], xs[ok]
        rim = disc[ys, xs] & ~cup[ys, xs]
        if rim.any():
            idx = np.nonzero(rim)[0]
            d.line([c.p((ys[idx.min()], xs[idx.min()])), c.p((ys[idx.max()], xs[idx.max()]))], fill=COLOURS['white'] + (255,), width=4)
    detail = ' · '.join(f"{WORD_KO.get(k2, k2)} {v:.0f}" for k2, v in isnt.detail.items())
    return write_example(dict(id='ex_oct_onh_report', modality='oct', modality_label='OCT', region='유두 테 둘레',
                              title='OCT 유두 리포트 · 테 두께 순서와 노치', source='ramirezgandia2026', source_file='provider_figures/cureus-0018-00000115500-i02.webp',
                              caption='Cirrus 유두 큐브 분석 리포트(오른눈, 저자 Figure 2)의 RNFL 편차 지도에 장비가 그린 유두 경계(검정)와 컵 경계(빨강)를 읽어 둘레 전체의 '
                                      'mask로 이었습니다(점선 구간은 각도별 반지름으로 보간, 4배 확대). 이렇게 만든 수직 컵/유두비 '
                                      f'{optic_disc.cup_disc_ratio(disc, cup).value:.2f}는 장비 보고값 0.48과 비슷합니다.'), c,
                         [L('isnt', '테 두께 순서(ISNT)', lay, [('ft_isnt_pattern', isnt, f"{WORD_KO.get(isnt.value, isnt.value)} ({detail}, 확대 화소)")],
                            'optic_disc.isnt_pattern', '유두 중심에서 위·코·아래·귀 방향(흰 선) 테 폭(초록 = 테, 노랑 = 컵)이 아래 ≥ 위 ≥ 코 ≥ 귀 순서인지', 'green'),
                          L('notch', '테 노치', lay, [('ft_cupping_notch', notch)], 'optic_disc.rim_notch',
                            '5° 간격 테 폭이 중앙값의 50 % 미만으로 꺼진 각도가 있는지(없으면 "관찰 안 됨")', 'yellow')])




def cfp_ma_turnover_example() -> dict:
    """RetmarkerDR marks on a colour photograph: red = new, yellow = disappeared, green = present at both visits."""
    box = (222, 395, 372, 530)
    im = provider('592_2020_1602_Fig1_HTML.jpg').crop(box)
    # marker centres read on the figure (original pixels): green both, yellow baseline only, red 6-month only
    green = [(430, 296), (460, 323), (470, 319), (474, 330), (481, 292)]
    yellow = [(428, 325), (433, 332), (436, 334), (437, 278), (448, 298), (450, 312), (460, 232), (481, 307)]
    red = [(432, 304), (453, 316), (456, 321), (470, 341), (474, 345), (482, 359), (503, 309)]
    k = 5
    shape = (im.height, im.width)
    rel = lambda pts: [((r - box[1]), (c - box[0])) for r, c in pts]
    before = disk_mask(shape, rel(green + yellow), 1.5)
    after = disk_mask(shape, rel(green + red), 1.5)
    m = lesions.turnover(before, after)
    big = im.resize((im.width * k, im.height * k), Image.LANCZOS)
    c = Canvas(big, 700)
    lay = c.layer(); d = c.draw(lay)
    for pts, col in ((green, COLOURS['green']), (yellow, COLOURS['blue']), (red, COLOURS['red'])):
        for r, q in rel(pts):
            dot(d, c.p((r * k, q * k)), 9, col, 3)
    return write_example(dict(id='ex_cfp_ma_retmarker', modality='cfp', modality_label='안저', region='미세동맥류 생성·소실',
                              title='안저 · 6개월 미세동맥류 생성·소실', source='marques2021', source_file='provider_figures/592_2020_1602_Fig1_HTML.jpg',
                              caption='2형 당뇨 눈의 안저 사진에 RetmarkerDR가 기준·6개월 방문을 정합해 표시한 미세동맥류입니다(저자 Fig. 1 표현형 C, 5배 확대; 저자 보고 '
                                      'MA turnover 16). 표시점 위치를 그림에서 읽어 두 시점 점 mask를 만들었습니다(겹친 표시는 하나로 셀 수 있음).'), c,
                         [L('turnover', '미세동맥류 생성·소실률', lay, [('ft_ma_turnover', m)], 'lesions.turnover',
                            '두 시점 모두 = 초록, 기준에만 = 파랑(사라짐, 원 그림 노랑), 6개월에만 = 빨강(새로 생김)', 'green')])


def last_figure_examples() -> list[dict]:
    out = []
    # --- venous beading marked by the authors on ultra-widefield FA (Zhuang 2025)
    im = provider('gendis-12-101390-gr1.jpg').crop((8, 180, 205, 330))
    tips, _ = arrow_tips(im, min_px=10)
    vb = disk_mask(np.asarray(im).shape[:2], tips, 4)
    disc, fovea = (88.0, 64.0), (92.0, 97.0)
    for modality, label, ex_id in (('fa', '형광안저혈관조영', 'ex_fa_vb'), ('uwf', '광각 안저', 'ex_uwf_vb')):
        big = im.resize((im.width * 4, im.height * 4), Image.LANCZOS)
        c = Canvas(big, 800)
        up = np.kron(vb, np.ones((4, 4), bool))
        lay = c.mask(up, COLOURS['orange'], 150, 255); d = c.draw(lay)
        f4, d4 = np.asarray(fovea) * 4, np.asarray(disc) * 4
        axis = (d4 - f4) / np.linalg.norm(d4 - f4); normal = np.array([-axis[1], axis[0]])
        for v in (axis, normal):
            d.line([c.p(f4 - 5000 * v), c.p(f4 + 5000 * v)], fill=COLOURS['white'] + (180,), width=2)
        out.append(write_example(dict(id=ex_id, modality=modality, modality_label=label, region='정맥 구슬모양 변화',
                                      title='광각 FA · 정맥 구슬모양 변화', source='zhuang2025', source_file='provider_figures/gendis-12-101390-gr1.jpg',
                                      caption='KDR 변이 환자 왼눈의 광각 형광안저혈관조영(저자 Figure 1A b, 4배 확대)입니다. 저자가 노란 화살표·화살촉으로 표시한 정맥 구슬모양 '
                                              '위치를 병변 점으로, 유두·중심와는 서비스가 읽은 위치를 썼습니다. 원 그림 해상도가 낮아 위치는 대략적입니다.'), c,
                                 [L('vb', '정맥 구슬모양 침범 사분면 수', lay,
                                    [('ft_vb_quadrants', lesions.quadrant_occupancy(vb, fovea, disc, feature_id='ft_vb_quadrants'))],
                                    'lesions.quadrant_occupancy', '유두–중심와 축(흰 선)으로 나눈 사분면 중 저자 화살표 끝(주황)이 있는 사분면 수', 'orange')]))
    return out


def main() -> None:
    examples = [fundus_disc(), fundus_vessels(), fundus_lesions(), lesion_shape_example(), lesion_place_example(),
                fundus_atrophy(), fundus_myopic_disc_example(), fundus_drusen_example(), fundus_nv_example(), fundus_irma_example(),
                fundus_vb_example(), *fundus_small_examples(), fundus_rd_example(), redfree_rnfl_example(), ma_turnover_example(),
                fa_widefield_example(), fa_mnv_example(), faf_example(), nir_change_example(), *icga_nir_examples(),
                oct_layer_example(), oct_inner_example(), oct_lesion_example(), *oct_volume_examples(), amd_sd_volume_example(), *octid_examples(),
                *onh_oct_examples(), octa_example(), *octa_extra_examples(),
                *fa_macula_examples(), fa_widefield_pdr_example(), *faf_lesion_examples(), *nir_examples(), *icga_examples(),
                *octa_vessel_examples(), *uwf_examples(), oct_rora_example(), *oct_small_examples(), *remaining_figure_examples(), *more_figure_examples(), *last_figure_examples(), *before_after_examples(), oct_onh_report_example(), cfp_ma_turnover_example()]
    sources = {**atlas_fig.SOURCES, **EXTRA_SOURCES}
    for ex in examples:
        src = sources[ex['source']]
        ex.update(credit=src['credit'], url=src['url'], license=src['license'], license_url=src['license_url'])
    manifest = {'generated_by': 'code/build_measurement_examples.py',
                'note': 'retinal-measures functions run on provider/expert masks; values in pixels unless stated',
                'examples': examples}
    text = json.dumps(manifest, ensure_ascii=False, indent=1) + '\n'
    MANIFEST.write_text(text, encoding='utf-8')
    (OUTPUT / 'source_manifest.json').write_text(text, encoding='utf-8')
    print(f'{len(examples)} examples, {sum(len(e["layers"]) for e in examples)} layers → {OUTPUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
