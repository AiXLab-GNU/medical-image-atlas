# 병리 영상 지도(전립선) 조사 표 v01

`code/build_pathology_atlas_catalog.py`가 등록 표에서 만든 읽기용 문서다. 손으로 고치지 않는다.

영상 종류 6 · 해부 21 · 병변 25 · 특징 36 · 질병 9 · 질병–소견 관계 39 · 판정 체계 5 · 근거 문헌 20

## A. 영상 종류

| ID | 이름 | 보이는 것 | 한계 |
| --- | --- | --- | --- |
| `img_he` | H&E 조직 슬라이드 | 샘 구조·핵 모양·간질·종양의 성장 양상 | 한 절편만 보며 3차원 구조는 추정; 염색·스캐너 차이가 큼 |
| `img_he_wsi` | H&E 전체 슬라이드 영상 | 종양 범위·조직 구성·병변 분포(저배율) | 고배율 세부는 확대해야 보임; 파일이 큼 |
| `img_he_hpf` | H&E 고배율 시야 | 핵 크기·핵소체·유사분열·기저세포층 | 좁은 범위만 보임 |
| `img_he_patch` | H&E 패치(10× 등) | 글리슨 패턴·샘 모양(AI 학습 단위) | 패치 경계에서 구조가 잘림 |
| `img_ihc` | 면역조직화학 염색 | 기저세포 유무(HMWCK·p63)·AMACR 과발현 | 염색 품질·판독 기준에 좌우; 단독 진단에 쓰지 않음 |
| `img_ihc_hmwck_amacr` | HMWCK·AMACR 이중 염색 | 기저세포 소실과 AMACR 양성 샘 | 양성 모방 병변도 AMACR 양성일 수 있음 |

## B. 해부

| ID | 이름 | 정의 | H&E·IHC |
| --- | --- | --- | --- |
| `ana_prostate` | 전립선 | 방광 아래 요도를 둘러싼 외분비샘 기관 | limited·limited |
| `ana_peripheral_zone` | 말초대 | 전립선 뒤·바깥쪽의 샘 구역(선암의 약 70%가 생김) | limited·none |
| `ana_transition_zone` | 이행대 | 요도 주변의 샘 구역(양성 전립선비대증이 생김) | limited·none |
| `ana_central_zone` | 중심대 | 사정관을 둘러싼 원뿔 모양 구역(크고 복잡한 샘) | limited·none |
| `ana_anterior_fibromuscular_stroma` | 앞쪽 섬유근육 간질 | 샘이 없는 전립선 앞쪽의 섬유근육 조직 | limited·none |
| `ana_capsule` | 전립선 피막·주변 지방 | 전립선 바깥의 섬유근육 띠와 그 밖의 지방 조직(피막 밖 침범의 기준) | direct·limited |
| `ana_urethra` | 요도 | 전립선 가운데를 지나는 요로 | direct·limited |
| `ana_seminal_vesicle` | 정낭 | 전립선 뒤 위쪽의 분비샘(침범 시 pT3b; 생검에서 암과 헷갈림) | direct·limited |
| `ana_benign_gland` | 양성 샘(선방) | 두 층(분비 세포 + 기저세포) 상피가 내강을 둘러싼 크고 굴곡진 샘 | direct·direct |
| `ana_gland_lumen` | 샘 내강 | 샘 가운데 비어 있는 공간(분비물·유리체가 있을 수 있음) | direct·limited |
| `ana_secretory_cells` | 분비(내강) 세포 | 내강 쪽의 키 큰 원주 세포(창백한 세포질) | direct·direct |
| `ana_basal_cell_layer` | 기저세포층 | 분비 세포 바깥의 납작한 세포층(양성 샘에는 있고 침윤암에는 없음) | limited·direct |
| `ana_corpora_amylacea` | 유리체(아밀라체) | 양성 샘 내강의 동심원 층 분비물 덩어리 | direct·none |
| `ana_stroma` | 섬유근육 간질 | 샘 사이를 채우는 평활근·섬유 조직(분홍색) | direct·direct |
| `ana_nerve` | 신경 | 간질 안의 신경 다발(신경주위 침범의 기준) | direct·limited |
| `ana_blood_vessel` | 혈관 | 간질 안의 동맥·정맥·모세혈관 | direct·limited |
| `ana_nucleus` | 세포핵 | 헤마톡실린으로 청자색인 세포핵(크기·모양·핵소체를 봄) | direct·limited |
| `ana_nucleolus` | 핵소체 | 핵 안의 작은 점(뚜렷하게 크면 암을 시사) | direct·none |
| `ref_tissue_area` | 조직 면적(분모) | 배경을 뺀 조직 면적 — 비율 측정의 분모 | direct·direct |
| `ref_pixel_size` | 화소 크기(µm/px) | 영상 한 화소의 실제 크기 — 길이·면적을 µm·mm로 바꾸는 기준 | direct·direct |
| `ref_hpf` | 고배율 시야 면적 | 현미경 40× 한 시야의 면적(대략 0.2–0.3 mm²; 장비마다 다름) | direct·direct |

## C. 병변

| ID | 묶음 | 이름 | 정의 | 감별 |
| --- | --- | --- | --- | --- |
| `les_adenocarcinoma` | 선암(통합) | 선방 선암(통합) | 기저세포 없이 간질로 침윤하는 암 샘(글리슨 패턴 3·4·5의 묶음) | 양성 샘 · 위축 · 선증(AAH) |
| `les_gleason_pattern_3` | 글리슨 패턴 | 글리슨 패턴 3 | 따로 떨어진 잘 형성된 작은 샘이 간질로 침윤 | 양성 샘 · 부분 위축 · 선증 |
| `les_gleason_pattern_4` | 글리슨 패턴 | 글리슨 패턴 4 | 잘 형성되지 않은 샘 · 융합 샘 · 사상(체 모양) 샘 · 사구체 모양 샘 | 접선으로 잘린 패턴 3 · 관내암 |
| `les_gleason_pattern_5` | 글리슨 패턴 | 글리슨 패턴 5 | 샘 형성 없이 고형 판 · 끈 · 단일 세포 · 면포 괴사가 있는 침윤 | 염증 세포 · 패턴 4의 접선 절단 |
| `les_poorly_formed_glands` | 패턴을 정하는 성장 양상 | 잘 형성되지 않은 샘 | 내강이 거의 없거나 불분명한 작은 샘 무리(패턴 4) | 접선 절단된 패턴 3 |
| `les_fused_glands` | 패턴을 정하는 성장 양상 | 융합 샘 | 샘들이 간질 없이 서로 붙은 모양(패턴 4) | 밀집한 패턴 3 |
| `les_cribriform` | 패턴을 정하는 성장 양상 | 사상(체 모양) 샘 | 한 샘 안에 여러 개의 구멍(내강)이 체처럼 뚫린 큰 샘(패턴 4 · 예후 나쁨) | 관내암 · 양성 사상 증식 · 중심대 샘 |
| `les_glomeruloid` | 패턴을 정하는 성장 양상 | 사구체 모양 샘 | 샘 안에 세포 덩어리가 사구체처럼 매달린 모양(패턴 4) | 사상 샘의 초기 형태 |
| `les_solid_sheets` | 패턴을 정하는 성장 양상 | 고형 판·끈·단일 세포 | 샘 없이 판·끈·흩어진 단일 세포로 자라는 모양(패턴 5) | 림프구 · 형질세포 염증 |
| `les_comedonecrosis` | 패턴을 정하는 성장 양상 | 면포 괴사 | 사상·고형 샘 가운데의 괴사 찌꺼기(패턴 5) | 내강 분비물 |
| `les_intraductal_carcinoma` | 관내·상피내 병변 | 관내암 | 기저세포가 남은 기존 관 안을 암세포가 채우고 넓힌 것(고형·조밀 사상 또는 심한 핵 이형) | 고등급 PIN · 사상 침윤암 · 비정형 관내 증식 |
| `les_atypical_intraductal_proliferation` | 관내·상피내 병변 | 비정형 관내 증식 | 관내암 기준에 못 미치는 비정형 관내 상피 증식 | 고등급 PIN · 관내암 |
| `les_hgpin` | 관내·상피내 병변 | 고등급 전립선 상피내 종양 | 기저세포가 남은 기존 샘의 분비 세포가 핵소체가 뚜렷한 이형 세포로 바뀐 것 | 관내암 · 비정형 관내 증식 · 암과 붙은 PIN 유사 샘 |
| `les_perineural_invasion` | 침범 | 신경주위 침범 | 암 샘이 신경을 둘러싸거나 신경 안으로 들어간 것 | 신경 옆의 양성 샘 |
| `les_lymphovascular_invasion` | 침범 | 림프혈관 침범 | 내피로 둘러싸인 혈관·림프관 안의 암세포 | 수축 인공 틈 |
| `les_extraprostatic_extension` | 침범 | 피막 밖 침범 | 암이 전립선 밖 지방 조직까지 나간 것(pT3a) | 피막 안 지방(정상 변이) |
| `les_seminal_vesicle_invasion` | 침범 | 정낭 침범 | 암이 정낭 근육벽까지 침범한 것(pT3b) | 정낭 상피의 비정형(양성) |
| `les_atrophy` | 암을 모방하는 양성 병변 | 위축 | 세포질이 줄어 작고 짙어 보이는 양성 샘(암과 헷갈림) | 글리슨 패턴 3 |
| `les_partial_atrophy` | 암을 모방하는 양성 병변 | 부분 위축 | 세포질이 일부만 줄어 창백하고 핵이 커 보이지 않는 양성 샘(암 모방) | 글리슨 패턴 3 |
| `les_adenosis` | 암을 모방하는 양성 병변 | 선증(비정형 선종성 과형성) | 이행대의 작은 샘이 밀집한 결절(기저세포는 조각으로 남음) | 글리슨 패턴 3 |
| `les_basal_cell_hyperplasia` | 암을 모방하는 양성 병변 | 기저세포 과형성 | 기저세포가 여러 층으로 늘어난 양성 샘 | 고등급 PIN |
| `les_nodular_hyperplasia` | 양성 변화 | 결절성 과형성 | 이행대의 샘·간질이 결절 모양으로 늘어난 것 | — |
| `les_prostatitis` | 양성 변화 | 염증(전립선염) | 샘·간질의 림프구·호중구 침윤 | 패턴 5 단일 세포 |
| `les_tissue_artifact` | 인공물 | 조직 인공물 | 접힘·찢김·기포·흐림 등 판독을 방해하는 부분 | — |
| `les_generic` | 공통 대상 | 병변 공통 | 여러 병변에 공통으로 쓰는 측정을 묶는 서비스 내부 대상 | — |

## D. 특징·측정

| ID | 대상 | 이름 | 유형 | 단위 | 영상 |
| --- | --- | --- | --- | --- | --- |
| `ft_tissue_area` | 조직 면적(분모) | 조직 면적 | quantitative | mm2 | img_he_wsi |
| `ft_tumor_fraction` | 선방 선암(통합) | 종양 비율 | quantitative | % | img_he_wsi |
| `ft_tumor_area` | 선방 선암(통합) | 종양 면적 | quantitative | mm2 | img_he_wsi |
| `ft_tumor_extent` | 선방 선암(통합) | 종양 최대 길이 | quantitative | mm | img_he_wsi |
| `ft_stroma_fraction` | 섬유근육 간질 | 간질 비율 | quantitative | % | img_he_wsi |
| `ft_benign_gland_fraction` | 양성 샘(선방) | 양성 샘 비율 | quantitative | % | img_he_wsi |
| `ft_artifact_fraction` | 조직 인공물 | 인공물 비율 | quantitative | % | img_he_wsi |
| `ft_pattern4_percent` | 글리슨 패턴 4 | 패턴 4 비율 | quantitative | % | img_he_wsi img_he_patch |
| `ft_pattern5_percent` | 글리슨 패턴 5 | 패턴 5 비율 | quantitative | % | img_he_wsi img_he_patch |
| `ft_pattern3_percent` | 글리슨 패턴 3 | 패턴 3 비율 | quantitative | % | img_he_wsi img_he_patch |
| `ft_cribriform_presence` | 사상(체 모양) 샘 | 사상 패턴 유무 | qualitative | presence | img_he_hpf img_he_patch |
| `ft_gland_count` | 양성 샘(선방) | 샘 개수 | quantitative | count | img_he_hpf img_he_patch |
| `ft_gland_density` | 양성 샘(선방) | 샘 밀도 | quantitative | count/mm2 | img_he_hpf img_he_patch |
| `ft_gland_area` | 양성 샘(선방) | 샘 크기 | quantitative | µm2 | img_he_hpf img_he_patch |
| `ft_gland_circularity` | 양성 샘(선방) | 샘 원형도 | quantitative | index(0–1) | img_he_hpf img_he_patch |
| `ft_lumen_fraction` | 샘 내강 | 내강 비율 | quantitative | % | img_he_hpf img_he_patch |
| `ft_lumina_per_gland` | 사상(체 모양) 샘 | 샘당 내강 수 | quantitative | count | img_he_hpf img_he_patch |
| `ft_nuclear_density` | 세포핵 | 핵 밀도 | quantitative | count/mm2 | img_he_hpf img_he_patch |
| `ft_nuclear_area` | 세포핵 | 핵 크기 | quantitative | µm2 | img_he_hpf |
| `ft_nuclear_area_variation` | 세포핵 | 핵 크기 다양성 | quantitative | ratio | img_he_hpf |
| `ft_hematoxylin_od` | 세포핵 | 헤마톡실린 광학밀도 | quantitative | OD | img_he_hpf img_he_wsi |
| `ft_texture_contrast` | 섬유근육 간질 | 조직 질감 대비 | quantitative | index | img_he_hpf img_he_wsi |
| `ft_nucleolus_prominence` | 핵소체 | 뚜렷한 핵소체 | qualitative | presence | img_he_hpf |
| `ft_basal_cell_presence` | 기저세포층 | 기저세포 유무 | qualitative | presence | img_ihc_hmwck_amacr img_he_hpf |
| `ft_amacr_positivity` | 선방 선암(통합) | AMACR 양성 | qualitative | presence | img_ihc_hmwck_amacr |
| `ft_pni_presence` | 신경주위 침범 | 신경주위 침범 유무 | qualitative | presence | img_he_hpf |
| `ft_idc_presence` | 관내암 | 관내암 유무 | qualitative | presence | img_he_hpf img_ihc_hmwck_amacr |
| `ft_epe_presence` | 피막 밖 침범 | 피막 밖 침범 유무 | qualitative | presence | img_he_wsi |
| `ft_lesion_generic_presence` | 병변 공통 | 소견 유무 | qualitative | presence | img_he_wsi img_he_hpf |
| `ft_lesion_generic_area` | 병변 공통 | 소견 면적 | quantitative | mm2 | img_he_wsi |
| `ft_lesion_generic_fraction` | 병변 공통 | 소견 비율 | quantitative | % | img_he_wsi |
| `ft_lesion_generic_count` | 병변 공통 | 소견 개수(초점) | quantitative | count | img_he_wsi |
| `ft_gleason_score` | 선방 선암(통합) | 글리슨 점수 | qualitative | category | img_he_wsi |
| `ft_isup_grade_group` | 선방 선암(통합) | ISUP 등급군 | qualitative | category(1–5) | img_he_wsi |
| `ft_basal_cell_coverage` | 기저세포층 | 기저세포 둘레 비율 | quantitative | % | img_ihc_hmwck_amacr |
| `ft_amacr_fraction` | 선방 선암(통합) | AMACR 양성 면적 비율 | quantitative | % | img_ihc_hmwck_amacr |

## E. 질병과 판정 체계

### 전립선 선암(선방형) (`dis_prostate_adenocarcinoma`)

- 글리슨 점수 — severity_classification: 가장 많은 패턴과 두 번째(생검은 가장 높은) 패턴의 합
- ISUP 등급군 — severity_classification: 글리슨 점수를 1–5 등급군으로 묶음
- 글리슨 패턴 3 — severity_classification: 잘 형성된 따로 떨어진 샘
- 글리슨 패턴 4 — severity_classification: 잘 형성되지 않은·융합·사상·사구체 모양 샘
- 글리슨 패턴 5 — severity_classification: 고형 판·끈·단일 세포·면포 괴사
- 패턴 4 비율 — prognostic: 등급군 2·3에서 패턴 4 비율을 보고
- 패턴 5 비율 — prognostic: 소량(5% 미만)이라도 3차 패턴 5는 보고
- 사상(체 모양) 샘 — prognostic: 사상 패턴은 전이·암 사망 위험이 높아 있으면 보고
- 사상 패턴 유무 — prognostic: 사상 패턴 유무 보고
- 종양 비율 — prognostic: 생검 코어 침범 비율·암 길이는 위험 분류에 쓰임
- 종양 최대 길이 — prognostic: 생검의 암 길이(mm)
- 신경주위 침범 — characteristic_nonspecific: 신경주위 침범은 암의 확실한 소견(양성에는 거의 없음)
- 기저세포 유무 — diagnostic_criterion: 기저세포 소실은 침윤암의 진단 근거(IHC로 확인)
- AMACR 양성 — characteristic_nonspecific: AMACR 과발현은 암을 시사하나 단독으로 진단하지 않음
- 뚜렷한 핵소체 — characteristic_nonspecific: 뚜렷한 핵소체는 암 세포의 특징
- 핵 크기 — characteristic_nonspecific: 암 세포 핵은 대개 크고 짙음(연구 지표)
- 샘 크기 — characteristic_nonspecific: 패턴 3 암 샘은 양성 샘보다 작고 둥긂(연구 지표)
- 피막 밖 침범 — severity_classification: 피막 밖 침범은 pT3a
- 정낭 침범 — severity_classification: 정낭 침범은 pT3b
- 림프혈관 침범 — prognostic: 림프혈관 침범은 나쁜 예후 인자
- 샘 밀도 — characteristic_nonspecific: 암 샘은 밀집해 침윤(연구 지표)
- 샘당 내강 수 — characteristic_nonspecific: 한 샘 안의 여러 내강은 사상 패턴을 시사(연구 지표)
- 기저세포 둘레 비율 — diagnostic_criterion: 침윤암 샘은 기저세포 둘레가 거의 없음(IHC)
- AMACR 양성 면적 비율 — characteristic_nonspecific: 암 샘은 AMACR 적색 양성 면적이 넓음
- 판정 체계 **글리슨 패턴(ISUP 2014)** (typing)
  1. 패턴 5 — 고형 판 · 끈 · 단일 세포 · 면포 괴사
  2. 패턴 4 — 잘 형성되지 않은 샘 · 융합 샘 · 사상 샘 · 사구체 모양 샘
  3. 패턴 3 — 따로 떨어진 잘 형성된 샘(크기 다양)
- 판정 체계 **ISUP 등급군** (staging)
  1. 등급군 5 — 글리슨 점수 9–10
  2. 등급군 4 — 글리슨 점수 8(4+4 · 3+5 · 5+3)
  3. 등급군 3 — 글리슨 점수 4+3=7
  4. 등급군 2 — 글리슨 점수 3+4=7
  5. 등급군 1 — 글리슨 점수 6 이하
- 판정 체계 **AJCC 8판 병리 병기(pT)** (staging)
  1. pT4 — 외괄약근·직장·방광·골반벽 등 주변 구조 침범
  2. pT3b — 정낭 침범
  3. pT3a — 피막 밖 침범 · 방광경부 현미경 침범
  4. pT2 — 전립선 안에 국한
- 판정 체계 **침윤암과 모방 병변 가르기** (representative)
  1. 침윤암을 지지 — 기저세포 소실 · 뚜렷한 핵소체 · 신경주위 침범 · 작은 둥근 샘의 침윤 · AMACR 양성
  2. 양성(모방 병변)을 지지 — 기저세포 유지 · 위축·부분 위축 · 선증 · 유리체

### 전립선 관내암 (`dis_idc_p`)

- 관내암 — diagnostic_criterion: 기저세포가 남은 관을 고형·조밀 사상 또는 심한 이형 세포가 채움
- 관내암 유무 — diagnostic_criterion: 관내암 유무를 보고
- 기저세포 유무 — diagnostic_criterion: 기저세포가 남아 있어야 관내암(없으면 침윤 사상암)
- 면포 괴사 — characteristic_nonspecific: 면포 괴사가 동반될 수 있음
- 기저세포 둘레 비율 — diagnostic_criterion: 관내암은 기저세포 둘레가 남아 있음
- 판정 체계 **관내암 진단 기준(Guo·Epstein)** (diagnostic)
  1. 관내암 — 고형 또는 조밀 사상 · 느슨한 사상·미세유두 + 핵이 정상의 6배 이상 · 면포 괴사
  2. 비정형 관내 증식 — 관내 비정형 증식이나 위 기준 미달

### 관 선암 (`dis_ductal_adenocarcinoma`)


### 고등급 전립선 상피내 종양 (`dis_hgpin`)

- 고등급 전립선 상피내 종양 — diagnostic_criterion: 기존 샘 안 분비 세포의 이형과 뚜렷한 핵소체 · 기저세포 유지
- 기저세포 유무 — diagnostic_criterion: 기저세포가 남아 있음
- 기저세포 둘레 비율 — diagnostic_criterion: HGPIN은 기저세포가 남아 있음(조각날 수 있음)
- AMACR 양성 면적 비율 — characteristic_nonspecific: HGPIN도 AMACR 양성일 수 있음(기저세포로 침윤암과 가름)

### 비정형 소선방 증식 (`dis_asap`)

- 글리슨 패턴 3 — characteristic_nonspecific: 암 같은 작은 샘이 소수 있으나 확진 기준에 못 미침

### 양성 전립선비대증 (`dis_bph`)

- 결절성 과형성 — diagnostic_criterion: 이행대의 샘·간질 결절

### 전립선염 (`dis_prostatitis`)

- 염증(전립선염) — diagnostic_criterion: 염증 세포 침윤

### 위축(양성) (`dis_atrophy_benign`)

- 위축 — diagnostic_criterion: 세포질이 줄어든 양성 샘 · 기저세포 유지
- 부분 위축 — characteristic_nonspecific: 부분 위축은 암을 모방

### 선증(비정형 선종성 과형성) (`dis_adenosis`)

- 선증(비정형 선종성 과형성) — diagnostic_criterion: 이행대의 작은 샘 결절 · 기저세포 조각

## 적용 관계

common_applied 68 · direct 36 · not_applicable 10 · not_investigated 5

