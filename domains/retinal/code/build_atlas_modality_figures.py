#!/usr/bin/env python3
"""Build real-image examples for each imaging modality page of the retinal atlas.

Sources (all open access, CC BY 4.0), stored once under root
``resources/datasets/retinal_atlas_modality_figures/provider_figures/`` with provider filenames:

- Penas et al. 2022, BMC Ophthalmol 22:363 (FA, ICGA, NIR, OCT en-face, OCTA)
- Feng et al. 2024, BMC Ophthalmol 24:20 (OCTA slabs)
- Fragiotta et al. 2018, Int J Retina Vitreous 4:44 (FAF)
- Zhou et al. 2022, Front Med 9:983548 (wide-field ICGA, IR)

Each example is one panel cropped from a published multi-panel figure and downscaled; panel letters
and the authors' arrows are kept. Colour fundus and OCT B-scan examples reuse the masked-figure base
images (IDRiD CC BY 4.0, AMD-SD CC0). The script verifies provider SHA-256, writes the crops, the
dataset ``source_manifest.json`` and the web manifest ``data/modality_figures.json``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

import retinal_atlas_registry as registry  # noqa: E402  (canonical source / checksum tables)

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
OUTPUT = ROOT / 'resources/datasets/retinal_atlas_modality_figures'
PROVIDER = OUTPUT / 'provider_figures'
MASKED_MANIFEST = PROJECT / 'packages/retinal-atlas-web/src/retinal_atlas_web/data/masked_figures.json'
WEB_MANIFEST = PROJECT / 'packages/retinal-atlas-web/src/retinal_atlas_web/data/modality_figures.json'
MAX_SIDE = 900
CC_BY = ('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/')

PROVIDER_FILES = {name: (row['source_id'], row['download_url'], row['sha256'])   # g_provider_figures_v01.csv
                  for name, row in registry.provider_figures_for('modality_figures').items()}
ARTICLES = {key: registry.article_record(key) for key in {v[0] for v in PROVIDER_FILES.values()}}
# id, modality, provider file, crop box (left, top, right, bottom), panel, Korean caption
CROPS = [
    ('octa_scp', 'octa', '12886_2024_3283_Fig1_HTML.png', (0, 4, 288, 290), 'Fig. 1 A1',
     '표층 모세혈관망(SCP) 슬랩. 굵은 혈관과 촘촘한 모세혈관이 흰 신호로 보이고 가운데 검은 부분이 중심와 무혈관 구역입니다.'),
    ('octa_icp', 'octa', '12886_2024_3283_Fig1_HTML.png', (302, 4, 585, 290), 'Fig. 1 B1',
     '중간 모세혈관망(ICP) 슬랩. 같은 눈에서 깊이만 바꾼 영상입니다.'),
    ('octa_dcp', 'octa', '12886_2024_3283_Fig1_HTML.png', (602, 4, 889, 290), 'Fig. 1 C1',
     '심층 모세혈관망(DCP) 슬랩. 그물 모양의 가는 모세혈관만 보이며 화살표는 혈류가 줄어든 부분입니다.'),
    ('octa_cc', 'octa', '12886_2024_3283_Fig1_HTML.png', (1209, 4, 1486, 290), 'Fig. 1 E1',
     '맥락막모세혈관(CC) 슬랩. 낱낱의 혈관 대신 고운 알갱이 무늬로 보이며, 검은 점이 flow deficit입니다.'),
    ('faf_bluelight', 'faf', '40942_2018_148_Fig2_HTML.jpg', (0, 0, 773, 597), 'Fig. 2a',
     '청색광 자가형광. RPE 리포푸신이 고르게 빛나고, 혈관·시신경유두는 어둡고 중심와는 황반 색소 때문에 어둡습니다. '
     '화살표는 작은 과자가형광 점(큐티큘러 드루젠)입니다.'),
    ('nir_macula', 'nir', '12886_2022_2566_Fig5_HTML.png', (0, 0, 630, 627), 'Fig. 5A',
     '근적외선 반사(황반 중심). 혈관이 어둡게, 바탕은 RPE·맥락막에서 돌아온 깊은 반사로 보입니다. '
     '위쪽의 어두운 띠는 혈관양선조입니다.'),
    ('nir_widefield', 'nir', 'fmed-09-983548-g004.jpg', (188, 185, 970, 971), 'Fig. 4 IR (OD)',
     '넓은 화각 근적외선 반사. 흰 점(고반사 반점)과 황반의 어두운 반사 저하가 보입니다.'),
    ('fa_early', 'fa', '12886_2022_2566_Fig4_HTML.png', (0, 0, 588, 556), 'Fig. 4A',
     '형광안저혈관조영 초기. 망막 혈관이 하얗게 차고 중심와 무혈관 구역은 어둡습니다. 화살촉은 작은 과형광 점입니다.'),
    ('fa_late', 'fa', '12886_2022_2566_Fig4_HTML.png', (0, 580, 588, 1139), 'Fig. 4C',
     '형광안저혈관조영 후기. 같은 점에서 형광이 번지는 누출이 보입니다.'),
    ('icga_macula', 'icga', '12886_2022_2566_Fig4_HTML.png', (596, 0, 1180, 556), 'Fig. 4B',
     '인도시아닌그린혈관조영 초기(황반). 망막 혈관 아래로 맥락막 혈관의 흐린 그물이 보입니다.'),
    ('icga_widefield', 'icga', 'fmed-09-983548-g004.jpg', (1000, 1110, 1812, 1932), 'Fig. 4 ICGA early (OD)',
     '넓은 화각 인도시아닌그린혈관조영 초기. 망막 혈관보다 굵은 맥락막 대혈관이 뚜렷하게 보입니다.'),
    ('oct_enface', 'oct', '12886_2022_2566_Fig5_HTML.png', (657, 0, 1290, 627), 'Fig. 5B',
     '구조 OCT en-face. volume 스캔을 깊이 방향으로 투영한 정면 영상으로, 망막하액 범위가 어둡게 보입니다.'),
]
# Colour fundus and OCT B-scan examples reuse masked-figure bases.
REUSE = [
    ('cfp_posterior_pole', 'cfp', 'fundus_optic_disc',
     '45° 컬러 안저 사진. 시신경유두·황반·혈관궁이 한 장에 담기고, 출혈·삼출물 같은 병변은 색으로 구분됩니다.'),
    ('oct_bscan', 'oct', 'oct_is_os',
     '구조 OCT B-scan. 망막층과 RPE·맥락막이 깊이 방향 띠로 보입니다(나이관련황반변성 눈).'),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, (_, url, digest) in PROVIDER_FILES.items():
        path = PROVIDER / name
        if not path.is_file():
            raise SystemExit(f'missing provider figure {path}; download it from {url}')
        if sha256(path) != digest:
            raise SystemExit(f'sha256 mismatch for {path}')
    figures, records = [], []
    masked = {f['id']: f for f in json.loads(MASKED_MANIFEST.read_text(encoding='utf-8'))['figures']}
    for fig_id, modality, masked_id, caption in REUSE:  # dataset images first, then article panels
        base = masked[masked_id]
        figures.append({'id': fig_id, 'modality': modality, 'file': base['base'], 'served': 'masked',
                        'width': base['width'], 'height': base['height'], 'caption': caption, 'panel': '',
                        'credit': base['credit'], 'title': base['name'], 'url': base['url'],
                        'license': base['license'], 'license_url': base['license_url'],
                        'transform': base['transform']})
    for fig_id, modality, provider, box, panel, caption in CROPS:
        article_key = PROVIDER_FILES[provider][0]
        article = ARTICLES[article_key]
        image = Image.open(PROVIDER / provider).convert('RGB').crop(box)
        image.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        name = f'{fig_id}.jpg'
        image.save(OUTPUT / name, quality=90, optimize=True)
        transform = f'{panel} 영역 {box}를 잘라 최대 {MAX_SIDE} px로 축소; 패널 글자·저자 표시는 원본 그대로'
        figures.append({'id': fig_id, 'modality': modality, 'file': name, 'served': 'modality',
                        'width': image.width, 'height': image.height, 'caption': caption, 'panel': panel,
                        'credit': article['credit'], 'title': article['title'], 'url': article['url'],
                        'license': CC_BY[0], 'license_url': CC_BY[1], 'transform': transform})
        records.append({'file': name, 'provider_file': f'provider_figures/{provider}',
                        'provider_sha256': PROVIDER_FILES[provider][2], 'download_url': PROVIDER_FILES[provider][1],
                        'crop_box': list(box), 'panel': panel, 'credit': article['credit'], 'article_url': article['url'],
                        'license': CC_BY[0], 'license_url': CC_BY[1], 'sha256': sha256(OUTPUT / name),
                        'modifications': transform})
    (OUTPUT / 'source_manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=1) + '\n',
                                                 encoding='utf-8')
    WEB_MANIFEST.write_text(json.dumps({'generated_by': 'code/build_atlas_modality_figures.py',
                                        'figures': figures}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'wrote {len(records)} crops to {OUTPUT} and {len(figures)} entries to {WEB_MANIFEST}')


if __name__ == '__main__':
    main()
