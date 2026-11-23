# 유방촬영 영상 지도 데이터 스키마 v01

작성: 2026-11-23 · 대상: `domains/mammography/docs/surveys/mammography_atlas_catalog/` 23개 표

망막 지도 스키마(`domains/retinal/docs/protocols/40_retinal_atlas_data_schema_v01_ko.md`)와 같은 구조다. 다른 점만 적는다.

## 관계

```text
A 영상(img_*) ──< B 해부(ana_*·ref_*·zone_*) ──< C 병변(les_*)       ← bc 관측(obs_*)이 대상 × 영상 표현을 잇는다
        │                │                        │
        └──────< D 특징(ft_*) >───────────────────┘   target_id = 해부·병변·영상 하나
                     │
E 질병(dis_*) ──< E 관계(rel_*) : finding_id = 해부·병변·특징
        └──< 판정 체계(gs_*) ──< 단계(st_*) : finding_ids = 해부·병변·특징
G 영상 출처(source_id) ──< H 그림·예시·층·값 ──> I 구현·질병 연결·예시 유무
mammography-measures registry : feature_id → 함수·입력(image·image_pair·lesion_mask·lesion_landmark·matched_views)
```

## 망막과 다른 열·값

| 표 | 열 | 값 |
| --- | --- | --- |
| B·C | `obs_ffdm`·`obs_dbt`·`obs_cem` | `direct`·`limited`·`none` |
| B | `map_axis` | `face`(위치 구역) · `tissue`(피부→흉벽 층) · `reference`(측정 기준) |
| B | `measure_class` | `region`·`zone`·`structure`·`layer`·`tissue`·`boundary`·`reference` |
| C | `lesion_group` | `mass`·`calcification`·`calcification_benign`·`calcification_suspicious`·`distortion`·`asymmetry`·`other_finding`·`associated`·`treatment`·`enhancement`·`aggregate` |
| C | `morphology_class` | `focal`·`cluster`·`region`·`linear`·`convergence`·`diffuse`·`device` |
| C | `depth_ko` | 생기는 곳(실질·지방·피부·유관 등) |
| D | `feature_role` | `measurement`(측정 목록) · `classification`(BI-RADS 최종 범주처럼 판정 결과) |
| I | `level` | `auto`(영상만) · `mask`(병변 mask) · `pair`(영상 쌍) · `reading`(정성 판독) · `none` |
| H | 값 `status` | `ok`·`not_observed`·`not_evaluable`·`reading`(판독 층, 함수 없음) |

## 불변 조건(검사기가 확인)

- 모든 키는 표 안에서 유일하고, 외래 키는 `SCHEMA`에 적은 도메인에 있다(`check_mammography_atlas_registry.py`).
- 영상 출처 라이선스는 CC BY 4.0 또는 CC0 1.0.
- H 그림 파일이 있고 SHA-256이 표와 같다. 판독 층(`status=reading`)만 함수가 비어 있다.
- mammography-measures 레지스트리가 가리키는 특징은 모두 D에 있다.
- 생성 표(H·I·`d_feature_applicability`)는 현재 웹 데이터로 다시 만든 결과와 같다.
