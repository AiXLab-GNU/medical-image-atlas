"""Prostate H&E lesion figures cut from CC BY 4.0 paper figures.

Provider files live once in ``resources/datasets/pathology_atlas_provider_figures/`` under their original names,
pinned by SHA-256 in ``g_provider_figures``. Panels are cut by fixed boxes (white gutters measured on the provider
file). Nothing is drawn on them: the lesion call is the author's own caption. Called from
``build_pathology_figures.py``; the panels are written next to the masked figures and carry ``kind: paper``.
"""
from __future__ import annotations

import csv

from PIL import Image

import pathology_atlas_registry as registry

PROVIDER_DIR = registry.DATASETS / 'pathology_atlas_provider_figures'
MIN_WIDTH = 460          # small journal panels are enlarged (LANCZOS) to this display width

G2, G3 = '13000_2016_478_Fig2_HTML.jpg', '13000_2016_478_Fig3_HTML.jpg'
GX = ((0, 229), (242, 472))
GY2 = ((0, 179), (187, 360), (372, 546))
GY3 = ((0, 174), (187, 360), (372, 546))
H1 = '41379_2021_860_Fig1_HTML.jpg'
HX, HY = ((0, 311), (323, 633)), ((0, 435), (448, 882))
O3 = '41467_2022_34945_Fig3_HTML.jpg'


def g(fig_rows, col, row):
    return (GX[col][0], fig_rows[row][0], GX[col][1], fig_rows[row][1])


def h(col, row):
    return (HX[col][0], HY[row][0], HX[col][1], HY[row][1])


# id, items, file, box (None = trim white border), panel label, Korean caption, author caption
PANELS = [
    ('paper_gp3', ['les_gleason_pattern_3'], G2, g(GY2, 0, 0), 'Fig. 2a',
     '따로 떨어진 잘 형성된 작은 샘이 간질 사이에 흩어진 글리슨 3+3=6(등급군 1)입니다.',
     'Gleason score 3 + 3 = 6 (Grade Group 1).'),
    ('paper_cribriform_minor', ['les_cribriform', 'les_gleason_pattern_4'], G2, g(GY2, 1, 0), 'Fig. 2b',
     '글리슨 3+4=7(등급군 2)로, 작은 사상 샘이 일부 섞여 있습니다.',
     'Gleason score 3 + 4 = 7 (Grade Group 2) with minor component of cribriform glands.'),
    ('paper_cribriform', ['les_cribriform', 'les_gleason_pattern_4'], G2, g(GY2, 0, 1), 'Fig. 2c',
     '한 샘 안에 여러 구멍이 뚫린 불규칙한 사상 샘(글리슨 4+4=8, 등급군 4)입니다.',
     'Gleason score 4 + 4 = 8 (Grade Group 4) with irregular cribriform glands.'),
    ('paper_fused', ['les_fused_glands', 'les_gleason_pattern_4'], G2, g(GY2, 1, 1), 'Fig. 2d',
     '샘 사이 간질이 사라져 샘이 서로 붙은 융합 샘(세포질 공포 동반, 글리슨 4+4=8)입니다.',
     'Gleason score 4 + 4 = 8 (Grade Group 4) with fused glands with cytoplasmic vacuoles.'),
    ('paper_glomeruloid', ['les_glomeruloid', 'les_gleason_pattern_4'], G2, g(GY2, 0, 2), 'Fig. 2e',
     '샘 안에 상피 덩어리가 사구체처럼 매달린 사구체 모양 샘(글리슨 4+4=8)입니다.',
     'Gleason score 4 + 4 = 8 (Grade Group 4) with glomeruloid glands.'),
    ('paper_poorly_formed', ['les_poorly_formed_glands', 'les_gleason_pattern_4'], G2, g(GY2, 1, 2), 'Fig. 2f',
     '내강이 거의 없는 불완전한 샘(글리슨 4+4=8)입니다.',
     'Gleason score 4 + 4 = 8 (Grade Group 4) with poorly-formed glands.'),
    ('paper_solid_sheets', ['les_solid_sheets', 'les_gleason_pattern_5'], G3, g(GY3, 0, 0), 'Fig. 3a',
     '샘 구조 없이 세포가 판으로 자라는 고형 패턴(글리슨 5+5=10, 등급군 5)입니다.',
     'Gleason score 5 + 5 = 10 (Grade Group 5) with solid sheets of cells.'),
    ('paper_cords', ['les_gleason_pattern_5'], G3, g(GY3, 1, 0), 'Fig. 3b',
     '세포가 끈 모양으로 늘어선 패턴 5(글리슨 5+5=10)입니다.',
     'Gleason score 5 + 5 = 10 (Grade Group 5) with cords of cells.'),
    ('paper_single_cells', ['les_gleason_pattern_5'], G3, g(GY3, 0, 1), 'Fig. 3c',
     '암세포가 하나씩 흩어져 침윤하는 패턴 5(글리슨 5+5=10)입니다.',
     'Gleason score 5 + 5 = 10 (Grade Group 5) with individual cells.'),
    ('paper_cribriform_necrosis', ['les_comedonecrosis', 'les_cribriform', 'les_gleason_pattern_5'], G3, g(GY3, 1, 1),
     'Fig. 3d', '가운데 괴사가 있는 사상 샘입니다(글리슨 5+4=9, 등급군 5). 면포 괴사는 패턴 5로 읽습니다.',
     'Gleason score 5 + 4 = 9 (Grade Group 5) with cribriform glands, some with necrosis.'),
    ('paper_idc', ['les_intraductal_carcinoma'], G3, g(GY3, 0, 2), 'Fig. 3e',
     '왼쪽 H&E는 괴사를 동반한 관내암입니다. 오른쪽 띠는 같은 병변의 면역염색으로, 둘레 기저세포(p63·HMWCK 갈색)가 남아 있고 '
     'AMACR가 양성입니다.',
     'Intraductal carcinoma with necrosis (left), surrounded by basal cells highlighted by p63 and high molecular '
     'weight cytokeratin (right) and positive for racemase.'),
    ('paper_gp5_single_cords', ['les_gleason_pattern_5'], H1, h(0, 0), 'Fig. 1A',
     '단일 세포와 끈 모양으로 침윤하는 패턴 5입니다(15×).', 'Single cells and cords, 15×.'),
    ('paper_solid_fields', ['les_solid_sheets', 'les_gleason_pattern_5'], H1, h(0, 1), 'Fig. 1C',
     '중간–큰 고형 영역으로 자라는 패턴 5입니다(15×).', 'Medium to large solid fields, 15×.'),
    ('paper_comedonecrosis', ['les_comedonecrosis', 'les_gleason_pattern_5'], H1, h(1, 1), 'Fig. 1D',
     '고형 둥지 가운데에 괴사 찌꺼기가 고인 면포 괴사(패턴 5)입니다(15×).', 'Comedonecrosis, 15×.'),
    ('paper_adenosis', ['les_adenosis'], '1746-1596-3-34-1.jpg', (0, 0, 295, 225), 'Figure 1A',
     '크기가 다양한 샘이 빽빽이 모인 선증(비정형 선종성 과형성)입니다. 암과 헷갈리는 양성 병변입니다(×200).',
     'Crowded haphazardly arranged variably sized glands with infiltrative appearance of glands at the edges. '
     'Original magnification × 200.'),
    ('paper_postatrophic', ['les_atrophy'], O3, (3, 3, 323, 326), 'Fig. 3A',
     '위축 후 과형성: 작고 위축된 샘이 무리 지은 양성 조직입니다(막대 500 µm).',
     'Benign prostatic tissue with postatrophic hyperplasia. Scale bar 500 µm.'),
    ('paper_partial_atrophy', ['les_partial_atrophy'], O3, (340, 3, 662, 326), 'Fig. 3B',
     '부분 위축: 세포질이 줄어든 양성 샘입니다. 원 논문에서 AI가 암으로 잘못 읽은 증례입니다(막대 500 µm).',
     'Benign prostatic tissue with partial atrophy (misinterpreted by AI as malignant). Scale bar 500 µm.'),
    ('paper_epe', ['les_extraprostatic_extension'], 'medicina-62-01465-g014.webp', None, 'Figure 14',
     '전립선 밖 조직으로 뻗은 암(피막 밖 침범)입니다(HE ×40).', 'Extraprostatic extension. HE ×40.'),
    ('paper_epe_fat', ['les_extraprostatic_extension', 'les_poorly_formed_glands'], '13000_2014_190_Fig3_HTML.jpg', None,
     'Figure 3', '전립선 밖 지방(흰 빈 칸) 사이에 놓인 불완전한 샘(패턴 4)입니다.',
     'Small tumor area (<5% of the whole tumor) of Gleason pattern 4 (poorly formed glands) in an extraprostatic position.'),
    ('paper_lvi', ['les_lymphovascular_invasion'], 'medicina-62-01465-g015.webp', None, 'Figure 15',
     '가운데 림프관 안에 암세포 덩어리가 떠 있는 림프관 침범입니다(HE ×200).', 'Invasion of lymphatic vessel. HE, ×200.'),
    ('paper_svi', ['les_seminal_vesicle_invasion', 'les_cribriform', 'ana_seminal_vesicle'], 'medicina-62-01465-g010.webp', None, 'Figure 10',
     '사상 샘암이 정낭을 침범한 모습입니다(HE ×100).', 'Cribriform adenocarcinoma invading seminal vesicles. HE, ×100.'),
    ('paper_pni', ['les_perineural_invasion', 'ana_nerve'], 'curroncol-33-00527-g003.webp', None, 'Figure 3',
     '종양 세포가 신경 다발(가운데 둥근 섬유 구조)을 둘러싸고 파고든 신경주위 침범입니다(×200, 막대 100 µm). 원 논문의 종양은 전립선 선양낭성암으로, '
     '흔한 선방 선암이 아니지만 신경주위 침범의 모습은 같습니다.',
     'Hematoxylin and eosin staining demonstrating perineural invasion. Tumor cells are observed surrounding and '
     'infiltrating nerve structures within the tumor stroma. Original magnification ×200; scale bar = 100 μm.'),
    ('paper_basal_cell_hyperplasia', ['les_basal_cell_hyperplasia'], 'cancers-16-01097-g006.jpg', (10, 510, 707, 993), 'Figure 6B',
     '기저세포가 여러 층으로 늘어나 고형 둥지를 이룬 기저세포 과형성(요로상피 화생 동반)입니다. 관내암의 고형 패턴과 헷갈릴 수 있는 양성 병변입니다.',
     'Basal cell hyperplasia with urothelial metaplasia, frequently present in varying proportions together, may simulate '
     'the dense solid pattern of intraductal carcinoma.'),
    ('paper_granulomatous_prostatitis', ['les_prostatitis'], 'gr1.jpg', (372, 3, 726, 280), 'Fig. 1B',
     '상피양 세포가 림프구에 둘러싸여 경계가 흐린 육아종을 이룬 육아종성 전립선염입니다(10×). 암으로 오인될 수 있는 염증입니다.',
     'Proliferating epithelioid cells surrounded by lymphocytes forming poorly defined granulomas (10X).'),
    ('paper_xanthogranulomatous_prostatitis', ['les_prostatitis'], 'gr1.jpg', (372, 577, 726, 849), 'Fig. 1F',
     '거품 조직구가 림프구·형질세포·호산구·호중구와 함께 빽빽이 들어찬 황색육아종성 전립선염입니다.',
     'Dense infiltration of foamy histiocytes, accompanied by lymphocytes, plasma cells, eosinophils, and neutrophils.'),
    # normal structures and benign nodules (Skrok 2024, Żurowska 2023, Pollack 2025)
    ('paper_blood_vessel', ['ana_blood_vessel'], 'boe-15-12-6816-g004.jpg', (8, 14, 170, 190), 'Fig. 4a',
     '전립선 주변 조직의 혈관입니다. 가운데 내강(L)을 내막(TI)·중막(TM, 파란 점선)·외막(TA, 자홍 점선)이 차례로 둘러쌉니다(막대 200 µm).',
     'Five examples of histology and en face OCT images of blood vessels located within periprostatic tissue. The blue '
     'lines mark the boundaries of individual layers in the blood vessel wall: TI = tunica intima, TM = tunica media, '
     'TA = tunica adventitia. L = vessel lumen, B = blood within blood vessels.'),
    ('paper_nerve', ['ana_nerve'], 'boe-15-12-6816-g003.jpg', (12, 420, 174, 601), 'Fig. 3c',
     '전립선 주변 지방 속의 신경입니다. 신경을 싸는 신경외막(초록 화살표) 안에 축삭(청록 화살표)이 모여 있고, 곁에 작은 혈관(빨간 화살표)이 있습니다(막대 200 µm).',
     'Four examples of histology and en face OCT images of nerves present in periprostatic tissue. ... the blue arrows '
     'correspond to axons, ... the red arrows correspond to blood vessels, and the green arrows correspond to the epineurium.'),
    ('paper_corpora_amylacea', ['ana_corpora_amylacea'], 'boe-15-12-6816-g005.jpg', (218, 500, 384, 668), 'Fig. 5d',
     '위축된 양성 샘의 내강에 든 둥근 층상 분비물 덩어리(유리체, 아밀라체; 화살표)입니다(막대 200 µm).',
     'Histology and en face OCT images of various types of healthy prostatic glands: ... (d) atrophic with the presence '
     'of corpora amylacea.'),
    ('paper_periprostatic', ['ana_capsule'], 'boe-15-12-6816-g002.jpg', (12, 526, 261, 756), 'Fig. 2h',
     '전립선 가장자리입니다. 샘(G)과 간질(S) 바깥에 전립선 주변 조직(P)이 이어지고, 그 안에 지방(A)·혈관(V)·신경(N)이 있습니다(막대 2 mm).',
     'G = healthy gland, T = tumor, S = stroma, P = periprostatic tissue, A = adipose tissue, V = blood vessel, N = nerve.'),
    ('paper_afms', ['ana_anterior_fibromuscular_stroma'], 'cancers-15-03682-g001b.jpg', (16, 27, 667, 518), 'Figure 1e',
     '근치 전립선절제 전체 절편입니다. 위쪽(앞쪽)에 샘이 없는 분홍 섬유근육 조직(화살표)이 앞쪽 섬유근육 간질이며, 여기서는 두꺼워져 있습니다.',
     'Hypertrophied anterior fibromuscular stroma (normal anatomic structure—PI-RADS 1): ... (e) whole mount '
     'histopathology after radical prostatectomy confirms the diagnosis depicting anterior fibromuscular stroma in the '
     'anterior part of the prostate (arrows).'),
    ('paper_bph_nodule', ['les_nodular_hyperplasia'], 'cancers-15-03682-g008.jpg', (367, 788, 669, 1044), 'Figure 8B(b)',
     '전체 절편의 오른엽(사진 왼쪽)에 피막으로 완전히 싸인 큰 결절성 과형성 결절(빨간 화살표)이 있습니다. 반대쪽 파란 선 안은 선방 선암입니다.',
     'Whole mount histopathology specimen after prostatectomy show the acinar prostate adenocarcinoma in the PZ and TZ of '
     'the left lobe of the prostate (... outlined and marked area on histopathology specimen) and large completely '
     'encapsulated BPH nodule in the right lobe of prostate (... red arrow on histopathology specimen (b)).'),
    ('paper_bph_stromal_nodule', ['les_nodular_hyperplasia'], 'cancers-15-03682-g009b.jpg', (8, 14, 716, 617), 'Figure 9g',
     '이행대의 간질형 결절성 과형성 결절(화살표)입니다. 샘이 거의 없는 간질 결절이라 MRI에서 암처럼 보였던 예입니다. 위쪽에는 샘이 많은 과형성 결절들이 보입니다.',
     'Atypical BPH nodule in the transition zone: ... (g) Histopathologically, it proved to be a stromal BPH nodule (arrow).'),
    ('paper_tz_section', ['ana_transition_zone', 'ana_urethra'], 'jci-135-186939-g126.jpg', (28, 20, 190, 200), 'Figure 1A',
     '전립선 가로 단면 전체입니다. 가운데가 요도이고, 빨간 네모는 결절성 과형성 결절이 있는 이행대 위치입니다(막대 1 cm).',
     'H&E-stained transverse cross section through prostate (urethra center), with red square marking transition zone '
     'location of BPH nodule.'),
    ('paper_bph_mixed_nodule', ['les_nodular_hyperplasia'], 'jci-135-186939-g126.jpg', (195, 20, 378, 200), 'Figure 1B',
     '왼쪽 단면 빨간 네모 부분을 키운 것입니다. 빨간 점선이 샘과 간질이 섞인 결절성 과형성 결절의 경계입니다(막대 1 mm).',
     'Magnified view with nodule border (and microdissected region) demarcated by red-dashed line.'),
]


def provider() -> dict[str, dict]:
    with (registry.CATALOG / 'g_provider_figures_v01.csv').open(encoding='utf-8', newline='') as handle:
        rows = {r['file']: r for r in csv.DictReader(handle)}
    for name, row in rows.items():
        if registry.sha256(PROVIDER_DIR / name) != row['sha256']:
            raise ValueError(f'provider file changed: {name}')
    return rows


def trim(im: Image.Image, white=235) -> tuple[int, int, int, int]:
    """Bounding box of the non-white part (journal page margin removed)."""
    grey = im.convert('L').point(lambda v: 255 if v < white else 0)
    return grey.getbbox() or (0, 0, im.width, im.height)


def build() -> list[dict]:
    rows = provider()
    figs = []
    for fid, items, name, box, label, caption, original in PANELS:
        row = rows[name]
        src = registry.source_record(row['source_id'])
        im = Image.open(PROVIDER_DIR / name).convert('RGB')
        box = box or trim(im)
        crop = im.crop(box)
        how = f'패널 {label} 잘라냄 (x {box[0]}–{box[2]}, y {box[1]}–{box[3]})'
        if crop.width < MIN_WIDTH:
            k = MIN_WIDTH / crop.width
            crop = crop.resize((MIN_WIDTH, round(crop.height * k)), Image.LANCZOS)
            how += f', 표시용 {k:.2f}배 확대'
        base = f'{fid}.jpg'
        crop.save(registry.MASKED_DIR / base, quality=90, optimize=True)
        figs.append({'id': fid, 'kind': 'paper', 'items': items, 'source': row['source_id'], 'source_file': name,
                     'panel': label, 'mask_label': '논문 그림 · 저자 판정', 'legend': [],
                     'caption': caption, 'original_caption': original, 'transform': how, 'base': base, 'overlay': '',
                     'width': crop.width, 'height': crop.height, 'name': src['name'],
                     'credit': f"{src['credit']}, {label}", 'source_credit': src['credit'], 'url': src['url'], 'license': src['license'],
                     'license_url': src['license_url']})
    return figs


if __name__ == '__main__':
    print(len(build()), 'paper panels')
