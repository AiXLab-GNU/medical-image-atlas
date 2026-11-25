# 망막 영상 지도 재구축 절차 v01

- 상태: CURRENT
- 작성일: 2026-11-23
- 목적: 저장소와 공개 원자료만으로 망막 영상 지도(지식 표 → 그림·예시 → 웹 서비스)를 처음부터 같은 결과로 다시 만들고,
  이후 항목을 더할 때 같은 방식으로 늘린다.
- 함께 읽을 문서: [데이터 스키마](40_retinal_atlas_data_schema_v01_ko.md), [등록 표 README](../surveys/retinal_atlas_catalog/README.md),
  [웹 서비스 README](../../packages/retinal-atlas-web/README.md)

모든 명령은 저장소(`medical-image-atlas`) 루트에서 실행하고 `P=domains/retinal`로 둔다.

## 1. 전체 흐름

```text
지식 표 A–F (직접 작성)            ─ build_retinal_atlas_catalog.py ─▶ atlas.json, 읽기 문서, F·D 적용 생성 표
영상 출처 표 G (직접 작성)  ┐
공개 데이터셋 원본(resources)├─ build_atlas_masked_figures.py   ─▶ 마스킹 그림 + masked_figures.json
논문 그림(provider_figures) ┘  build_atlas_modality_figures.py ─▶ 영상 종류 그림 + modality_figures.json
                               build_measurement_examples.py   ─▶ 측정 표시 예시 + measurement_examples.json
도식 생성 코드                  ─ build_vessel_schematic.py · build_lesion_schematics.py · build_oct_schematic.py ─▶ 도식 템플릿·SVG, item_schematics.json, oct_layer_colors.json
JSON + atlas.json              ─ export_retinal_atlas_registry.py ─▶ H·I 생성 표
전체                            ─ check_retinal_atlas_registry.py  ─▶ 키·참조·파일·체크섬·라이선스 검사
웹 서비스                       ─ retinal-atlas-web (Flask)        ─▶ http://127.0.0.1:8877
```

## 2. 준비

### 2.1 환경

| 환경 | 만들기 | 쓰는 곳 |
| --- | --- | --- |
| 저장소 `.venv` (Python 3.12, numpy·scipy·scikit-image·Pillow·pandas·openpyxl) | 저장소 루트 `uv sync` (`uv.lock`이 생기면 `--frozen`) | 지식 표·그림·예시 생성, 내보내기, 검사 |
| 웹 `.venv` (Flask) | `$P/packages/retinal-atlas-web`에서 `uv sync --frozen` | 웹 서비스와 그 테스트 |

측정 함수는 `$P/packages/retinal-measures`(설치 없이 `src/`를 경로로 읽음), 측정 대응은
`$P/packages/ophthalmic-quantification`에 있다. 둘 다 저장소 안에 있어 따로 받을 것이 없다.

### 2.2 원자료 (공개·CC BY/CC0만)

공개 데이터셋은 `g_image_sources_v01.csv`의 `kind=dataset` 12행이 전부다. `resource_path`에 원본을 한 번만 두고,
영역 `$P/resources/`에는 상대 심볼릭 링크만 둔다. 원자료는 루트 `resources/datasets/`에 이 저장소의 복사본으로 둔다(루트 `resources/README.md`). 새로 받을 때는 각 행의 `url`(DOI)에서 받는다.

| source_id | 내용 | 라이선스 | 위치 |
| --- | --- | --- | --- |
| `idrid_seg`·`idrid_loc` | IDRiD 분할·위치 | CC BY 4.0 | `resources/datasets/public_dr/IDRiD/` |
| `refined_idrid` | Refined IDRiD 혈관·병변 라벨 | CC BY 4.0 | `resources/datasets/public_dr/refined_idrid/` |
| `fundus_avseg_7c` | Fundus-AVSeg-7C 동정맥·유두·중심와 | CC BY 4.0 | `resources/datasets/public_dr/fundus_avseg_7c/` |
| `uwf_dr_2026` | 광각 SLO 당뇨망막병증 | CC BY 4.0 | `resources/datasets/public_dr/uwf_dr_2026/` |
| `chaksu` | Chákṣu 유두·컵 | CC BY 4.0 | `resources/datasets/public_glaucoma/chaksu/` |
| `palm` | PALM 근시 병변·유두·중심와 | CC0 1.0 | `resources/datasets/public_myopia/palm/` |
| `amd_sd` | AMD-SD OCT 병변 | CC0 1.0 | `resources/datasets/public_amd/amd_sd/` |
| `amd_dme_3d` | AMD/DME 3D OCT 볼륨 | CC BY 4.0 | `resources/datasets/public_amd/amd_dme_3d_oct/` |
| `octid`·`octid_mh` | OCTID | CC0 1.0 | `resources/datasets/public_amd/octid*/` |
| `olives` | OLIVES OCT 층 | CC BY 4.0 | `resources/datasets/olives/zenodo_7105232/` |

**쓰지 않는 자료**: FGADR, HYAMD, MAPLES-DR·MESSIDOR 영상, Tianjin, 기관 내부 자료(제한 자료), PAPILA(GPL),
RET-Amrita. 이 자료의 영상은 지도에 넣지 않는다.

논문 그림은 `g_provider_figures_v01.csv` 95장이다. `resources/datasets/retinal_atlas_modality_figures/provider_figures/`에
`file` 이름으로 두며, 대부분 PMC 공개 자료 저장소(`pmc-oa-opendata`)에서 그 논문(`g_image_sources.pmcid`·`doi`)의
그림 파일을 받았다. 받은 뒤 SHA-256이 표와 같아야 한다(다르면 생성 코드가 멈춘다).

### 2.3 원자료 확인

```bash
.venv/bin/python -B $P/code/check_retinal_atlas_registry.py   # 데이터셋이 없으면 warning, 논문 그림이 없거나 바뀌면 error
```

## 3. 처음부터 다시 만들기

| 순서 | 명령 | 결과 | 걸리는 시간(참고) |
| --- | --- | --- | --- |
| 1 | `.venv/bin/python -B $P/code/build_retinal_atlas_catalog.py` | `atlas.json`, 읽기 문서, `f_existing_measurements`·`d_feature_applicability` | 수 초 |
| 2 | `.venv/bin/python -B $P/code/build_vessel_schematic.py` · `build_lesion_schematics.py` · `build_oct_schematic.py` | 혈관·OCT 도식 템플릿(`_vessel_schematic.html`·`_oct_schematic.html`), 항목 도식 SVG(`static/schematics/`)와 `item_schematics.json`, `oct_layer_colors.json` | 수 초 |
| 3 | `.venv/bin/python -B $P/code/build_atlas_masked_figures.py` | 마스킹 그림 152장, `masked_figures.json` | 1–2분 |
| 4 | `.venv/bin/python -B $P/code/build_atlas_modality_figures.py` | 영상 종류 그림 14장, `modality_figures.json` | 수 초 |
| 5 | `.venv/bin/python -B $P/code/build_measurement_examples.py` | 측정 표시 예시 89장·층 239개, `measurement_examples.json` | 약 4분 |
| 6 | `.venv/bin/python -B $P/code/export_retinal_atlas_registry.py` | H·I 생성 표 9개 | 수 초 |
| 7 | `.venv/bin/python -B $P/code/check_retinal_atlas_registry.py` | `26 tables · 0 errors` | 수 초 |
| 8 | `.venv/bin/python -B -m unittest discover -s $P/code/tests -p "test_retinal_atlas_*.py"` | 지식 표·등록 표 테스트 | 수 초 |
| 9 | `cd $P/packages/retinal-atlas-web && .venv/bin/python -B -m unittest discover -s tests` | 웹 테스트 | 수 초 |
| 10 | `cd $P/packages/retinal-atlas-web && .venv/bin/python -B -m retinal_atlas_web --port 8877` | 웹 서비스 | — |

순서 3·4·5는 1의 `atlas.json`을 읽고, 4는 3의 `masked_figures.json`을, 5는 3·4의 결과를 읽는다. 6은 1·3·4·5 뒤에 돌린다.
`catalog.json`·`image_links.json`(개념 분류 화면의 표본·연결)은 생성 코드 없이 직접 작성한 웹 데이터다.

**같은 결과 확인**: 3·4는 다시 돌려도 JSON이 바이트 단위로 같다. 5도 같은 값을 낸다(그림 압축은 Pillow 판에 따라 조금 다를 수 있다).
H·I 표는 `export_retinal_atlas_registry.py --check`로 최신인지 본다.

## 4. 늘리는 방법

### 4.1 논문 그림 하나를 더할 때

1. 논문이 **CC BY 2.0 이상 또는 CC0**인지 확인한다(판 번호가 적혀 있지 않으면 쓰지 않는다)(Europe PMC `LICENSE:"cc by"`, 또는 PMC 공개 자료 저장소의 `license_code`).
   CC BY-NC·NC-ND는 쓰지 않는다.
2. 그림 파일을 공급자 파일명 그대로 `provider_figures/`에 둔다. 이미 같은 이름이 있으면 학술지 접두어를 붙이고
   `provider_name`에 원래 이름을 적는다.
3. `g_image_sources_v01.csv`에 행을 더한다: `source_id`(첫 저자 성 + 연도, 같은 논문의 다른 그림이면 접미어), `kind=article`,
   `credit`(그림 아래 표기, 패널 포함), `citation`(패널 없이), `doi`·`pmcid`·`url`, 라이선스.
4. `g_provider_figures_v01.csv`에 `file`·`source_id`·`sha256`(`sha256sum`)·`used_by`를 더한다.
5. 생성 코드에서 `provider('<file>')`로 연다(체크섬은 자동 확인). 출처 키·체크섬을 코드에 다시 적지 않는다.

### 4.2 공개 데이터셋을 더할 때

1. 라이선스(CC BY·CC0)를 확인하고 원본을 `resources/datasets/<영역>/<이름>/`에 한 번만 둔다.
2. `$P/resources/`에 상대 링크를 만들고 `$P/resources/README.md`에 적는다.
3. `g_image_sources_v01.csv`에 `kind=dataset`, `resource_path`와 함께 더한다.

### 4.3 측정을 더하거나 예시를 만들 때

1. `d_features_v01.csv`에 측정을 더한다(`target_id`·`imaging_ids`·`unit`·`output_type`·`feature_role=measurement`).
2. 계산 함수는 `retinal-measures`에 구현하고 `retinal_measures/registry.py`에 등록한다(합성 테스트 포함).
3. 1단계(`build_retinal_atlas_catalog.py`)로 `atlas.json`을 갱신한다.
4. 예시: `build_measurement_examples.py`에 생성 함수를 더하고 `main()`의 목록에 넣는다.
   - 입력 우선순위: 공급자·전문가 mask → 저자가 그림에 남긴 표시(화살표·타원·분할선·장비 경계) → 서비스 추정(밝기·모양 규칙).
     서비스 추정이면 캡션에 그렇게 적는다.
   - 계산 코드가 없는 정성 항목은 `R(...)` 판독 층으로 넣는다(값 대신 볼 자리와 기준).
   - 값은 화소 단위가 기본이다. 장비 눈금·유두지름 같은 근거가 있을 때만 다른 단위로 바꾼다.
   - 두 시점 비교는 같은 눈·같은 조영 시기·정합 근거가 있을 때만 만든다(정합 방법을 캡션에 적는다).
5. `i_example_coverage`가 `no`인 조합이 없도록 측정마다 `imaging_ids`의 영상 종류 전부에 예시를 둔다.

### 4.4 질병 관계를 더할 때

1. 근거 문헌이 `sources_v01.csv`에 없으면 먼저 더한다(PMID·DOI를 실제로 조회해 `verification`을 적는다).
2. `e_disease_findings_v01.csv`에 `relation_id`(`rel_<질병 약칭>_<측정·소견>`)·`disease_id`·`finding_id`·`relation_type`·
   `condition_ko`·`evidence_source_ids`·`review_status=source_linked`를 더한다. 관계 ID가 겹치지 않는지 확인한다.
3. 1단계를 다시 돌린다. 측정 목록의 "대상 질병"과 `i_measure_disease_links`에 반영된다.
4. 특정 질병의 근거가 없는 공통 지표는 억지로 잇지 않는다(화면에 "공통 지표 · 특정 질병 없음").

### 4.5 고친 뒤 항상

```bash
.venv/bin/python -B $P/code/export_retinal_atlas_registry.py
.venv/bin/python -B $P/code/check_retinal_atlas_registry.py
.venv/bin/python -B -m unittest discover -s $P/code/tests -p "test_retinal_atlas_*.py"
(cd $P/packages/retinal-atlas-web && .venv/bin/python -B -m unittest discover -s tests)
```

그리고 저장소 루트 `STATUS.md`에 무엇을 더했는지 적는다.

## 5. 지켜야 할 원칙

- 공개하는 영상은 CC BY 2.0 이상·CC0 1.0만 쓰고, 그림마다 출처 줄(저자·학술지·그림 번호·라이선스 링크)을 단다.
- 원자료와 논문 그림은 저장소에 한 번만 둔다. 원본 파일명과 바이트를 바꾸지 않는다(체크섬 고정).
- 출처·라이선스·체크섬은 G 표에만 적는다. 생성 코드에 다시 적지 않는다.
- 생성 표(H·I, F 기존 측정, D 적용)와 생성 JSON은 손으로 고치지 않는다.
- 측정 목록에는 판정 기준·임계값을 넣지 않는다(질병 페이지에서 본다).
- 값은 함수 동작을 보여 주는 예시이며 임상값이 아니다. 서비스 추정 입력은 아직 전문가 검토를 거치지 않았다.
