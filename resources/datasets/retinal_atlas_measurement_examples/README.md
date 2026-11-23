# 망막 영상 지도 측정 표시 예시

생성: `projects/P003_ophthalmic_foundation_model_validation/code/build_measurement_examples.py`

측정 목록 페이지의 "영상에 측정을 표시하는 예"에 쓰는 파생 그림이다. 측정 목록의 측정 160개를 모두 실제 영상 89장(영상 종류·부위별)에
나눠 싣는다. 같은 측정이 해당하는 여러 영상 종류(안저·FA·FAF·근적외선·ICGA·OCT·OCTA·광각)에 각각 나오도록 영상 종류마다 예시를 더했다.
영상마다 원 영상(`ex_*.jpg`)과 측정 층별 투명 PNG(`ex_*_<층>.png`, 모두 239개)를 둔다. 각 층은 공개 `retinal-measures`
함수를 입력 mask·경계에 실제로 실행한 결과를 그린 것이며, 계산값은 `source_manifest.json`(웹 `data/measurement_examples.json`과 동일)에 있다.

입력은 세 가지다.

- 공급자·전문가 mask: 데이터셋이 준 분할(예: Chákṣu 유두·컵, Refined IDRiD 병변, PALM 위축·박리, AMD-SD 병변, AMD/DME 3D OCT 망막내액)
- 서비스 추정: 공급자 mask가 없는 경우의 밝기 규칙·경계 추적(OCT 층 경계, 논문 그림의 병변 등). 영상마다 캡션과 층 설명에 적는다.
  `retinal_atlas_masked_figures`의 공개 mask를 그대로 다시 쓴 경우도 있다.
- 판독 항목: 계산 코드가 없는 정성 측정(유두 색, FAF 양상, MNV 활동성 등). 측정값 대신 볼 자리와 판독 기준을 표시하며 상태는 `reading`이다.

| 예시 | 원 자료 | 라이선스 | 층 | 측정(판독) |
|---|---|---|---|---|
| 안저 · 시신경유두 | Kumar JRH, et al. Chákṣu: A glaucoma specific fundus image database. Sci Data 2023;10:70 (figshare 20123135, Test split) (`Test/1.0_Original_Fundus_Images/Remidio/IMG_4198.JPG`) | CC BY 4.0 | 10 | 10 (판독 2) |
| 안저 · 망막 혈관 | Intajag S, Bhurayanontachai P. Fundus-AVSeg-7C (Zenodo 23277451; 원 자료 Fundus-AVSeg, Deng Z et al. Sci Data 2025) (`OrginalImages/Org/005_N.png`) | CC BY 4.0 | 15 | 23 (판독 2) |
| 안저 · 당뇨망막병증 병변 | Refined IDRiD annotations (Zenodo 18676805) (`Train/Images/IDRiD_31.jpg`) | CC BY 4.0 | 4 | 8 |
| 안저 · 병변 크기·형태(공통) | Refined IDRiD annotations (Zenodo 18676805) (`Train/Images/IDRiD_31.jpg`) | CC BY 4.0 | 8 | 10 (판독 3) |
| 안저 · 병변 위치·분포(공통) | Refined IDRiD annotations (Zenodo 18676805) (`Train/Images/IDRiD_31.jpg`) | CC BY 4.0 | 6 | 8 |
| 안저 · 근시성 황반 위축 | Fang H, et al. PALM: Open fundus photograph dataset with pathologic myopia recognition and anatomical structure annotation. Sci Data 2024;11:99 (figshare 21299148) (`Training/Images/P0004.jpg`) | CC0 1.0 | 3 | 3 |
| 안저 · 근시성 기울어진 유두 | Fang H, et al. PALM: Open fundus photograph dataset with pathologic myopia recognition and anatomical structure annotation. Sci Data 2024;11:99 (figshare 21299148) (`Training/Images/P0054.jpg`) | CC0 1.0 | 2 | 2 |
| 안저 · 드루젠 | Intajag S, Bhurayanontachai P. Fundus-AVSeg-7C (Zenodo 23277451; 원 자료 Fundus-AVSeg, Deng Z et al. Sci Data 2025) (`OrginalImages/Org/061_A.png`) | CC BY 4.0 | 1 | 2 |
| 안저 · 증식성 신생혈관 | Refined IDRiD annotations (Zenodo 18676805) (`Train/Images/IDRiD_27.png`) | CC BY 4.0 | 2 | 4 |
| 안저 · IRMA·유리체 출혈 | Refined IDRiD annotations (Zenodo 18676805) (`Train/Images/IDRiD_17.jpg`) | CC BY 4.0 | 2 | 3 (판독 1) |
| 안저 · 정맥 구슬모양 변화 | Haydinger CD, et al. (2023) Antioxidants 12:1649, Figure 1D (`provider_figures/antioxidants-12-01649-g001.jpg`) | CC BY 4.0 | 2 | 2 |
| 안저 · 유두 출혈 위치 | Tsuda K, et al. (2022) J Med Case Rep 16:462, Fig. 1B (`provider_figures/13256_2022_3690_Fig1_HTML.jpg`) | CC BY 4.0 | 1 | 1 |
| 안저 · 화염상 출혈 | Jain P, et al. (2026) Cureus 18:e108935, Figure 1a (`provider_figures/cureus-0018-00000108935-i01.jpg`) | CC BY 4.0 | 1 | 1 |
| 안저 · 범망막 광응고 반흔 | Chi K, et al. (2026) Medicine (Baltimore) 105:e50535, Figure 1D1·E2 (`provider_figures/medi-105-e50535-g001.webp`) | CC BY 4.0 | 1 | 2 |
| 광각 안저 · 망막앞 출혈 | Ultra-wide-field (SLO) fundus image dataset for intelligent DR system (figshare 31259494) (`PDR512/5_142_2021-11-14_1_R.png`) | CC BY 4.0 | 1 | 1 |
| 안저 · 망막박리 | Fang H, et al. PALM: Open fundus photograph dataset with pathologic myopia recognition and anatomical structure annotation. Sci Data 2024;11:99 (figshare 21299148) (`Training/Images/P0058.jpg`) | CC0 1.0 | 2 | 2 |
| 무적색 안저 · 신경섬유층 결손 | Zhang W, et al. (2023) BMC Ophthalmol 23:134, Fig. 4B (`provider_figures/12886_2023_2887_Fig4_HTML.jpg`) | CC BY 4.0 | 1 | 1 |
| 광각 안저 · 미세혈관 병변 생성·소실 | Burggraaf-Sánchez de las Matas R, et al. (2025) Antioxidants 14:244, Figure 1a (대조군) (`provider_figures/antioxidants-14-00244-g001.jpg`) | CC BY 4.0 | 1 | 1 |
| FA · 광각 무관류와 누출 | Chi K, et al. (2026) Medicine (Baltimore) 105:e50535, Figure 1D1·E2 (`provider_figures/medi-105-e50535-g001.webp`) | CC BY 4.0 | 2 | 3 (판독 1) |
| FA · 황반 신생혈관 | Penas S, et al. (2022) BMC Ophthalmol 22:363 Fig. 4C (`retinal_atlas_modality_figures/fa_late.jpg`) | CC BY 4.0 | 2 | 2 (판독 1) |
| FAF · 위축 가장자리 양상 | Corradetti G, et al. (2026) Invest Ophthalmol Vis Sci 67:46, Figure 2E (`provider_figures/iovs-67-8-46-f002.jpg`) | CC BY 4.0 | 2 | 2 (판독 2) |
| 근적외선 · 18개월 병변 변화 | Corradetti G, et al. (2026) Invest Ophthalmol Vis Sci 67:46, Figure 1 (`provider_figures/iovs-67-8-46-f001.jpg`) | CC BY 4.0 | 2 | 2 |
| ICGA · 결절성 맥락막혈관병증 | Carta V, et al. (2023) Cureus 15:e47942, Figures 2D·3B (`provider_figures/cureus-0015-00000047942-i02.jpg`) | CC BY 4.0 | 1 | 1 |
| 근적외선 · 망막하 드루젠양 침착물 | Kominami T, et al. (2025) Cureus 17:e93258, Figure 1E (`provider_figures/cureus-0017-00000093258-i01.jpg`) | CC BY 4.0 | 2 | 3 (판독 1) |
| OCT · 황반 망막층 | Prabhushankar M, Kokilepersaud K, et al. OLIVES Dataset: Ophthalmic Labels for Investigating Visual Eye Semantics. NeurIPS 2022 Datasets and Benchmarks (Zenodo 7105232) (`TREX DME/Monthly/0222MOS/V26/OS/TREX_DME_000024.tif`) | CC BY 4.0 | 10 | 15 |
| OCT · 황반 내층(RNFL·GCIPL) | Bringmann A, et al. (2022) PLoS One 17:e0266968, Fig 2A·C (`provider_figures/pone.0266968.g002.jpg`) | CC BY 4.0 | 2 | 2 |
| OCT · 황반 병변(액체·PED) | Li G et al. AMD-SD OCT dataset (figshare 25513435) (`images/64/64_25.png`) | CC0 1.0 | 11 | 14 (판독 2) |
| OCT 볼륨 · 두께 지도와 망막내액 | Huang W, et al. (2025) Comprehensive 3D OCT dataset for AMD and DME (figshare 30582035) (`DME_labeled/input/DME0101.tif`) | CC BY 4.0 | 2 | 6 |
| OCT · DME 중심 단면과 맥락막 | Huang W, et al. (2025) Comprehensive 3D OCT dataset for AMD and DME (figshare 30582035) (`DME_labeled/input/DME0101.tif (B-scan 232)`) | CC BY 4.0 | 5 | 7 |
| OCT 연속 단면 · AMD 병변 부피 | Li G et al. AMD-SD OCT dataset (figshare 25513435) (`images/83/ (25장)`) | CC0 1.0 | 3 | 4 |
| OCT · 전층 황반원공 | Gholami P, et al. OCTID: Optical coherence tomography image database — Macular Hole Retinal OCT images (Borealis) (`images/MH7.jpeg`) | CC0 1.0 | 2 | 3 |
| OCT · 유리체황반 견인 | Gholami P, et al. OCTID: Optical coherence tomography image database (Borealis) (`images/AMRD25.jpeg`) | CC0 1.0 | 1 | 1 |
| OCT · 망막전막 | Gholami P, et al. OCTID: Optical coherence tomography image database — Macular Hole Retinal OCT images (Borealis) (`images/MH30.jpeg`) | CC0 1.0 | 2 | 2 (판독 1) |
| OCT · 후포도종 굴곡 | Gholami P, et al. OCTID: Optical coherence tomography image database — Macular Hole Retinal OCT images (Borealis) (`images/MH28.jpeg`) | CC0 1.0 | 1 | 1 |
| OCT · 맥락막 과투과 | Gholami P, et al. OCTID: Optical coherence tomography image database (Borealis) (`images/AMRD27.jpeg`) | CC0 1.0 | 1 | 1 |
| OCT · 드루젠 | Gholami P, et al. OCTID: Optical coherence tomography image database (Borealis) (`images/AMRD15.jpeg`) | CC0 1.0 | 3 | 3 |
| OCT · 유두주위 RNFL 원형 스캔 | Markowitz DM, et al. (2026) Am J Ophthalmol Case Rep 42:102544, Fig. 4 (OD) (`provider_figures/gr4.jpg`) | CC BY 4.0 | 2 | 3 |
| OCT · 시신경유두 방사 단면 | Oyur G, et al. (2026) BMC Ophthalmol 26:755, Fig. 1C (`provider_figures/12886_2026_5473_Fig1_HTML.webp`) | CC BY 4.0 | 1 | 1 |
| OCTA · 황반 표층 혈관망 | Feng Y, et al. (2024) BMC Ophthalmol 24:20, Fig. 1 (`retinal_atlas_modality_figures/octa_scp.jpg`) | CC BY 4.0 | 2 | 3 |
| OCTA · 황반 심층 혈관망 | Feng Y, et al. (2024) BMC Ophthalmol 24:20 Fig. 1 C1 (`retinal_atlas_modality_figures/octa_dcp.jpg`) | CC BY 4.0 | 1 | 1 |
| OCTA · 맥락막모세혈관층 | Feng Y, et al. (2024) BMC Ophthalmol 24:20 Fig. 1 E1 (`retinal_atlas_modality_figures/octa_cc.jpg`) | CC BY 4.0 | 1 | 1 |
| OCTA · 유두주위 방사상 모세혈관 | Hassanpour K, et al. (2022) J Ophthalmic Vis Res 17:140, Figure 1 (대조군 오른눈) (`provider_figures/jovr-17-140-g001.jpg`) | CC BY 4.0 | 1 | 1 |
| OCTA · 6개월 FAZ 변화 | Bromeo AJ, et al. (2022) Int J Retina Vitreous 8:57, Fig. 2A·D (`provider_figures/40942_2022_406_Fig2_HTML.jpg`) | CC BY 4.0 | 1 | 1 |
| FA · 황반 혈관망과 FAZ | Penas S, et al. (2022) BMC Ophthalmol 22:363 Fig. 4A (`retinal_atlas_modality_figures/fa_early.jpg`) | CC BY 4.0 | 6 | 9 |
| FA · 과형광 병변(공통) | Penas S, et al. (2022) BMC Ophthalmol 22:363 Fig. 4C (`retinal_atlas_modality_figures/fa_late.jpg`) | CC BY 4.0 | 9 | 13 |
| FA · 광각 신생혈관(NVD·NVE) | Chi K, et al. (2026) Medicine (Baltimore) 105:e50535, Figure 1D1·E2 (`provider_figures/medi-105-e50535-g001.webp`) | CC BY 4.0 | 6 | 10 |
| FAF · 광각 다발 반점(공통) | Shahid MM, et al. (2026) Cureus 18:e104405, Figure 1C (`provider_figures/cureus-0018-00000104405-i01.jpg`) | CC BY 4.0 | 10 | 16 |
| FAF · 소눈 모양 위축 | Maheshwari SY, et al. (2022) Cureus 14:e30859, Figure 3a·b (`provider_figures/cureus-0014-00000030859-i03.jpg`) | CC BY 4.0 | 2 | 3 |
| 근적외선 · 광각 밝은 점과 유두 둘레 | Zhou Y, et al. (2022) Front Med 9:983548 Fig. 4 IR (OD) (`retinal_atlas_modality_figures/nir_widefield.jpg`) | CC BY 4.0 | 13 | 19 |
| 근적외선 · 다발 위축 | Corradetti G, et al. (2026) Invest Ophthalmol Vis Sci 67:46, Figure 1 (`provider_figures/iovs-67-8-46-f001.jpg`) | CC BY 4.0 | 2 | 3 |
| ICGA · 과형광 점(공통) | Demirel S, et al. (2022) Diagnostics 12:1368, Figure 2D (`provider_figures/diagnostics-12-01368-g002.jpg`) | CC BY 4.0 | 9 | 14 |
| ICGA · 결절·분지 혈관망 면적 | Carta V, et al. (2023) Cureus 15:e47942, Figures 2D·3B (`provider_figures/cureus-0015-00000047942-i02.jpg`) | CC BY 4.0 | 1 | 1 |
| OCTA · 표층 혈관 그래프 | Feng Y, et al. (2024) BMC Ophthalmol 24:20, Fig. 1 (`retinal_atlas_modality_figures/octa_scp.jpg`) | CC BY 4.0 | 6 | 9 |
| OCTA · 모세혈관 무관류 | Bromeo AJ, et al. (2022) Int J Retina Vitreous 8:57, Fig. 2A·D (`provider_figures/40942_2022_406_Fig2_HTML.jpg`) | CC BY 4.0 | 1 | 1 |
| 광각 안저 · 사분면별 출혈 | Ultra-wide-field (SLO) fundus image dataset for intelligent DR system (figshare 31259494) (`PDR512/5_359_2021-04-13_5_L.png`) | CC BY 4.0 | 2 | 3 |
| 광각 안저 · 유두 밖 신생혈관 | Ultra-wide-field (SLO) fundus image dataset for intelligent DR system (figshare 31259494) (`PDR512/5_118_2022-04-21_3_R.png`) | CC BY 4.0 | 2 | 3 (판독 1) |
| OCT · 위축 18개월 변화 | Corradetti G, et al. (2026) Invest Ophthalmol Vis Sci 67:46, Figure 1 (`provider_figures/iovs-67-8-46-f001.jpg`) | CC BY 4.0 | 5 | 10 |
| OCT · 뾰족한 색소상피박리(결절) | Carta V, et al. (2023) Cureus 15:e47942, Figures 2D·3B (`provider_figures/cureus-0015-00000047942-i03.jpg`) | CC BY 4.0 | 1 | 1 |
| OCT · 드루젠 단면 크기 | Gholami P, et al. OCTID: Optical coherence tomography image database (Borealis) (`images/AMRD15.jpeg`) | CC0 1.0 | 1 | 2 |
| 안저 · 망막앞 출혈 치료 전후 | Douillet I, et al. (2026) Cureus 18:e105301, Figure 1 (`provider_figures/cureus-0018-00000105301-i01.jpg`) | CC BY 4.0 | 2 | 2 |
| OCTA · 미세동맥류 | Guro M, et al. (2026) Optom Vis Sci 103:e70090 (`provider_figures/OVS2-103-e70090-g006.webp`) | CC BY 4.0 | 1 | 2 |
| OCTA · 유두 밖 신생혈관 | Guro M, et al. (2026) Optom Vis Sci 103:e70090 (`provider_figures/OVS2-103-e70090-g003.webp`) | CC BY 4.0 | 1 | 2 |
| OCTA · 유두 신생혈관 | Guro M, et al. (2026) Optom Vis Sci 103:e70090 (`provider_figures/OVS2-103-e70090-g007.webp`) | CC BY 4.0 | 1 | 2 |
| OCTA · 망막내 미세혈관 이상 | Guro M, et al. (2026) Optom Vis Sci 103:e70090 (`provider_figures/OVS2-103-e70090-g004.webp`) | CC BY 4.0 | 1 | 1 |
| OCTA · 결절성 맥락막혈관병증 혈관망 | Shen M, et al. (2021) Am J Ophthalmol Case Rep 22:101057, Fig. 4 (`provider_figures/ajoc-22-101057-gr4.jpg`) | CC BY 4.0 | 2 | 2 |
| FA + OCT · MNV 유형 | Shen M, et al. (2021) Am J Ophthalmol Case Rep 22:101057, Fig. 4 (`provider_figures/ajoc-22-101057-gr4.jpg`) | CC BY 4.0 | 1 | 1 |
| ICGA + OCT · MNV 유형 | Shen M, et al. (2021) Am J Ophthalmol Case Rep 22:101057, Fig. 4 (`provider_figures/ajoc-22-101057-gr4.jpg`) | CC BY 4.0 | 1 | 1 |
| FA · 미세동맥류 | Videkar RP, et al. (2024) Cureus 16:e73228, Figure 7 (`provider_figures/cureus-0016-00000073228-i07.jpg`) | CC BY 4.0 | 1 | 3 |
| ICGA · 48주 병변 변화 | Carta V, et al. (2023) Cureus 15:e47942, Figure 2D·H (`provider_figures/cureus-0015-00000047942-i02.jpg`) | CC BY 4.0 | 1 | 1 |
| ICGA + EDI-OCT · 맥락막 대혈관 | Kitagawa Y, et al. (2021) BMC Ophthalmol 21:320, Fig. 1 (`provider_figures/12886_2021_2067_Fig1_HTML.jpg`) | CC BY 4.0 | 1 | 1 |
| 광각 안저 · 주변부 레이저 반흔 | Panse K, et al. (2023) Am J Ophthalmol Case Rep 32:101908, Fig. 1A (`provider_figures/ajoc-32-101908-gr1.jpg`) | CC BY 4.0 | 1 | 2 |
| 광각 무적색 · IRMA 침범 사분면 | Guro M, et al. (2026) Optom Vis Sci 103:e70090 (`provider_figures/OVS2-103-e70090-g004.webp`) | CC BY 4.0 | 1 | 1 |
| 광각 FA · 허혈 지수 | Chi K, et al. (2026) Medicine (Baltimore) 105:e50535, Figure 1D1·E2 (`provider_figures/medi-105-e50535-g001.webp`) | CC BY 4.0 | 1 | 1 |
| FAF · 유두 둘레 위축 반점 변화 | Bai J, et al. (2026) Medicine (Baltimore) 105:e47893, Figures 3B·5B (`provider_figures/medi-105-e47893-g005.jpg`) | CC BY 4.0 | 2 | 2 |
| FAF · 망막하 드루젠양 침착물 | Li M, et al. (2019) Retina 39:802–816, Fig. 3 (`provider_figures/retina-39-802-g003.jpg`) | CC BY 4.0 | 1 | 1 |
| OCT · 망막하 드루젠양 침착물 | Li M, et al. (2019) Retina 39:802–816, Fig. 3 (`provider_figures/retina-39-802-g003.jpg`) | CC BY 4.0 | 2 | 2 (판독 1) |
| 광각 안저 · 황반을 비낀 망막박리 | Al-Saleh A, et al. (2025) Cureus 17:e85709, Figure 1 (`provider_figures/cureus-0017-00000085709-i01.jpg`) | CC BY 4.0 | 2 | 2 |
| FAF · 범망막 광응고 반흔(12개월) | Higaki M, et al. (2018) J Ophthalmol 2018:9371895, Figure 1c (`provider_figures/JOPH2018-9371895.001.jpg`) | CC BY 4.0 | 1 | 2 |
| OCT · BMO로 정한 유두 면적 | Choung HK, et al. (2021) PLoS One 16:e0254889, Fig 1B (`provider_figures/pone.0254889.g001.jpg`) | CC BY 4.0 | 1 | 1 |
| FAF · 고도근시 유두주위 위축 | Fonollosa A, et al. (2026) Front Med 13:1745948, Figure 4B (`provider_figures/fmed-13-1745948-g004.jpg`) | CC BY 4.0 | 1 | 1 |
| 광각 FA · 망막내 미세혈관 이상 | Yang Z, et al. (2022) Front Endocrinol 13:1079217, Figure 5C (`provider_figures/fendo-13-1079217-g005.jpg`) | CC BY 4.0 | 1 | 2 |
| OCT · 유두 단면의 컵과 테 | Driessen SJ, et al. (2024) Transl Vis Sci Technol 13(12):5, Figure 2C (`provider_figures/tvst-13-12-5-f002.jpg`) | CC BY 4.0 | 1 | 3 |
| OCT 표면 영상 · 근시성 반달 | Hu R, et al. (2024) Front Neurol 15:1366593, Figure 2B (`provider_figures/fneur-15-1366593-g002.jpg`) | CC BY 4.0 | 1 | 1 |
| 근적외선 · 특발 망막전막 | Vogt D, et al. (2026) Int J Retina Vitreous 12:59, Fig. 1A (`provider_figures/40942_2026_849_Fig1_HTML.jpg`) | CC BY 4.0 | 1 | 1 |
| 광각 FA · 정맥 구슬모양 변화 | Zhuang X, et al. (2025) Genes Dis 12:101390, Figure 1A(b) (`provider_figures/gendis-12-101390-gr1.jpg`) | CC BY 4.0 | 1 | 1 |
| 광각 FA · 정맥 구슬모양 변화 | Zhuang X, et al. (2025) Genes Dis 12:101390, Figure 1A(b) (`provider_figures/gendis-12-101390-gr1.jpg`) | CC BY 4.0 | 1 | 1 |
| FA · 치료 전후 미세동맥류 변화 | Lee J, et al. (2023) BMC Ophthalmol 23:34, Fig. 2 (`provider_figures/12886_2023_2788_Fig2_HTML.jpg`) | CC BY 4.0 | 2 | 2 |
| OCT 유두 리포트 · 테 두께 순서와 노치 | Ramirez Gandia AI, et al. (2026) Cureus 18:e115500, Figure 2 (`provider_figures/cureus-0018-00000115500-i02.webp`) | CC BY 4.0 | 2 | 2 |
| 안저 · 6개월 미세동맥류 생성·소실 | Marques IP, et al. (2021) Acta Diabetol 58:197–205, Fig. 1 (Phenotype C) (`provider_figures/592_2020_1602_Fig1_HTML.jpg`) | CC BY 4.0 | 1 | 1 |

새로 받은 논문 그림 4장은 원본 파일명 그대로 `retinal_atlas_modality_figures/provider_figures/`에 한 번만 두고 SHA-256을 생성 코드
(`NEW_PROVIDER`)에 고정했다: `40942_2022_406_Fig2_HTML.jpg`(Bromeo 2022, FAZ 6개월 비교), `antioxidants-14-00244-g001.jpg`
(Burggraaf-Sánchez de las Matas 2025, 12개월 광각 비교), `gr4.jpg`(Markowitz 2026, 유두주위 원형 스캔), `iovs-67-8-46-f002.jpg`
(Corradetti 2026, FAF 양상). AMD/DME 3D OCT 볼륨은 `public_amd/amd_dme_3d_oct/`의 공급자 원본(`DME_labeled/DME0101`)을 읽는다.

장비 보정 정보가 없으면 값은 화소 단위다(유두지름 DD, 원형 스캔의 200 µm 눈금으로 바꾼 µm 제외). OCT 볼륨의 ETDRS 격자는 공급자가
화소 크기를 밝히지 않아 촬영 범위를 6×6 mm로 가정했고, 깊이 화소 크기가 없어 황반 부피는 "계산 불가"로 둔다. 임상 판정이나 검증값이 아니다.

지도에서 측정마다 정한 영상 종류(안저·광각·FA·FAF·근적외선·ICGA·OCT·OCTA) 모두에 예시가 있다. 원 그림 해상도 때문에 일부는 저자 표시(화살표·타원·분할선·장비 경계선)를
입력으로 쓰거나 원형 가정 같은 근사를 썼고, 영상마다 캡션에 적었다.

남은 항목 대부분은 논문 그림(CC BY)에서 저자가 표시한 화살표·타원·분할선이나 서비스 밝기 규칙으로 입력을 만들었다. 영상마다 캡션에 그 방법을 적었다.
