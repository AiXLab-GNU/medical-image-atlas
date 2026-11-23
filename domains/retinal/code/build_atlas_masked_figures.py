"""Build masked real-image figures for retinal-atlas-web from openly licensed datasets.

Sources (expert or provider annotations, not our model output):
- IDRiD segmentation set (CC BY 4.0): optic disc, microaneurysm, haemorrhage, hard and soft exudate masks.
- IDRiD localization set (CC BY 4.0): fovea and optic-disc centre coordinates.
- Refined IDRiD (CC BY 4.0): retinal vessel masks on the provider's 1024 px images.
- AMD-SD (CC0): OCT B-scan masks for IRF, SRF, PED, SHRM and IS/OS.

For each figure the script writes a resized base JPEG and a same-size RGBA PNG overlay to
the central resource folder, and the figure metadata (no pixels) to the web package.
Selection rules are deterministic so the same files are chosen on every run.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import retinal_atlas_registry as registry  # noqa: E402  (canonical source / checksum tables)

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
DATASETS = ROOT / 'resources/datasets'
OUTPUT = DATASETS / 'retinal_atlas_masked_figures'
MANIFEST = PROJECT / 'packages/retinal-atlas-web/src/retinal_atlas_web/data/masked_figures.json'

IDRID_SEG = DATASETS / 'public_dr/IDRiD/A. Segmentation/A. Segmentation'
IDRID_LOC = DATASETS / 'public_dr/IDRiD/C. Localization/C. Localization'
REFINED = DATASETS / 'public_dr/refined_idrid/extracted/Train'
AMD_SD = DATASETS / 'public_amd/amd_sd/extracted/AMD-SD'
AVSEG = DATASETS / 'public_dr/fundus_avseg_7c/extracted'
OCTID = DATASETS / 'public_amd/octid/images'
OCTID_MH = DATASETS / 'public_amd/octid_mh/images'
PALM = DATASETS / 'public_myopia/palm/extracted/PALM/Training'
OLIVES = DATASETS / 'olives/zenodo_7105232/extracted'
CHAKSU = DATASETS / 'public_glaucoma/chaksu/extracted/Test'
UWF_ZIP = DATASETS / 'public_dr/uwf_dr_2026/UWF_DR_2026.zip'
UWF_DIR = ('Ultra-wide-field (SLO) fundus image dataset for intelligent diabetic retinopathy system/'
           'diabetic retinopathy/PDR512/')
SERVICE = '서비스 표시(자동 추정, 전문가 검토 전)'
ARTICLE_FIGURES = DATASETS / 'retinal_atlas_modality_figures'
AVSEG_LABELS = {'retina': 8, 'vein': 12, 'fovea': 16, 'crossing': 20, 'artery': 24, 'disc': 32}
ARTERY, VEIN = (235, 64, 52), (40, 110, 235)
AMD_PALETTE = {'IRF': (0, 255, 0), 'SRF': (255, 0, 0), 'PED': (0, 0, 255), 'SHRM': (255, 255, 0),
               'IS_OS': (255, 0, 255)}
SOURCES = registry.source_records()          # g_image_sources_v01.csv
HIGHLIGHT = (255, 211, 77)
BASE_WIDTH = 1200


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overlay_from_mask(mask: np.ndarray, color=HIGHLIGHT, fill_alpha=95, edge_alpha=255, thin=False) -> Image.Image:
    """Semi-transparent fill plus a solid contour for a boolean mask."""
    mask_img = Image.fromarray((mask > 0).astype(np.uint8) * 255)
    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    rgba[..., :3] = color
    if thin:
        rgba[..., 3] = np.where(mask > 0, 220, 0)
    else:
        grown = np.array(mask_img.filter(ImageFilter.MaxFilter(5))) > 0
        edge = grown & ~(mask > 0)
        rgba[..., 3] = np.where(mask > 0, fill_alpha, 0)
        rgba[..., 3] = np.where(edge, edge_alpha, rgba[..., 3])
    return Image.fromarray(rgba, 'RGBA')


def save_pair(name: str, base: Image.Image, overlay: Image.Image, context=None) -> dict:
    scale = min(1.0, BASE_WIDTH / base.width)
    size = (round(base.width * scale), round(base.height * scale))
    base = base.convert('RGB').resize(size, Image.LANCZOS)
    overlay = overlay.resize(size, Image.LANCZOS)
    base_path, overlay_path = OUTPUT / f'{name}.jpg', OUTPUT / f'{name}_mask.png'
    base.save(base_path, quality=88)
    overlay.save(overlay_path, optimize=True)
    record = {'base': base_path.name, 'overlay': overlay_path.name, 'width': size[0], 'height': size[1],
              'base_sha256': sha256(base_path), 'overlay_sha256': sha256(overlay_path)}
    if context is not None:  # (full image, crop box): locator showing where the zoomed crop sits in the whole image
        full, (x0, y0, x1, y1) = context
        k = 360 / full.width
        thumb = full.convert('RGB').resize((360, round(full.height * k)), Image.LANCZOS)
        ImageDraw.Draw(thumb).rectangle((x0 * k, y0 * k, x1 * k, y1 * k), outline=HIGHLIGHT, width=3)
        context_path = OUTPUT / f'{name}_context.jpg'
        thumb.save(context_path, quality=88)
        record |= {'context': context_path.name, 'context_sha256': sha256(context_path)}
    return record


def crop_box(mask: np.ndarray, size: tuple[int, int]) -> tuple[int, int, int, int]:
    """Window of `size` (w, h) containing the most mask pixels (coarse integral-image search)."""
    h, w = mask.shape
    cw, ch = min(size[0], w), min(size[1], h)
    integral = np.pad(mask.astype(np.int64), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    best, best_xy = -1, (0, 0)
    for y in range(0, h - ch + 1, 32):
        for x in range(0, w - cw + 1, 32):
            total = integral[y + ch, x + cw] - integral[y, x + cw] - integral[y + ch, x] + integral[y, x]
            if total > best:
                best, best_xy = total, (x, y)
    return best_xy[0], best_xy[1], best_xy[0] + cw, best_xy[1] + ch


def idrid_mask(image_id: str, folder: str, suffix: str) -> np.ndarray | None:
    path = IDRID_SEG / '2. All Segmentation Groundtruths/a. Training Set' / folder / f'{image_id}_{suffix}.tif'
    return np.array(Image.open(path)) > 0 if path.exists() else None


def fundus_figures() -> list[dict]:
    lesion_specs = [('1. Microaneurysms', 'MA'), ('2. Haemorrhages', 'HE'), ('3. Hard Exudates', 'EX'),
                    ('4. Soft Exudates', 'SE')]
    images = sorted((IDRID_SEG / '1. Original Images/a. Training Set').glob('IDRiD_*.jpg'))
    # Deterministic choice: the training image with soft exudates that has the largest total lesion area.
    scored = []
    for path in images:
        image_id = path.stem
        masks = {code: idrid_mask(image_id, folder, code) for folder, code in lesion_specs}
        if all(m is not None and m.any() for m in masks.values()):
            scored.append((sum(int(m.sum()) for m in masks.values()), image_id))
    image_id = max(scored)[1]
    original = Image.open(IDRID_SEG / f'1. Original Images/a. Training Set/{image_id}.jpg')
    source_file = f'A. Segmentation/1. Original Images/a. Training Set/{image_id}.jpg'
    figures = []
    disc = idrid_mask(image_id, '5. Optic Disc', 'OD')
    figures.append(dict(id='fundus_optic_disc', items=['ana_optic_disc', 'ana_peripapillary_region'],
                        source='idrid_seg', source_file=source_file, mask_label='시신경유두(전문가 분할)',
                        caption='컬러 안저 사진에서 시신경유두 경계를 표시했습니다.',
                        transform='원본 4288×2848을 가로 1200 px로 축소; mask를 같은 비율로 축소해 반투명 겹침',
                        **save_pair('fundus_optic_disc', original, overlay_from_mask(disc))))
    lesion_items = {'MA': (['les_microaneurysm', 'les_red_lesion_pooled'], '미세동맥류'),
                    'HE': (['les_hemorrhage_pooled', 'les_hemorrhage_dot_blot'], '출혈(층위 미구분)'),
                    'EX': (['les_hard_exudate'], '경성삼출물'),
                    'SE': (['les_cotton_wool_spot'], '면화반(연성삼출물)')}
    for folder, code in lesion_specs:
        mask = idrid_mask(image_id, folder, code)
        x0, y0, x1, y1 = crop_box(mask, (1400, 930))
        items, label = lesion_items[code]
        crop_mask = mask[y0:y1, x0:x1]
        figures.append(dict(id=f'fundus_{code.lower()}', items=items, source='idrid_seg', source_file=source_file,
                            mask_label=f'{label}(전문가 분할)',
                            caption=f'컬러 안저 사진의 일부를 확대해 {label} 위치를 표시했습니다.',
                            transform=f'원본에서 ({x0},{y0})–({x1},{y1}) 영역을 잘라 가로 1200 px로 확대·축소; '
                                      'mask 외곽선과 반투명 채움',
                            **save_pair(f'fundus_{code.lower()}', original.crop((x0, y0, x1, y1)),
                                        overlay_from_mask(crop_mask), context=(original, (x0, y0, x1, y1)))))
    # Vessels on the provider's refined 1024 px image (same IDRiD numbering).
    vessel_mask = np.array(Image.open(REFINED / f'Labels/{image_id}_vessel.png')) > 0
    vessel_image = Image.open(REFINED / f'Images/{image_id}.jpg')
    figures.append(dict(id='fundus_vessels', items=['ana_retinal_vasculature', 'ana_vascular_tree',
                                                     'ana_vascular_arcades'],
                        source='refined_idrid', source_file=f'Train/Images/{image_id}.jpg',
                        mask_label='망막 혈관(전문가 정제 분할; 동정맥 미구분)',
                        caption='같은 눈의 안저 사진에서 망막 혈관을 표시했습니다.',
                        transform='공급자 1024×1024 영상과 혈관 mask를 그대로 사용(가는 선 강조)',
                        **save_pair('fundus_vessels', vessel_image,
                                    overlay_from_mask(vessel_mask, color=(64, 224, 255), thin=True))))
    return figures


def colour_layer(masks_colours, shape, alpha=225) -> Image.Image:
    rgba = np.zeros((*shape, 4), dtype=np.uint8)
    for mask, colour in masks_colours:
        rgba[mask, :3] = colour
        rgba[mask, 3] = alpha
    return Image.fromarray(rgba, 'RGBA')


def vessel_figures() -> list[dict]:
    """Artery/vein, crossing, OCTA plexus, FAZ and cilioretinal-territory figures."""
    from scipy import ndimage
    from skimage import filters, morphology

    figures = []
    name = '005_N'  # normal eye, posterior pole centred, disc on the right like the schematics
    image = Image.open(AVSEG / f'OrginalImages/Org/{name}.png').convert('RGB')
    label = np.array(Image.open(AVSEG / f'Fundus-AVSeg-7C-Mask/Labels/Org/{name}.png'))
    artery, vein = label == AVSEG_LABELS['artery'], label == AVSEG_LABELS['vein']
    crossing, disc = label == AVSEG_LABELS['crossing'], label == AVSEG_LABELS['disc']
    common = dict(source='fundus_avseg_7c', source_file=f'OrginalImages/Org/{name}.png',
                  transform='공급자 1024×1024 영상과 7분류 mask(동맥 24·정맥 12·교차 20·유두 32)를 그대로 사용')
    legend_av = [{'label': '동맥', 'cls': 'artery'}, {'label': '정맥', 'cls': 'vein'}]
    figures.append(dict(id='fundus_arteries', items=['ana_retinal_arterioles'], mask_label='망막 동맥(전문가 분할)',
                        caption='정상 눈의 안저 사진에서 동맥만 빨간색으로 표시했습니다. 정맥보다 가늘고 밝은 붉은색입니다.',
                        legend=[{'label': '동맥', 'cls': 'artery'}], **common,
                        **save_pair('fundus_arteries', image, colour_layer([(artery, ARTERY)], artery.shape))))
    figures.append(dict(id='fundus_veins', items=['ana_retinal_venules'], mask_label='망막 정맥(전문가 분할)',
                        caption='같은 눈에서 정맥만 파란색으로 표시했습니다. 동맥보다 굵고 어두운 붉은색입니다.',
                        legend=[{'label': '정맥', 'cls': 'vein'}], **common,
                        **save_pair('fundus_veins', image, colour_layer([(vein, VEIN)], vein.shape))))
    figures.append(dict(id='fundus_av', items=['ana_retinal_vasculature', 'ana_vascular_tree', 'ana_vascular_arcades'],
                        mask_label='동맥·정맥(전문가 분할)', legend=legend_av,
                        caption='동맥(빨강)과 정맥(파랑)을 함께 표시했습니다. 유두에서 나온 이측 큰 가지가 황반을 위·아래로 둘러싸며 혈관 아케이드를 이룹니다.',
                        **common, **save_pair('fundus_av', image,
                                              colour_layer([(vein, VEIN), (artery, ARTERY)], artery.shape))))
    ys, xs = np.nonzero(disc)
    cy, cx = int(ys.mean()), int(xs.mean())
    half = int(1.6 * (xs.max() - xs.min()))
    box = (max(cx - half, 0), max(cy - half, 0), min(cx + half, image.width), min(cy + half, image.height))
    edge = disc & ~ndimage.binary_erosion(disc, iterations=3)
    disc_layer = colour_layer([(vein, VEIN), (artery, ARTERY), (edge, (255, 255, 255))], disc.shape)
    figures.append(dict(id='fundus_av_disc', items=['ana_central_retinal_artery', 'ana_central_retinal_vein'],
                        mask_label='유두의 동맥·정맥(전문가 분할)',
                        legend=legend_av + [{'label': '시신경유두 경계', 'cls': 'disc'}],
                        caption='시신경유두를 확대했습니다. 중심망막동·정맥은 유두 중앙에서 나와 위·아래 가지로 갈라집니다(줄기 자체는 시신경 안에 있어 안저에서는 유두 위의 시작 부분만 보입니다).',
                        **(common | {'transform': common['transform'] + f'; 유두 주변 {box} 영역을 잘라 확대'}),
                        **save_pair('fundus_av_disc', image.crop(box), disc_layer.crop(box), context=(image, box))))
    rings = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(rings)
    labels, n = ndimage.label(crossing)
    near_a = ndimage.binary_dilation(artery, iterations=4)
    near_v = ndimage.binary_dilation(vein, iterations=4)
    keep = [i for i in range(1, n + 1) if (near_a & (labels == i)).any() and (near_v & (labels == i)).any()]
    centres = ndimage.center_of_mass(crossing, labels, keep)
    n = len(keep)
    for y, x in centres:
        draw.ellipse((x - 14, y - 14, x + 14, y + 14), outline=(255, 211, 77, 255), width=4)
    figures.append(dict(id='fundus_av_crossing', items=['ana_av_crossing'], mask_label=f'동정맥 교차 {n}곳(전문가 표시)',
                        legend=[{'label': '동정맥 교차', 'cls': 'crossing'}],
                        caption='동맥과 정맥이 겹쳐 지나가는 지점을 노란 원으로 표시했습니다. 고혈압성 변화에서 교차부 정맥이 눌려 보이는 소견(AV nicking)을 보는 자리입니다.',
                        **(common | {'transform': common['transform'] + '; 동맥·정맥 모두에 닿는 교차 성분 중심에 반지름 14 px 원'}),
                        **save_pair('fundus_av_crossing', image, rings)))

    # OCTA plexus slabs (article panels already cropped for the modality pages)
    for fig_id, item, crop, colour, block, offset, label_ko in [
            ('octa_scp_flow', 'ana_superficial_capillary_plexus', 'octa_scp.jpg', (239, 68, 68), 25, -4, '표층'),
            ('octa_icp_flow', 'ana_intermediate_capillary_plexus', 'octa_icp.jpg', (168, 85, 247), 25, -4, '중간'),
            ('octa_dcp_flow', 'ana_deep_capillary_plexus', 'octa_dcp.jpg', (56, 189, 248), 15, -2, '심층')]:
        base = Image.open(ARTICLE_FIGURES / crop).convert('RGB')
        g = np.asarray(base.convert('L'), dtype=float)
        flow = g > filters.threshold_local(ndimage.gaussian_filter(g, 0.7), block, offset=offset)
        flow = morphology.remove_small_objects(flow, 15)
        figures.append(dict(id=fig_id, items=[item, 'zone_octa_slab'], source='feng2024', source_file=f'retinal_atlas_modality_figures/{crop}',
                            mask_label=f'{label_ko} 모세혈관망 혈류 신호(자동 이진화)', legend=[{'label': f'{label_ko} 혈류', 'cls': fig_id}],
                            caption=f'OCTA {label_ko} 모세혈관망 슬랩에서 혈류 신호를 색으로 표시했습니다. 표시는 국소 임계값으로 자동 이진화한 것이며 전문가 분할이 아닙니다.',
                            transform=f'논문 패널을 국소 임계값(block {block}, offset {offset})으로 이진화',
                            **save_pair(fig_id, base, colour_layer([(flow, colour)], flow.shape, alpha=170))))
    base = Image.open(ARTICLE_FIGURES / 'octa_scp.jpg').convert('RGB')
    g = ndimage.gaussian_filter(np.asarray(base.convert('L'), dtype=float), 3)
    h, w = g.shape
    win = g[h // 2 - 40:h // 2 + 40, w // 2 - 40:w // 2 + 40]
    dy, dx = np.unravel_index(win.argmin(), win.shape)
    seed = (h // 2 - 40 + dy, w // 2 - 40 + dx)
    lab, _ = ndimage.label(g < np.percentile(win, 25))
    faz = ndimage.binary_fill_holes(ndimage.binary_closing(ndimage.binary_opening(lab == lab[seed], iterations=2),
                                                           iterations=3))
    figures.append(dict(id='octa_faz', items=['ana_foveal_avascular_zone'], source='feng2024',
                        source_file='retinal_atlas_modality_figures/octa_scp.jpg', mask_label='중심와 무혈관 구역(자동 추정)',
                        legend=[{'label': '무혈관 구역', 'cls': 'faz'}],
                        caption='OCTA 표층 슬랩 가운데 혈관이 없는 어두운 부분을 노란색으로 표시했습니다. 자동 영역 추정이라 경계는 대략적입니다.',
                        transform='중심 80 px 창의 가장 어두운 점에서 하위 25 백분위 영역을 확장·평활',
                        **save_pair('octa_faz', base, overlay_from_mask(faz))))

    # Cilioretinal artery territory: perfused (dark) tongue on red-free CRAO image
    figure = Image.open(ARTICLE_FIGURES / 'provider_figures/cureus-0015-00000048157-i01.jpg').convert('RGB')
    panel = figure.crop((390, 0, 750, 268))
    g = ndimage.median_filter(np.asarray(panel.convert('L'), dtype=float), 9)
    seed = (125, 135)
    lab, _ = ndimage.label(np.abs(g - g[seed]) < 10)
    region = ndimage.binary_opening(lab == lab[seed], iterations=3)
    lab, _ = ndimage.label(region)
    region = ndimage.binary_fill_holes(ndimage.binary_closing(lab == lab[seed], iterations=3))
    figures.append(dict(id='cilioretinal_territory', items=['ana_cilioretinal_artery'], source='bhatt2023',
                        source_file='provider_figures/cureus-0015-00000048157-i01.jpg', mask_label='섬모체망막동맥 관류 영역(자동 추정)',
                        legend=[{'label': '섬모체망막동맥 영역', 'cls': 'cilio'}],
                        caption='중심망막동맥폐쇄로 망막이 하얗게 된 눈(무적색광 사진)에서, 섬모체망막동맥이 살려 둔 유두–황반 사이 혀 모양 영역이 어둡게 남아 있습니다. 그 영역을 주황색으로 표시했습니다.',
                        transform='Figure 1b 패널을 잘라 씨앗점 영역 확장(허용 오차 10)으로 대략 표시',
                        **save_pair('cilioretinal_territory', panel,
                                    overlay_from_mask(region, color=(255, 140, 0)))))
    return figures


def _grow(gray, seed, tol, box=None):
    from scipy import ndimage
    region = np.abs(gray - gray[seed]) < tol
    if box:
        x0, y0, x1, y1 = box
        limit = np.zeros_like(region)
        limit[y0:y1, x0:x1] = True
        region &= limit
    labels, _ = ndimage.label(region)
    region = labels == labels[seed]
    region = ndimage.binary_opening(region, iterations=2)
    labels, _ = ndimage.label(region)
    if labels[seed]:
        region = labels == labels[seed]
    return ndimage.binary_fill_holes(ndimage.binary_closing(region, iterations=3))


def _box(shape, box):
    m = np.zeros(shape, bool)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = True
    return m


def public_lesion_figures() -> list[dict]:
    """Service-marked lesions on openly licensed images without lesion masks (stage ②)."""
    import zipfile
    from scipy import ndimage
    from skimage import filters, morphology

    figures = []

    def add(fig_id, items, source, source_file, image, mask, label, caption, method, colour=HIGHLIGHT, thin=False):
        figures.append(dict(id=fig_id, items=items, source=source, source_file=source_file,
                            mask_label=f'{label} — {SERVICE}', caption=caption, transform=method,
                            legend=[{'label': label, 'cls': 'service'}],
                            **save_pair(fig_id, image, overlay_from_mask(mask, color=colour, thin=thin))))

    def oct_img(name):
        img = Image.open(OCTID / f'{name}.jpeg').convert('RGB')
        return img, ndimage.gaussian_filter(np.asarray(img.convert('L'), dtype=float), 2)

    # --- OCTID B-scans (CC0)
    img, g = oct_img('AMRD37')
    ped = _grow(g, (235, 500), 22, (345, 140, 655, 300))
    add('octid_ped_serous', ['les_ped_serous', 'les_ped_unspecified'], 'octid', 'images/AMRD37.jpeg', img, ped,
        '색소상피박리 내부', 'AMD 눈의 OCT에서 RPE가 크게 돔 모양으로 들린 색소상피박리입니다. 속이 어둡고 고른 부분을 표시했습니다.',
        '씨앗점(500, 235) 영역 확장(허용 오차 22)')
    img, g = oct_img('AMRD12')
    heavy = ndimage.gaussian_filter(g, 4)
    vit = np.median(heavy[5:30, :])
    below_ilm = np.zeros(g.shape, bool)
    for x in range(g.shape[1]):
        hit = np.nonzero(heavy[:, x] > vit + 30)[0]
        if hit.size:
            below_ilm[hit[0] + 6:, x] = True
    cysts = (g < filters.threshold_otsu(g[60:195, 190:560])) & below_ilm & _box(g.shape, (190, 40, 560, 192))
    keep = morphology.remove_small_objects(morphology.binary_opening(cysts, morphology.disk(3)), 60)
    add('octid_cme', ['les_cystoid_macular_edema'], 'octid', 'images/AMRD12.jpeg', img, ndimage.binary_fill_holes(keep),
        '낭포 공간', '망막 안에 생긴 크고 작은 낭포(어두운 둥근 공간)를 표시했습니다.', '열마다 내경계막(ILM) 아래에서 Otsu 임계보다 어두운 60 px 이상 성분')
    img, g = oct_img('AMRD15')
    x0, x1, y0, y1 = 240, 600, 215, 280
    ys = np.array([y0 + int(np.argmax(g[y0:y1, x])) for x in range(x0, x1)], dtype=float)
    base = ndimage.maximum_filter1d(ys, 70)
    drusen = np.zeros(g.shape, bool)
    for k, x in enumerate(range(x0, x1)):
        if base[k] - ys[k] > 4:
            drusen[int(ys[k]) + 3:int(base[k]) + 1, x] = True
    drusen = morphology.remove_small_objects(ndimage.binary_closing(drusen, iterations=2), 30)
    add('octid_drusen', ['les_drusen_unspecified'], 'octid', 'images/AMRD15.jpeg', img, drusen,
        'RPE 아래 드루젠', 'RPE가 작은 언덕처럼 솟은 드루젠(RPE 아래 침착물)을 표시했습니다.',
        'B-scan 열마다 RPE(가장 밝은 점)를 찾고, 이동 최대값 기준선보다 솟은 부분을 채움')
    img, g = oct_img('AMRD7')
    dome = _grow(g, (255, 365), 30, (322, 200, 408, 292))
    add('octid_ped_drusenoid', ['les_ped_drusenoid'], 'octid', 'images/AMRD7.jpeg', img, dome,
        '중심와 아래 돔 모양 융기', '중심와 아래 중간 반사의 돔 모양 융기로, 드루젠양 색소상피박리로 보이는 병변입니다.',
        '씨앗점(365, 255) 영역 확장(허용 오차 30)')
    img, g = oct_img('AMRD42')
    core = _grow(g, (212, 435), 18, (412, 192, 460, 234))
    ring = ndimage.binary_dilation(core, iterations=6)
    add('octid_ort', ['les_outer_retinal_tubulation'], 'octid', 'images/AMRD42.jpeg', img, ring,
        '고리 모양 구조', '외망막 안의 밝은 테두리를 가진 둥근 고리(외망막 관상 구조)를 표시했습니다.',
        '어두운 중심 씨앗점(435, 212) 확장 후 6 px 팽창')
    img, g = oct_img('AMRD27')
    band = g[215:330, :]
    col = band.mean(0)
    ref = np.median(np.r_[col[60:200], col[640:820]])
    cols = np.zeros(g.shape[1], bool)
    cols[245:600] = col[245:600] > ref + 6
    cols = ndimage.binary_opening(cols, structure=np.ones(4))
    columns = np.zeros(g.shape, bool)
    columns[215:330, cols] = True
    add('octid_hypertd', ['les_hypertransmission'], 'octid', 'images/AMRD27.jpeg', img,
        columns, '맥락막 쪽 과투과',
        'RPE가 손상된 곳 아래로 신호가 깊이 들어가 맥락막에 생긴 밝은 세로 기둥(과투과)을 표시했습니다.',
        '맥락막 띠(깊이 215–330 px)의 열 평균 밝기가 병변 밖 기준보다 6 이상 높은 열')

    def hyaloid(g, x0, x1, ymax):
        line = np.zeros(g.shape, bool)
        vit = np.median(g[5:60, x0:x1])
        for x in range(x0, x1):
            col = g[:ymax, x]
            retina = np.nonzero(col > vit + 45)[0]
            top = retina[0] - 6 if retina.size else ymax
            if top < 8:
                continue
            y = int(np.argmax(col[:top]))
            if col[y] > vit + 14:
                line[max(0, y - 1):y + 2, x] = True
        return morphology.remove_small_objects(ndimage.binary_closing(line, structure=np.ones((3, 9))), 40)
    img, g = oct_img('AMRD25')
    add('octid_vmt', ['les_vitreomacular_traction'], 'octid', 'images/AMRD25.jpeg', img, hyaloid(g, 100, 470, 200),
        '후유리체막', '비스듬히 내려온 후유리체막이 중심와에 붙어 망막을 끌어당기고 있습니다(그 아래 망막하액).',
        '열마다 망막 위 유리체에서 가장 밝은 점을 이어 선으로 표시', thin=True)
    img, g = oct_img('AMRD48')
    add('octid_vma', ['les_vitreomacular_adhesion'], 'octid', 'images/AMRD48.jpeg', img, hyaloid(g, 0, 879, 200),
        '후유리체막', '후유리체막이 황반 표면을 따라 붙어 있는 모습을 표시했습니다(아래 망막하 반흔과 별개).',
        '열마다 망막 위 유리체에서 가장 밝은 점을 이어 선으로 표시', thin=True)
    scar = _grow(g, (225, 340), 40, (200, 190, 560, 300))
    add('octid_fibrotic', ['les_fibrotic_scar'], 'octid', 'images/AMRD48.jpeg', img, scar,
        '망막하 고반사 반흔', '망막 아래의 밝고 두꺼운 물질로, 신생혈관 뒤 생긴 섬유성 반흔으로 보이는 병변입니다.',
        '씨앗점(340, 225) 영역 확장(허용 오차 40)')

    # --- Fundus-AVSeg colour fundus (CC BY 4.0)
    def avseg(name):
        img = Image.open(AVSEG / f'OrginalImages/Org/{name}.png').convert('RGB')
        lab = np.array(Image.open(AVSEG / f'Fundus-AVSeg-7C-Mask/Labels/Org/{name}.png'))
        return img, np.asarray(img, dtype=float), lab
    for name, item, size_note, fig_id in (('061_A', 'les_drusen_large', '대형', 'fundus_drusen_large'),
                                          ('063_A', 'les_drusen_medium', '중형', 'fundus_drusen_medium')):
        img, a, lab = avseg(name)
        green = ndimage.gaussian_filter(a[..., 1], 1.2)
        tophat = morphology.white_tophat(green, morphology.disk(14 if size_note == '대형' else 8))
        fov = ndimage.binary_erosion(lab > 0, iterations=12)
        disc_mask = lab == AVSEG_LABELS['disc']
        near_disc = ndimage.distance_transform_edt(~disc_mask) < 1.8 * np.sqrt(disc_mask.sum() / np.pi)
        exclude = near_disc | ndimage.binary_dilation((lab == AVSEG_LABELS['artery']) | (lab == AVSEG_LABELS['vein']),
                                                      iterations=7)
        spots = (tophat > np.percentile(tophat[fov & ~exclude], 97.5)) & fov & ~exclude
        spots = morphology.remove_small_objects(spots, 12)
        add(fig_id, [item], 'fundus_avseg_7c', f'OrginalImages/Org/{name}.png', img, spots, f'노란 드루젠({size_note})',
            f'AMD 눈의 안저 사진에서 노란 드루젠을 표시했습니다. 유두 직경(약 1,500 µm)과 비교한 크기는 {size_note} 드루젠에 해당합니다.',
            '녹색 채널 top-hat 상위 2.5 %, 유두 주변·혈관 제외')
    img, a, lab = avseg('083_G')
    disc = lab == AVSEG_LABELS['disc']
    green = ndimage.gaussian_filter(a[..., 1], 2)
    cup = disc & (green > np.percentile(green[disc], 50))
    cup = ndimage.binary_fill_holes(morphology.remove_small_objects(ndimage.binary_opening(cup, iterations=3), 200))
    edge = disc & ~ndimage.binary_erosion(disc, iterations=3)
    figures.append(dict(id='fundus_cupping', items=['les_disc_cupping'], source='fundus_avseg_7c',
                        source_file='OrginalImages/Org/083_G.png', mask_label=f'함몰(밝은 부분) — {SERVICE}',
                        legend=[{'label': '함몰', 'cls': 'service'}, {'label': '유두 경계(전문가 분할)', 'cls': 'disc'}],
                        caption='녹내장 눈의 유두입니다. 유두 경계(흰 선)는 데이터셋의 전문가 분할이고, 함몰로 보이는 밝은 부분은 자동 추정입니다.',
                        transform='유두 mask 안 녹색 채널 상위 50 % 밝기',
                        **save_pair('fundus_cupping', img, Image.alpha_composite(
                            overlay_from_mask(cup), colour_layer([(edge, (255, 255, 255))], edge.shape)))))
    img, a, lab = avseg('068_A')
    disc = lab == AVSEG_LABELS['disc']
    dist = ndimage.distance_transform_edt(~disc)
    radius = np.sqrt(disc.sum() / np.pi)
    lum = ndimage.gaussian_filter(a.mean(-1), 3)
    ring = (dist > 2) & (dist < 0.9 * radius)
    vessels = ndimage.binary_dilation((lab == AVSEG_LABELS['artery']) | (lab == AVSEG_LABELS['vein']), iterations=3)
    far = (dist > 1.5 * radius) & (dist < 3 * radius)
    ppa = ring & ~vessels & (lum > np.percentile(lum[far], 90))
    ppa = morphology.remove_small_objects(ndimage.binary_closing(ppa, iterations=3), 150)
    add('fundus_ppa', ['les_peripapillary_atrophy'], 'fundus_avseg_7c', 'OrginalImages/Org/068_A.png', img, ppa,
        '유두주위 위축', '유두 바로 바깥의 창백한 띠(유두주위 위축)를 표시했습니다.', '유두 경계에서 0.9 반지름 안, 주변보다 밝은 부분(혈관 제외)')
    img, a, lab = avseg('056_A')
    red = ndimage.gaussian_filter(a[..., 0], 1.5)
    fov = ndimage.binary_erosion(lab > 0, iterations=15)
    retinal = ndimage.binary_dilation((lab == AVSEG_LABELS['artery']) | (lab == AVSEG_LABELS['vein']) |
                                      (lab == AVSEG_LABELS['disc']), iterations=5)
    lower = np.zeros_like(fov)
    lower[int(img.height * 0.55):, :] = True
    chor = (red > filters.threshold_local(red, 41, offset=-3)) & fov & ~retinal & lower
    chor = morphology.remove_small_objects(chor, 60)
    add('fundus_tessellated', ['les_tessellated_fundus'], 'fundus_avseg_7c', 'OrginalImages/Org/056_A.png', img, chor,
        '비쳐 보이는 맥락막 혈관', '아래쪽 망막을 통해 맥락막 혈관이 줄무늬처럼 비쳐 보이는 호피 모양 안저입니다. 아래쪽 구역의 맥락막 혈관을 표시했습니다.',
        '아래쪽 45 % 구역의 적색 채널 국소 임계 위, 망막 혈관·유두 제외', thin=True)

    # --- UWF-DR (CC BY 4.0)
    with zipfile.ZipFile(UWF_ZIP) as z:
        for fig_id, name, item, label, caption, method in (
                ('uwf_preretinal', '5_142_2021-11-14_1_R.png', 'les_hemorrhage_preretinal', '큰 출혈',
                 '증식 당뇨망막병증 눈의 광각 영상에서 황반 근처의 큰 검붉은 출혈(망막앞 출혈로 보임)을 표시했습니다.', 'seed'),
                ('uwf_fvp', '5_118_2022-04-21_3_R.png', 'les_fibrovascular_proliferation', '섬유혈관 증식막',
                 '증식 당뇨망막병증 눈의 광각 영상에서 혈관궁을 따라 자란 섬유혈관 증식막(노랗고 흰 막)을 표시했습니다.', 'colour')):
            img = Image.open(z.open(UWF_DIR + name)).convert('RGB')
            a = np.asarray(img, dtype=float)
            if method == 'seed':
                lum = ndimage.gaussian_filter(a.mean(-1), 2)
                mask = _grow(lum, (290, 240), 16, (165, 215, 310, 330))
                how = '씨앗점(240, 290) 영역 확장(허용 오차 16)'
            else:
                r, gch = ndimage.gaussian_filter(a[..., 0], 1), ndimage.gaussian_filter(a[..., 1], 1)
                mask = (gch > 95) & (r > 125) & _box(r.shape, (190, 120, 380, 420))
                mask = morphology.remove_small_objects(ndimage.binary_closing(mask, iterations=2), 40)
                how = '상자 안 노랗고 밝은 화소(녹색 > 95, 적색 > 125)'
            add(fig_id, [item], 'uwf_dr_2026', 'PDR512/' + name, img, mask, label, caption, how)
    return figures


VITREOUS, MEMBRANE = (125, 211, 252), (244, 114, 182)


def vitreoretinal_figures() -> list[dict]:
    """Service-marked vitreoretinal interface findings on OCTID macular-hole B-scans (stage ③, CC0)."""
    from scipy import ndimage
    from skimage import filters, morphology

    figures = []

    def load(name):
        img = Image.open(OCTID_MH / f'{name}.jpeg').convert('RGB')
        return img, ndimage.gaussian_filter(np.asarray(img.convert('L'), dtype=float), 2)

    def surface(g, x0, x1, ystart=0, rise=45):
        """Row of the inner retinal surface (first column hit above the vitreous level)."""
        vit = np.median(g[ystart:ystart + 30, x0:x1])
        heavy = ndimage.gaussian_filter(g, 3)
        top = np.full(g.shape[1], -1)
        for x in range(x0, x1):
            hit = np.nonzero(heavy[ystart:, x] > vit + rise)[0]
            if hit.size:
                top[x] = ystart + hit[0]
        return top

    def add(fig_id, items, name, img, layers, legend, caption, method):
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        for mask, colour, thin, *alpha in layers:
            overlay = Image.alpha_composite(overlay, overlay_from_mask(
                mask, color=colour, thin=thin, fill_alpha=alpha[0] if alpha else 95,
                edge_alpha=0 if alpha else 255))
        figures.append(dict(id=fig_id, items=items, source='octid_mh', source_file=f'images/{name}.jpeg',
                            mask_label=f'{legend[0]["label"]} — {SERVICE}', caption=caption, transform=method,
                            legend=legend, **save_pair(fig_id, img, overlay)))

    # Full-thickness macular hole: the gap between the hole edges down to the RPE.
    img, g = load('MH7')
    hole = _grow(g, (185, 365), 20, (312, 122, 424, 214))
    add('octid_mh_full', ['les_macular_hole_full_thickness'], 'MH7', img, [(hole, HIGHLIGHT, False)],
        [{'label': '전층 결손', 'cls': 'service'}],
        '망막 전층이 끊겨 RPE까지 뚫린 황반원공입니다. 양쪽 가장자리는 낭포로 부풀어 있습니다. 구멍 부분을 표시했습니다.',
        '씨앗점(365, 185) 영역 확장(허용 오차 20), 원공 가장자리 위쪽 선까지로 제한')

    # Lamellar-looking hole: irregular inner defect with preserved outer retina at the base.
    img, g = load('MH97')
    lam = _grow(g, (122, 375), 16, (298, 98, 445, 150))
    add('octid_mh_lamellar', ['les_macular_hole_lamellar'], 'MH97', img, [(lam, HIGHLIGHT, False)],
        [{'label': '안쪽 망막 결손', 'cls': 'service'}],
        '중심와의 안쪽 망막이 넓게 패였지만 바닥의 바깥 망막은 남아 있습니다. 층판 황반원공으로 보이는 결손 부분을 표시했습니다.',
        '씨앗점(375, 122) 영역 확장(허용 오차 16), 결손 가장자리 위쪽 선까지로 제한')

    # Epiretinal membrane: bright, wrinkled surface line.
    img, g = load('MH30')
    top = surface(g, 380, 748, ystart=40, rise=40)
    erm = np.zeros(g.shape, bool)
    for x in range(380, 748):
        if top[x] > 0:
            erm[top[x]:top[x] + 4, x] = True
    erm = morphology.remove_small_objects(erm, 30)
    add('octid_erm', ['les_epiretinal_membrane'], 'MH30', img, [(erm, MEMBRANE, True)],
        [{'label': '표면의 밝은 막', 'cls': 'membrane'}],
        '원공 옆 망막 표면을 덮은 밝고 주름진 막으로, 망막전막으로 보입니다. 막이 당기는 곳마다 표면이 뾰족하게 솟아 있습니다.',
        '열마다 망막 표면의 첫 밝은 점에서 4 px 두께의 선')

    # ERM with foveoschisis: columnar intraretinal splitting under the surface membrane.
    img, g = load('MH17')
    top = surface(g, 400, 748, ystart=20, rise=40)
    heavy = ndimage.gaussian_filter(g, 3)
    inside = np.zeros(g.shape, bool)
    membrane = np.zeros(g.shape, bool)
    for x in range(400, 748):
        if top[x] <= 0:
            continue
        rpe = top[x] + 40 + int(np.argmax(heavy[top[x] + 40:, x]))  # RPE: brightest row below the inner retina
        inside[top[x] + 6:rpe - 26, x] = True
        membrane[top[x]:top[x] + 3, x] = True
    vit = np.median(g[20:50, 400:748])
    dark = (g < vit + 14) & inside
    schisis = morphology.remove_small_objects(morphology.binary_opening(dark, np.ones((5, 1))), 80)
    add('octid_erm_schisis', ['les_erm_foveoschisis'], 'MH17', img,
        [(schisis, HIGHLIGHT, False), (membrane, MEMBRANE, True)],
        [{'label': '층간분리 공간', 'cls': 'service'}, {'label': '표면의 막', 'cls': 'membrane'}],
        '표면 막 아래 망막 안쪽이 세로 기둥 모양으로 갈라진 층간분리로 보입니다(같은 단면에 황반원공 동반). '
        '갈라진 공간과 표면 막을 표시했습니다.',
        '열마다 망막 표면과 RPE 사이에서 유리체 밝기 +14 이하인 80 px 이상 성분; 막은 표면 첫 밝은 점에서 3 px')

    # Posterior hyaloid and the vitreous gel in front of it.
    img, g = load('MH25')
    vit = np.median(g[20:60, :])
    line = np.zeros(g.shape, bool)
    for x in range(4, 740):
        y = 40 + int(np.argmax(g[40:186, x]))  # band between the image top and the retinal surface (~y 195)
        if g[y, x] > vit + 10:
            line[max(0, y - 1):y + 2, x] = True
    line = morphology.remove_small_objects(ndimage.binary_closing(line, structure=np.ones((3, 9))), 60)
    first = np.full(g.shape[1], -1)
    rows = np.argmax(line, axis=0)
    first[line.any(0)] = rows[line.any(0)]
    known = np.nonzero(first > 0)[0]
    rows = np.interp(np.arange(known[0], known[-1] + 1), known, first[known]).astype(int)
    gel = np.zeros(g.shape, bool)
    for x, row in zip(range(known[0], known[-1] + 1), rows):
        gel[12:row - 2, x] = True
    add('octid_hyaloid', ['ana_posterior_hyaloid', 'ana_vitreous'], 'MH25', img,
        [(gel, VITREOUS, False, 60), (line, HIGHLIGHT, True)],
        [{'label': '후유리체막', 'cls': 'service'}, {'label': '유리체 젤 쪽', 'cls': 'vitreous'}],
        '망막에서 떨어져 들린 후유리체막이 원공 가장자리에만 붙어 있습니다. 막 위쪽이 유리체 젤, '
        '막과 망막 사이의 어두운 공간은 막이 떨어져 생긴 공간입니다.',
        '열마다 망막 위 띠(깊이 40–186 px)에서 가장 밝은 점을 이은 선; 그 위쪽을 유리체 쪽으로 옅게 칠함')
    return figures


def myopia_figures() -> list[dict]:
    """Pathologic-myopia findings: PALM expert masks (CC0) and one OCTID macular-hole B-scan (stage ③)."""
    import pandas as pd
    from scipy import ndimage
    from skimage import measure

    figures = []
    fovea = pd.read_excel(PALM / 'Fovea Localization.xlsx').set_index('imgName')

    def palm(name):
        img = Image.open(PALM / f'Images/{name}.jpg').convert('RGB')
        def mask(folder):
            path = PALM / f'{folder}/{name}.bmp'
            return np.array(Image.open(path).convert('L')) < 128 if path.exists() else np.zeros(img.size[::-1], bool)
        fx, fy = fovea.loc[f'{name}.jpg']
        return img, mask('Lesion Masks/Atrophy'), mask('Disc Masks'), mask('Lesion Masks/Detachment'), (int(fy), int(fx))

    def outline(mask, width=6):
        return mask & ~ndimage.binary_erosion(mask, iterations=width)

    def add(fig_id, items, name, img, layers, legend, mask_label, caption, method, source='palm', folder='Images'):
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        for layer in layers:
            overlay = Image.alpha_composite(overlay, layer)
        figures.append(dict(id=fig_id, items=items, source=source, source_file=f'{folder}/{name}.jpg' if source == 'palm'
                            else f'images/{name}.jpeg', mask_label=mask_label, caption=caption, transform=method,
                            legend=legend, **save_pair(fig_id, img, overlay)))

    # Macular atrophy: the expert atrophy component that contains the fovea.
    img, atrophy, disc, _, fov = palm('P0004')
    labels, _ = ndimage.label(atrophy)
    macular = labels == labels[fov]
    add('palm_macular_atrophy', ['les_myopic_macular_atrophy'], 'P0004', img,
        [overlay_from_mask(macular), colour_layer([(outline(disc), (255, 255, 255))], disc.shape)],
        [{'label': '위축(전문가 분할)', 'cls': 'service'}, {'label': '유두 경계', 'cls': 'disc'}],
        '중심와를 덮는 위축(공급자 전문가 분할)',
        '병적 근시 눈에서 중심와를 덮는 경계가 뚜렷한 둥근 위축입니다. 가장자리에 색소가 모여 있습니다. '
        '공급자 위축 mask 중 중심와 좌표를 포함한 조각만 표시했습니다.',
        '공급자 위축 mask의 연결 성분 중 공급자 중심와 좌표를 포함한 성분; 유두 경계는 공급자 유두 mask')

    # Patchy atrophy: discrete atrophy patches away from the disc and the fovea.
    img, atrophy, disc, _, fov = palm('P0031')
    labels, n = ndimage.label(atrophy)
    near_disc = ndimage.binary_dilation(disc, iterations=40)
    patches = np.zeros_like(atrophy)
    for k in range(1, n + 1):
        part = labels == k
        if not (part & near_disc).any() and not part[fov]:
            patches |= part
    add('palm_patchy_atrophy', ['les_myopic_patchy_atrophy'], 'P0031', img,
        [overlay_from_mask(patches), colour_layer([(outline(disc), (255, 255, 255))], disc.shape)],
        [{'label': '반점형 위축(전문가 분할)', 'cls': 'service'}, {'label': '유두 경계', 'cls': 'disc'}],
        '따로 떨어진 위축 조각(공급자 전문가 분할)',
        '병적 근시 눈의 후극부에 흩어진, 경계가 뚜렷한 회백색 위축 조각들입니다. 유두에 붙은 유두주위 위축은 빼고 '
        '따로 떨어진 조각만 표시했습니다.',
        '공급자 위축 mask의 연결 성분 중 유두 mask(40 px 팽창)와 닿지 않는 성분')

    # Tilted disc: the expert disc outline and its ovality.
    img, atrophy, disc, _, _ = palm('P0054')
    props = measure.regionprops(disc.astype(np.uint8))[0]
    ratio = props.minor_axis_length / props.major_axis_length
    add('palm_tilted_disc', ['les_tilted_disc'], 'P0054', img,
        [overlay_from_mask(disc, fill_alpha=40), colour_layer([(outline(atrophy & ndimage.binary_dilation(disc, iterations=250), 4),
                                                                (255, 255, 255))], disc.shape)],
        [{'label': '유두(전문가 분할)', 'cls': 'service'}, {'label': '유두주위 위축 경계', 'cls': 'disc'}],
        '유두(공급자 전문가 분할)',
        f'병적 근시 눈의 기울어진 유두입니다. 유두 mask에 맞춘 타원의 짧은 지름/긴 지름 비는 {ratio:.2f}이고, '
        '유두 옆에 넓은 유두주위 위축(흰 선)이 붙어 있습니다.',
        '공급자 유두 mask를 옅게 칠하고 타원 근사(regionprops)로 짧은/긴 지름 비 계산; 흰 선은 유두 근처 공급자 위축 mask 경계')

    # Retinal detachment drawn by the provider.
    img, atrophy, disc, detach, _ = palm('P0058')
    add('palm_detachment', ['les_retinal_detachment_rhegmatogenous'], 'P0058', img,
        [overlay_from_mask(detach, color=(64, 224, 255))],
        [{'label': '망막박리(전문가 분할)', 'cls': 'vitreous'}],
        '망막박리 범위(공급자 전문가 분할)',
        '병적 근시 눈에서 후극부 망막이 넓게 들뜬 망막박리입니다(공급자 표시). 이 영상만으로 열공이 원인인지는 '
        '확인할 수 없습니다.',
        '공급자 망막박리 mask')

    # Posterior staphyloma-looking curvature on OCT (service-traced RPE).
    img = Image.open(OCTID_MH / 'MH28.jpeg').convert('RGB')
    g = ndimage.gaussian_filter(np.asarray(img.convert('L'), dtype=float), 3)
    ys = ndimage.median_filter(np.argmax(g[60:440, :], axis=0) + 60, 25)
    rpe = np.zeros(g.shape, bool)
    for x, y in enumerate(ys):
        rpe[y - 2:y + 2, x] = True
    add('octid_staphyloma', ['les_posterior_staphyloma'], 'MH28', img, [overlay_from_mask(rpe, thin=True)],
        [{'label': 'RPE 선', 'cls': 'service'}], f'눈 뒤벽 굴곡(RPE 선) — {SERVICE}',
        '눈 뒤벽(RPE 선)이 중심와 쪽으로 깊게 오목해진 고도근시 단면으로, 후포도종으로 보이는 굴곡입니다(같은 단면에 '
        '황반원공 동반). 후포도종의 확정에는 넓은 범위 영상이 필요합니다.',
        '열마다 깊이 60–440 px에서 가장 밝은 행(가우시안 σ 3), 열 방향 중앙값 필터(25)', source='octid_mh')
    return figures


PAPER_FIGURES = {name: (row['source_id'], row['sha256'])   # g_provider_figures_v01.csv
                 for name, row in registry.provider_figures_for('masked_figures').items()}


def paper_myopia_figures() -> list[dict]:
    """Myopic findings on CC BY article figure panels with service marks (stage ③)."""
    from scipy import ndimage

    figures = []

    def panel(name, box=None):
        path = ARTICLE_FIGURES / 'provider_figures' / name
        if sha256(path) != PAPER_FIGURES[name][1]:
            raise ValueError(f'provider figure changed: {name}')
        img = Image.open(path).convert('RGB')
        return img.crop(box) if box else img

    def ring(shape, cx, cy, rx, ry, width=4):
        yy, xx = np.mgrid[:shape[0], :shape[1]]
        r = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        inner = ((xx - cx) / (rx - width)) ** 2 + ((yy - cy) / (ry - width)) ** 2
        return (r <= 1) & (inner > 1)

    def add(fig_id, items, name, img, layers, legend, caption, method, crop):
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        for layer in layers:
            overlay = Image.alpha_composite(overlay, layer)
        source = PAPER_FIGURES[name][0]
        figures.append(dict(id=fig_id, items=items, source=source, source_file=f'provider_figures/{name}',
                            mask_label=f'{legend[0]["label"]} — {SERVICE}', caption=caption,
                            transform=f'{crop}; {method}', legend=legend, **save_pair(fig_id, img, overlay)))

    # Myopic traction maculopathy: outer retinoschisis band and foveal detachment pocket.
    img = panel('12886_2016_195_Fig1_HTML.gif')
    g = ndimage.gaussian_filter(np.asarray(img.convert('L'), dtype=float), 1.2)
    schisis = _grow(g, (125, 140), 16, (20, 100, 300, 147))
    pocket = _grow(g, (146, 185), 18, (160, 136, 215, 155))
    add('paper_myopic_traction', ['les_myopic_traction_maculopathy'], '12886_2016_195_Fig1_HTML.gif', img,
        [overlay_from_mask(schisis), overlay_from_mask(pocket, color=(64, 224, 255))],
        [{'label': '망막층간분리', 'cls': 'service'}, {'label': '중심와 박리', 'cls': 'vitreous'}],
        '고도근시 눈의 OCT입니다. 바깥 망막이 기둥을 남기며 넓게 갈라졌고(층간분리), 중심와 아래에는 망막이 '
        'RPE에서 들뜬 주머니(중심와 박리)가 있습니다. 근시성 견인 황반병증의 전형적 소견입니다(저자 설명).',
        '층간분리: 씨앗점(140, 125) 영역 확장(허용 오차 16); 박리: 씨앗점(185, 146) 영역 확장(허용 오차 18)',
        '원 그림 전체(358×184)')

    # Lacquer crack: ring around the crack the authors' black arrows point to (2001 panel).
    img = panel('12886_2021_2216_Fig1_HTML.png', (0, 0, 643, 484))
    add('paper_lacquer_crack', ['les_lacquer_crack'], '12886_2021_2216_Fig1_HTML.png', img,
        [overlay_from_mask(ring((484, 643), 292, 302, 34, 40), thin=True)],
        [{'label': '래커 균열 부위', 'cls': 'service'}],
        '고도근시(−20 D) 눈의 2001년 안저 사진입니다. 검은 화살표가 가리키는 가는 노란 선이 래커 균열이며(저자 표시), '
        '노란 원으로 그 부위를 둘렀습니다. 이 균열은 5년 뒤 사진에서는 보이지 않았습니다.',
        '저자 화살표가 가리키는 부위에 타원(중심 292, 302)', '패널 a(0, 0, 643, 484) 잘라냄')

    # Dome-shaped macula: RPE contour traced along the top of the bright RPE–sclera band.
    img = panel('12886_2020_1473_Fig1_HTML.png', (0, 0, 1418, 370))
    g = ndimage.gaussian_filter(np.asarray(img.convert('L'), dtype=float), 3)
    bright = g > 175
    bright[:190] = False
    labels, n = ndimage.label(bright)
    band = labels == (1 + int(np.argmax(ndimage.sum(bright, labels, range(1, n + 1)))))
    tops = np.where(band.any(0), np.argmax(band, axis=0), -1)
    cols = np.nonzero(tops > 0)[0]
    tops = ndimage.median_filter(tops[cols], 31)
    rpe = np.zeros(g.shape, bool)
    for x, y in zip(cols, tops):
        rpe[y - 2:y + 3, x] = True
    add('paper_dome_macula', ['les_dome_shaped_macula'], '12886_2020_1473_Fig1_HTML.png', img,
        [overlay_from_mask(rpe, thin=True)],
        [{'label': 'RPE 선(돔 윤곽)', 'cls': 'service'}],
        '고도근시 눈의 세로 OCT입니다. 뒤로 오목해야 할 RPE 선이 중심와 아래에서 안쪽으로 볼록하게 솟아 있습니다'
        '(돔 높이 85 µm, 저자 측정). 검은 선은 저자의 높이·지름 측정선, 흰 삼각형은 공막 바깥 경계입니다.',
        '밝은 RPE–공막 띠(가우시안 σ 3, 밝기 > 175)의 최대 연결 성분 윗경계, 열 방향 중앙값 필터(31)',
        '패널 A(0, 0, 1418, 370) 잘라냄')

    # Myopic CNV: OCT B-scan (A) and OCTA en face (B) of the same lesion.
    img = panel('fmed-08-657772-g002.jpg', (0, 0, 268, 478))
    add('paper_myopic_cnv', ['les_myopic_cnv'], 'fmed-08-657772-g002.jpg', img,
        [overlay_from_mask(ring((478, 268), 124, 238, 58, 66), thin=True),
         overlay_from_mask(ring((478, 268), 150, 52, 22, 26, 3), thin=True)],
        [{'label': '신생혈관막', 'cls': 'service'}],
        '고도근시(−14.75 D) 눈의 활동성 근시성 맥락막 신생혈관입니다. 위 OCT(A)에서 RPE 위로 솟은 고반사 병변(2형 CNV), '
        '아래 OCTA(B)에서 어두운 테두리로 둘러싸인 그물 모양 신생혈관막이 보입니다(저자 설명). 노란 원은 두 영상의 병변 위치입니다.',
        '저자 화살표·화살촉 부위에 타원 두 개', '왼쪽 열 패널 A–B(0, 0, 268, 478) 잘라냄')
    return figures


def fovea_figure() -> dict:
    def read(path):
        with path.open(encoding='utf-8-sig', newline='') as handle:
            return {row[0]: (int(row[1]), int(row[2])) for row in csv.reader(handle)
                    if row and row[0].startswith('IDRiD_') and row[1]}
    gt = IDRID_LOC / '2. Groundtruths'
    fovea = read(gt / '2. Fovea Center Location/IDRiD_Fovea_Center_Training Set_Markups.csv')
    disc = read(gt / '1. Optic Disc Center Location/a. IDRiD_OD_Center_Training Set_Markups.csv')
    image_id = sorted(set(fovea) & set(disc))[0]
    image = Image.open(IDRID_LOC / f'1. Original Images/a. Training Set/{image_id}.jpg')
    (fx, fy), (dx, dy) = fovea[image_id], disc[image_id]
    dd = abs(dx - fx) / 2.5  # disc diameter estimated from the disc–fovea distance (≈2.5 DD)
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w = max(4, round(image.width / 600))
    for radius, alpha in ((1.5 * dd, 255), (0.75 * dd, 255)):
        draw.ellipse((fx - radius, fy - radius, fx + radius, fy + radius), outline=(*HIGHLIGHT, alpha), width=w)
    draw.ellipse((fx - 3 * w, fy - 3 * w, fx + 3 * w, fy + 3 * w), fill=(*HIGHLIGHT, 255))
    draw.ellipse((dx - 3 * w, dy - 3 * w, dx + 3 * w, dy + 3 * w), fill=(64, 224, 255, 255))
    draw.line((dx, dy, fx, fy), fill=(255, 255, 255, 200), width=max(2, w // 2))
    return dict(id='fundus_fovea_landmarks',
                items=['ref_fovea_center', 'ref_disc_center', 'ref_disc_diameter', 'ana_fovea', 'ana_macula',
                       'ana_posterior_pole'],
                source='idrid_loc', source_file=f'C. Localization/1. Original Images/a. Training Set/{image_id}.jpg',
                mask_label='중심와 중심(노랑)·유두 중심(하늘) 좌표와 파생 원',
                caption='전문가가 표시한 중심와·유두 중심 좌표입니다. 노란 원 두 개는 좌표에서 계산한 대략적 범위'
                        '(유두–중심와 거리 ≈ 2.5 DD 가정)이며 분할이 아닙니다.',
                transform='원본을 가로 1200 px로 축소; 좌표 점·연결선·파생 원(반지름 0.75·1.5 DD)을 겹침',
                **save_pair('fundus_fovea_landmarks', image, overlay))


def oct_figures() -> list[dict]:
    specs = [('IRF', ['les_intraretinal_fluid', 'les_cystoid_macular_edema'], '망막내액'),
             ('SRF', ['les_subretinal_fluid', 'les_serous_retinal_detachment'], '망막하액'),
             ('PED', ['les_ped_unspecified', 'les_ped_fibrovascular'], '색소상피박리'),
             ('SHRM', ['les_shrm'], '망막하 고반사 물질'),
             ('IS_OS', ['ana_ellipsoid_zone', 'les_ez_disruption', 'ana_photoreceptors'], 'IS/OS(EZ에 해당) 띠')]
    paths = sorted(AMD_SD.glob('images/*/*.png'), key=lambda p: (int(p.parent.name), p.stem))
    best: dict[str, tuple[int, Path]] = {}
    for path in paths:
        rgb = np.array(Image.open(path).convert('RGB'))
        mask_rgb = rgb[:, rgb.shape[1] // 2:]
        for code, color in AMD_PALETTE.items():
            area = int(np.all(np.abs(mask_rgb.astype(int) - color) < 40, axis=2).sum())
            if area > best.get(code, (0, None))[0]:
                best[code] = (area, path)
    figures = []
    for code, items, label in specs:
        path = best[code][1]
        rgb = np.array(Image.open(path).convert('RGB'))
        half = rgb.shape[1] // 2
        oct_img, mask_rgb = Image.fromarray(rgb[:, :half]), rgb[:, half:]
        mask = np.all(np.abs(mask_rgb.astype(int) - AMD_PALETTE[code]) < 40, axis=2)
        name = f'oct_{code.lower()}'
        figures.append(dict(id=name, items=items, source='amd_sd',
                            source_file=f'images/{path.parent.name}/{path.name}',
                            mask_label=f'{label}(공급자 분할)',
                            caption=f'OCT B-scan에서 {label}을(를) 표시했습니다. 공급자 mask 중 해당 병변 면적이 가장 큰 단면입니다.',
                            transform='공급자 결합 영상의 왼쪽 OCT 절반(570×380)을 원 크기로 사용; 오른쪽 색 mask에서 해당 색만 추출해 겹침',
                            **save_pair(name, oct_img, overlay_from_mask(mask, thin=code == 'IS_OS'))))
    return figures


def grade4_figures() -> list[dict]:
    """Expert IRMA, NV and vitreous-haemorrhage labels of the Refined IDRiD unified masks."""
    from scipy import ndimage

    figures = []
    for fig_id, image_id, code, items, label, note in [
            ('fundus_irma', 'IDRiD_08', 96, ['les_irma'], '망막내 미세혈관 이상(IRMA)',
             '굵은 혈관 사이에서 가늘고 구불구불하게 갈라진 이상 혈관입니다.'),
            ('fundus_nv', 'IDRiD_27', 166, ['les_neovascularization_pooled'], '신생혈관(NV)',
             '공급자 mask는 유두 신생혈관(NVD)과 망막 신생혈관(NVE)을 나누지 않습니다. 이 눈의 표시는 유두 경계에서 '
             '약 1 유두지름 안팎의 큰 혈관을 따라 있습니다.'),
            ('fundus_vh', 'IDRiD_17', 4, ['les_hemorrhage_vitreous'], '유리체 출혈',
             '아래쪽에 고인 넓은 출혈이 망막 혈관을 가리고 있습니다.')]:
        label_map = np.array(Image.open(REFINED / f'Labels/{image_id}_vessel.png'))
        mask = ndimage.binary_closing(label_map == code, iterations=2) | (label_map == code)
        suffix = 'png' if (REFINED / f'Images/{image_id}.png').exists() else 'jpg'
        image = Image.open(REFINED / f'Images/{image_id}.{suffix}').convert('RGB')
        transform = '공급자 1024×1024 영상과 통합 mask(IRMA 96·NV 166·VH 4)를 그대로 사용'
        if code == 96:
            x0, y0, x1, y1 = crop_box(mask, (720, 480))
            context = (image, (x0, y0, x1, y1))
            image, mask = image.crop((x0, y0, x1, y1)), mask[y0:y1, x0:x1]
            transform += f'; ({x0},{y0})–({x1},{y1}) 영역을 잘라 확대'
        else:
            context = None
        figures.append(dict(id=fig_id, items=items, source='refined_idrid', source_file=f'Train/Images/{image_id}.{suffix}',
                            mask_label=f'{label}(공급자 전문가 mask)',
                            caption=f'컬러 안저 사진에서 {label}을(를) 표시했습니다. {note}',
                            transform=transform, **save_pair(fig_id, image, overlay_from_mask(mask), context=context)))
    return figures


def zone_figures() -> list[dict]:
    """Macular and peripapillary reference zones drawn from expert fovea/disc labels of a normal eye."""
    name = '005_N'
    image = Image.open(AVSEG / f'OrginalImages/Org/{name}.png').convert('RGB')
    label = np.array(Image.open(AVSEG / f'Fundus-AVSeg-7C-Mask/Labels/Org/{name}.png'))
    fy, fx = np.argwhere(label == AVSEG_LABELS['fovea']).mean(0)
    from skimage.morphology import convex_hull_image
    disc = convex_hull_image(label == AVSEG_LABELS['disc'])  # provider disc label excludes vessels on the disc
    dy, dx = np.argwhere(disc).mean(0)
    mm = float(np.hypot(dx - fx, dy - fy)) / 4.5  # px per mm, disc centre–fovea ≈ 4.5 mm
    common = dict(source='fundus_avseg_7c', source_file=f'OrginalImages/Org/{name}.png')
    scale_note = f'유두 중심–중심와 거리를 4.5 mm로 가정해 1 mm ≈ {mm:.0f} px로 환산'
    yy, xx = np.mgrid[:label.shape[0], :label.shape[1]]
    r_fovea = np.hypot(xx - fx, yy - fy) / mm

    def ring(r0, r1):
        return (r_fovea >= r0) & (r_fovea < r1)

    figures = []
    for fig_id, items, r0, r1, label_ko, extra in [
            ('zone_foveola', ['ana_foveola'], 0, 0.175, '중심소와(지름 0.35 mm)', '중심와 바닥의 가장 얇은 가운데 부분입니다.'),
            ('zone_parafovea', ['ana_parafovea'], 0.75, 1.25, '부중심와(중심에서 0.75–1.25 mm 띠)',
             '중심와(지름 1.5 mm)를 둘러싼 0.5 mm 폭의 띠로, 신경절세포층이 가장 두꺼운 곳입니다.'),
            ('zone_perifovea', ['ana_perifovea'], 1.25, 2.75, '주변황반(중심에서 1.25–2.75 mm 띠)',
             '부중심와 바깥 1.5 mm 폭의 띠로, 황반의 가장 바깥 부분입니다.')]:
        mask = ring(r0, r1)
        figures.append(dict(id=fig_id, items=items, mask_label=f'{label_ko}(해부학적 정의로 그린 구역)',
                            caption=f'정상 눈 안저 사진에서 {label_ko}을(를) 표시했습니다. {extra} 중심은 전문가가 표시한 '
                                    '중심와이고, 크기는 평균 눈 크기로 환산한 근사입니다.',
                            transform=f'{scale_note}; 전문가 중심와 mask의 중심에서 반지름 {r0}–{r1} mm 영역', **common,
                            **save_pair(fig_id, image, overlay_from_mask(mask, fill_alpha=80 if r0 else 120))))
    # ETDRS grid: 1, 3, 6 mm circles; inner and outer rings split into four sectors.
    grid = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(grid)
    for radius in (0.5, 1.5, 3.0):
        r = radius * mm
        draw.ellipse((fx - r, fy - r, fx + r, fy + r), outline=(*HIGHLIGHT, 255), width=3)
    for angle in (45, 135, 225, 315):
        c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
        draw.line((fx + 0.5 * mm * c, fy + 0.5 * mm * s, fx + 3 * mm * c, fy + 3 * mm * s), fill=(*HIGHLIGHT, 255), width=3)
    figures.append(dict(id='zone_etdrs_grid', items=['zone_etdrs_grid'], mask_label='ETDRS 격자(1·3·6 mm 원, 9구역)',
                        caption='정상 눈 안저 사진에 ETDRS 격자를 겹쳤습니다. 중심 1 mm 원, 3 mm·6 mm 고리를 위·아래·코쪽·귀쪽 '
                                '네 구역으로 나눠 모두 9구역이며, OCT 두께 지도는 이 구역별 평균으로 보고합니다.',
                        transform=f'{scale_note}; 전문가 중심와 mask의 중심에 격자를 그림', **common,
                        **save_pair('zone_etdrs_grid', image, grid)))
    # Peripapillary band: disc margin to the 3.46 mm circle used by OCT RNFL scans.
    r_disc = np.hypot(xx - dx, yy - dy) / mm
    band = (r_disc < 1.73) & ~disc
    edge = Image.new('RGBA', image.size, (0, 0, 0, 0))
    edge.alpha_composite(overlay_from_mask(band, fill_alpha=70))
    edge.alpha_composite(overlay_from_mask(disc, color=(255, 255, 255), fill_alpha=0))
    box = (int(dx - 2.6 * mm), int(dy - 2.6 * mm), int(dx + 2.6 * mm), int(dy + 2.6 * mm))
    figures.append(dict(id='zone_peripapillary', items=['zone_peripapillary'],
                        mask_label='유두주위 구역(유두 경계–지름 3.46 mm 원)',
                        legend=[{'label': '유두주위 구역', 'cls': 'service'}, {'label': '시신경유두 경계(전문가)', 'cls': 'disc'}],
                        caption='시신경유두(흰 선, 전문가 분할) 바깥에서 OCT 유두주위 신경섬유층 원형 스캔 자리(지름 3.46 mm)까지를 '
                                '표시했습니다.',
                        transform=f'{scale_note}; 전문가 유두 mask(유두 위 혈관 자리를 볼록 껍질로 메움) 중심에서 반지름 1.73 mm 원 안, 유두 바깥; {box} 영역을 잘라 확대',
                        **common, **save_pair('zone_peripapillary', image.crop(box), edge.crop(box), context=(image, box))))
    # Quadrants: horizontal line through the disc–fovea axis, vertical line through the fovea.
    quad = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(quad)
    angle = np.arctan2(dy - fy, dx - fx)
    far = 2 * image.width
    for a in (angle, angle + np.pi / 2):
        draw.line((fx - far * np.cos(a), fy - far * np.sin(a), fx + far * np.cos(a), fy + far * np.sin(a)),
                  fill=(*HIGHLIGHT, 255), width=4)
    nasal = 1 if dx > fx else -1
    for text, (ox, oy) in [('위', (0, -0.3)), ('아래', (0, 0.3)), ('코쪽', (0.22 * nasal, 0.05)), ('귀쪽', (-0.22 * nasal, 0.05))]:
        x, y = fx + ox * image.width, fy + oy * image.height
        draw.rounded_rectangle((x - 34, y - 18, x + 34, y + 18), 6, fill=(0, 0, 0, 150))
        draw.text((x, y), {'위': 'S', '아래': 'I', '코쪽': 'N', '귀쪽': 'T'}[text], fill=(*HIGHLIGHT, 255), anchor='mm',
                  font=ImageFont.load_default(size=26))
    figures.append(dict(id='zone_fundus_quadrant', items=['zone_fundus_quadrant'],
                        mask_label='안저 사분면(S 위·I 아래·N 코쪽·T 귀쪽)',
                        caption='중심와를 지나는 두 선으로 안저를 위·아래·코쪽·귀쪽 사분면으로 나눴습니다. 가로선은 유두와 중심와를 '
                                '잇는 선입니다. 사분면의 기준점(중심와 또는 유두)은 쓰임새마다 다를 수 있습니다.',
                        transform='전문가 중심와·유두 mask 중심을 지나는 선과 그 수직선', **common,
                        **save_pair('zone_fundus_quadrant', image, quad)))
    return figures


def crao_figures() -> list[dict]:
    """Cherry-red spot and ischaemic whitening on the colour panel of the CRAO case figure."""
    from scipy import ndimage

    source_file = 'provider_figures/cureus-0015-00000048157-i01.jpg'
    panel = Image.open(ARTICLE_FIGURES / source_file).convert('RGB').crop((0, 0, 372, 268))
    fx, fy = 178, 86  # darkest point of the smoothed panel near the macula
    spot = Image.new('RGBA', panel.size, (0, 0, 0, 0))
    ImageDraw.Draw(spot).ellipse((fx - 16, fy - 16, fx + 16, fy + 16), outline=(*HIGHLIGHT, 255), width=3)
    g = ndimage.median_filter(np.asarray(panel.convert('L'), dtype=float), 11)
    yy, xx = np.mgrid[:g.shape[0], :g.shape[1]]
    r = np.hypot(xx - fx, yy - fy)
    zone = (r < 120) & (r > 10) & (yy < 250)
    pale = zone & (g > np.percentile(g[zone], 35))
    pale = ndimage.binary_fill_holes(ndimage.binary_closing(ndimage.binary_opening(pale, iterations=3), iterations=4)) & zone
    labels, n = ndimage.label(pale)
    pale = labels == 1 + int(np.argmax(ndimage.sum(pale, labels, range(1, n + 1))))
    common = dict(source='bhatt2023', source_file=source_file)
    transform = 'Figure 1a 컬러 패널(0,0)–(372,268)을 잘라 확대'
    return [
        dict(id='crao_cherry_red_spot', items=['les_cherry_red_spot'], mask_label=f'체리 적색 반점 위치({SERVICE})',
             caption='중심망막동맥폐쇄 눈의 컬러 안저 사진입니다. 주변 망막이 허혈로 뿌옇게 하얘져서, 망막이 가장 얇은 중심와는 '
                     '맥락막 색이 비쳐 상대적으로 붉고 어둡게 보입니다(노란 원).',
             transform=transform + '; 평활 영상에서 황반 부근 가장 어두운 점에 원', **common,
             **save_pair('crao_cherry_red_spot', panel, spot)),
        dict(id='crao_retinal_whitening', items=['les_retinal_whitening'], mask_label=f'허혈성 백색 부종 범위(대략, {SERVICE})',
             caption='같은 눈에서 허혈로 하얗고 불투명해진 후극부 망막을 대략 표시했습니다. 유두와 중심와 사이의 어두운 혀 모양 '
                     '부분은 섬모체망막동맥이 살려 둔 곳이라 표시에서 빠져 있습니다. 경계는 밝기 기준의 자동 추정입니다.',
             transform=transform + '; 중심와에서 반지름 120 px 안, 밝기 상위 65% 영역을 열기·닫기 후 가장 큰 덩어리', **common,
             **save_pair('crao_retinal_whitening', panel, overlay_from_mask(pale, fill_alpha=80))),
    ]


def _trace_layers(g):
    """Per-column ILM, OPL, ONL, EZ, RPE and Bruch-membrane rows of a Spectralis B-scan (simple profile rules)."""
    from scipy import ndimage
    h, w = g.shape
    rpe = ndimage.median_filter(np.argmax(ndimage.gaussian_filter(g, (1.5, 6))[60:430], axis=0) + 60, 15)
    grad = ndimage.gaussian_filter(g, (3, 6), order=(1, 0))
    ilm = ndimage.median_filter(np.array([np.argmax(grad[:max(rpe[x] - 25, 5), x]) for x in range(w)]), 11)
    s = ndimage.gaussian_filter(g, (1, 5))
    s2 = ndimage.gaussian_filter(g, (3, 8))
    bm, ez, opl, onl = [], [], [], []
    for x in range(w):
        r = int(rpe[x])
        below = s[r:r + 15, x]
        bm.append(r + int(np.argmax(below < (below[0] + below.min()) / 2)))
        ez.append(r - 20 + int(np.argmax(s[r - 20:r - 6, x])))
        a, b = int(ilm[x] + 0.35 * (r - ilm[x])), r - 14
        o = a + int(np.argmin(s2[a:b, x])) if b > a + 3 else a
        top = max(int(ilm[x]) + 3, o - 25)
        onl.append(o)
        opl.append(top + int(np.argmax(s2[top:o, x])) if o > top else o)
    med = lambda v, k=15: ndimage.median_filter(np.array(v), k)
    return dict(ilm=ilm, rpe=rpe, bm=med(bm), ez=med(ez, 9), opl=med(opl, 21), onl=med(onl, 21))


def _band(shape, top, bottom):
    rows = np.arange(shape[0])[:, None]
    return (rows >= np.asarray(top)[None, :]) & (rows < np.asarray(bottom)[None, :])


def olives_figures() -> list[dict]:
    """Retinal layers on a label-free foveal B-scan and three biomarker-labelled DME B-scans (OLIVES)."""
    from scipy import ndimage

    def load(rel):
        return np.asarray(Image.open(OLIVES / rel).convert('L'), dtype=float)

    figures = []
    rows = slice(40, 340)  # drop the empty lower half of the 496-row scan
    normal = 'TREX DME/Monthly/0222MOS/V26/OS/TREX_DME_000024.tif'
    g = load(normal)
    t = _trace_layers(g)
    base = Image.fromarray(g.astype(np.uint8)).convert('RGB').crop((0, rows.start, g.shape[1], rows.stop))
    line = lambda v, width=2: _band(g.shape, np.asarray(v) - width // 2, np.asarray(v) + (width + 1) // 2)
    note = ('공급자 바이오마커 16종이 모두 0(이상 없음)인 중심와 단면입니다. 경계는 열마다 밝기 변화로 자동 추적한 것이라 '
            '실제 층 경계와 몇 화소 어긋날 수 있습니다.')
    layer_specs = [
        ('olives_ilm', ['ana_ilm'], '내경계막(망막 안쪽 표면)', line(t['ilm'], 3), True,
         '유리체와 망막이 만나는 맨 위 밝은 경계입니다. 위쪽의 가는 선은 떨어진 후유리체막입니다.'),
        ('olives_total_retina', ['ana_total_retina'], '전체 망막(내경계막–브루크막)', _band(g.shape, t['ilm'], t['bm']), False,
         'OCT 두께 지도가 재는 전체 망막 구간입니다. 중심와에서 가장 얇습니다.'),
        ('olives_neurosensory_retina', ['ana_neurosensory_retina'], '신경감각망막(내경계막–RPE 위)',
         _band(g.shape, t['ilm'], t['rpe'] - 4), False, '빛을 받아 신호를 만드는 망막 본체로, 아래의 RPE와는 따로 셉니다.'),
        ('olives_inner_retina', ['ana_inner_retina'], '내망막(내경계막–바깥망상층)', _band(g.shape, t['ilm'], t['opl']), False,
         '신경섬유층·신경절세포층·속망상층·속핵층을 포함하는 안쪽 구간입니다. 중심와에서는 옆으로 비켜나 거의 없습니다.'),
        ('olives_outer_retina', ['ana_outer_retina'], '외망막(바깥망상층–브루크막)', _band(g.shape, t['opl'], t['bm']), False,
         '외핵층·광수용체·RPE를 포함하는 바깥 구간으로, 중심와에서 오히려 두꺼워집니다.'),
        ('olives_onl', ['ana_onl'], '외핵층(어두운 두꺼운 띠)', _band(g.shape, t['opl'] + 3, t['ez'] - 6), False,
         '광수용체 세포체가 모인 어두운 띠입니다. 중심와 아래에서 가장 두껍습니다.'),
        ('olives_bruch', ['ana_bruch_membrane'], '브루크막 위치(RPE 띠 아래 경계)', line(t['bm'], 3), True,
         '정상 눈에서는 RPE와 붙어 있어 따로 보이지 않으므로, RPE 밝은 띠의 아래 경계를 브루크막 위치로 표시했습니다.'),
    ]
    for fig_id, items, label, mask, thin, extra in layer_specs:
        mask = mask[rows]
        figures.append(dict(id=fig_id, items=items, source='olives', source_file=normal,
                            mask_label=f'{label}({SERVICE})', caption=f'OCT B-scan에서 {label}을(를) 표시했습니다. {extra} {note}',
                            transform=f'원 B-scan 504×496에서 {rows.start}–{rows.stop}행을 잘라 사용; 열별 밝기 경계 자동 추적',
                            **save_pair(fig_id, base, overlay_from_mask(mask, thin=thin, fill_alpha=85))))

    def scan_base(rel):
        g = load(rel)
        return g, Image.fromarray(g.astype(np.uint8)).convert('RGB').crop((0, rows.start, g.shape[1], rows.stop))

    dme = 'TREX DME/GILA/0204GOS/V21/OS/TREX_DME_000025.tif'
    g, base = scan_base(dme)
    t = _trace_layers(g)
    figures.append(dict(id='olives_macular_thickening', items=['les_macular_thickening'], source='olives', source_file=dme,
                        mask_label=f'두꺼워진 망막 전체 구간({SERVICE})',
                        caption='당뇨황반부종 눈의 OCT B-scan입니다. 공급자 라벨은 망막 두꺼워짐·황반부종(DRT/ME)과 망막내액입니다. '
                                '망막 안에 어두운 낭 모양 공간이 생기며 전체 두께가 늘었고, 정상 중심와의 오목함이 사라졌습니다. '
                                '표시는 내경계막–브루크막 구간의 자동 추적입니다.',
                        transform=f'원 B-scan 504×496에서 {rows.start}–{rows.stop}행을 잘라 사용; 열별 밝기 경계 자동 추적',
                        **save_pair('olives_macular_thickening', base,
                                    overlay_from_mask(_band(g.shape, t['ilm'], t['bm'])[rows], fill_alpha=70))))

    rpe_scan = 'TREX DME/TREX/0242TOS/V12/OS/TREXO_000019.tif'
    g, base = scan_base(rpe_scan)
    t = _trace_layers(g)
    shadow = np.array([g[int(t['rpe'][x]) + 25:int(t['rpe'][x]) + 120, x].mean() for x in range(g.shape[1])])
    shadow = ndimage.uniform_filter1d(shadow, 9)
    cx = int(np.argmin(shadow[30:-30]) + 30)
    cy = int(t['rpe'][cx]) - rows.start
    ring = Image.new('RGBA', base.size, (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((cx - 22, cy - 18, cx + 22, cy + 18), outline=(*HIGHLIGHT, 255), width=3)
    figures.append(dict(id='olives_rpe_disruption', items=['les_rpe_attenuation_disruption'], source='olives',
                        source_file=rpe_scan, mask_label=f'RPE 단절 위치({SERVICE})',
                        caption='당뇨황반부종 눈의 OCT B-scan입니다. 공급자 라벨에 RPE 단절이 있는 단면이며, 노란 원 자리에서 RPE 띠가 '
                                '끊기고 그 위 고반사 물질 아래로 세로 그림자가 집니다. 단면 단위 라벨이라 원의 위치는 그림자 열을 찾아 '
                                '자동으로 정했습니다.',
                        transform=f'원 B-scan에서 {rows.start}–{rows.stop}행을 잘라 사용; RPE 아래 25–120행 평균이 가장 어두운 열({cx})에 원',
                        **save_pair('olives_rpe_disruption', base, ring)))

    hrf_scan = 'TREX DME/Monthly/0222MOS/V26/OS/TREX_DME_000025.tif'
    g, base = scan_base(hrf_scan)
    t = _trace_layers(g)
    sm = ndimage.gaussian_filter(g, 1.2)
    top_hat = sm - ndimage.grey_opening(sm, size=(9, 9))
    inside = _band(g.shape, t['ilm'] + 8, t['ez'] - 8)
    peaks = (top_hat > np.percentile(top_hat[inside], 99.7)) & inside & (sm == ndimage.maximum_filter(sm, 7))
    labels, n = ndimage.label(ndimage.binary_dilation(peaks, iterations=2))
    centres = ndimage.center_of_mass(peaks, labels, range(1, n + 1))
    dots = Image.new('RGBA', base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(dots)
    for y, x in centres:
        y -= rows.start
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), outline=(*HIGHLIGHT, 255), width=2)
    figures.append(dict(id='olives_hrf', items=['les_hyperreflective_foci'], source='olives', source_file=hrf_scan,
                        mask_label=f'고반사 점 후보 {len(centres)}곳({SERVICE})',
                        caption='당뇨황반부종 치료 중인 눈의 OCT B-scan입니다. 공급자 라벨은 망막내 고반사 점(IR HRF) 하나뿐입니다. '
                                '망막 안의 작고 밝은 점들을 노란 원으로 표시했습니다. 위치는 밝기 기준의 자동 후보라 일부는 혈관 단면 '
                                '등 다른 밝은 점일 수 있습니다.',
                        transform=f'원 B-scan에서 {rows.start}–{rows.stop}행을 잘라 사용; 내경계막+8–타원체대−8 구간의 top-hat 상위 0.3% 국소 최댓값',
                        **save_pair('olives_hrf', base, dots)))
    return figures


def _paper_source(name: str) -> Image.Image:
    path = ARTICLE_FIGURES / 'provider_figures' / name
    if sha256(path) != PAPER_FIGURES[name][1]:
        raise ValueError(f'provider figure changed: {name}')
    return Image.open(path).convert('RGB')


def _paper_panel(name: str, box) -> Image.Image:
    return _paper_source(name).crop(box)


def _ring_layer(img: Image.Image, cx, cy, r, width=4, ry=None) -> Image.Image:
    ry = r if ry is None else ry
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((cx - r, cy - ry, cx + r, cy + ry), outline=(*HIGHLIGHT, 255), width=width)
    return layer


def _enlarge(img: Image.Image, mask: np.ndarray, k=3):
    """Display-only upscale of a small montage panel so the mask edge stays legible."""
    size = (img.width * k, img.height * k)
    return img.resize(size, Image.LANCZOS), np.asarray(Image.fromarray(mask).resize(size)) > 0


def _comp_near(mask: np.ndarray, x, y, r) -> np.ndarray:
    """Largest connected component of `mask` inside the circle (x, y, r)."""
    from skimage import measure
    yy, xx = np.mgrid[:mask.shape[0], :mask.shape[1]]
    labels = measure.label(mask & (np.hypot(xx - x, yy - y) < r))
    return labels == max(measure.regionprops(labels), key=lambda p: p.area).label


def _ring_figure(fig_id, items, name, box, rings, label, caption, method, k=1, context=False) -> dict:
    """Paper panel with author-guided rings (cx, cy, r[, ry]); k>1 enlarges small panels for display."""
    img = _paper_panel(name, box)
    if k > 1:
        img = img.resize((img.width * k, img.height * k), Image.LANCZOS)
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    for ring in rings:
        cx, cy, r = ring[:3]
        ry = ring[3] if len(ring) > 3 else r
        layer = Image.alpha_composite(layer, _ring_layer(img, cx * k, cy * k, r * k, width=3 + k, ry=ry * k))
    return _paper_figure(fig_id, items, name, box, img, layer, label, caption,
                         method + ('' if k == 1 else f'; 표시용 {k}배 확대'), context=context)


def _paper_figure(fig_id, items, name, box, img, overlay, label, caption, method, legend=None, context=False) -> dict:
    """Record for a crop of a CC BY provider figure.

    `context` adds a locator when the crop is part of one photo: True uses the whole provider figure, a box limits the
    locator to the photo panel that holds the crop."""
    ctx = None
    if context:
        frame = (0, 0, *_paper_source(name).size) if context is True else context
        ctx = (_paper_source(name).crop(frame), tuple(v - frame[i % 2] for i, v in enumerate(box)))
    fig = dict(id=fig_id, items=items, source=PAPER_FIGURES[name][0], source_file=f'provider_figures/{name}',
               mask_label=f'{label}({SERVICE})', caption=caption,
               transform=f'패널 {box} 잘라 사용; {method}', **save_pair(fig_id, img, overlay, ctx))
    if legend:
        fig['legend'] = legend
    return fig


def paper_vascular_figures() -> list[dict]:
    """Vascular and exudative findings on CC BY case-report panels with service marks."""
    from scipy import ndimage
    from skimage import morphology

    figures = []
    panel, circle = _paper_panel, _ring_layer

    def add(*args, **kwargs):
        figures.append(_paper_figure(*args, **kwargs))

    name, box = '12886_2019_1035_Fig3_HTML.png', (0, 0, 588, 510)
    img = panel(name, box)
    add('paper_macroaneurysm', ['les_arterial_macroaneurysm'], name, box, img, circle(img, 350, 388, 32),
        '망막 동맥 대동맥류 위치',
        '형광안저혈관조영 초기 사진입니다. 아래쪽 귀쪽 동맥 가지 위에서 둥글게 부풀어 형광이 차오르는 대동맥류(노란 원, 저자 화살표 '
        '자리)가 보입니다.', '저자 화살표가 가리키는 과형광 결절 중심에 원')

    name, box = '12886_2019_1035_Fig2_HTML.png', (0, 0, 486, 410)
    img = panel(name, box)
    a = np.asarray(img, dtype=float)
    lum = a[..., :2].mean(2)
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    star = (np.hypot(xx - 250, yy - 274) < 54) & (lum > ndimage.median_filter(lum, 25) + 9) & (a[..., 1] > 0.5 * a[..., 0])
    star = morphology.remove_small_objects(star, 3)
    add('paper_macular_star', ['les_macular_star'], name, box, img, overlay_from_mask(star, fill_alpha=150, edge_alpha=0),
        '별 모양 삼출물',
        '망막 동맥 대동맥류 눈의 컬러 안저 사진입니다. 중심와를 중심으로 노란 경성삼출물이 바큇살처럼 뻗어 별 모양을 이룹니다. '
        '표시는 주변보다 밝은 노란 점을 자동으로 고른 것입니다.', '중심와 둘레 반지름 54 px 안에서 국소 배경보다 밝은 노란 화소')

    name, box = '12886_2024_3373_Fig1_HTML.png', (0, 562, 732, 1106)
    img = panel(name, box)
    a = np.asarray(img, dtype=float)
    red, green = a[..., 0], a[..., 1]
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    sheath = ((green > 0.6 * red) & (green > 60) & (green > ndimage.median_filter(green, 41) + 15)
              & (yy > 290) & (yy < 500) & (xx > 20) & (xx < 620))
    sheath = morphology.remove_small_objects(sheath, 25)
    hem = (red < 0.72 * ndimage.median_filter(red, 101)) & (yy > 340) & (yy < 530) & (xx > 330)
    hem = morphology.remove_small_objects(ndimage.binary_opening(hem, iterations=2), 150)
    add('paper_vessel_sheathing', ['les_vessel_sheathing'], name, box, img,
        colour_layer([(sheath, (64, 224, 255))], sheath.shape, alpha=200), '혈관을 감싼 흰 피막',
        '서리 낀 나뭇가지 혈관염 눈의 광각 안저 사진입니다. 아래쪽 혈관들이 희고 두꺼운 껍질에 싸여 서리 낀 가지처럼 보입니다. '
        '표시는 주변보다 희고 노르스름한 혈관 띠를 자동으로 고른 것입니다.', '아래쪽 영역에서 녹색 채널이 국소 배경보다 밝은 화소',
        legend=[{'label': '혈관 피막', 'cls': 'vitreous'}])
    add('paper_vasculitis', ['les_retinal_vasculitis_signs'], name, box, img,
        Image.alpha_composite(colour_layer([(sheath, (64, 224, 255))], sheath.shape, alpha=200),
                              overlay_from_mask(hem, fill_alpha=90)),
        '혈관 피막·출혈',
        '같은 눈입니다. 혈관염의 흔적으로 혈관 피막(하늘색)과 막힌 혈관 주변 망막 출혈(노랑)이 함께 보입니다. 출혈 표시는 '
        '주변보다 붉은빛이 크게 줄어든 덩어리를 자동으로 고른 것이라 일부만 잡혔습니다.',
        '혈관 피막은 녹색 채널 국소 대비, 출혈은 빨강 채널이 주변 중앙값의 72% 미만인 덩어리',
        legend=[{'label': '혈관 피막', 'cls': 'vitreous'}, {'label': '출혈', 'cls': 'service'}])

    name, box = '13256_2022_3474_Fig1_HTML.jpg', (825, 0, 1592, 659)
    img = panel(name, box)
    add('paper_telangiectasia', ['les_retinal_telangiectasia'], name, box, img, circle(img, 236, 250, 42),
        '모세혈관확장 위치',
        'Coats병 눈의 형광안저혈관조영 사진입니다. 저자 화살촉이 가리키는 곳 주변에서 가늘게 늘어나 구불거리는 확장 혈관과 그 '
        '위쪽의 넓은 형광 누출이 보입니다.', '저자 화살촉 옆 확장 혈관 부위에 원')

    name, box = '12886_2026_4791_Fig1_HTML.png', (0, 0, 973, 778)
    img = panel(name, box)
    add('paper_disc_edema', ['les_disc_edema'], name, box, img, circle(img, 585, 418, 78),
        '부은 시신경유두',
        '고혈압성 망막병증 소아의 광각 안저 사진(가색)입니다. 유두 경계가 흐려지고 부어 혈관이 유두 가장자리에서 묻혀 보입니다. '
        '양옆의 노란 부종과 황반 별 모양 삼출물이 함께 있습니다. 가색 영상이라 실제 색과 다릅니다.', '혈관이 모이는 유두 중심에 원')
    return figures


def paper_case_figures() -> list[dict]:
    """Fourth batch: CC BY case-report panels (PMC open-access copies) for vascular, tumour, perfusion and scar items."""
    from scipy import ndimage
    from skimage import measure, morphology

    figures = []

    def add(*args, **kwargs):
        figures.append(_paper_figure(*args, **kwargs))

    enlarge, comp_near = _enlarge, _comp_near

    name, box = 'cureus-0018-00000117184-i01.webp', (600, 130, 1100, 620)
    img = _paper_panel(name, box)
    rings = Image.alpha_composite(_ring_layer(img, 207, 147, 26), _ring_layer(img, 250, 375, 26))
    add('paper_av_nicking', ['les_av_nicking'], name, box, img, rings, '동정맥 교차 부위',
        '광각 안저 사진(가색)의 시신경유두 주변입니다. 유두 위·아래 귀쪽에서 동맥이 정맥 위를 지나는 자리(노란 원, 저자 화살촉 '
        '자리)에서 정맥이 눌려 가늘어지고 끊겨 보입니다. 가색 영상이라 실제 색과 다릅니다.',
        '저자 화살촉이 가리키는 두 교차점에 원', context=True)

    name, box = 'cureus-0016-00000075056-i01.jpg', (0, 0, 750, 519)
    img = _paper_panel(name, box)
    a = np.asarray(img, dtype=float)
    red, green = a[..., 0], a[..., 1]
    ratio = ndimage.gaussian_filter(red / (green + 1), 6)
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    grey = (ratio < np.percentile(ratio[red > 40], 12)) & (red > 40) & (np.hypot(xx - 372, yy - 350) > 40)
    labels = measure.label(grey)
    nevus = ndimage.binary_fill_holes(labels == labels[230, 400])
    add('paper_choroidal_nevus', ['les_choroidal_nevus'], name, box, img, overlay_from_mask(nevus, fill_alpha=70),
        '회색 맥락막 병변',
        '시신경유두 위쪽의 편평한 회갈색 맥락막 병변(노랑)입니다. 망막 혈관이 병변 위를 그대로 지나고, 병변 위에 주황 색소(저자 '
        '흰 화살표)가 있습니다. 이 증례는 이후 흑색종으로 바뀌었으므로, 주황 색소는 모반이 커질 위험 신호의 예이기도 합니다.',
        '빨강/녹색 비(가우시안 σ 6)가 하위 12%인 회색 화소 중 저자 화살표 자리 연결 성분, 구멍 채움')

    name, box = 'medi-105-e50535-g001.webp', (220, 872, 432, 1085)
    img = _paper_panel(name, box)
    g = np.asarray(img.convert('L'), dtype=float)
    fov = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.binary_opening(g > 8, iterations=2)), iterations=4)
    smooth = ndimage.gaussian_filter(ndimage.grey_opening(g, size=7), 4)
    dark = morphology.remove_small_objects(fov & (smooth < np.percentile(smooth[fov], 30)), 150)
    img, dark = enlarge(img, ndimage.binary_fill_holes(dark))
    add('paper_nonperfusion', ['les_nonperfusion'], name, box, img, overlay_from_mask(dark, fill_alpha=80),
        '어둡게 비어 보이는 무관류 영역',
        '루푸스 혈관폐쇄 망막병증 눈의 형광안저혈관조영 사진입니다. 유두 주변에는 혈관과 모세혈관 그물이 밝게 차오르지만, '
        '귀쪽·아래쪽(노랑, 저자 별표 자리)은 모세혈관이 차오르지 않아 어둡고 평평하게 비어 보입니다.',
        '굵은 혈관을 지운 뒤(회색 열림 7) 흐린 밝기(σ 4)가 시야 안 하위 30%인 영역; 표시용 3배 확대')

    name, box = 'medi-105-e50535-g001.webp', (1345, 1075, 1600, 1305)
    img = _paper_panel(name, box)
    a = np.asarray(img, dtype=float)
    red, green, blue = a[..., 0], a[..., 1], a[..., 2]
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    fov = ndimage.binary_erosion(red > 60, iterations=6)
    drawn = ndimage.binary_dilation((blue > red - 10) & (blue > 90), iterations=5)  # authors' macula circle
    spots = ((ndimage.white_tophat(green, size=11) > 14) & fov & ~drawn
             & (np.hypot(xx - 50, yy - 140) > 32) & (xx < 210))
    labels = measure.label(morphology.remove_small_objects(spots, 6))
    spots = np.isin(labels, [r.label for r in measure.regionprops(labels) if r.area < 90 and r.eccentricity < 0.9])
    img, spots = enlarge(img, spots)
    add('paper_laser_scar', ['les_laser_scar'], name, box, img, overlay_from_mask(spots, fill_alpha=90),
        '범망막 광응고 반흔',
        '범망막 광응고 치료 뒤의 컬러 안저 사진입니다. 황반(저자 보라 원) 바깥으로 둥근 연노랑 레이저 반흔이 줄지어 '
        '찍혀 있습니다. 표시는 주변보다 밝은 둥근 점을 자동으로 고른 것이라 흐린 반흔 일부는 빠졌습니다.',
        '녹색 채널 백색 톱햇(11)이 14 초과인 둥근 작은 점, 유두·저자 원 제외; 표시용 3배 확대')

    def ring_fig(*args, **kwargs):
        figures.append(_ring_figure(*args, **kwargs))

    name, box = 'cureus-0017-00000099652-i03.jpg', (0, 0, 750, 572)
    img = _paper_panel(name, box)
    a = np.asarray(img, dtype=float)
    blood = ndimage.gaussian_filter(((a[..., 1] > a[..., 0] + 10) & (a[..., 0] < 120)).astype(float), 2) > 0.5
    blood = ndimage.binary_fill_holes(comp_near(ndimage.binary_opening(blood, iterations=3), 310, 255, 140))
    add('paper_subretinal_hemorrhage', ['les_hemorrhage_subretinal'], name, box, img,
        overlay_from_mask(blood, fill_alpha=60), '황반 아래 큰 출혈',
        '유리체강 주사 뒤 생긴 큰 황반하 출혈의 광각 안저 사진(가색)입니다. 위·아래 혈관궁 사이 황반 전체를 덮는 둥근 출혈 '
        '덩어리(노랑)가 보입니다. 이 장비의 가색 영상에서는 피가 짙은 녹색으로 나타나므로 실제 색(검붉은색)과 다릅니다.',
        '녹색이 빨강보다 강하고 빨강이 낮은 화소(가우시안 σ 2), 열림 3회 뒤 황반 주변 최대 성분, 구멍 채움')

    ring_fig('paper_pamm', ['les_paracentral_amn'], 'cureus-0017-00000100159-i01.jpg', (0, 0, 362, 677),
             [(148, 150, 18), (135, 458, 26)], '회백색 병변과 OCT 띠',
             '위는 컬러 안저 사진으로, 중심와 위 귀쪽에 흐린 회백색 병변(노란 원, 저자 화살표 자리)이 있습니다. 아래 OCT 단면에서는 '
             '같은 자리 망막 가운데층(내핵층·내망상층)이 띠 모양으로 하얗게 밝아져 있습니다(노란 원).',
             '저자 화살표가 가리키는 안저 병변과 OCT 고반사 띠에 원')

    name, box = 'cureus-0018-00000104405-i01.jpg', (505, 5, 750, 212)
    img = _paper_panel(name, box)
    g = np.asarray(img.convert('L'), dtype=float)
    yy, xx = np.mgrid[:g.shape[0], :g.shape[1]]
    dots = (ndimage.white_tophat(g, size=13) > 22) & ndimage.binary_erosion(g > 25, iterations=8) & (np.hypot(xx - 127, yy - 75) > 14)
    labels = measure.label(morphology.remove_small_objects(dots, 4))
    dots = np.isin(labels, [r.label for r in measure.regionprops(labels) if r.area < 120])
    img, dots = enlarge(img, dots)
    add('paper_white_dots', ['les_white_dots'], name, box, img, overlay_from_mask(dots, fill_alpha=110),
        '과자가형광 점',
        '다발성 일과성 흰점 증후군(MEWDS) 눈의 광각 자가형광 사진입니다. 후극부와 중간 주변부에 작고 밝은 점(노랑)이 흩어져 '
        '있습니다. 컬러 사진에서는 흐린 흰 점으로 보이는 병변이 자가형광에서 더 뚜렷합니다.',
        '흰색 톱햇(13)이 22 초과인 작은 점, 유두 제외; 표시용 3배 확대')

    name, box = 'cureus-0018-00000107568-i05.jpg', (8, 684, 373, 981)
    img = _paper_panel(name, box)
    a = np.asarray(img, dtype=float)
    lum = a.mean(2)
    spic = ((lum < ndimage.median_filter(lum, 31) - 14) & ndimage.binary_erosion(lum > 30, iterations=3)
            & (a[..., 0] < 1.3 * a[..., 2] + 45))
    img, spic = enlarge(img, morphology.remove_small_objects(spic, 6), 2)
    add('paper_bone_spicule', ['les_bone_spicule_pigment'], name, box, img, overlay_from_mask(spic, fill_alpha=90),
        '골소체 모양 색소',
        '망막색소변성 눈의 컬러 안저 사진입니다. 중간 주변부에 뼈 조각처럼 가지 친 검은 색소 덩어리(노랑)가 흩어져 있고, '
        '유두는 창백하며 혈관이 가늘어져 있습니다.',
        '밝기가 국소 중앙값(31)보다 14 이상 어두운 회흑색 화소; 표시용 2배 확대')

    name, box = 'cureus-0018-00000108935-i01.jpg', (0, 0, 372, 279)
    img = _paper_panel(name, box)
    a = np.asarray(img, dtype=float)
    fov = ndimage.binary_erosion(a[..., 0] > 50, iterations=6)
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    ratio = ndimage.gaussian_filter(a[..., 0] / (a[..., 1] + 1), 1.5)
    flame = (ratio > np.percentile(ratio[fov], 75)) & fov & (np.hypot(xx - 272, yy - 120) > 40)
    img, flame = enlarge(img, morphology.remove_small_objects(ndimage.binary_opening(flame), 30), 2)
    add('paper_flame_hemorrhage', ['les_hemorrhage_flame'], name, box, img, overlay_from_mask(flame, fill_alpha=70),
        '신경섬유층을 따라 퍼진 출혈',
        '중심망막정맥폐쇄 눈의 컬러 안저 사진입니다. 유두에서 바큇살처럼 뻗는 신경섬유 방향을 따라 붓으로 그은 듯한 화염 모양 '
        '출혈(노랑)이 넓게 퍼져 있고, 정맥은 굵고 구불거립니다. 표시는 붉은빛이 가장 강한 영역을 고른 것이라 굵은 정맥 일부가 '
        '섞여 있습니다.', '빨강/녹색 비(σ 1.5)가 시야 안 상위 25%인 영역, 유두 제외; 표시용 2배 확대')

    ring_fig('paper_retinal_break', ['les_retinal_break'], 'cureus-0018-00000109005-i04.jpg', (0, 0, 750, 778),
             [(335, 385, 70)], '말굽 모양 열공',
             '세극등 검사 렌즈로 본 주변부 망막입니다. 6시 방향에 끝이 날카로운 말굽 모양 열공(노란 원, 저자 화살표 자리)이 '
             '있고, 그 아래로 붉은 맥락막 바탕이 비쳐 보입니다.', '저자 화살표가 가리키는 열공에 원')

    name, box = 'RomJOphthalmol-65-275-g001.jpg', (305, 0, 602, 247)
    img = _paper_panel(name, box)
    a = np.asarray(img, dtype=float)
    lum = a.mean(2)
    dark = ndimage.binary_opening(ndimage.gaussian_filter(lum, 1.5) < 0.8 * np.median(lum[lum > 30]))
    img, chrpe = enlarge(img, ndimage.binary_fill_holes(comp_near(dark, 117, 92, 45)), 2)
    add('paper_chrpe', ['les_chrpe'], name, box, img, overlay_from_mask(chrpe, fill_alpha=60),
        '경계가 분명한 검은 색소 병변',
        '귀쪽 주변부의 둥글고 경계가 분명한 편평한 검은 병변(노랑)입니다. 가장자리에 옅은 테가 있고 위로 지나는 혈관은 '
        '변하지 않습니다. 선천 망막색소상피 비대의 전형적인 모습입니다.',
        '밝기(σ 1.5)가 중앙값의 80% 미만인 화소 중 저자 병변 자리 최대 성분, 구멍 채움; 표시용 2배 확대')

    name, box = 'cureus-0014-00000030859-i03.jpg', (20, 10, 735, 560)
    img = _paper_panel(name, box)
    g = np.asarray(img, dtype=float)[..., 1]
    yy, xx = np.mgrid[:g.shape[0], :g.shape[1]]
    fl = ((ndimage.white_tophat(g, size=9) > 9) & (np.hypot(xx - 300, yy - 215) < 190)
          & (np.hypot(xx - 525, yy - 265) > 75) & (g > 60))
    labels = measure.label(morphology.remove_small_objects(fl, 3))
    fl = np.isin(labels, [r.label for r in measure.regionprops(labels) if r.area < 80])
    add('paper_flecks', ['les_flecks'], name, box, img, overlay_from_mask(fl, fill_alpha=150, edge_alpha=0),
        '황백색 반점',
        '스타가르트병 눈의 컬러 안저 사진입니다. 위축된 황반 둘레에 물고기 꼬리 모양의 작은 황백색 반점(노랑, 저자 화살표 '
        '자리)이 흩어져 있습니다. 표시는 주변보다 밝은 작은 점을 자동으로 고른 것입니다.',
        '녹색 채널 흰색 톱햇(9)이 9 초과인 작은 점, 황반 주변 반지름 190 px, 유두 제외')

    name, box = 'cureus-0014-00000030859-i03.jpg', (18, 578, 737, 1120)
    img = _paper_panel(name, box)
    lum = np.asarray(img.convert('L'), dtype=float)
    hypo = ndimage.binary_opening(ndimage.gaussian_filter(lum, 2) < 0.45 * np.median(lum[lum > 60]), iterations=2)
    hypo = comp_near(hypo, 392, 229, 120)
    add('paper_bulls_eye', ['les_bulls_eye_maculopathy'], name, box, img, overlay_from_mask(hypo, fill_alpha=70),
        '어두운 고리와 가운데 남은 부분',
        '스타가르트병 눈의 자가형광 사진입니다. 황반에 타원형으로 어두운(저자가형광) 위축 고리(노랑)가 있고, 그 가운데에 덜 어두운 '
        '부분이 남아 과녁처럼 보입니다. 저자들은 이를 과녁 모양 황반병증으로 기술했습니다.',
        '밝기(σ 2)가 중앙값의 45% 미만인 황반 성분(구멍은 채우지 않아 가운데 남은 부분이 드러남)')

    ring_fig('paper_polypoidal', ['les_polypoidal_lesion'], 'cureus-0015-00000047942-i02.jpg', (190, 183, 375, 365),
             [(132, 113, 10)], '결절 모양 과형광',
             '인도시아닌그린 혈관조영 사진입니다. 어두운 병변 안에 둥글게 빛나는 결절(노란 원, 저자 화살표 자리)이 있어 '
             '결절성 맥락막혈관병증의 폴립으로 보입니다.', '저자 화살표 위 과형광 결절에 원', k=3)

    ring_fig('paper_sharp_ped', ['les_sharp_peaked_ped'], 'cureus-0015-00000047942-i03.jpg', (522, 0, 750, 138),
             [(153, 46, 28)], '뾰족하게 솟은 색소상피박리',
             '결절성 맥락막혈관병증 눈의 OCT 단면입니다. 망막색소상피가 꼭대기가 뾰족한 둥근 지붕처럼 솟아(노란 원, 저자 화살촉 자리) 그 안에 '
             '폴립의 내강이 비칩니다. 왼쪽 망막 안에는 밝은 경성삼출물 점들이 있습니다.', '저자 화살촉 아래 솟은 RPE 꼭대기에 원', k=3)

    name, box = 'cureus-0016-00000068214-i01.jpg', (110, 80, 260, 210)
    img = _paper_panel(name, box)
    a = np.asarray(img, dtype=float)
    lum = a[..., :2].mean(2)
    yy, xx = np.mgrid[:lum.shape[0], :lum.shape[1]]
    vit = (lum > ndimage.median_filter(lum, 41) + 8) & (np.hypot(xx - 75, yy - 65) < 16)
    vit = ndimage.binary_fill_holes(ndimage.binary_closing(comp_near(vit, 75, 65, 16), iterations=2))
    img, vit = enlarge(img, vit)
    add('paper_vitelliform', ['les_vitelliform_lesion'], name, box, img, overlay_from_mask(vit, fill_alpha=50),
        '중심와의 노란 난황 모양 병변',
        '성인형 난황모양 황반이영양증 눈의 중심와를 확대한 컬러 안저 사진입니다. 중심와에 작고 둥근 노란 병변(노랑)이 '
        '달걀노른자처럼 자리합니다.', '중심와 반지름 16 px 안에서 국소 중앙값보다 밝은 노란 화소; 표시용 3배 확대', context=(0, 0, 375, 313))
    return figures


def paper_fill_figures() -> list[dict]:
    """Fifth batch: CC BY figures for the remaining structure, layer and lesion items (PMC open-access copies)."""
    from scipy import ndimage
    from skimage import morphology

    figures = []

    def add(*args, **kwargs):
        figures.append(_paper_figure(*args, **kwargs))

    def ring_fig(*args, **kwargs):
        figures.append(_ring_figure(*args, **kwargs))

    def tophat_spots(g, size, thr, keep, max_area, min_area=3):
        from skimage import measure
        spots = morphology.remove_small_objects((ndimage.white_tophat(g, size=size) > thr) & keep, min_area)
        labels = measure.label(spots)
        return np.isin(labels, [r.label for r in measure.regionprops(labels) if r.area < max_area])

    # --- optic disc and vessels
    name, box = '13256_2022_3690_Fig1_HTML.jpg', (395, 0, 784, 385)
    img = _paper_panel(name, box)
    a = np.asarray(img, dtype=float)
    blood = (a[..., 0] > 2.4 * a[..., 1]) & (a[..., 0] > 60)
    blood = ndimage.binary_fill_holes(_comp_near(ndimage.binary_closing(ndimage.binary_opening(blood), iterations=3), 200, 140, 110))
    add('paper_disc_hemorrhage', ['les_disc_hemorrhage'], name, box, img, overlay_from_mask(blood, fill_alpha=60),
        '유두와 그 둘레의 출혈',
        '백신 접종 뒤 생긴 시신경유두 출혈의 컬러 안저 사진입니다. 유두 위와 둘레를 덮는 짙은 붉은 출혈(노랑)이 유두 경계를 '
        '가립니다. 녹내장에서 흔한 유두 가장자리의 작은 선 모양 출혈보다 범위가 넓은 예입니다.',
        '빨강이 녹색의 2.4배를 넘는 화소, 열림·닫힘 뒤 유두 주변 최대 성분, 구멍 채움')

    ring_fig('paper_venous_dilation', ['les_venous_dilation_tortuosity'], '13256_2023_4100_Fig1_HTML.jpg', (275, 0, 515, 245),
             [(345 - 275, 152, 18), (335 - 275, 55, 18)], '굵고 구불거리는 정맥',
             '중심망막정맥폐쇄 눈의 컬러 안저 사진입니다. 유두에서 나오는 정맥이 굵게 부풀고 구불거리며(노란 원), 그 둘레와 '
             '황반 위로 망막내 출혈이 흩어져 있습니다(저자 설명: 충혈되고 구불거리는 정맥).', '유두 위·아래의 굵고 구불거리는 정맥 가지에 원', k=2)

    ring_fig('paper_arteriolar_narrowing', ['les_arteriolar_narrowing'], 'medi-105-e48683-g001.jpg', (0, 0, 397, 300),
             [(265, 160, 16), (275, 72, 16)], '가는 동맥과 굵은 정맥',
             '반복된 중심망막동맥폐쇄 뒤의 컬러 안저 사진입니다. 혈류는 돌아왔지만 밝은 붉은색 동맥이 옆의 검붉은 정맥보다 '
             '눈에 띄게 가늘어져 있습니다(노란 원 안에서 두 혈관의 굵기를 비교, 저자 설명: 동맥이 좁아짐).',
             '유두 위·아래 귀쪽에서 동맥과 정맥이 나란히 지나는 자리에 원', k=2)

    # --- choroid and RPE
    ring_fig('paper_angioid_streaks', ['les_angioid_streaks'], 'cureus-0015-00000045983-i01.jpg', (0, 0, 375, 280),
             [(222, 80, 14), (228, 165, 14), (286, 186, 14)], '유두에서 뻗는 적갈색 선',
             '탄력섬유가성황색종 환자의 컬러 안저 사진입니다. 시신경유두 둘레에서 바깥으로 뻗는 불규칙한 적갈색 선(노란 원, '
             '저자 화살표 자리)이 혈관양선조입니다. 망막 혈관보다 깊고 폭이 고르지 않습니다.', '저자 화살표 끝의 선조 위치에 원', k=2)

    ring_fig('paper_choroidal_hyperpermeability', ['les_choroidal_hyperpermeability'], 'diagnostics-12-01368-g002.jpg',
             (555, 0, 728, 185), [(75, 82, 26)], '후기 ICGA의 밝은 맥락막 구역',
             '인도시아닌그린 혈관조영 후기 사진입니다. 황반 둘레에 경계가 흐린 밝은 구역(노란 원)이 남아 있는데, 저자들은 이를 '
             '형광안저혈관조영의 누출 자리와 같은 국소 맥락막 과투과로 기술했습니다.', '저자 설명의 과형광 구역에 원', k=3)

    name, box = 'cureus-0018-00000115772-i03.webp', (0, 0, 810, 494)
    img = _paper_panel(name, box)
    g = ndimage.gaussian_filter(np.asarray(img.convert('L'), dtype=float), 1.5)
    rpe = ndimage.median_filter(160 + np.argmax(g[160:215], axis=0), 21)
    band = np.zeros(g.shape, bool)
    for x in range(250, 560):
        band[rpe[x] + 8:rpe[x] + 108, x] = True
    add('paper_pachychoroid', ['les_pachychoroid_features'], name, box, img, overlay_from_mask(band, fill_alpha=55),
        '두꺼워진 맥락막',
        '만성 중심장액맥락망막병증 눈의 OCT 단면입니다. 망막하액 아래 RPE 밑의 맥락막(노랑)이 두껍고, 큰 맥락막 혈관이 '
        '어둡게 넓어져 있습니다(저자 노란 양방향 화살표 자리). RPE는 울퉁불퉁하고 드루젠이 동반되어 있습니다.',
        '열마다 깊이 160–215 px에서 가장 밝은 행을 RPE로(중앙값 21), 그 아래 8–108 px 띠, 저자 화살표 둘레 x 250–560')

    ring_fig('paper_rpe_hypopigmentation', ['les_rpe_hypopigmentation'], 'pone.0266968.g002.jpg', (115, 725, 265, 895),
             [(75, 75, 62, 72)], '색소가 옅어 맥락막 혈관이 비침',
             '눈피부 백색증 환자의 안저 사진입니다. 망막색소상피의 색소가 전반적으로 옅어서 그 아래 큰 맥락막 혈관이 주황색 '
             '줄무늬로 그대로 비쳐 보입니다(노란 테 안).', '안저 사진 후극부에 타원', k=3)

    ring_fig('paper_irora', ['les_atrophy_incomplete'], 'iovs-67-8-46-f001.jpg', (120, 48, 364, 168),
             [(123, 64, 26, 34)], 'RPE·외망막 불완전 위축 자리',
             'OCT 단면에서 RPE가 부분적으로 끊기고 그 아래로 빛이 비쳐 내려가며(과투과), 위쪽 외망막 층이 얇아진 좁은 '
             '구역입니다(노란 테, 저자 표시 자리). 폭이 250 µm 미만이라 불완전 위축(iRORA)으로 분류됩니다.',
             '저자 노란 타원 자리에 더 큰 타원', k=3)

    name, box = 'cureus-0018-00000110402-i03.jpg', (505, 10, 720, 380)
    ring_fig('paper_chorioretinal_scar', ['les_chorioretinal_scar'], name, box, [(185, 75, 40), (180, 260, 42)],
             '경계가 분명한 맥락망막 흉터',
             '눈 톡소포자충 망막맥락막염이 아문 6개월 뒤 영상입니다. 위는 광각 가색 사진으로 경계가 뚜렷하고 가장자리에 색소가 '
             '모인 흉터(노란 원), 아래는 같은 자리의 자가형광으로 어두운 테와 밝은 가운데가 보입니다.',
             '저자 화살표가 가리키는 병변에 원', k=2)

    # --- deposits and neovascular
    name, box = 'medi-101-e32032-g001.jpg', (0, 915, 400, 1165)
    img = _paper_panel(name, box)
    g = np.asarray(img.convert('L'), dtype=float)
    yy, xx = np.mgrid[:g.shape[0], :g.shape[1]]
    vessels = ndimage.binary_dilation(ndimage.white_tophat(ndimage.gaussian_filter(g, 1), size=15) > 45, iterations=1) & \
        (ndimage.uniform_filter((ndimage.white_tophat(g, size=15) > 40).astype(float), 9) > 0.3)
    spots = tophat_spots(g, 5, 18, ~vessels, 12, 2)
    img, spots = _enlarge(img, spots, 2)
    add('paper_cuticular_drusen', ['les_drusen_cuticular'], name, box, img, overlay_from_mask(spots, fill_alpha=160, edge_alpha=0),
        '밤하늘 별 같은 과형광 점',
        '소용돌이형(cuticular) 드루젠 눈의 형광안저혈관조영 중기 사진입니다. 황반 둘레에 아주 작고 고른 과형광 점이 무수히 '
        '흩어져 "밤하늘의 별" 모양을 이룹니다(노랑). 표시는 혈관을 뺀 작은 밝은 점을 자동으로 고른 것입니다.',
        '흰색 톱햇(5) > 18인 2–12 화소 점, 굵은 혈관 근처 제외; 표시용 2배 확대')

    name, box = 'cureus-0017-00000093258-i01.jpg', (0, 595, 375, 985)
    img = _paper_panel(name, box)
    a = np.asarray(img, dtype=float)
    green_line = ndimage.binary_dilation(a[..., 1] > a[..., 0] + 25, iterations=2)
    g = a[..., 0]
    yy, xx = np.mgrid[:g.shape[0], :g.shape[1]]
    sdd = tophat_spots(g, 9, 22, ~green_line & (np.hypot(xx - 200, yy - 185) < 150), 60, 3)
    add('paper_sdd', ['les_subretinal_drusenoid_deposit'], name, box, img, overlay_from_mask(sdd, fill_alpha=140, edge_alpha=0),
        '그물 모양 밝은 점',
        '근적외선 반사 영상입니다. 황반 둘레에 작은 밝은 점과 고리가 그물처럼 이어진 망막하 드루젠양 침착물(가성드루젠, '
        '노랑)이 넓게 퍼져 있습니다. 표시는 저자 측정선(녹색)을 뺀 작은 밝은 점을 자동으로 고른 것입니다.',
        '흰색 톱햇(9) > 22인 3–60 화소 점, 녹색 측정선 제외, 황반 반지름 150 px')

    ring_fig('paper_mnv', ['les_macular_neovascularization'], 'medi-105-e47893-g004.jpg', (0, 0, 400, 310),
             [(162, 168, 22)], '중심와 출혈을 동반한 신생혈관 자리',
             '점상 내맥락막병증 뒤 생긴 맥락막 신생혈관(황반 신생혈관) 눈의 광각 가색 사진입니다. 중심와에 신생혈관에서 나온 '
             '출혈(노란 원, 저자 화살표 자리)이 있고, 유두 둘레에는 노란 점상 병변이 모여 있습니다. 가색이라 실제 색과 다릅니다.',
             '저자 화살표 끝의 중심와 병변에 원', k=2)

    name, box = 'medi-103-e38150-g004.jpg', (0, 0, 372, 300)
    img = _paper_panel(name, box)
    a = np.asarray(img, dtype=float)
    lum = ndimage.gaussian_filter(a[..., :2].mean(2), 1)
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    folds = ((ndimage.white_tophat(lum, size=9) > 9) & (np.hypot(xx - 210, yy - 150) < 125)
             & (a[..., 2] < 0.75 * a[..., 1]))
    folds = morphology.remove_small_objects(folds, 15)
    img, folds = _enlarge(img, folds, 2)
    add('paper_pvr', ['les_pvr'], name, box, img, overlay_from_mask(folds, fill_alpha=150, edge_alpha=0),
        '유두로 모이는 별 모양 망막 주름',
        '급성 망막괴사 뒤 증식유리체망막병증으로 망막 전체가 박리된 눈의 광각 가색 사진입니다. 망막 앞면의 증식막이 수축해 '
        '시신경유두 쪽으로 모이는 별 모양 고정 주름(노랑)이 생겼습니다. 가색 영상입니다.',
        '밝기 흰색 톱햇(9) > 9인 선, 유두 반지름 125 px 안; 표시용 2배 확대')

    ring_fig('paper_pseudohole', ['les_macular_pseudohole'], '12886_2018_755_Fig3_HTML.jpg', (189, 195, 567, 369),
             [(191, 67, 24)], '가파른 벽의 가성원공',
             'OCT 단면입니다. 망막앞막이 중심와 둘레를 당겨 중심와 벽이 가파르게 솟고 좁은 오목이 생겼지만, 망막 조직은 '
             '빠지지 않았습니다(노란 원). 겉으로는 원공처럼 보이는 황반 가성원공입니다.', '중심와 오목에 원', k=2)

    # --- OCT layers on an author-labelled B-scan (Bringmann 2022, Fig 2C flat panel, Fig 2A labels at the right edge)
    name, box = 'pone.0266968.g002.jpg', (30, 598, 328, 718)
    img = _paper_panel(name, box)
    k = 3
    for fig_id, item, rows, label, text in (
            ('plos_gcipl', 'ana_gcipl', (13, 36), '신경절세포층 + 내망상층',
             '저자가 층 이름을 붙인 OCT 단면입니다. 밝은 신경섬유층 바로 아래의 회색 신경절세포층과 그 아래 내망상층을 합친 '
             '띠(노랑)가 신경절세포·내망상층 복합(GCIPL)입니다.'),
            ('plos_hfl', 'ana_hfl', (52, 62), '헨레섬유층',
             '저자가 층 이름을 붙인 OCT 단면입니다. 외망상층 바로 아래, 어두운 외핵층 위쪽의 얇은 띠(노랑)가 저자가 헨레섬유층으로 표지한 '
             '자리입니다. 헨레섬유는 비스듬히 달려서 보통 OCT에서는 외핵층과 잘 구분되지 않습니다.')):
        band = np.zeros((img.height * k, img.width * k), bool)
        band[rows[0] * k:rows[1] * k, :] = True
        big = img.resize((img.width * k, img.height * k), Image.LANCZOS)
        add(fig_id, [item], name, box, big, overlay_from_mask(band, fill_alpha=70), label, text,
            f'저자 층 이름표의 지시선 높이에 맞춘 수평 띠(패널 행 {rows[0]}–{rows[1]}); 표시용 3배 확대')

    name, box = 'pone.0266968.g002.jpg', (37, 140, 328, 300)
    img = _paper_panel(name, box)
    g = ndimage.gaussian_filter(np.asarray(img.convert('L'), dtype=float), 1)
    ez = np.zeros(img.width, int)
    x0 = 320 - box[0]
    ez[x0] = 275 - box[1]  # upper of the two bright outer bands (EZ; RPE lies ~14 px below) at x = 320
    for x in list(range(x0 - 1, -1, -1)) + list(range(x0 + 1, img.width)):
        prev = ez[x + 1] if x < x0 else ez[x - 1]
        ez[x] = prev - 1 + int(np.argmax(g[prev - 1:prev + 2, x]))
    ez = np.round(ndimage.uniform_filter1d(ez.astype(float), 15)).astype(int)
    k = 3
    big = img.resize((img.width * k, img.height * k), Image.LANCZOS)
    for fig_id, item, (d0, d1), label, text in (
            ('plos_myoid', 'ana_myoid_zone', (-7, -2), '근양대',
             '저자가 층 이름을 붙인 OCT 단면입니다. 외경계막(ELM)과 타원체대(EZ) 사이의 얇고 조금 어두운 띠(노랑)가 '
             '광수용체 내절의 근양대입니다.'),
            ('plos_photoreceptor_os', 'ana_photoreceptor_os', (3, 8), '광수용체 외절',
             '저자가 층 이름을 붙인 OCT 단면입니다. 밝은 타원체대(EZ) 아래부터 맞물림대(IZ) 위까지의 띠(노랑)가 광수용체 외절입니다.'),
            ('plos_iz', 'ana_interdigitation_zone', (8, 11), '맞물림대',
             '저자가 층 이름을 붙인 OCT 단면입니다. 타원체대와 RPE 사이의 가는 밝은 선(노랑)이 RPE 돌기와 원뿔세포 외절 끝이 맞물리는 '
             '맞물림대(IZ)입니다.')):
        band = np.zeros((img.height, img.width), bool)
        for x in range(img.width):
            band[ez[x] + d0:ez[x] + d1, x] = True
        band = np.asarray(Image.fromarray(band).resize(big.size)) > 0
        add(fig_id, [item], name, box, big, overlay_from_mask(band, fill_alpha=90), label, text,
            f'바깥쪽 두 밝은 띠 중 위쪽(EZ)을 x 320에서 시작해 열마다 ±1 px로 따라간 뒤, EZ 기준 {d0}–{d1} px 띠 '
            '(ELM은 EZ 약 8 px 위, RPE는 약 14 px 아래); 자동 추적이라 1–2 px 오차가 있을 수 있음; 표시용 3배 확대')

    ring_fig('paper_elm_disruption', ['les_elm_disruption'], 'fmed-08-706084-g0001.jpg', (350, 50, 705, 400),
             [(167, 140, 36, 18)], 'ELM 끊긴 자리',
             '당뇨황반부종 눈의 OCT 단면입니다. 왼쪽에서는 가는 밝은 외경계막(ELM)과 그 아래 IS/OS 선이 이어지다가, '
             '중심와 쪽에서 끊겨 있습니다(노란 테, 저자 녹색 (a) 구간).', '저자 (a) 구간에 타원', k=2)

    # --- disc OCT: BMO and lamina cribrosa (Oyur 2026, Fig 1C)
    name, box = '12886_2026_5473_Fig1_HTML.webp', (560, 600, 1180, 1150)
    ring_fig('paper_bmo', ['ana_bmo'], name, box, [(731 - 560, 780 - 600, 18), (998 - 560, 780 - 600, 18)],
             '브루크막 개구부 양끝',
             '시신경유두를 지나는 OCT 단면입니다. 브루크막이 유두 가장자리에서 끝나는 두 점(노란 원, 저자 녹색 BMO 선의 '
             '양끝)이 브루크막 개구부입니다. 두 점을 이은 선이 유두 함몰과 사상판 깊이를 재는 기준선입니다.',
             '저자 BMO 기준선의 양 끝점에 원')
    ring_fig('paper_lamina_cribrosa', ['ana_lamina_cribrosa'], name, box, [(880 - 560, 990 - 600, 105, 95)],
             '사상판', '시신경유두를 지나는 OCT 단면입니다. 유두 함몰 바닥 아래의 밝고 성긴 반사 조직(노란 테)이 시신경섬유가 눈 밖으로 나가는 '
             '체 모양의 사상판입니다(저자 LCD·LCCW 측정 자리).', '저자 사상판 측정선 둘레에 타원')

    # --- vortex vein ampulla (Regenold 2026, Fig 1 top)
    ring_fig('paper_vortex_vein', ['ana_vortex_vein'], 'jcm-15-03614-g001.jpg', (0, 0, 784, 520),
             [(670, 300, 70)], '와정맥 팽대부',
             '적도부 근처를 확대한 안저 사진입니다. 망막 아래로 비치는 맥락막 정맥들이 한곳으로 모여 주머니처럼 부푼 자리(노란 '
             '원)가 와정맥 팽대부입니다. 이 증례에서는 팽대부가 정맥류처럼 커져 있습니다.', '맥락막 정맥이 모이는 팽대부에 원')

    # --- OCTA FAZ enlargement (Hoshiyama 2022, Fig 2A)
    name, box = 'medicina-58-01797-g002.jpg', (12, 42, 248, 278)
    img = _paper_panel(name, box)
    g = np.asarray(img.convert('L'), dtype=float)
    density = ndimage.gaussian_filter((g > 110).astype(float), 5)
    faz = ndimage.binary_fill_holes(_comp_near(density < 0.08, 113, 123, 70))
    img, faz = _enlarge(img, faz, 3)
    add('paper_faz_enlargement', ['les_faz_enlargement'], name, box, img, overlay_from_mask(faz, fill_alpha=70),
        '넓어진 중심와 무혈관 구역',
        '당뇨황반허혈 눈의 OCTA 표층 사진입니다. 가운데 혈관이 없는 어두운 구역(노랑)이 넓고 경계가 울퉁불퉁합니다. '
        '저자 측정값은 0.558 mm²로, 정상(대개 0.2–0.4 mm²)보다 큽니다.',
        '혈관 화소(밝기 > 110) 비율(σ 5)이 0.08 미만인 중앙 성분, 구멍 채움; 표시용 3배 확대')
    return figures


def chaksu_figures() -> list[dict]:
    """Optic cup and neuroretinal rim from Chákṣu STAPLE consensus masks (5 experts, CC BY 4.0)."""
    from PIL import ImageOps
    stem = 'IMG_4198'
    img = ImageOps.exif_transpose(Image.open(CHAKSU / '1.0_Original_Fundus_Images/Remidio' / f'{stem}.JPG')).convert('RGB')
    disc = np.asarray(Image.open(CHAKSU / '5.0_OD_OC_Mean_Median_Majority_STAPLE/Remidio/Disc/STAPLE' / f'{stem}.png').convert('L')) > 127
    cup = np.asarray(Image.open(CHAKSU / '5.0_OD_OC_Mean_Median_Majority_STAPLE/Remidio/Cup/STAPLE' / f'{stem}.png').convert('L')) > 127
    ys, xs = np.where(disc)
    cy, cx, r = int(ys.mean()), int(xs.mean()), int(1.6 * max(np.ptp(ys), np.ptp(xs)))
    box = (cx - r, cy - r, cx + r, cy + r)
    crop = img.crop(box)
    sub = lambda m: m[box[1]:box[3], box[0]:box[2]]
    figures = []
    for fig_id, item, mask, label, caption in (
            ('chaksu_optic_cup', 'ana_optic_cup', sub(cup), '유두 함몰(컵)',
             '정상 눈의 시신경유두입니다. 유두 가운데 혈관이 꺾여 들어가는 하얗게 오목한 부분(노랑)이 유두 함몰(컵)입니다. '
             '테두리는 안과 전문의 5명의 컵 경계를 통계적으로 합친 합의 경계입니다.'),
            ('chaksu_neuroretinal_rim', 'ana_neuroretinal_rim', sub(disc & ~cup), '신경망막 테',
             '정상 눈의 시신경유두입니다. 유두 경계와 컵 경계 사이의 분홍빛 고리(노랑)가 신경섬유가 모여 지나는 신경망막 테입니다. '
             '정상에서는 아래·위·코·귀 순서로 두껍습니다(ISNT).')):
        figures.append(dict(id=fig_id, items=[item], source='chaksu', source_file=f'Test/1.0_Original_Fundus_Images/Remidio/{stem}.JPG',
                            mask_label=f'{label}(전문가 5명 합의 경계)', caption=caption,
                            transform=f'유두 중심 둘레 {box} 잘라 사용; STAPLE 합의 mask(Disc·Cup) 사용',
                            **save_pair(fig_id, crop, overlay_from_mask(mask, fill_alpha=70), (img, box))))
    return figures


def refined_rule_figures() -> list[dict]:
    """Refined IDRiD expert masks read through clinical location rules: NVD/NVE split, CSME zone, circinate ring."""
    from scipy import ndimage
    from skimage import measure

    def load(image_id):
        label_map = np.array(Image.open(REFINED / f'Labels/{image_id}_vessel.png'))
        suffix = 'png' if (REFINED / f'Images/{image_id}.png').exists() else 'jpg'
        return label_map, Image.open(REFINED / f'Images/{image_id}.{suffix}').convert('RGB'), f'Train/Images/{image_id}.{suffix}'

    def record(fig_id, item, source_file, image, overlay, label, caption, transform, context=None, legend=None):
        fig = dict(id=fig_id, items=[item], source='refined_idrid', source_file=source_file, mask_label=label,
                   caption=caption, transform=transform, **save_pair(fig_id, image, overlay, context=context))
        if legend:
            fig['legend'] = legend
        return fig

    figures = []
    label_map, image, src = load('IDRiD_27')
    disc = label_map == 32
    nv = ndimage.binary_closing(label_map == 166, iterations=2) | (label_map == 166)
    ys, xs = np.where(disc)
    dd = max(np.ptp(ys), np.ptp(xs))
    dist = ndimage.distance_transform_edt(~disc) / dd
    labels = measure.label(nv)
    near = np.zeros_like(nv)
    for r in measure.regionprops(labels):
        if dist[labels == r.label].min() <= 1.0:
            near |= labels == r.label
    far = nv & ~near
    ring = ndimage.binary_dilation(dist <= 1.0, iterations=2) & ~(dist <= 1.0)
    for fig_id, item, mask, label, note in (
            ('fundus_nvd', 'les_nv_disc', near, '유두 신생혈관(NVD)',
             '유두 위 또는 유두 경계에서 1 유두지름 안쪽(하늘색 선 안)에 있는 신생혈관만 남긴 것입니다.'),
            ('fundus_nve', 'les_nv_elsewhere', far, '망막 신생혈관(NVE)',
             '유두 경계에서 1 유두지름보다 멀리(하늘색 선 밖) 있는 신생혈관만 남긴 것입니다.')):
        x0, y0, x1, y1 = crop_box(mask, (640, 480))
        overlay = Image.alpha_composite(overlay_from_mask(mask), colour_layer([(ring, (125, 211, 252))], ring.shape, alpha=230))
        figures.append(record(fig_id, item, src, image.crop((x0, y0, x1, y1)), overlay.crop((x0, y0, x1, y1)),
                              f'{label}(공급자 전문가 NV mask, 위치 규칙으로 나눔)',
                              f'증식 당뇨망막병증 눈의 컬러 안저 사진입니다. 공급자 전문가 신생혈관 mask 중 {note} '
                              '노란 부분이 가늘고 엉킨 새 혈관입니다.',
                              f'통합 mask NV(166)의 연결 성분을 유두 mask(32) 경계와의 최소 거리로 나눔(1 유두지름 = {dd} px 기준); '
                              f'({x0},{y0})–({x1},{y1}) 확대', context=(image, (x0, y0, x1, y1)),
                              legend=[{'label': '유두 경계 + 1 유두지름', 'cls': 'vitreous'}]))

    label_map, image, src = load('IDRiD_09')
    fy, fx = [v.mean() for v in np.where(label_map == 16)]
    dy, dx = [v.mean() for v in np.where(label_map == 32)]
    df = float(np.hypot(fx - dx, fy - dy))
    r500 = df * 0.5 / 4.5
    yy, xx = np.mgrid[:label_map.shape[0], :label_map.shape[1]]
    zone = np.hypot(xx - fx, yy - fy) <= r500
    ex = label_map == 63
    circle = ndimage.binary_dilation(zone, iterations=2) & ~zone
    overlay = Image.alpha_composite(overlay_from_mask(ex & zone, fill_alpha=200),
                                    Image.alpha_composite(overlay_from_mask(ex & ~zone, color=(255, 255, 255), fill_alpha=0, edge_alpha=150),
                                                          colour_layer([(circle, (125, 211, 252))], circle.shape, alpha=240)))
    s = int(df * 1.1)
    box = (int(fx) - s, int(fy) - s, int(fx) + s, int(fy) + s)
    figures.append(record('fundus_csme_zone', 'les_csme', src, image.crop(box), overlay.crop(box),
                          '중심와 500 µm 안 경성삼출물(공급자 EX mask)',
                          '당뇨망막병증 눈의 황반입니다. 하늘색 원은 중심와 중심에서 500 µm, 노랑은 그 안에 들어온 경성삼출물(흰 테는 원 '
                          '밖)입니다. 중심와 500 µm 안의 경성삼출물에 인접한 망막 두꺼워짐이 있으면 임상적으로 유의한 황반부종(CSME)입니다. '
                          '두꺼워짐은 사진만으로 확인할 수 없으므로 이 그림은 판정 구역과 삼출물 위치만 보여줍니다.',
                          f'통합 mask 중심와(16)·유두(32) 중심 거리 {df:.0f} px를 4.5 mm로 보고 500 µm = {r500:.0f} px; EX(63) 사용',
                          context=(image, box), legend=[{'label': '중심와 500 µm', 'cls': 'vitreous'}]))

    label_map, image, src = load('IDRiD_32')
    ex = label_map == 63
    from skimage import morphology
    closed = morphology.binary_closing(ex, morphology.disk(12))
    hole = ndimage.binary_fill_holes(closed) & ~closed
    labels = measure.label(hole)
    centre = max(measure.regionprops(labels), key=lambda p: p.area).centroid
    yy, xx = np.mgrid[:ex.shape[0], :ex.shape[1]]
    ringex = ex & (np.hypot(xx - centre[1], yy - centre[0]) < 150)
    x0, y0, x1, y1 = crop_box(ringex, (480, 360))
    figures.append(record('fundus_circinate', 'les_circinate_exudate', src, image.crop((x0, y0, x1, y1)),
                          overlay_from_mask(ringex, fill_alpha=150).crop((x0, y0, x1, y1)),
                          '고리 모양 경성삼출물(공급자 EX mask)',
                          '당뇨망막병증 눈에서 황반 귀쪽의 경성삼출물(노랑)이 가운데 빈 곳을 둘러 고리를 이룹니다. 고리 가운데의 새는 '
                          '미세혈관(미세동맥류)에서 나온 지질이 둘레에 쌓인 환상 삼출물입니다.',
                          f'EX(63)를 반지름 12 원판으로 닫았을 때 생기는 가장 큰 빈 곳의 중심 150 px 안 EX; ({x0},{y0})–({x1},{y1}) 확대',
                          context=(image, (x0, y0, x1, y1))))
    return figures


def uwf_zone_figures() -> list[dict]:
    import zipfile
    """Posterior pole / mid / far periphery and the ETDRS 7 standard fields drawn on a normal UWF-DR image."""
    from scipy import ndimage
    name = '1_105_2020-04-14_2_R.png'
    with zipfile.ZipFile(UWF_ZIP) as z:
        img = Image.open(z.open(UWF_DIR.replace('PDR512/', 'Normal512/') + name)).convert('RGB')
    a = np.asarray(img, dtype=float)
    disc, fovea = np.array([250.0, 227.0]), np.array([196.0, 226.0])
    df = float(np.hypot(*(disc - fovea)))
    r_field = 0.95 * df  # 30° field ≈ 8.6 mm ≈ 1.9 × disc–fovea distance (4.5 mm)
    temporal = -1.0  # right eye: temporal is to the left in this image
    centres = {'1': disc, '2': fovea, '3': fovea + [temporal * r_field, 0],
               '4': disc + [temporal * r_field, -r_field], '5': disc + [temporal * r_field, r_field],
               '6': disc + [-temporal * r_field, -r_field], '7': disc + [-temporal * r_field, r_field]}
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    fields = np.zeros(a.shape[:2], bool)
    for c in centres.values():
        fields |= np.hypot(xx - c[0], yy - c[1]) <= r_field
    retina = (a.mean(2) > 25) & ~((a[..., 1] > a[..., 0] + 70) & (a[..., 1] > 150))  # drop eyelid/lash glare
    retina = ndimage.binary_opening(ndimage.binary_fill_holes(ndimage.binary_opening(retina, iterations=3)), iterations=6)
    mid_c = (disc + fovea) / 2
    r_eq = 3.5 * df
    equator = np.hypot(xx - mid_c[0], yy - mid_c[1]) <= r_eq
    mid = retina & equator & ~fields
    far = retina & ~equator
    figures = []

    def add(fig_id, items, overlay, label, caption, how, legend=None):
        fig = dict(id=fig_id, items=items, source='uwf_dr_2026', source_file='Normal512/' + name,
                   mask_label=f'{label}(해부학적 정의로 그린 근사 구역)', caption=caption,
                   transform=f'유두 중심 {tuple(disc.astype(int))}·중심와 {tuple(fovea.astype(int))} 육안 지정, 거리 {df:.0f} px = 4.5 mm 가정; {how}',
                   **save_pair(fig_id, img, overlay))
        if legend:
            fig['legend'] = legend
        figures.append(fig)

    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for key, c in centres.items():
        d.ellipse((c[0] - r_field, c[1] - r_field, c[0] + r_field, c[1] + r_field), outline=(*HIGHLIGHT, 255), width=2)
        ty = c[1] + (0.45 * r_field if key in '12' else -0.45 * r_field if key in '346' else 0.45 * r_field)
        d.text((c[0] - 3, ty - 5), key, fill=(255, 255, 255, 255))
    add('uwf_etdrs_7field', ['zone_etdrs_7field'], layer, 'ETDRS 7 표준 촬영 범위',
        '정상 눈의 초광각 영상 위에 ETDRS 7 표준 촬영 범위(30° 원 7개)를 근사로 그렸습니다. 1은 유두, 2는 황반 중심, '
        '3은 황반 귀쪽, 4–7은 유두를 기준으로 위·아래 귀쪽과 코쪽입니다. 초광각 영상은 이 범위 바깥의 넓은 주변부까지 담습니다.',
        '30° 원 반지름 = 0.95 × 유두–중심와 거리, 4–7번은 유두 중심을 지나는 가로·세로선에 접하도록 배치')
    add('uwf_mid_periphery', ['ana_mid_periphery'], overlay_from_mask(mid, fill_alpha=70), '중간 주변부',
        '정상 눈의 초광각 영상에서 후극부(ETDRS 7 범위) 바깥부터 적도(와정맥 팽대부 부근)까지를 중간 주변부로 표시했습니다.',
        f'7 범위 합집합 밖, 유두–중심와 중점에서 {r_eq:.0f} px(3.5 × 거리, 적도 근사) 안의 망막')
    add('uwf_far_periphery', ['ana_far_periphery'], overlay_from_mask(far, fill_alpha=70), '원주변부',
        '정상 눈의 초광각 영상에서 적도 바깥부터 영상이 닿는 끝까지를 원주변부로 표시했습니다. 실제 원주변부는 거상연까지 이어지지만 '
        '초광각 영상도 위·아래 끝은 눈꺼풀에 가려 다 담지 못합니다.',
        f'유두–중심와 중점에서 {r_eq:.0f} px 밖의 망막, 눈꺼풀·속눈썹 반사 제외')
    add('uwf_retinal_periphery', ['zone_retinal_periphery'],
        Image.alpha_composite(colour_layer([(mid, (125, 211, 252))], mid.shape, alpha=110), overlay_from_mask(far, fill_alpha=70)),
        '망막 주변부(중간 + 원주변부)',
        '후극부 바깥의 망막 주변부를 중간 주변부(하늘색)와 원주변부(노랑)로 나누어 표시했습니다.',
        '중간 주변부 = 7 범위 밖·적도 안, 원주변부 = 적도 밖',
        legend=[{'label': '중간 주변부', 'cls': 'vitreous'}, {'label': '원주변부', 'cls': 'service'}])
    return figures


def paper_fill2_figures() -> list[dict]:
    """Sixth batch: further CC BY panels for disc, vessel, choroid and myopia items."""
    from scipy import ndimage
    from skimage import morphology

    figures = []

    def add(*args, **kwargs):
        figures.append(_paper_figure(*args, **kwargs))

    def ring_fig(*args, **kwargs):
        figures.append(_ring_figure(*args, **kwargs))

    ring_fig('paper_retinal_embolus', ['les_retinal_embolus'], 'CRIM.OPHMED2013-421352.001.jpg', (330, 20, 578, 220),
             [(100, 96, 14)], '혈관 가지점의 반짝이는 색전',
             '콜레스테롤 결정 색전증 환자의 안저 사진에서 저자가 확대한 부분입니다. 망막 동맥이 갈라지는 자리에 노랗고 반짝이는 '
             '작은 덩어리(노란 원, 저자 화살표 자리)가 걸려 있습니다(Hollenhorst 판).', '저자 화살표 끝의 색전에 원', k=2, context=True)

    ring_fig('paper_macular_pigment', ['ana_macular_pigment'], 'gr1.webp', (45, 305, 555, 815), [(255, 255, 60)],
             '황반 중심의 색소 밀집',
             '건강한 눈의 두 파장 자가형광으로 구한 황반 색소 광학밀도(MPOD) 지도입니다. 황반 색소(루테인·제아잔틴)가 중심와에 '
             '가장 짙게 모여 가운데가 밝고(노란 원), 바깥으로 갈수록 옅어집니다. 회색 격자는 저자 측정 격자입니다.',
             '중심와 MPOD 최고점 둘레에 원')

    ring_fig('paper_choroidal_hemangioma', ['les_choroidal_hemangioma'], 'rc9-138-4141-g001.webp', (0, 0, 1500, 310),
             [(250, 130, 45), (700, 120, 42), (1215, 112, 42)], '주황색 융기와 조기 과형광',
             '국한성 맥락막 혈관종 눈입니다. 왼쪽 광각 컬러 사진에서 유두 옆의 주황빛으로 솟은 맥락막 병변, 가운데 형광안저'
             '혈관조영과 오른쪽 인도시아닌그린 혈관조영에서 같은 자리가 일찍 밝게 차오릅니다(노란 원).',
             '저자 설명의 유두 코쪽 병변 자리에 원(세 영상 각각)')

    ring_fig('paper_myopic_diffuse_atrophy', ['les_myopic_diffuse_atrophy'], '41598_2022_7172_Fig1_HTML.jpg', (0, 0, 170, 102),
             [(100, 50, 32, 24)], '경계가 흐린 황백색 위축',
             '고도근시 눈의 광각 가색 사진입니다. 유두 둘레와 황반 쪽으로 경계가 흐릿한 황백색 구역(노란 테)이 퍼져 있는데, '
             '이것이 미만성 맥락망막 위축입니다. 경계가 뚜렷한 흰 반점형 위축과 구분됩니다.', '유두 둘레 황백색 구역에 타원', k=4)

    ring_fig('paper_rnfl_defect', ['les_rnfl_defect'], '12886_2023_2887_Fig4_HTML.jpg', (297, 0, 595, 299),
             [(415 - 297, 131, 13), (415 - 297, 166, 13)], '쐐기 모양 신경섬유층 결손',
             '녹내장 눈의 무적색(red-free) 사진입니다. 유두에서 뻗는 밝은 신경섬유 줄무늬 사이에 어둡게 빠진 쐐기 모양 띠(노란 '
             '원, 저자 화살표 자리)가 위·아래 귀쪽에 있습니다.', '저자 화살표 끝의 결손 띠에 원', k=2)

    name, box = '12886_2023_3104_Fig1_HTML.jpg', (0, 0, 677, 632)
    img = _paper_panel(name, box)
    lum = ndimage.gaussian_filter(np.asarray(img, dtype=float).mean(2), 4)
    from skimage import filters
    pale = lum > filters.threshold_otsu(lum)
    pale = ndimage.binary_fill_holes(_comp_near(ndimage.binary_opening(pale, iterations=3), 380, 320, 260))
    add('paper_disc_pallor', ['les_disc_pallor'], name, box, img, overlay_from_mask(pale, fill_alpha=35),
        '창백해진 유두',
        '시신경병증 3개월 뒤의 유두 사진입니다. 유두 전체가 분홍빛을 잃고 하얗게 창백해졌습니다(노란 테). 정상 유두의 '
        '신경망막 테는 분홍색이어야 합니다.', '밝기(σ 4) Otsu 임계 위 영역 중 유두 자리 최대 성분, 구멍 채움')

    name, box = 'cureus-0016-00000063557-i01.jpg', (375, 550, 750, 790)
    ring_fig('paper_gravitational_tract', ['les_rpe_gravitational_tract'], name, box, [(570 - 375, 745 - 550, 24, 48)],
             '아래로 흘러내린 궤적',
             '만성 중심장액맥락망막병증 눈의 광각 자가형광 사진입니다. 황반 아래에서 아래쪽으로 길게 흘러내린 밝고 어두운 띠(노란 '
             '테)가 망막하액이 중력 방향으로 흘러 RPE를 상하게 한 궤적입니다(저자: 하행 궤적).', '저자 설명의 하행 궤적에 타원', k=2)

    ring_fig('paper_fuchs_spot', ['les_fuchs_spot'], 'cureus-0017-00000086567-i01.jpg', (0, 0, 750, 691), [(375, 350, 32)],
             '황반의 검은 색소 반점',
             '고도근시 눈의 컬러 안저 사진입니다. 유두 둘레의 흰 위축 옆, 황반에 둥글고 검은 색소 반점(노란 원, 저자 검은 '
             '화살표 자리)이 있습니다. 근시성 맥락막 신생혈관이 흉터로 남아 색소가 모인 푹스 반점입니다.',
             '저자 검은 화살표 끝의 반점에 원')

    name, box = 'jovr-17-140-g001.jpg', (243, 440, 382, 575)
    img = _paper_panel(name, box)
    g = np.asarray(img.convert('L'), dtype=float)
    big = ndimage.binary_dilation(morphology.remove_small_objects(
        ndimage.white_tophat(ndimage.gaussian_filter(g, 0.8), size=7) > 32, 18), iterations=1)
    marks = ndimage.binary_dilation((np.asarray(img, dtype=float)[..., 0] > np.asarray(img, dtype=float)[..., 1] + 40)
                                    | (np.asarray(img, dtype=float)[..., 1] > np.asarray(img, dtype=float)[..., 0] + 40), iterations=2)
    inner = np.zeros(g.shape, bool)
    inner[6:-6, 6:-6] = True
    rpc = inner & ~big & ~marks
    img, rpc = _enlarge(img, rpc, 3)
    add('paper_rpc', ['ana_radial_peripapillary_capillaries'], name, box, img, overlay_from_mask(rpc, fill_alpha=45, edge_alpha=0),
        '유두주위 방사상 모세혈관',
        '건강한 눈의 유두 OCTA 중 내경계막–신경섬유층 슬랩입니다. 큰 혈관(표시 없음) 사이를 촘촘히 채운 가는 그물 신호'
        '(옅은 노랑)가 신경섬유층 안을 유두 쪽으로 달리는 유두주위 방사상 모세혈관입니다. 이 해상도에서는 개별 모세혈관보다 '
        '그물의 밀도로 보입니다.',
        '흰색 톱햇(7) > 32인 큰 혈관과 저자 측정선을 뺀 슬랩 영역; 표시용 3배 확대')

    ring_fig('paper_sub_rpe_ring', ['les_sub_rpe_ring_lesion'], 'cureus-0015-00000047942-i03.jpg', (522, 0, 750, 138),
             [(153, 54, 13)], 'RPE 아래 고리 모양 병변',
             '결절성 맥락막혈관병증 눈의 OCT 단면입니다. 뾰족하게 솟은 색소상피박리 안쪽, RPE 바로 아래에 가장자리가 밝고 '
             '가운데가 어두운 고리 모양 구조(노란 원)가 보이는데, 이것이 폴립의 내강입니다(저자 설명).',
             '저자 화살촉 아래 PED 안 저반사 내강에 원', k=3)

    ring_fig('paper_premacular_bursa', ['ana_premacular_bursa'], 'BMRI2020-7627128.001.jpg', (0, 0, 591, 271),
             [(280, 116, 150, 26)], '황반 앞 액화 주머니',
             '건강한 눈의 광각 SS-OCT 단면입니다. 중심와 바로 앞 유리체에 배 모양으로 어둡게 비어 있는 공간(노란 테)이 황반앞 '
             '유리체 주머니입니다. 위쪽 경계는 얇은 유리체 피질 막이며, 붉은 선은 저자의 폭·두께 측정선입니다.',
             '저자 폭(W)·중심 두께(CT) 측정선 둘레의 저반사 공간에 타원')

    ring_fig('paper_sclera', ['ana_sclera'], 'diagnostics-12-01418-g001.jpg', (300, 100, 794, 330),
             [(580 - 300, 285 - 100, 70, 30)], '드러난 공막',
             '고도근시 눈의 SS-OCT 단면입니다. 반점형 위축 자리(저자 화살표)에서 RPE·브루크막·맥락막이 없어져, 그 아래의 두껍고 '
             '균일하게 밝은 공막(노란 테)이 망막 바로 밑에 드러나 보입니다.', '저자 화살표 아래 공막 띠에 타원', k=2)

    ring_fig('paper_intraretinal_pigment', ['les_intraretinal_hyperreflective_pigment'], 'jcm-15-01327-g002.jpg',
             (299, 1160, 746, 1455), [(455 - 299, 1252 - 1160, 26)], '망막 안의 고반사 색소 덩어리',
             '2형 황반모세혈관확장증 눈의 OCT 단면입니다. 중심와 옆 외망막 안으로 RPE에서 떨어져 나온 색소 덩어리가 짙은 고반사'
             '(노란 원, 저자 파란 별·화살표 자리)로 올라와 있고, 그 아래로 빛이 가려 그림자가 집니다.',
             '저자 파란 별·화살표가 가리키는 고반사 덩어리에 원', k=2)

    ring_fig('paper_sub_rpe_hemorrhage', ['les_hemorrhage_sub_rpe'], '10.1177_24741264261442930-fig1.jpg', (0, 0, 250, 155),
             [(150, 97, 65, 15)], 'RPE 아래에 고인 출혈',
             '결절성 맥락막혈관병증 눈에 생긴 큰 RPE 아래 출혈의 OCT 단면입니다. 밝은 RPE 선(노랑·초록 색입힘)이 크게 들려 있고, 그 '
             '아래 공간(노란 테)이 출혈로 어둡게 차 있습니다(저자 설명: 거대한 RPE 아래 출혈로 생긴 RPE 박리).',
             '들린 RPE 선 아래 공간에 타원', k=3)

    ring_fig('paper_disc_collaterals', ['les_disc_collaterals'], 'cureus-0018-00000112968-i03.webp', (440, 570, 840, 970),
             [(640 - 440, 790 - 570, 55)], '유두 위 측부혈관(시신경섬모체 단락)',
             '중심망막정맥폐쇄 눈의 시신경유두를 확대한 사진입니다. 충혈된 유두 위에 막힌 정맥 대신 맥락막 쪽으로 피를 돌리는 '
             '구불구불한 단락 혈관이 생겼습니다(노란 원 안, 저자 설명: 시신경섬모체 단락). 주변에는 화염 모양 출혈이 퍼져 있습니다.',
             '저자 설명의 단락 혈관이 있는 유두에 원', context=True)

    ring_fig('paper_lattice_degeneration', ['les_lattice_degeneration'], 'fmed-13-1929247-g001.webp', (538, 0, 1037, 384),
             [(735 - 538, 255, 60, 30)], '주변부 격자변성',
             '근시 눈의 주변부 광각 가색 사진입니다. 망막 주변부에 가장자리를 따라 색소가 모인 가늘고 긴 얇아진 구역(노란 테, 저자 '
             '빨간 화살표 자리)이 격자변성입니다. 가색 영상이라 실제 색과 다릅니다.', '저자 빨간 화살표 끝 병변에 타원')

    ring_fig('paper_subretinal_lipid', ['les_lipid_subretinal'], '13256_2021_3221_Fig3_HTML.jpg', (740, 90, 1592, 560),
             [(930 - 740, 270 - 90, 75, 28)], '망막 아래 지질 침착',
             'Coats병 눈의 OCT 단면(색입힘)입니다. 떠 있는 망막 아래쪽 망막하 공간에 밝은 점 모양 지질 삼출물(노란 테)이 쌓여 있고, '
             '그 아래로 망막하액과 망막박리가 있습니다(저자 설명).', '망막하 공간의 고반사 점 무리에 타원')

    ring_fig('paper_rpe_hyperpigmentation', ['les_rpe_hyperpigmentation'], 'jcm-11-06274-g007.jpg', (0, 0, 160, 150),
             [(80, 64, 9), (98, 64, 9)], '황반의 작은 과색소 병변',
             '맥락막비후 색소상피병증 눈의 컬러 안저 사진입니다. 황반에 RPE가 진하게 착색된 작은 색소 병변과 드루젠 같은 병변(노란 '
             '원, 저자 화살촉 자리)이 있습니다.', '저자 화살촉 아래 병변에 원', k=4)

    name, box = 'antioxidants-12-01649-g001.jpg', (41, 286, 653, 676)
    ring_fig('paper_venous_beading', ['les_venous_beading'], name, box, [(170 - 41, 388 - 286, 18)], '구슬처럼 굵기가 바뀌는 정맥',
             '당뇨망막병증 눈의 광각 가색 사진입니다. 저자 2번 화살표가 가리키는 정맥 가지(노란 원)가 구슬을 꿴 것처럼 굵어졌다 '
             '가늘어지기를 되풀이합니다. 정맥 구슬모양 변화는 중증 비증식 당뇨망막병증의 기준 소견입니다.',
             '저자 2번 화살표 아래 정맥 가지에 원', k=2, context=True)
    ring_fig('paper_venous_loop', ['les_venous_loop_reduplication'], name, box, [(284 - 41, 620 - 286, 14)], '정맥 고리',
             '당뇨망막병증 눈의 광각 가색 사진입니다. 저자 5번 화살표 끝(노란 원)에서 정맥 가지가 작은 고리를 만들며 되돌아갑니다. 정맥 고리는 '
             '막힌 곳을 우회하는 혈류 변화로 생기며 진행된 당뇨망막병증에서 보입니다.',
             '저자 5번 화살표 끝의 정맥 고리에 원', k=2, context=True)

    ring_fig('paper_small_drusen', ['les_drusen_small'], 'AOS-103-e318-g008.jpg', (0, 0, 245, 245), [(70, 137, 12)],
             'RPE 아래 작은 드루젠',
             '초기 나이관련황반변성 눈의 OCT 단면입니다. RPE 선이 아주 작게 솟아오른 자리(노란 원, 저자 빨간 화살표 자리)가 소형 '
             '드루젠이며, 저자 측정 넓이는 약 1,700 µm²입니다. 오른쪽 위 작은 그림은 저자의 확대 영상입니다.',
             '저자 빨간 화살표 끝의 RPE 돌출에 원', k=2)

    name, box = 'diagnostics-15-01688-g014.jpg', (0, 258, 768, 512)
    ring_fig('paper_enface_rpe_elevation', ['les_enface_complex_rpe_elevation'], name, box,
             [(120, 380 - 258, 40), (532, 318 - 258, 26)], 'en-face의 불규칙한 RPE 융기',
             '신생혈관 나이관련황반변성 눈입니다. 왼쪽 en-face OCT에서 녹색 십자선 교차부의 불규칙한 융기 영역(노란 원)이, 오른쪽 '
             'B-scan에서는 여러 덩어리가 섞인 불규칙한 색소상피박리(노란 원, 저자 흰 화살표 자리)로 보입니다.',
             '저자 십자선 교차부(en-face)와 흰 화살표(B-scan)에 원')

    ring_fig('paper_ora_serrata', ['ana_ora_serrata'], '12886_2026_5068_Fig1_HTML.webp', (512, 381, 993, 734),
             [(770 - 512, 580 - 381, 170, 24)], '거상연',
             '유리체절제술 중 내시경으로 본 주변부 망막입니다. 아래쪽 망막(별표)이 끝나고 위쪽 섬모체 평면부로 바뀌는 톱니 모양 '
             '경계(노란 테, 저자 흰 화살촉 자리)가 거상연입니다. 위쪽의 흰 기구는 유리체 절제기입니다.',
             '저자 흰 화살촉이 가리키는 경계선 둘레에 타원')
    return figures


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    figures = (fundus_figures() + [fovea_figure()] + oct_figures() + vessel_figures() + public_lesion_figures()
               + vitreoretinal_figures() + myopia_figures()
               + paper_myopia_figures() + grade4_figures() + zone_figures() + crao_figures() + olives_figures() + paper_vascular_figures()
               + paper_case_figures() + paper_fill_figures() + chaksu_figures()
               + refined_rule_figures() + uwf_zone_figures() + paper_fill2_figures())
    for figure in figures:
        figure.update(SOURCES[figure['source']] | {'source_key': figure['source']})
    manifest = {'generated_by': 'code/build_atlas_masked_figures.py', 'figures': figures}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (OUTPUT / 'source_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n',
                                                 encoding='utf-8')
    print(f'{len(figures)} figures → {OUTPUT.relative_to(ROOT)}; manifest → {MANIFEST.relative_to(PROJECT)}')


if __name__ == '__main__':
    main()
