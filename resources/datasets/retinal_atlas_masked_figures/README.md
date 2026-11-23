# Retinal atlas masked figures

망막 영상 지도(`retinal-atlas-web`)의 항목 페이지에 쓰는 실제 영상과 mask 겹침 그림이다.
`projects/P003_ophthalmic_foundation_model_validation/code/build_atlas_masked_figures.py`가 공개 데이터셋에서
결정적 규칙으로 생성한다. 각 그림은 축소·잘라낸 원본 JPEG와 같은 크기의 반투명 mask PNG 한 쌍이다.

| 원 자료 | 라이선스 | 사용한 주석 |
| --- | --- | --- |
| IDRiD Segmentation·Localization | CC BY 4.0 | 시신경유두·미세동맥류·출혈·경성삼출물·면화반 mask, 중심와·유두 중심 좌표 |
| Refined IDRiD | CC BY 4.0 | 망막 혈관 mask |
| Fundus-AVSeg-7C | CC BY 4.0 | 동맥·정맥·혈관 교차·유두 mask(혈관 항목) |
| Feng et al. 2024, BMC Ophthalmol 24:20 | CC BY 4.0 | OCTA SCP·ICP·DCP 슬랩(혈류 신호는 국소 임계값 자동 이진화, FAZ는 자동 영역 추정) |
| OCTID(AMD OCT) | CC0 1.0 | 서비스 표시: 장액성·드루젠양 PED, 낭포, 드루젠, 외망막 관상 구조, 과투과, 후유리체막(견인·부착), 망막하 반흔 |
| OCTID(Macular Hole OCT) | CC0 1.0 | 서비스 표시: 전층·층판 황반원공 결손, 망막전막(표면 막), 망막전막 동반 층간분리, 후유리체막과 유리체 쪽 |
| PALM | CC0 1.0 | 위축·망막박리·유두 mask와 중심와 좌표(공급자 전문가 주석): 근시성 황반 위축·반점형 위축, 경사 유두, 망막박리 |
| OCTID(Macular Hole OCT) MH28 | CC0 1.0 | 서비스 표시: 후포도종으로 보이는 굴곡의 RPE 선 |
| Lai 2016 BMC Ophthalmol 16:18 · Jonas 2021 BMC Ophthalmol 21:443 · Lee 2020 BMC Ophthalmol 20:202 · Wang 2021 Front Med 8:657772 | CC BY 4.0 | 원 그림 패널(저자 화살표 유지)에 서비스 표시: 근시성 견인 황반병증, 래커 균열, 돔 모양 황반, 근시성 CNV. 원 그림은 `../retinal_atlas_modality_figures/provider_figures/`에 SHA-256 고정 |
| UWF-DR 2026 | CC BY 4.0 | 서비스 표시: 망막앞 출혈, 섬유혈관 증식막 |
| Bhatt et al. 2023, Cureus 15:e48157 | CC BY 4.0 | 중심망막동맥폐쇄 무적색광 사진(섬모체망막동맥 관류 영역은 씨앗점 영역 확장으로 대략 추정) |
| AMD-SD | CC0 1.0 | OCT IRF·SRF·PED·SHRM·IS/OS mask |
| Refined IDRiD(통합 mask) | CC BY 4.0 | IRMA·신생혈관(NVD/NVE 미구분)·유리체 출혈 공급자 전문가 mask |
| Fundus-AVSeg-7C 정상 눈 005_N | CC BY 4.0 | 전문가 중심와·유두 mask 위에 해부학적 정의로 그린 구역: 중심소와·부중심와·주변황반, ETDRS 격자, 유두주위 구역(지름 3.46 mm), 사분면. mm 환산은 유두–중심와 4.5 mm 가정 |
| Bhatt et al. 2023 Figure 1a | CC BY 4.0 | 서비스 표시: 체리 적색 반점 위치, 허혈성 백색 부종 범위 |
| OLIVES(TREX DME B-scan 5장) | CC BY 4.0 | 바이오마커가 모두 0인 중심와 단면의 층 경계 자동 추적(내경계막·전체/신경감각/내/외망막·외핵층·브루크막 위치), 공급자 단면 라벨이 붙은 황반 두꺼워짐·RPE 단절·고반사 점 단면에 서비스 표시 |
| Lin 2019 · Garbrecht 2024 BMC Ophthalmol, Adriono 2022 J Med Case Rep, Gabison 2026 BMC Ophthalmol | CC BY 4.0 | 원 그림 패널에 서비스 표시: 망막 동맥 대동맥류, 황반 별 모양 삼출물, 혈관 피막, 혈관염 소견(피막·출혈), 모세혈관확장, 유두 부종 |
| CC BY 증례 보고 14편(Cureus 11, Medicine, Rom J Ophthalmol; PMC 공개 접근 사본) | CC BY 4.0 | 원 그림 패널에 서비스 표시: 동정맥 교차 현상, 맥락막 모반, 무관류 영역, 레이저 반흔, 망막하 출혈, PAMM, 다발성 흰 점, 골소체 모양 색소, 화염상 출혈, 망막 열공, CHRPE, 황백색 반점, 과녁 모양 황반병증, 결절 모양 병변, 뾰족한 색소상피박리, 난황모양 병변. 작은 몽타주 패널은 표시용으로 2–3배 확대 |
| Chákṣu Test split (전문가 5명 STAPLE 합의 mask) | CC BY 4.0 | 유두 함몰(컵), 신경망막 테(유두 − 컵) |
| Refined IDRiD 통합 mask + 위치 규칙 | CC BY 4.0 | NV 성분을 유두 경계 1 유두지름 기준으로 나눈 NVD·NVE, 중심와 500 µm 원 안 경성삼출물(CSME 판정 구역), 고리 모양 경성삼출물 |
| UWF-DR 정상 눈 + 해부학적 정의 | CC BY 4.0 | ETDRS 7 표준 범위, 중간 주변부, 원주변부, 망막 주변부(유두–중심와 거리 4.5 mm 가정 근사) |
| CC BY 논문 그림 29편(PMC 공개 접근 사본) | CC BY 4.0 | 유두 출혈, 정맥 확장, 소동맥 협착, 혈관양선조, 맥락막 과투과, 맥락막 비후, RPE 저색소, iRORA, 맥락망막 흉터, 소용돌이형 드루젠, 망막하 드루젠양 침착물, 황반 신생혈관, PVR, 가성원공, GCIPL·헨레섬유층·근양대·광수용체 외절·맞물림대(저자 층 이름표 기준), ELM 단절, 브루크막 개구부, 사상판, 와정맥 팽대부, FAZ 확대, 망막동맥 색전, 황반 색소, 맥락막 혈관종, 근시성 미만성 위축, 신경섬유층 결손, 유두 창백, 중력 궤적, 푹스 반점, 유두주위 방사상 모세혈관, RPE 아래 고리 병변, 황반앞 유리체 주머니, 공막 |
| CC BY 논문 그림 10편(PMC 공개 접근 사본, 그림 설명문 자동 검색으로 찾음) | CC BY 4.0 | 망막내 고반사 색소, RPE 아래 출혈, 유두 측부혈관, 격자변성, 망막하 지질, RPE 과색소, 정맥 구슬모양 변화, 정맥 고리, 소형 드루젠, en-face 복합 RPE 융기, 거상연 |

mask는 공급자·전문가 주석이며 우리 모델의 분할 결과가 아니다. 파생 원(중심와 범위)은 좌표에서 계산한
대략적 표시다. 확대(잘라낸) 그림에는 전체 영상에 확대 범위를 상자로 그린 위치 안내 `<id>_context.jpg`가 함께 있다. 그림별 원 파일·변환·SHA-256은 `source_manifest.json`에 있다. 원 자료는 이 폴더로 복사하지 않는다.
PAPILA(유두·컵 경계)는 데이터 라이선스가 GPL 3.0+(CC BY/CC0 아님)이라 사용하지 않았다.


"서비스 표시"는 전문가 주석이 없는 공개 영상에 이 서비스가 위치(상자·씨앗점)를 정하고 영역 확장·임계값·RPE 선 융기·유리체막 추적·망막 표면 추적으로 자동 추정한
표시다. Fundus-AVSeg의 드루젠·유두 함몰·유두주위 위축·호피 모양 안저도 같은 방식이며, 유두 경계만 데이터셋의 전문가 분할이다.
그림마다 방법이 manifest의 `transform`에 있다. 전문가 검토 전이다.
