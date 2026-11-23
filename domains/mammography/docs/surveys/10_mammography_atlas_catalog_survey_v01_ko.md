# 유방촬영 영상 지도 조사 표 v01

`code/build_mammography_atlas_catalog.py`가 등록 표에서 만든 읽기용 문서다. 손으로 고치지 않는다.

영상 종류 13 · 해부 28 · 병변 38 · 특징 62 · 질병 21 · 질병–소견 관계 74 · 판정 체계 10 · 근거 문헌 25

## A. 영상 종류

| ID | 이름 | 보이는 것 | 한계 |
| --- | --- | --- | --- |
| `img_ffdm` | 2D 디지털 유방촬영 | 종괴·석회화·구조왜곡·비대칭과 유방 실질 밀도 | 조직이 겹쳐 병변이 가려지거나 겹침 음영이 생김; 석회화 형태는 확대 촬영이 더 정확 |
| `img_ffdm_cc` | 두미 방향(CC) 영상 | 내측·외측 위치와 유두에서의 깊이 | 상하 위치는 MLO와 함께 봐야 함; 외측 끝과 액와 꼬리는 일부만 포함 |
| `img_ffdm_mlo` | 내외사위(MLO) 영상 | 대흉근·액와 꼬리를 포함한 상부와 하부 유방 전체 | 사선 투영이라 상하 위치가 실제와 조금 다름(ML 영상과 비교) |
| `img_ffdm_ml` | 내외측(ML·LM) 영상 | 병변의 실제 상하 위치·유즙 석회의 찻잔 모양 | 선별 검사의 표준 영상이 아님 |
| `img_spot_compression` | 국소 압박 영상 | 겹침 음영과 실제 병변의 구분·경계 평가 | 좁은 영역만 포함 |
| `img_magnification` | 확대 촬영 | 석회화의 형태·분포·개수 | 좁은 영역만 포함; 움직임 흐림에 약함 |
| `img_dbt` | 디지털 유방단층합성 | 겹침이 줄어든 종괴 경계와 구조왜곡 | 깊이 방향 해상도가 낮음; 석회화 군집이 여러 단면에 흩어짐 |
| `img_dbt_slice` | DBT 재구성 단면 | 한 깊이에서 본 병변 경계와 구조왜곡의 침상선 | 단면 밖 구조가 흐린 잔상으로 남음 |
| `img_dbt_slab` | DBT 두꺼운 단면(slab) | 석회화 군집 전체의 분포 | slab 두께에 따라 겹침이 다시 생김 |
| `img_synthetic_2d` | 합성 2D 영상 | DBT와 함께 보는 2D 비교 영상 | 석회화와 종괴의 모양이 FFDM과 다를 수 있음 |
| `img_cem` | 조영증강 유방촬영 | 조영 증강되는 병변(신생혈관)과 배경 실질 증강 | 조영제 부작용 위험; 시간에 따른 증강 정보는 제한적 |
| `img_cem_low_energy` | CEM 저에너지 영상 | 일반 FFDM과 같은 형태 정보(석회화·종괴) | 조영 증강은 보이지 않음 |
| `img_cem_recombined` | CEM 재조합(감산) 영상 | 요오드 분포(증강 병변과 배경 실질 증강) | 해부 구조가 지워져 위치는 저에너지 영상과 함께 봄; 감산 잡음 |

## B. 해부

| ID | 이름 | 정의 | FFDM·DBT·CEM |
| --- | --- | --- | --- |
| `ana_breast` | 유방 | 피부에서 흉벽 앞까지의 유방 조직 전체 | direct·direct·direct |
| `ana_upper_outer_quadrant` | 외상사분면 | 유두를 중심으로 위쪽·바깥쪽 1/4 구역(유방암이 가장 많이 생기는 곳) | direct·direct·direct |
| `ana_upper_inner_quadrant` | 내상사분면 | 유두를 중심으로 위쪽·안쪽 1/4 구역 | direct·direct·direct |
| `ana_lower_outer_quadrant` | 외하사분면 | 유두를 중심으로 아래쪽·바깥쪽 1/4 구역 | direct·direct·direct |
| `ana_lower_inner_quadrant` | 내하사분면 | 유두를 중심으로 아래쪽·안쪽 1/4 구역 | direct·direct·direct |
| `ana_subareolar_region` | 유륜하 영역 | 유두·유륜 바로 뒤 영역(BI-RADS 위치 서술의 한 구역) | direct·direct·direct |
| `ana_central_region` | 중앙부 | 유두 뒤 깊은 중앙 영역(사분면에 속하지 않는 위치) | direct·direct·direct |
| `ana_axillary_tail` | 액와 꼬리 | 외상사분면에서 액와 쪽으로 뻗은 유방 조직 | direct·direct·limited |
| `ana_nipple_areola` | 유두·유륜 | 유방 앞쪽 가운데의 유두와 둘레의 유륜 | direct·limited·limited |
| `ana_inframammary_fold` | 유방하주름 | 유방 아래 경계의 피부 주름(MLO에서 보이면 아래쪽까지 포함된 것) | direct·limited·limited |
| `ana_axilla` | 액와 | 겨드랑이 부위(림프절과 지방) | direct·limited·limited |
| `ana_axillary_lymph_nodes` | 액와 림프절 | 액와의 림프절(정상은 가운데 지방문이 있는 콩 모양) | direct·limited·limited |
| `ana_skin` | 피부 | 유방 표면의 얇은 띠(정상은 대개 2 mm 이하) | direct·direct·limited |
| `ana_subcutaneous_fat` | 피하 지방층 | 피부와 유선 실질 사이의 지방층 | direct·direct·limited |
| `ana_cooper_ligaments` | 쿠퍼 인대 | 실질에서 피부로 이어지는 얇은 섬유 띠(지방 안의 곡선 음영) | direct·direct·none |
| `ana_fibroglandular_tissue` | 유선 실질(섬유선 조직) | 유관·소엽과 섬유 기질로 이루어진 X선 밀도가 높은 조직 | direct·direct·direct |
| `ana_ducts` | 유관 | 유두로 모이는 젖샘관(정상은 거의 따로 보이지 않음) | limited·limited·none |
| `ana_tdlu` | 말단 유관 소엽 단위 | 소엽과 말단 유관(대부분의 유방암이 시작하는 곳; 영상에서 따로 보이지 않음) | none·none·none |
| `ana_breast_vessels` | 유방 혈관 | 유방 안을 지나는 동맥과 정맥(가늘고 긴 관 모양 음영) | direct·direct·limited |
| `ana_retromammary_fat` | 유방후 지방층 | 유선 실질과 대흉근 사이의 지방층 | direct·direct·limited |
| `ana_pectoralis_major` | 대흉근 | 유방 뒤 흉벽의 근육(MLO 위쪽 뒤에 삼각형으로 보임) | direct·direct·limited |
| `ana_chest_wall` | 흉벽 | 유방 뒤 경계(대흉근과 늑골) | limited·limited·none |
| `ref_nipple` | 유두 기준점 | 거리·시계 방향·깊이를 재는 기준점 | direct·direct·direct |
| `ref_posterior_nipple_line` | 후유두선 | 유두에서 대흉근 앞 경계(MLO) 또는 영상 뒤 끝(CC)까지 수직으로 그은 선 | direct·direct·limited |
| `ref_pectoral_edge` | 대흉근 앞 경계선 | MLO에서 대흉근과 유방 조직의 경계선 | direct·limited·none |
| `zone_quadrants` | 사분면 체계 | 유두를 중심으로 유방을 네 구역으로 나눔(CC로 안쪽·바깥쪽 · MLO로 위·아래) | direct·direct·direct |
| `zone_clock_face` | 시계 방향 위치 | 환자를 마주 본 시계 방향으로 위치를 적음(오른쪽 유방 바깥쪽 9시 · 왼쪽 유방 바깥쪽 3시) | direct·direct·direct |
| `zone_depth_thirds` | 깊이 3구역 | 후유두선을 셋으로 나눈 앞·중간·뒤 깊이 | direct·direct·direct |

## C. 병변

| ID | 묶음 | 이름 | 정의 | 감별 |
| --- | --- | --- | --- | --- |
| `les_mass` | 종괴 | 종괴 | 두 방향 영상 모두에서 보이고 바깥으로 볼록한 경계를 가진 3차원 병변 | 비대칭(볼록한 경계 없음) · 겹침 음영(국소 압박으로 사라짐) |
| `les_mass_circumscribed` | 종괴 | 경계가 분명한 종괴 | 경계의 75% 이상이 주변 조직과 뚜렷이 구분되는 종괴 | 낭종 · 섬유선종 · 점액암 · 유방 내 림프절 |
| `les_mass_indistinct` | 종괴 | 경계가 불분명한 종괴 | 경계 일부 또는 전체가 주변 조직과 섞여 구분되지 않는 종괴 | 가려진 경계(주변 조직에 덮임) · 겹침 음영 |
| `les_mass_spiculated` | 종괴 | 침상형 종괴 | 경계에서 가는 선(침상)이 바깥으로 방사상으로 뻗는 종괴 | 방사상 흉터 · 지방괴사 · 수술 후 흉터 |
| `les_fat_containing_mass` | 종괴 | 지방 함유 종괴 | 안에 지방 밀도가 있는 종괴(지방종 · 기름 낭종 · 과오종 · 유즙낭종) | 유방 내 림프절(지방문) |
| `les_intramammary_lymph_node` | 그 밖의 소견 | 유방 내 림프절 | 가운데 지방문이 있는 1 cm 이하의 콩 모양 종괴(주로 외상사분면 · 혈관 옆) | 경계가 분명한 종괴(지방문 없음) |
| `les_skin_lesion` | 그 밖의 소견 | 피부 병변 | 피부에 있는 사마귀·점 등이 유방 안 병변처럼 겹쳐 보이는 것(표지자로 확인) | 종괴 · 석회화(피부 석회화) |
| `les_solitary_dilated_duct` | 그 밖의 소견 | 단일 확장 유관 | 유두 뒤에서 한 개의 유관이 관 모양으로 넓어진 것 | 유관 확장증(양쪽 · 여러 유관) |
| `les_asymmetry` | 비대칭 | 비대칭 | 한 방향 영상에서만 보이는 섬유선 조직 음영(대부분 겹침 음영) | 겹침 음영 · 종괴 |
| `les_global_asymmetry` | 비대칭 | 전반적 비대칭 | 한 사분면 이상 넓은 범위에서 반대쪽보다 섬유선 조직이 많은 것 | 정상 변이 · 반대쪽 수술 후 변화 |
| `les_focal_asymmetry` | 비대칭 | 국소 비대칭 | 두 방향에서 보이나 한 사분면보다 작고 볼록한 경계가 없는 음영 | 종괴 · 정상 섬유선 섬 |
| `les_developing_asymmetry` | 비대칭 | 새로 생긴 비대칭 | 이전 검사보다 새로 생기거나 커지거나 더 뚜렷해진 국소 비대칭 | 호르몬 치료 · 체중 변화에 따른 실질 변화 |
| `les_architectural_distortion` | 구조왜곡 | 구조왜곡 | 종괴 없이 한 점에서 가는 선이 방사상으로 뻗거나 실질 가장자리가 당겨진 모양 | 수술 후 흉터 · 방사상 흉터 · 겹친 정상 구조 |
| `les_calcification` | 석회화(통합) | 석회화 | 유방 안 칼슘 침착(형태와 분포로 양성·의심을 가름) | 잡영 · 피부 표면 물질(데오도란트) |
| `les_calc_skin` | 전형적 양성 석회화 | 피부 석회화 | 가운데가 투명한 고리 모양의 피부 석회화(접선 영상으로 확인) | 실질 안 석회화 |
| `les_calc_vascular` | 전형적 양성 석회화 | 혈관 석회화 | 혈관 벽을 따라 평행한 두 줄(기찻길 모양)로 보이는 석회화 | 미세 선형 석회화(시작 부분이 짧으면 헷갈림) |
| `les_calc_coarse_popcorn` | 전형적 양성 석회화 | 거친(팝콘) 석회화 | 2–3 mm보다 큰 덩어리 석회화(퇴행한 섬유선종) | 거친 불균질 석회화(더 작고 불규칙) |
| `les_calc_large_rodlike` | 전형적 양성 석회화 | 큰 막대 모양 석회화 | 유관을 따라 유두를 향하는 1 mm 이상의 굵고 매끈한 막대(분비성 질환) | 미세 선형·분지형 석회화(가늘고 불규칙) |
| `les_calc_round_punctate` | 전형적 양성 석회화 | 둥근·점상 석회화 | 둥근 석회화(1 mm 미만은 점상 · 0.5 mm 미만은 점상으로 따로 부름) | 무정형 석회화(형태를 알 수 없을 만큼 작고 흐림) |
| `les_calc_rim` | 전형적 양성 석회화 | 테두리 석회화 | 둥근 구조의 표면을 따라 얇게 침착한 석회화(지방괴사 · 낭종 벽) | 피부 석회화 |
| `les_calc_dystrophic` | 전형적 양성 석회화 | 이영양성 석회화 | 수술·외상·방사선 치료 뒤 생기는 불규칙하고 큰 석회화(흔히 0.5 mm 이상) | 거친 불균질 석회화 |
| `les_calc_milk_of_calcium` | 전형적 양성 석회화 | 유즙 석회(칼슘유) | 작은 낭종 안에 가라앉은 칼슘(CC에서 흐린 둥근 점 · 옆 영상에서 찻잔 모양) | 무정형 석회화(옆 영상에서 모양이 안 바뀜) |
| `les_calc_suture` | 전형적 양성 석회화 | 봉합사 석회화 | 봉합사에 석회가 침착한 선형·매듭 모양 | 미세 선형 석회화 |
| `les_calc_amorphous` | 의심 석회화 | 무정형 석회화 | 형태를 특정할 수 없을 만큼 작고 흐린 석회화 | 점상 석회화 · 유즙 석회 |
| `les_calc_coarse_heterogeneous` | 의심 석회화 | 거친 불균질 석회화 | 0.5–1 mm 사이의 불규칙하고 뚜렷한 석회화(합쳐지는 경향) | 이영양성 석회화 · 퇴행 섬유선종 |
| `les_calc_fine_pleomorphic` | 의심 석회화 | 미세 다형성 석회화 | 0.5 mm 미만의 모양·크기가 서로 다른 석회화 | 무정형 석회화 · 점상 석회화 |
| `les_calc_fine_linear_branching` | 의심 석회화 | 미세 선형·분지형 석회화 | 가늘고 불규칙한 선 · 점선 · 가지 모양(유관 안 괴사 · 의심 정도가 가장 높음) | 큰 막대 모양 석회화 · 혈관 석회화 · 봉합사 석회화 |
| `les_skin_retraction` | 동반 소견 | 피부 함몰 | 피부가 안쪽으로 당겨진 것 | 수술 후 변화 |
| `les_nipple_retraction` | 동반 소견 | 유두 함몰 | 유두가 안쪽으로 당겨진 것(새로 생긴 경우 의미가 있음) | 선천성 · 오래된 양측 함몰 유두 |
| `les_skin_thickening` | 동반 소견 | 피부 비후 | 피부가 정상보다 두꺼워진 것(국소 또는 전체) | 방사선 치료 후 · 울혈성 심부전 · 유방염 |
| `les_trabecular_thickening` | 동반 소견 | 소주 비후 | 섬유 격벽(쿠퍼 인대 등)이 두꺼워져 그물 모양이 짙어진 것 | 부종 · 방사선 치료 후 |
| `les_axillary_adenopathy` | 동반 소견 | 액와 림프절 비대 | 지방문이 없어지거나 커지고 밀도가 높아진 액와 림프절 | 반응성 림프절 · 정상 큰 림프절(지방문 유지) |
| `les_postsurgical_scar` | 치료 흔적·기구 | 수술 후 흉터 | 수술 부위의 구조왜곡·피부 함몰·지방괴사(시간이 지나며 줄어듦) | 구조왜곡 · 재발암(커지거나 새 석회화) |
| `les_biopsy_marker` | 치료 흔적·기구 | 조직검사 표지자 | 조직검사 뒤 위치 표시로 남긴 금속 표지자 | 석회화 |
| `les_breast_implant` | 치료 흔적·기구 | 유방 보형물 | 유방 안 또는 근육 뒤의 보형물(실리콘·식염수) | — |
| `les_enhancing_mass` | 조영 증강(CEM) | 조영 증강 종괴 | CEM 재조합 영상에서 볼록한 경계를 가지고 증강되는 병변 | 배경 실질 증강 · 증강되는 양성 종괴(섬유선종) |
| `les_non_mass_enhancement` | 조영 증강(CEM) | 비종괴 증강 | 종괴의 볼록한 경계 없이 구역·선·분절 모양으로 증강되는 부위 | 배경 실질 증강 |
| `les_generic` | 공통 대상 | 병변 공통 | 여러 병변에 공통으로 쓰는 측정을 묶는 서비스 내부 대상 | — |

## D. 특징·측정

| ID | 대상 | 이름 | 유형 | 단위 | 영상 |
| --- | --- | --- | --- | --- | --- |
| `ft_breast_area` | 유방 | 유방 면적 | quantitative | mm2 또는 px2 | img_ffdm_cc img_ffdm_mlo |
| `ft_breast_composition` | 유방 | 유방 구성(밀도 범주) | qualitative | category(a–d) | img_ffdm_cc img_ffdm_mlo img_dbt_slice |
| `ft_percent_density` | 유방 | 유방 밀도 백분율 | quantitative | % | img_ffdm_cc img_ffdm_mlo |
| `ft_dense_area` | 유선 실질(섬유선 조직) | 치밀 조직 면적 | quantitative | mm2 또는 px2 | img_ffdm_cc img_ffdm_mlo |
| `ft_bpe_level` | 유선 실질(섬유선 조직) | 배경 실질 증강 정도 | qualitative | category | img_cem_recombined |
| `ft_skin_thickness` | 피부 | 피부 두께 | quantitative | mm | img_ffdm_cc img_ffdm_mlo |
| `ft_nipple_in_profile` | 유두·유륜 | 유두 측면 노출 | qualitative | presence | img_ffdm_cc img_ffdm_mlo |
| `ft_pectoral_area` | 대흉근 | 대흉근 면적 | quantitative | mm2 또는 px2 | img_ffdm_mlo |
| `ft_pectoral_angle` | 대흉근 | 대흉근 각도 | quantitative | ° | img_ffdm_mlo |
| `ft_pectoral_reaches_pnl` | 대흉근 | 대흉근이 후유두선 높이까지 보임 | qualitative | presence | img_ffdm_mlo |
| `ft_pnl_length` | 후유두선 | 후유두선 길이 | quantitative | mm 또는 px | img_ffdm_cc img_ffdm_mlo |
| `ft_pnl_cc_mlo_difference` | 후유두선 | CC·MLO 후유두선 길이 차이 | quantitative | mm | img_ffdm_cc img_ffdm_mlo |
| `ft_imf_visible` | 유방하주름 | 유방하주름 노출 | qualitative | presence | img_ffdm_mlo |
| `ft_ln_long_axis` | 액와 림프절 | 림프절 긴 지름 | quantitative | mm | img_ffdm_mlo |
| `ft_ln_fatty_hilum` | 액와 림프절 | 림프절 지방문 | qualitative | presence | img_ffdm_mlo |
| `ft_ln_density` | 액와 림프절 | 림프절 밀도 | qualitative | category | img_ffdm_mlo |
| `ft_mass_shape` | 종괴 | 종괴 모양 | qualitative | category | img_ffdm_cc img_ffdm_mlo img_dbt_slice |
| `ft_mass_margin` | 종괴 | 종괴 경계 | qualitative | category | img_ffdm_cc img_ffdm_mlo img_spot_compression img_dbt_slice |
| `ft_mass_density` | 종괴 | 종괴 밀도 | qualitative | category | img_ffdm_cc img_ffdm_mlo |
| `ft_mass_size` | 종괴 | 종괴 크기(최대 지름) | quantitative | mm 또는 px | img_ffdm_cc img_ffdm_mlo img_dbt_slice |
| `ft_mass_area` | 종괴 | 종괴 면적 | quantitative | mm2 또는 px2 | img_ffdm_cc img_ffdm_mlo img_dbt_slice |
| `ft_mass_circularity` | 종괴 | 종괴 원형도 | quantitative | index(0–1) | img_ffdm_cc img_ffdm_mlo img_dbt_slice |
| `ft_mass_solidity` | 종괴 | 종괴 볼록도 | quantitative | ratio(0–1) | img_ffdm_cc img_ffdm_mlo img_dbt_slice |
| `ft_mass_radial_sd` | 종괴 | 종괴 반지름 변동 | quantitative | index | img_ffdm_cc img_ffdm_mlo img_dbt_slice |
| `ft_mass_spiculation_index` | 종괴 | 침상 지수 | quantitative | ratio(0–1) | img_ffdm_cc img_ffdm_mlo img_dbt_slice |
| `ft_mass_margin_sharpness` | 종괴 | 경계 선명도 | quantitative | index | img_ffdm_cc img_ffdm_mlo img_spot_compression |
| `ft_mass_contrast` | 종괴 | 종괴 대비 | quantitative | index | img_ffdm_cc img_ffdm_mlo |
| `ft_calc_morphology` | 석회화 | 석회화 형태 | qualitative | category | img_magnification img_ffdm_cc img_ffdm_mlo |
| `ft_calc_distribution` | 석회화 | 석회화 분포 | qualitative | category | img_magnification img_ffdm_cc img_ffdm_mlo img_dbt_slab |
| `ft_calc_count` | 석회화 | 석회화 개수 | quantitative | count | img_magnification img_ffdm_cc img_ffdm_mlo img_dbt_slab |
| `ft_calc_extent` | 석회화 | 석회화 범위 | quantitative | mm 또는 px | img_magnification img_ffdm_cc img_ffdm_mlo img_dbt_slab |
| `ft_calc_density` | 석회화 | 석회화 밀집도 | quantitative | count/area | img_magnification img_ffdm_cc img_ffdm_mlo |
| `ft_calc_size` | 석회화 | 석회화 크기 | quantitative | mm2 또는 px2 | img_magnification img_ffdm_cc img_ffdm_mlo |
| `ft_calc_size_variation` | 석회화 | 석회화 크기 다양성 | quantitative | ratio | img_magnification img_ffdm_cc img_ffdm_mlo |
| `ft_calc_elongation` | 석회화 | 석회화 길쭉함 | quantitative | ratio | img_magnification img_ffdm_cc img_ffdm_mlo |
| `ft_calc_branching` | 석회화 | 석회화 분지 비율 | quantitative | ratio | img_magnification |
| `ft_calc_linearity` | 석회화 | 석회화 배열 선형성 | quantitative | index(0–1) | img_magnification img_ffdm_cc img_ffdm_mlo |
| `ft_calc_nn_distance` | 석회화 | 석회화 최근접 거리 | quantitative | mm 또는 px | img_magnification img_ffdm_cc img_ffdm_mlo |
| `ft_calc_contrast` | 석회화 | 석회화 대비 | quantitative | index | img_magnification img_ffdm_cc img_ffdm_mlo |
| `ft_ad_presence` | 구조왜곡 | 구조왜곡 유무 | qualitative | presence | img_ffdm_cc img_ffdm_mlo img_dbt_slice |
| `ft_ad_convergence_index` | 구조왜곡 | 침상선 수렴 지수 | quantitative | ratio(0–1) | img_ffdm_cc img_ffdm_mlo img_dbt_slice |
| `ft_ad_extent` | 구조왜곡 | 구조왜곡 범위 | quantitative | mm 또는 px | img_ffdm_cc img_ffdm_mlo img_dbt_slice |
| `ft_asym_type` | 비대칭 | 비대칭 유형 | qualitative | category | img_ffdm_cc img_ffdm_mlo |
| `ft_asym_bilateral_difference` | 비대칭 | 좌우 치밀 조직 차이 | quantitative | % 또는 mm2 | img_ffdm_cc img_ffdm_mlo |
| `ft_asym_area` | 국소 비대칭 | 국소 비대칭 면적 | quantitative | mm2 또는 px2 | img_ffdm_cc img_ffdm_mlo |
| `ft_enh_intensity_ratio` | 조영 증강 종괴 | 증강 강도 비 | quantitative | ratio | img_cem_recombined |
| `ft_enh_pattern` | 조영 증강 종괴 | 내부 증강 양상 | qualitative | category | img_cem_recombined |
| `ft_lesion_conspicuity` | 조영 증강 종괴 | 병변 뚜렷함 | qualitative | category | img_cem_recombined |
| `ft_nme_distribution` | 비종괴 증강 | 비종괴 증강 분포 | qualitative | category | img_cem_recombined |
| `ft_nme_extent` | 비종괴 증강 | 비종괴 증강 범위 | quantitative | mm 또는 px | img_cem_recombined |
| `ft_lesion_generic_presence` | 병변 공통 | 소견 유무 | qualitative | presence | img_ffdm_cc img_ffdm_mlo img_dbt_slice img_cem_recombined |
| `ft_lesion_generic_count` | 병변 공통 | 소견 개수 | quantitative | count | img_ffdm_cc img_ffdm_mlo |
| `ft_lesion_generic_size` | 병변 공통 | 소견 크기(최대 지름) | quantitative | mm 또는 px | img_ffdm_cc img_ffdm_mlo img_dbt_slice img_cem_recombined |
| `ft_lesion_distance_nipple` | 병변 공통 | 유두에서의 거리 | quantitative | mm 또는 px | img_ffdm_cc img_ffdm_mlo |
| `ft_lesion_depth_third` | 병변 공통 | 깊이 구역 | qualitative | category | img_ffdm_cc img_ffdm_mlo |
| `ft_lesion_view_half` | 병변 공통 | 한 방향 영상의 위치(절반) | qualitative | category | img_ffdm_cc img_ffdm_mlo |
| `ft_lesion_quadrant` | 병변 공통 | 사분면 위치 | qualitative | category | img_ffdm_cc img_ffdm_mlo |
| `ft_lesion_clock_position` | 병변 공통 | 시계 방향 위치 | qualitative | category | img_ffdm_cc img_ffdm_mlo |
| `ft_lesion_two_view` | 병변 공통 | 두 방향에서 보임 | qualitative | presence | img_ffdm_cc img_ffdm_mlo |
| `ft_lesion_generic_change` | 병변 공통 | 이전 검사 대비 변화 | quantitative | mm 또는 개수 차이 | img_ffdm_cc img_ffdm_mlo |
| `ft_img_positioning_quality` | img_ffdm | 촬영 자세 품질 | qualitative | category | img_ffdm_cc img_ffdm_mlo |
| `ft_birads_assessment` | 병변 공통 | BI-RADS 최종 판정 범주 | qualitative | category(0–6) | img_ffdm_cc img_ffdm_mlo img_dbt_slice img_cem_recombined |

## E. 질병과 판정 체계

### 유방암 (`dis_breast_cancer`)

- BI-RADS 최종 판정 범주 — diagnostic_criterion: 가장 의심스러운 소견으로 0–6 범주를 정함 · 4·5는 조직검사 권고
- 침상형 종괴 — diagnostic_criterion: 침상형 불규칙 종괴는 악성 가능성이 높은 소견
- 종괴 경계 — diagnostic_criterion: 경계 서술 중 침상·불분명·미세 분엽은 의심 소견
- 종괴 모양 — diagnostic_criterion: 불규칙형은 의심 소견
- 종괴 밀도 — characteristic_nonspecific: 고밀도 종괴는 의심 정도를 조금 높임 · 지방 함유는 양성
- 구조왜곡 — diagnostic_criterion: 수술 이력 없는 구조왜곡은 조직검사 대상
- 새로 생긴 비대칭 — diagnostic_criterion: 새로 생긴 비대칭은 추가 검사 후 남으면 조직검사 고려
- 석회화 형태 — diagnostic_criterion: 미세 선형·분지형과 미세 다형성이 가장 의심스러운 형태
- 석회화 분포 — diagnostic_criterion: 선형·분절성 분포는 유관을 따른 병변을 시사
- 종괴 크기(최대 지름) — severity_classification: 종양 최대 지름으로 T 병기를 나눔(영상 크기는 임상 병기의 근거)
- 피부 비후 — severity_classification: 피부 침범(부종·궤양·위성 결절)은 T4
- 액와 림프절 비대 — severity_classification: 액와 림프절 전이는 N 병기
- 유방 구성(밀도 범주) — prognostic: 치밀 유방(c·d)은 병변을 가리고 유방암 위험이 높음
- 유방 밀도 백분율 — prognostic: 밀도 백분율이 높을수록 유방암 위험이 커짐(75% 이상은 10% 미만보다 약 4–5배)
- 시계 방향 위치 — characteristic_nonspecific: 위치는 좌우·시계 방향·유두에서의 거리로 기록
- 유두에서의 거리 — characteristic_nonspecific: 유두에서의 거리로 위치를 기록
- 조영 증강 종괴 — diagnostic_criterion: CEM에서 증강되는 종괴는 의심 소견
- 비종괴 증강 — diagnostic_criterion: 분절·선형 비종괴 증강은 DCIS를 시사
- 배경 실질 증강 정도 — prognostic: 배경 실질 증강이 높으면 병변이 가려질 수 있음
- 증강 강도 비 — characteristic_nonspecific: 악성 병변은 대체로 주변보다 강하게 증강
- 침상 지수 — characteristic_nonspecific: 침상 지수는 침상 경계의 정량 근사(연구 지표)
- 종괴 원형도 — characteristic_nonspecific: 원형도·볼록도가 낮을수록 불규칙(연구 지표)
- 이전 검사 대비 변화 — activity_monitoring: 이전 검사와 비교해 새로 생기거나 커진 소견은 의심 정도를 높임
- 침상선 수렴 지수 — characteristic_nonspecific: 침상선 수렴 지수(구조왜곡 검출의 연구 지표)
- 좌우 치밀 조직 차이 — characteristic_nonspecific: 좌우 치밀 조직 차이(전반적 비대칭의 근사)
- 판정 체계 **BI-RADS 최종 판정 범주** (diagnostic)
  1. 범주 6 · 조직검사로 확진된 악성 — 치료 전 조직검사로 악성이 확인된 병변
  2. 범주 5 · 악성 가능성 매우 높음(95% 이상) — 침상형 불규칙 종괴 · 미세 선형·분지형 석회화의 선형·분절 분포 · 위 두 소견의 동반
  3. 범주 4 · 의심(2–95%) — 불규칙 또는 경계 불분명 종괴 · 의심 형태 석회화(무정형 · 거친 불균질 · 미세 다형성) · 수술 이력 없는 구조왜곡 · 새로 생긴 비대칭
  4. 범주 3 · 양성 가능성 높음(2% 이하) — 기준선 검사의 경계 분명 비석회화 종괴 · 국소 비대칭 · 둥근·점상 석회화의 단일 군집
  5. 범주 2 · 양성 — 지방 함유 종괴(기름 낭종 · 지방종 · 과오종) · 전형적 양성 석회화 · 유방 내 림프절 · 보형물 · 수술 흉터
  6. 범주 1 · 음성 — 적을 소견 없음
  7. 범주 0 · 추가 영상 필요 — 국소 압박·확대 촬영·초음파 등으로 확인이 필요함 · 이전 검사와 비교가 필요함
- 판정 체계 **유방 구성 범주(BI-RADS 밀도)** (typing)
  1. d · 매우 치밀 — 섬유선 조직이 매우 많아 유방촬영의 민감도가 낮음
  2. c · 불균질하게 치밀 — 치밀한 부분이 작은 종괴를 가릴 수 있음
  3. b · 흩어진 섬유선 조직 — 섬유선 조직이 흩어져 있음
  4. a · 거의 지방 — 유방 대부분이 지방
- 판정 체계 **석회화 형태의 의심 단계** (typing)
  1. 미세 선형·분지형 — 가늘고 불규칙한 선·가지 모양(양성예측도 약 70%)
  2. 미세 다형성 — 0.5 mm 미만의 모양·크기가 다른 석회화(약 29%)
  3. 무정형 — 형태를 알 수 없이 작고 흐림(약 21%)
  4. 거친 불균질 — 0.5–1 mm 불규칙하고 뚜렷함(약 13%)
  5. 전형적 양성 — 피부 · 혈관 · 팝콘 · 큰 막대 · 둥근 · 테두리 · 이영양성 · 유즙 석회 · 봉합사
- 판정 체계 **석회화 분포** (typing)
  1. 분절성 — 한 유관 가지를 따라 삼각형으로 퍼짐
  2. 선형 — 한 줄로 늘어섬(유관 안)
  3. 군집 — 1 cm 안팎의 작은 범위(가장 긴 길이 2 cm 이하)에 모임
  4. 구역성 — 2 cm보다 넓은 범위에 퍼짐(유관 분포를 따르지 않음)
  5. 미만성 — 양쪽 유방 전체에 흩어짐(대개 양성)
- 판정 체계 **AJCC 8판 원발 종양(T) 병기** (staging)
  1. T4 · 흉벽·피부 침범 — 흉벽 침범(T4a) · 피부 궤양·위성 결절·부종(T4b) · T4a와 T4b 동반(T4c) · 염증성 유방암(T4d)
  2. T3 — 최대 지름 50 mm 초과
  3. T2 — 최대 지름 20 mm 초과 50 mm 이하
  4. T1c — 최대 지름 10 mm 초과 20 mm 이하
  5. T1b — 최대 지름 5 mm 초과 10 mm 이하
  6. T1a — 최대 지름 1 mm 초과 5 mm 이하
  7. T1mi — 최대 지름 1 mm 이하의 미세 침윤
  8. Tis — 상피내암(DCIS) 또는 유두 파제트병
- 판정 체계 **비대칭 유형과 의미** (typing)
  1. 새로 생긴 비대칭 — 이전 검사보다 새로 생기거나 커지거나 뚜렷해짐
  2. 국소 비대칭 — 두 방향에서 보이나 한 사분면보다 작고 볼록한 경계가 없음
  3. 전반적 비대칭 — 한 사분면 이상 넓은 범위에서 반대쪽보다 조직이 많음
  4. 비대칭 — 한 방향 영상에서만 보임
- 판정 체계 **CEM 배경 실질 증강 수준** (typing)
  1. 고도(marked) — 정상 실질 대부분이 강하게 증강
  2. 중등도(moderate) — 정상 실질의 상당 부분이 증강
  3. 경도(mild) — 정상 실질 일부가 약하게 증강
  4. 최소(minimal) — 증강이 거의 없음

### 침윤성 유방암(비특수형) (`dis_idc`)

- 침상형 종괴 — characteristic_nonspecific: 불규칙 침상형 고밀도 종괴가 전형
- 석회화 형태 — characteristic_nonspecific: 동반 미세 석회화(관내 성분)

### 침윤성 소엽암 (`dis_ilc`)

- 구조왜곡 — characteristic_nonspecific: 구조왜곡으로 보이는 경우가 많음
- 국소 비대칭 — characteristic_nonspecific: 한 방향에서만 보이는 비대칭으로 나타날 수 있음
- 두 방향에서 보임 — characteristic_nonspecific: CC에서만 보이는 경우가 흔함

### 관상피내암 (`dis_dcis`)

- 미세 다형성 석회화 — diagnostic_criterion: 미세 다형성 석회화(군집·선형·분절)
- 미세 선형·분지형 석회화 — diagnostic_criterion: 미세 선형·분지형 석회화(고등급 DCIS의 괴사형 석회화)
- 무정형 석회화 — characteristic_nonspecific: 무정형 석회화(저등급 DCIS 또는 양성)
- 석회화 분포 — diagnostic_criterion: 선형·분절성 분포는 유관 안 확산
- 석회화 범위 — severity_classification: 석회화 범위가 절제 범위 계획에 쓰임(실제 범위보다 작게 잴 수 있음)
- 석회화 개수 — characteristic_nonspecific: 군집 석회화 개수(연구 지표)

### 점액암 (`dis_mucinous_carcinoma`)

- 경계가 분명한 종괴 — characteristic_nonspecific: 경계 분명 또는 미세 분엽 종괴

### 염증성 유방암 (`dis_inflammatory_breast_cancer`)

- 피부 비후 — diagnostic_criterion: 피부 비후와 부종(T4d는 임상 진단)
- 소주 비후 — characteristic_nonspecific: 소주 비후·전반적 밀도 증가

### 유두 파제트병 (`dis_paget_nipple`)

- 유두 함몰 — characteristic_nonspecific: 유두·유륜 변화 · 유륜하 석회화가 동반될 수 있음

### 섬유선종 (`dis_fibroadenoma`)

- 경계가 분명한 종괴 — characteristic_nonspecific: 경계 분명 타원형 종괴
- 거친(팝콘) 석회화 — diagnostic_criterion: 팝콘 석회화는 퇴행 섬유선종의 전형(범주 2)
- 종괴 모양 — characteristic_nonspecific: 타원형
- 판정 체계 **섬유선종의 대표 소견** (representative)
  1. 전형 — 경계 분명 · 타원형
  2. 퇴행 — 거친 팝콘 석회화

### 유방 낭종 (`dis_breast_cyst`)

- 경계가 분명한 종괴 — characteristic_nonspecific: 경계 분명 둥근·타원형 종괴(초음파로 낭종 확인)
- 테두리 석회화 — characteristic_nonspecific: 낭종 벽 테두리 석회화

### 섬유낭성 변화 (`dis_fibrocystic_change`)

- 유즙 석회(칼슘유) — diagnostic_criterion: 유즙 석회(옆 영상의 찻잔 모양)는 양성
- 둥근·점상 석회화 — characteristic_nonspecific: 둥근·점상 석회화
- 유방 구성(밀도 범주) — characteristic_nonspecific: 치밀 실질이 흔함

### 엽상 종양 (`dis_phyllodes_tumor`)

- 종괴 크기(최대 지름) — characteristic_nonspecific: 큰 종괴(빠른 증가)
- 경계가 분명한 종괴 — characteristic_nonspecific: 경계 분명 분엽형 종괴

### 유관 내 유두종 (`dis_intraductal_papilloma`)

- 단일 확장 유관 — characteristic_nonspecific: 단일 확장 유관
- 종괴 — characteristic_nonspecific: 유륜하 작은 종괴

### 방사상 흉터(복합 경화성 병변) (`dis_radial_scar`)

- 구조왜곡 — characteristic_nonspecific: 가운데가 투명하고 침상선이 긴 구조왜곡(암과 영상만으로 구분 불가)

### 지방괴사 (`dis_fat_necrosis`)

- 테두리 석회화 — diagnostic_criterion: 기름 낭종의 테두리 석회화
- 지방 함유 종괴 — diagnostic_criterion: 기름 낭종(지방 함유 종괴)
- 이영양성 석회화 — characteristic_nonspecific: 이영양성 석회화
- 침상형 종괴 — characteristic_nonspecific: 침상형 종괴처럼 보여 암과 헷갈릴 수 있음
- 판정 체계 **지방괴사의 대표 소견** (representative)
  1. 초기 — 경계 불분명 종괴 · 침상형 종괴(암과 헷갈림)
  2. 기름 낭종 — 얇은 벽의 지방 함유 종괴
  3. 후기 — 테두리 석회화 · 이영양성 석회화

### 지방종 (`dis_lipoma`)

- 지방 함유 종괴 — diagnostic_criterion: 얇은 피막의 지방 밀도 종괴(범주 2)

### 과오종 (`dis_hamartoma`)

- 지방 함유 종괴 — diagnostic_criterion: 지방과 실질이 섞인 피막 종괴(범주 2)

### 유방염·농양 (`dis_mastitis_abscess`)

- 피부 비후 — characteristic_nonspecific: 피부 비후
- 소주 비후 — characteristic_nonspecific: 소주 비후
- 경계가 불분명한 종괴 — characteristic_nonspecific: 농양은 경계 불분명 종괴

### 유관 확장증(분비성 질환) (`dis_duct_ectasia`)

- 큰 막대 모양 석회화 — diagnostic_criterion: 유관을 따라 유두를 향하는 큰 막대 모양 석회화(범주 2)
- 단일 확장 유관 — characteristic_nonspecific: 확장된 유관

### 액와 림프절병증 (`dis_axillary_lymphadenopathy`)

- 액와 림프절 비대 — diagnostic_criterion: 지방문이 없어지고 커지며 짙어진 림프절
- 림프절 지방문 — diagnostic_criterion: 지방문 소실이 가장 중요한 소견
- 림프절 긴 지름 — characteristic_nonspecific: 크기 증가(지방문이 있으면 큰 림프절도 정상일 수 있음)
- 림프절 밀도 — characteristic_nonspecific: 밀도 증가
- 판정 체계 **액와 림프절의 대표 소견** (representative)
  1. 의심 — 지방문 소실 · 커지고 둥글어짐 · 밀도 증가
  2. 정상 — 가운데 지방문이 있는 콩 모양

### 유방 동맥 석회화 (`dis_breast_arterial_calcification`)

- 혈관 석회화 — diagnostic_criterion: 혈관 벽을 따른 평행 석회화(유방암과 무관 · 범주 2)

### 수술·치료 후 변화 (`dis_post_treatment_change`)

- 수술 후 흉터 — diagnostic_criterion: 수술 부위 구조왜곡·흉터(이전 검사와 비교해 줄어듦)
- 이영양성 석회화 — characteristic_nonspecific: 이영양성 석회화
- 봉합사 석회화 — characteristic_nonspecific: 봉합사 석회화
- 피부 두께 — activity_monitoring: 방사선 치료 후 피부 두께가 늘었다가 서서히 줄어듦
- 이전 검사 대비 변화 — activity_monitoring: 흉터가 커지거나 새 석회화가 생기면 재발을 의심

## 적용 관계

common_applied 293 · direct 62 · not_applicable 17 · not_investigated 7

