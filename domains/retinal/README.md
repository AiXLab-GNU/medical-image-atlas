# 망막 영역 (retinal)

망막 영상 지도: 안저·광각·FA·FAF·근적외선·ICGA·OCT·OCTA에서 무엇이 보이고(해부 73·병변 117), 무엇을 재며(측정 160),
어떤 질병의 근거인지(질병 65, 관계 300)를 실제 영상 위에 보여 준다.

| 무엇 | 어디 |
| --- | --- |
| 웹 서비스 | [`packages/retinal-atlas-web`](packages/retinal-atlas-web/README.md) — `.venv/bin/python -B -m retinal_atlas_web --port 8877` |
| 측정 함수 | [`packages/retinal-measures`](packages/retinal-measures) (측정 146/160 함수, 합성 테스트) |
| 정량화 패키지(복사본) | [`packages/ophthalmic-quantification`](packages/ophthalmic-quantification/README.md) — 기존 측정 대응(F 표)에 씀 |
| 등록 표 26개 | [`docs/surveys/retinal_atlas_catalog/`](docs/surveys/retinal_atlas_catalog/README.md) |
| 데이터 스키마 | [`docs/protocols/40_retinal_atlas_data_schema_v01_ko.md`](docs/protocols/40_retinal_atlas_data_schema_v01_ko.md) |
| 재구축 절차 | [`docs/protocols/50_retinal_atlas_rebuild_runbook_v01_ko.md`](docs/protocols/50_retinal_atlas_rebuild_runbook_v01_ko.md) |
| 개념·요구사항·설계 | [`docs/concept/`](docs/concept) (조사 범위, 서비스 요구사항, 웹 설계, 측정 개념 분류) |
| 생성 코드 | [`code/`](code) (지식 표, 마스킹 그림, 영상 종류 그림, 측정 예시, 도식, 등록 표 내보내기·검사) |
| 동결 입력 | [`references/`](references) — E118 측정 등록부(F 표 원천), E012 안저 지표 사전(정량화 패키지 테스트) |

출처: oculophenome-xai `projects/P003_ophthalmic_foundation_model_validation`에서 2026-11-23 복사.

빠른 확인(저장소 루트에서):

```bash
.venv/bin/python -B domains/retinal/code/check_retinal_atlas_registry.py
.venv/bin/python -B -m unittest discover -s domains/retinal/code/tests -p "test_retinal_atlas_*.py"
```
