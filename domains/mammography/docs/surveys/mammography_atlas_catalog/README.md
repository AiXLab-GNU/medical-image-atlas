# 유방촬영 영상 지도 등록 표

유방촬영 영상 지도(웹 서비스 `packages/mammography-atlas-web`, 포트 8879)를 이루는 모든 데이터를 서로 참조되는 표로 모은 곳이다.
망막 지도(`domains/retinal`)와 같은 틀을 쓴다. 열 정의·키·관계는 [데이터 스키마](../../protocols/40_mammography_atlas_data_schema_v01_ko.md)에,
처음부터 다시 만드는 순서는 [재구축 절차](../../protocols/50_mammography_atlas_rebuild_runbook_v01_ko.md)에 있다. 읽기용 문서는
[조사 표 v01](../10_mammography_atlas_catalog_survey_v01_ko.md)이며 이 표에서 생성한다.

## 표 목록

"직접"은 사람이 고치는 정본이고, "생성"은 아래 갱신 순서로 다시 만드는 결과다. 생성 표는 손으로 고치지 않는다.

### A–E. 지식(무엇을 보고 무엇을 재는가)

| 파일 | 내용 | 작성 방식 |
| --- | --- | --- |
| `a_imaging_v01.csv` | A. 영상 종류(FFDM·DBT·CEM)와 표현(CC·MLO·ML·국소 압박·확대·DBT 단면·slab·합성 2D·CEM 저에너지·재조합) | 직접 작성 |
| `b_anatomy_v01.csv` | B. 위치 구역·조직층·구조·측정 기준(유두·후유두선·대흉근 경계·사분면·시계 방향·깊이 3구역) | 직접 작성 |
| `c_lesions_v01.csv` | C. 병변(BI-RADS 종괴·석회화 형태·구조왜곡·비대칭·동반 소견·치료 흔적·CEM 증강) | 직접 작성 |
| `bc_observations_v01.csv` | 관측: 대상 × 영상 표현 × 보이는 모습 × 해석 조건 × 근거 | 직접 작성 |
| `d_features_v01.csv` | D. 정성 특징·정량 측정(측정 61 + 판정 분류 1) | 직접 작성 |
| `d_common_feature_sets_v01.csv` | 병변 형태 분류(focal·cluster·region·linear·convergence·diffuse·device)별 공통 특징 | 직접 작성 |
| `d_applicability_overrides_v01.csv` | 대상별 공통 특징 적용·해당 없음 지정 | 직접 작성 |
| `d_feature_applicability_v01.csv` | 대상 × 특징 적용 관계 | 생성 |
| `e_diseases_v01.csv` | E. 질병(유방암과 아형, 양성 종괴·변화, 염증·치료 후, 림프절·혈관) | 직접 작성 |
| `e_disease_findings_v01.csv` | E. 질병–소견·측정 관계(관계 유형·분류 판본·조건·근거) | 직접 작성 |
| `e_grading_schemes_v01.csv` | E. 판정 체계(BI-RADS 범주·유방 구성·석회화 형태·분포·AJCC T·비대칭·CEM 배경 증강·대표 소견) | 직접 작성 |
| `e_grading_steps_v01.csv` | E. 판정 체계의 단계와 그 단계를 정하는 소견·측정 | 직접 작성 |
| `sources_v01.csv` | 정의·분류·근거 문헌과 서지 확인 상태(`src_*`, Europe PMC로 PMID 확인) | 직접 작성 |

### G. 영상 출처(정본)

| 파일 | 내용 | 작성 방식 |
| --- | --- | --- |
| `g_image_sources_v01.csv` | 영상을 준 데이터셋·논문(라이선스·서지·로컬 경로). DMID와 DBT·CEM 논문 4편(모두 CC BY 4.0) | 직접 작성 |
| `g_provider_figures_v01.csv` | 논문 그림 파일 8개(원본 파일명·SHA-256·PMC OA 주소·쓰는 생성기) | 직접 작성 |

### H. 영상 산출물

| 파일 | 내용 | 작성 방식 |
| --- | --- | --- |
| `h_masked_figures_v01.csv` | 항목 페이지 그림(원 영상·겹침·체크섬) | 생성 |
| `h_masked_figure_items_v01.csv` | 그림 × 그 그림이 보여 주는 항목 | 생성 |
| `h_measure_examples_v01.csv` | 측정 표시 예시 영상 | 생성 |
| `h_example_layers_v01.csv` | 예시의 표시 층(스위치 하나 = 층 하나) | 생성 |
| `h_example_values_v01.csv` | 층이 계산한 측정값(상태 ok·not_observed·not_evaluable·reading) | 생성 |

### I. 파생 관계

| 파일 | 내용 | 작성 방식 |
| --- | --- | --- |
| `i_feature_implementations_v01.csv` | 특징별 구현 수준(auto·mask·pair·reading·none)과 mammography-measures 함수 | 생성 |
| `i_measure_disease_links_v01.csv` | 측정 → 대상 질병(직접 또는 대상 항목 경유) | 생성 |
| `i_example_coverage_v01.csv` | 측정 × 영상 종류 × 예시 유무 | 생성 |

## 갱신 순서

medical-image-atlas 루트에서 실행한다.

```bash
M=domains/mammography
.venv/bin/python -B $M/code/build_mammography_atlas_catalog.py       # 적용 관계·읽기 문서·web atlas.json
.venv/bin/python -B $M/code/build_mammography_figures.py             # 항목 그림·측정 표시 예시(DMID + 논문 그림, 후자는 build_mammography_paper_examples.py)
.venv/bin/python -B $M/code/export_mammography_atlas_registry.py     # H·I 생성 표
.venv/bin/python -B $M/code/check_mammography_atlas_registry.py      # 키·참조·파일·체크섬·라이선스 검사
.venv/bin/python -B -m unittest discover -s $M/code/tests
```

## 규칙

- 지식 ID는 `img_*`·`ana_*`·`ref_*`·`zone_*`·`les_*`·`obs_*`·`ft_*`·`dis_*`·`rel_*`·`gs_*`·`st_*`·`src_*`이며 이름이 바뀌어도 유지한다.
- 관측 열은 `obs_ffdm`·`obs_dbt`·`obs_cem`이고 값은 `direct`·`limited`·`none`이다.
- 한 칸에 여러 값은 `;`로 구분한다. 서술 칸에서는 쉼표 대신 `·`를 쓴다.
- 공개하는 영상은 CC BY 4.0·CC0 1.0만 쓴다. CBIS-DDSM(CC BY 3.0)·VinDr-Mammo·EMBED·INbreast·BCS-DBT(CC BY-NC)는 쓰지 않는다.
- DMID에는 화소 간격이 없어 측정값은 화소 단위다. 환자 번호가 없어 CC·MLO 짝은 연속 번호의 같은 쪽 영상을 같은 유방으로 가정한 예시 하나만 둔다(캡션에 적음).
- 병변 그림의 색 영역은 공급자 전문가 ROI이고, 해부 그림(유방 경계·대흉근·치밀 조직·유두·후유두선·구역)은 서비스 자동 추정이다.
- `d_applicability_overrides`·`d_feature_applicability`에서 `feature_id`가 빈 행은 그 대상 전체에 대한 지정이다.
