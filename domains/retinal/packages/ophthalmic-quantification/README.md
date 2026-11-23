# ophthalmic-quantification

안저 RGB·혈관/병변 입력, OCT label mask, 구조화 VA/IOP와 임상 텍스트에서 감사 가능한
정량지표를 계산하는 영역 공용 Python 패키지다. P001–P003가 재사용하며 E017이 TDD 검증과
전체 합성 예제를 소유한다.

## 잠금 범위

- E012 legacy 안저 session metric 139개 exact ID
- E027 label-blind 확장 안저 anatomy·혈관 metric 43개
- E030 DR 병변·분포·황반/혈관 거리·형태·혈관 이질성 metric 77개와 음성대조 6개
- E046 7개 known lesion의 outcome-blind 주석 계약, 병변당 fine phenomics 20개와 grading-specific
  출혈 층위·NVD/NVE·4-2-1·PDR·gradability 계약
- `amd-oct-quant`의 outcome-independent OCT 2D mask metric 25개
- 영상 QC·색상·texture·FOV와 혈관 공간 지표
- 범용 binary mask morphology 및 ground-truth/prediction agreement
- VA/BCVA/UCVA, IOP와 임상 텍스트 수치의 fail-closed 구조화
- metric catalog, 질병·임상역할·근거수준 연결, provenance, 비식별 synthetic example CSV/HTML

모델 의존 지표는 raw RGB에서 꾸며내지 않고 upstream model output으로 받는다. 환자 원자료,
restricted E012 table과 식별자는 패키지나 공개 예제에 포함하지 않는다.

## 개발 규칙

모든 공개 함수는 정상·경계·실패 테스트를 먼저 추가한다. exact-count, ID 집합, zero rule,
source type, 단위와 missing reason을 regression test로 고정한다.

## 공개 API

- `extract_fundus_metrics`: RGB, vessel mask와 명시적 upstream model value에서 139개 계산
- `extract_extended_metrics`: RGB, vessel mask와 label-blind landmark에서 확장 안저 43개 계산
- `extract_dr_mask_metrics`: RGB와 검증된 병변·해부·혈관 mask에서 DR 직접 지표 78개 계산
- `validate_annotation_document`, `rasterize_annotation_document`: 미검토·음성·불확실을 분리하는
  7개 DR 병변 point/polygon/brush 주석 교환 형식 검증과 mask 변환
- `extract_known_lesion_measurements`, `quantify_annotation_document`: 전문의 주석에서 병변별
  존재·개수·면적·크기·형태·공간·황반/혈관 관계 20개를 결정론적으로 계산
- `validate_dr_grading_assessment`, `reconstruct_icdr_grade`: schema v2의 출혈 층위, NVD/NVE,
  사분면별 4-2-1, PDR 활동/치료와 판독 가능성을 fail-closed로 검증하고 Grade 1--4 후보를 재구성
- `quantify-dr-annotations`: 웹에서 내보낸 JSON과 `.npy` FOV·선택적 유두/중심와/혈관 mask를
  받아 결측을 JSON `null`로 보존한 측정 파일 생성

```bash
PYTHONPATH=projects/P003_ophthalmic_foundation_model_validation/packages/ophthalmic-quantification/src \
  .venv/bin/python -B -m ophthalmic_quantification.cli quantify-dr-annotations \
  --annotations dr_lesion_annotations_v01.json \
  --fov-mask fov_mask.npy \
  --disc-mask disc_mask.npy \
  --fovea-mask fovea_mask.npy \
  --vessel-mask vessel_mask.npy \
  --output dr_lesion_measurements_v01.json
```
- `add_dr_prespecified_interactions`: 직접 지표와 명시적 upstream 값에서 DR 상호작용 5개 계산
- `extract_oct_metrics`: integer OCT label mask에서 25개 phenotype 계산
- `binary_mask_metrics`: binary ground-truth/prediction mask morphology
- `segmentation_agreement`: prediction–ground-truth Dice·IoU·precision·recall·specificity
- `parse_visual_acuity`, `parse_iop`: 구조화 임상 수치의 단위 보존·fail-closed 파싱
- `extract_clinical_numbers`: 근거 span을 보존하는 VA·IOP·thickness 규칙기반 텍스트 추출
- `extract_clinical_numbers_hybrid`: AI 후보의 span·단위·범위를 검증하고 규칙 우선으로 병합
- `metric_catalog`: collection, input source, unit, algorithm version registry
- `p003_metric_catalog`: 기존 190개와 확장 안저 43개, E019 병변 10개, DR 83개를 합친 326개 통합 registry
- `disease_context_catalog`: 190개 전 항목의 질병 연결·임상 역할·근거 수준·claim 제한 registry
- `build_atlas_catalog`, `write_medical_metric_atlas`: 190개 계산기·질병·근거·T1–T4·QC 계보 Atlas 생성

안저 139개 중 model/segmentation 의존 9개는 `upstream_values`로 받아야 한다. `strict=True`는
누락을 오류로 처리한다. OCT 25개는 검증된 `amd-oct-quant`를 adapter로 호출한다.

## 테스트

```bash
.venv/bin/python -B -m unittest discover \
  -s projects/P003_ophthalmic_foundation_model_validation/packages/ophthalmic-quantification/tests \
  -v
```

## 전체 합성 예제

```bash
PYTHONPATH=projects/P003_ophthalmic_foundation_model_validation/packages/ophthalmic-quantification/src \
  .venv/bin/python -B -m ophthalmic_quantification.cli build-examples \
  --output-dir projects/P003_ophthalmic_foundation_model_validation/experiments/E017_ophthalmic_quantification_engine/artifacts
```

현재 bundle은 환자자료 없이 190개 예제를 생성한다: 안저 139, OCT 25, 범용 mask 13,
segmentation agreement 6, 구조화 임상 3, 규칙기반 임상 텍스트 3, hybrid adapter 1.
P003 확장 계산기는 별도 합성 계약 테스트에서 43개 확장 안저 지표와 DR 83개를 모두
계산하며, E027/E030 실험 진입점 회귀 테스트로 기존 결과와의 호환성을 확인한다.
HTML은 canonical Medical Metric Atlas 분류를 재사용한 T1–T4 카드와 지표 family 계보,
Tier·질병·collection filter가 연결된 190개 계산표를 제공한다. 같은 bundle의 질병–정량지표
한 장 지도와 왕복 이동할 수 있고, 지도에서 질병 또는 지표 family를 누르면 연결된 지표 목록을
확인할 수 있다. 190개 전체 관계 지도는 모든 개별 지표 노드와 Analysis/QC를 보존하면서
명시적 family 계보, T1↔T2·T3↔T4 공통 질병 맥락과 질병–지표 연결을 별도 선 종류로
표시한다. 각 행은 관련 질병, 임상 역할,
근거 수준, 근거 ID를 함께 표시한다. QC·성능평가·target 미지정 mask는 질병 또는 의료 Tier에
억지로 연결하지 않고 별도 Analysis registry로 유지하며 모든 연결은 `단독 진단용 아님`이다.

## Ophthalmic Medical Metric Atlas

```bash
PYTHONPATH=projects/P003_ophthalmic_foundation_model_validation/packages/ophthalmic-quantification/src \
  .venv/bin/python -B -m ophthalmic_quantification.cli build-atlas \
  --output projects/P003_ophthalmic_foundation_model_validation/docs/concept/ophthalmic_medical_metric_atlas_v02_ko.html
```

Atlas는 외부 CSS·JavaScript 없이 동작하는 단일 HTML이며 T1–T4, 질병 지도, family 계보,
190개 metric explorer, QC·검증 분리 registry와 primary evidence 상세 패널을 제공한다.
