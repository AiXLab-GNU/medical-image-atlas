# 병리 영상 지도 데이터 스키마 v01

작성: 2026-11-23 · 대상: `domains/pathology/docs/surveys/pathology_atlas_catalog/` 25개 표

유방촬영 지도 스키마(`domains/mammography/docs/protocols/40_mammography_atlas_data_schema_v01_ko.md`)와 같은 구조다. 다른 점만 적는다.

| 표 | 열 | 값 |
| --- | --- | --- |
| B·C | `obs_he`·`obs_ihc` | `direct`·`limited`·`none` |
| B | `map_axis` | `face`(구역·구조) · `tissue`(샘·간질) · `cell`(핵·핵소체) · `reference`(조직 면적·화소 크기·HPF) |
| C | `lesion_group` | `carcinoma`·`gleason_pattern`·`gleason_architecture`·`intraductal`·`invasion`·`benign_mimic`·`benign_change`·`artifact`·`aggregate` |
| C | `morphology_class` | `region`(면적으로 재는 병변) · `gland`(샘 단위) · `focal`(신경주위·림프혈관 침범) |
| D | `feature_role` | `measurement` · `classification`(글리슨 점수·ISUP 등급군) |
| I | `level` | `auto`(영상만) · `mask`(주석·mask 입력) · `reading`(판독) · `none` |
| G | `kind` | `dataset` · `article`(CC BY 논문, 그림 원본은 `g_provider_figures`) |
| H | `h_masked_figures.kind` | `masked`(데이터셋 영상 + 주석·추정 표시) · `paper`(논문 패널, `overlay_file` 빈칸) |
| I | `i_measure_validation` | 검사 하나당 한 행: 함수·정답(주석)·나눔(조정/검증)·사례·지표·값·결정(채택 여부) |
| H | 값 `status` | `ok`·`not_observed`·`not_evaluable`·`reading` |

측정 함수 입력 종류(`pathology_measures.registry`): `image` · `label_map`(화소별 주석 지도) · `region_mask` · `pattern_mask` · `ihc_region` · `reader_labels`.
불변 조건은 유방촬영과 같다(키 유일·외래 키·라이선스·파일 SHA-256·판독 층만 함수 없음·생성 표 최신).
