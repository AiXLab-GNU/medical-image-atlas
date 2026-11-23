# 병리 영상 지도(전립선) 등록 표

병리 영상 지도(웹 `packages/pathology-atlas-web`, 포트 8881)를 이루는 데이터를 서로 참조되는 표로 모은 곳이다. 첫 범위는 전립선
조직병리(H&E·IHC)다. 망막·유방촬영 지도와 같은 틀이며, 열 정의는 [데이터 스키마](../../protocols/40_pathology_atlas_data_schema_v01_ko.md),
처음부터 다시 만드는 순서는 [재구축 절차](../../protocols/50_pathology_atlas_rebuild_runbook_v01_ko.md)에 있다.

## 표 목록

"직접"은 사람이 고치는 정본, "생성"은 아래 갱신 순서로 다시 만드는 결과다.

| 파일 | 내용 | 작성 방식 |
| --- | --- | --- |
| `a_imaging_v01.csv` | A. 영상 종류(H&E·IHC)와 표현(WSI·고배율·패치·HMWCK–AMACR) | 직접 작성 |
| `b_anatomy_v01.csv` | B. 전립선 구역·샘과 간질·세포·측정 기준(조직 면적·화소 크기·HPF) | 직접 작성 |
| `c_lesions_v01.csv` | C. 선암·글리슨 패턴 3·4·5·성장 양상·관내암·HGPIN·침범·암 모방 양성 병변·인공물 | 직접 작성 |
| `bc_observations_v01.csv` | 관측: 대상 × 영상 표현 × 보이는 모습 × 해석 조건 × 근거 | 직접 작성 |
| `d_features_v01.csv` | D. 측정 32 + 판정 분류 2(글리슨 점수·ISUP 등급군) | 직접 작성 |
| `d_common_feature_sets_v01.csv` | 병변 형태 분류(region·gland·focal)별 공통 특징 | 직접 작성 |
| `d_applicability_overrides_v01.csv` | 대상별 적용·해당 없음 지정 | 직접 작성 |
| `d_feature_applicability_v01.csv` | 대상 × 특징 적용 관계 | 생성 |
| `e_diseases_v01.csv` | E. 질병(전립선 선암·관내암·관 선암·HGPIN·ASAP·BPH·전립선염·위축·선증) | 직접 작성 |
| `e_disease_findings_v01.csv` | E. 질병–소견·측정 관계 | 직접 작성 |
| `e_grading_schemes_v01.csv` | E. 판정 체계(글리슨 패턴·ISUP 등급군·pT·관내암 기준·암과 모방 병변 가르기) | 직접 작성 |
| `e_grading_steps_v01.csv` | E. 판정 단계 | 직접 작성 |
| `sources_v01.csv` | 근거 문헌(Europe PMC로 PMID 확인) | 직접 작성 |
| `g_image_sources_v01.csv` | 영상 출처: PRECISE·SICAPv2(모두 CC BY 4.0) | 직접 작성 |
| `g_provider_figures_v01.csv` | 논문 그림 파일(아직 없음 · IHC·신경주위 침범 그림을 넣을 자리) | 직접 작성 |
| `h_masked_figures_v01.csv` | 항목 페이지 그림 | 생성 |
| `h_masked_figure_items_v01.csv` | 그림 × 항목 | 생성 |
| `h_measure_examples_v01.csv` | 측정 표시 예시 | 생성 |
| `h_example_layers_v01.csv` | 예시의 표시 층 | 생성 |
| `h_example_values_v01.csv` | 층이 계산한 값 | 생성 |
| `i_feature_implementations_v01.csv` | 특징별 구현 수준과 pathology-measures 함수 | 생성 |
| `i_measure_disease_links_v01.csv` | 측정 → 대상 질병 | 생성 |
| `i_example_coverage_v01.csv` | 측정 × 영상 종류 × 예시 유무 | 생성 |

## 갱신 순서

```bash
P=domains/pathology
.venv/bin/python -B $P/code/build_pathology_atlas_catalog.py      # 적용 관계·읽기 문서·atlas.json
.venv/bin/python -B $P/code/build_pathology_figures.py            # 그림·측정 표시 예시(PRECISE·SICAPv2)
.venv/bin/python -B $P/code/export_pathology_atlas_registry.py    # H·I 생성 표
.venv/bin/python -B $P/code/check_pathology_atlas_registry.py     # 키·참조·파일·체크섬·라이선스 검사
.venv/bin/python -B -m unittest discover -s $P/code/tests
```

## 규칙

- 관측 열은 `obs_he`·`obs_ihc`(값 `direct`·`limited`·`none`). 한 칸에 여러 값은 `;`로 구분한다.
- PRECISE 주석 class: 1 종양 · 2 양성 샘 · 3 인공물 · 4 HGPIN · 5 관내암 · 6 비정형 관내 증식 · 7 간질(자동 보충 포함 가능).
- SICAPv2 주석 값은 실제로 0·3·4·5(패턴 번호)다. 공급자 readme의 1·2·3 표기와 다르다.
- PRECISE는 OME 메타데이터의 µm/px로 mm·µm² 단위를 쓰고, SICAPv2는 화소 단위다.
- 병변 색 영역은 공급자 주석, 조직·내강·핵은 서비스 자동 추정이다. 핵은 검증된 분할이 아닌 후보다.
- 공개 영상은 CC BY 4.0·CC0 1.0만 쓴다. PANDA·LEOPARD·CHIMERA·PBGG(비영리)와 기관 자료는 쓰지 않는다.
- `d_applicability_overrides`·`d_feature_applicability`에서 `feature_id`가 빈 행은 그 대상 전체에 대한 지정이다.
