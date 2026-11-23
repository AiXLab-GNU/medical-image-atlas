# 망막 영상 지도 등록 표

망막 영상 지도(웹 서비스 `packages/retinal-atlas-web`)를 이루는 모든 데이터를 서로 참조되는 표로 모은 곳이다.
[조사 범위](../../concept/40_retinal_atlas_survey_scope_v01_ko.md)를 따르고, 열 정의·키·관계 전체는
[데이터 스키마](../../protocols/40_retinal_atlas_data_schema_v01_ko.md)에, 처음부터 다시 만드는 순서는
[재구축 절차](../../protocols/50_retinal_atlas_rebuild_runbook_v01_ko.md)에 있다. 읽기용 문서는
[조사 표 v01](../10_retinal_atlas_catalog_survey_v01_ko.md)이며 이 표에서 생성한다.

## 표 목록

"직접"은 사람이 고치는 정본이고, "생성"은 아래 갱신 순서로 다시 만드는 결과다. 생성 표는 손으로 고치지 않는다.

### A–F. 지식(무엇을 보고 무엇을 재는가)

| 파일 | 내용 | 작성 방식 |
| --- | --- | --- |
| `a_imaging_v01.csv` | A. 영상 종류(modality)와 표현(representation) | 직접 작성 |
| `b_anatomy_v01.csv` | B. 위치 기준·구역·해부 구조 | 직접 작성 |
| `c_lesions_v01.csv` | C. 병변·소견(집계형 대상 포함) | 직접 작성 |
| `bc_observations_v01.csv` | 관측: 대상 × 영상 표현 × 직접 보이는 것 × 해석 조건 × 근거 | 직접 작성 |
| `d_features_v01.csv` | D. 정성 특징·정량 측정(측정 160 + 판정 분류 3) | 직접 작성 |
| `d_common_feature_sets_v01.csv` | 형태 분류(병변)·측정 분류(해부)별 공통 특징 | 직접 작성 |
| `d_applicability_overrides_v01.csv` | 대상별 공통 특징 적용·해당 없음·미조사 지정 | 직접 작성 |
| `d_feature_applicability_v01.csv` | 대상 × 특징 적용 관계(직접·공통 적용·해당 없음·미조사) | 생성 |
| `e_diseases_v01.csv` | E. 질병 | 직접 작성 |
| `e_disease_findings_v01.csv` | E. 질병–소견·측정 관계(관계 유형·분류 판본·조건·근거) | 직접 작성 |
| `e_grading_schemes_v01.csv` | E. 질병별 판정·등급 체계 | 직접 작성 |
| `e_grading_steps_v01.csv` | E. 등급 체계의 단계와 그 단계를 정하는 소견·측정 | 직접 작성 |
| `sources_v01.csv` | 정의·분류·근거 문헌과 서지 확인 상태(`src_*`) | 직접 작성 |
| `f_mapping_rules_v01.csv` | F. 기존 측정 → D 대응 규칙(위에서부터 첫 일치) | 직접 작성 |
| `f_existing_measurements_v01.csv` | F. 기존 측정 644건의 대응 후보(원본 ID·개념 ID·정의 해시·구역·통계량 보존) | 생성 |

### G. 영상 출처(정본, 생성 코드가 읽음)

| 파일 | 내용 | 작성 방식 |
| --- | --- | --- |
| `g_image_sources_v01.csv` | 영상을 준 데이터셋·논문(라이선스·서지·로컬 경로). 그림·예시의 `source_id` | 직접 작성 |
| `g_provider_figures_v01.csv` | 논문 그림 파일(원본 파일명·SHA-256 고정·쓰는 생성기) | 직접 작성 |

### H. 영상 산출물(생성기 결과를 표로 펼침)

| 파일 | 내용 | 작성 방식 |
| --- | --- | --- |
| `h_masked_figures_v01.csv` | 항목 페이지의 마스킹 그림(원 영상·mask 겹침·체크섬) | 생성 |
| `h_masked_figure_items_v01.csv` | 마스킹 그림 × 그 그림이 보여 주는 항목 | 생성 |
| `h_modality_figures_v01.csv` | 영상 종류 페이지의 대표 그림(마스킹 그림 재사용 또는 논문 그림 잘라냄) | 생성 |
| `h_measure_examples_v01.csv` | 측정 표시 예시 영상(영상 종류·부위·출처·생성 함수) | 생성 |
| `h_example_layers_v01.csv` | 예시의 표시 층(스위치 하나 = 층 하나, 함수·설명·파일) | 생성 |
| `h_example_values_v01.csv` | 층이 계산한 측정값(측정 ID·상태·표시값) | 생성 |

### I. 파생 관계(웹 서비스가 쓰는 계산 결과)

| 파일 | 내용 | 작성 방식 |
| --- | --- | --- |
| `i_feature_implementations_v01.csv` | 특징별 구현 수준·retinal-measures 함수·입력 | 생성 |
| `i_measure_disease_links_v01.csv` | 측정 → 대상 질병(직접 관계 또는 대상 항목 경유) | 생성 |
| `i_example_coverage_v01.csv` | 측정 × 해당 영상 종류 × 예시 유무 | 생성 |

## 갱신 순서

저장소 루트에서 실행한다(전체 재구축은 [재구축 절차](../../protocols/50_retinal_atlas_rebuild_runbook_v01_ko.md)).

```bash
P=domains/retinal
.venv/bin/python -B $P/code/build_retinal_atlas_catalog.py          # A–F 생성 표, 읽기 문서, web data/atlas.json
.venv/bin/python -B $P/code/build_atlas_masked_figures.py           # 마스킹 그림(G 표를 읽음)
.venv/bin/python -B $P/code/build_atlas_modality_figures.py         # 영상 종류 그림(G 표를 읽음)
.venv/bin/python -B $P/code/build_measurement_examples.py           # 측정 표시 예시(G 표를 읽음)
.venv/bin/python -B $P/code/export_retinal_atlas_registry.py        # H·I 생성 표
.venv/bin/python -B $P/code/check_retinal_atlas_registry.py         # 키·참조·파일·체크섬·라이선스 검사
.venv/bin/python -B -m unittest discover -s $P/code/tests -p "test_retinal_atlas_*.py"
```

## 규칙

- 지식 ID는 `img_*`·`ref_*`·`zone_*`·`ana_*`·`les_*`·`obs_*`·`ft_*`·`dis_*`·`rel_*`·`gs_*`·`st_*`·`src_*`이며 이름이 바뀌어도 유지한다.
- 영상 출처 ID(`g_image_sources.source_id`)는 지식 근거 `src_*`와 다른 이름공간이다. 같은 논문의 다른 그림을 다른
  표기로 쓰면 키를 나눈다(예: `bai2026`·`bai2026_faf`).
- 한 칸에 여러 값을 넣을 때는 `;`로 구분한다. 서술 칸 안에서는 쉼표 대신 `·`를 쓴다.
- 관측 열 값은 `direct`·`limited`·`none`이다. 관측 열(`obs_*`)은 영상 종류 단위의 신호 가용성이고, 신호와 임상 해석은
  `bc_observations_v01.csv`에서 분리한다.
- F는 측정 정의와 식별자만 옮긴다. 환자별 값은 복제하지 않는다. F 관계는 규칙으로 만든 미검토 후보
  (`mapping_status=unreviewed_rule_candidate`)이며 생성기가 대상 일치와 출력 형태 호환을 검사한다.
- 검토 상태(`review_status`): `draft` → `source_linked`(서지 연결) → `definition_checked_abstract`·`definition_checked`
  → `measurement_checked` → `expert_reviewed`. 근거가 없는 E 관계는 `needs_source`다.
- 공개하는 영상은 CC BY 4.0·CC0 1.0만 쓴다. 논문 그림은 `provider_figures/`에 원본 파일명으로 한 번만 두고 SHA-256을
  `g_provider_figures`에 고정한다. 공급자 파일명이 기존 파일과 겹칠 때만 학술지 접두어를 붙이고 `provider_name`에 원래 이름을 남긴다.
- `d_applicability_overrides`·`d_feature_applicability`에서 `feature_id`가 빈 행은 그 대상 전체에 대한 지정이다.
