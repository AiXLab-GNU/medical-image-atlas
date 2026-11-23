# 병리 영상 지도 데이터 스키마 v01

작성: 2026-11-23 · 대상: `domains/pathology/docs/surveys/pathology_atlas_catalog/` 23개 표

유방촬영 지도 스키마(`domains/mammography/docs/protocols/40_mammography_atlas_data_schema_v01_ko.md`)와 같은 구조다. 다른 점만 적는다.

| 표 | 열 | 값 |
| --- | --- | --- |
| B·C | `obs_he`·`obs_ihc` | `direct`·`limited`·`none` |
| B | `map_axis` | `face`(구역·구조) · `tissue`(샘·간질) · `cell`(핵·핵소체) · `reference`(조직 면적·화소 크기·HPF) |
| C | `lesion_group` | `carcinoma`·`gleason_pattern`·`gleason_architecture`·`intraductal`·`invasion`·`benign_mimic`·`benign_change`·`artifact`·`aggregate` |
| C | `morphology_class` | `region`(면적으로 재는 병변) · `gland`(샘 단위) · `focal`(신경주위·림프혈관 침범) |
| D | `feature_role` | `measurement` · `classification`(글리슨 점수·ISUP 등급군) |
| I | `level` | `auto`(영상만) · `mask`(주석·mask 입력) · `reading`(판독) · `none` |
| H | 값 `status` | `ok`·`not_observed`·`not_evaluable`·`reading` |

측정 함수 입력 종류(`pathology_measures.registry`): `image` · `label_map`(화소별 주석 지도) · `region_mask` · `pattern_mask`.
불변 조건은 유방촬영과 같다(키 유일·외래 키·라이선스·파일 SHA-256·판독 층만 함수 없음·생성 표 최신).
