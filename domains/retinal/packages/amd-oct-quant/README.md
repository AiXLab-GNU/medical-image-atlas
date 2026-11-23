# amd-oct-quant

`amd-oct-quant`는 AMD OCT segmentation mask를 재현 가능한 정량 표현형으로 변환하는
독립 Python 패키지다. AMD-SD의 RGB mask decoder, IRF·SRF·PED·SHRM·IS/OS 2D 지표,
결과 QC와 provenance schema, segmentation/정량일치도/분류 평가 함수를 제공한다.

이 패키지는 Experiment 016에서 개발·검증되었지만 특정 experiment 디렉터리나 MARIO
outcome에 의존하지 않는다. 배포 이름은 `amd-oct-quant`, Python import namespace는
`amd_oct_quant`, CLI 명령은 `amd-oct-quant`다. 현재 패키지 버전은 `0.2.1`이고 2D 지표
알고리즘 버전은 `amd_oct_quant.metrics2d.v0.1.0`이다.

> 연구용 소프트웨어다. 임상 진단이나 치료 결정을 위한 검증된 의료기기가 아니며,
> 입력 데이터셋의 이용조건과 환자정보 보호정책은 별도로 준수해야 한다.

## 무엇을 정량화하는가

기본 입력은 `0`부터 `5`까지의 class ID를 갖는 2차원 정수 label mask다.

| ID | Class | Meaning in this package |
|---:|---|---|
| 0 | `background` | 배경 |
| 1 | `IRF` | 망막내액(intraretinal fluid) |
| 2 | `SRF` | 망막하액(subretinal fluid) |
| 3 | `PED` | 망막색소상피박리(pigment epithelial detachment) |
| 4 | `SHRM` | 망막하 고반사 물질(subretinal hyperreflective material) |
| 5 | `IS_OS` | IS/OS 또는 ellipsoid-zone 보존 annotation |

### IRF, SRF, PED, SHRM

네 면적 병변에 동일한 다섯 지표를 계산하여 총 20개 값을 만든다. 아래의 `{lesion}`은
`irf`, `srf`, `ped`, `shrm` 중 하나다.

| Metric | Definition | Unit | Empty-mask rule |
|---|---|---|---|
| `{lesion}_presence` | 해당 class pixel이 하나 이상이면 1 | binary | 0 |
| `{lesion}_area_px` | 해당 class pixel 수 | px | 0 |
| `{lesion}_area_fraction` | `area_px / (height × width)` | fraction | 0.0 |
| `{lesion}_component_count` | 8-connectivity connected component 수 | count | 0 |
| `{lesion}_largest_component_fraction` | 최대 component 면적 / 전체 병변 면적 | fraction of lesion area | 0.0 |

`area_fraction`은 서로 다른 영상 크기의 상대적 burden 비교에 사용할 수 있지만 실제
망막 면적이나 volume은 아니다. `component_count`는 대각선으로 맞닿은 pixel도 같은
component로 간주한다.

### IS/OS

IS/OS는 면적 병변으로 취급하지 않고, 각 영상 column에 IS/OS pixel이 존재하는지를 먼저
계산해 수평 보존과 단절을 정량화한다.

| Metric | Definition | Unit | Empty-mask rule |
|---|---|---|---|
| `is_os_presence` | IS/OS가 표시된 column이 하나 이상이면 1 | binary | 0 |
| `is_os_preserved_fraction` | IS/OS가 존재하는 column 수 / 전체 width | fraction of columns | 0.0 |
| `is_os_central_preserved_fraction` | 중앙 band 안에서 IS/OS가 존재하는 column 비율 | fraction of central columns | 0.0 |
| `is_os_central_preserved` | 중앙 보존 비율이 0보다 크면 1 | binary | 0 |
| `is_os_largest_gap_px` | IS/OS가 없는 가장 긴 연속 column 구간 | px | 완전 결손이면 image width |

중앙 band 기본값은 영상 width의 20%이며 `central_band_fraction` 인자로 바꿀 수 있다.
해부학적 foveal center를 따로 입력하지 않으므로 여기서 "central"은 단순한 영상 중심이다.

### 물리 단위 제한

검증된 lateral/axial pixel spacing을 입력받거나 적용하는 기능은 현재 없다. 따라서 출력은
`px`, image fraction 또는 column fraction이며 `mm²`나 `mm³`로 해석하면 안 된다. 영상
resize 전후의 `area_px`도 직접 비교하면 안 되며, 원본 label grid와 전처리 provenance를
함께 보존해야 한다.

## 지원 입력

### 1. 정수 label mask

가장 일반적인 인터페이스다. shape이 `H × W`이고 dtype이 integer인 NumPy array를 받는다.
허용되지 않은 class ID, 실수 dtype, 2D가 아닌 입력은 예외로 거부한다.

```python
import numpy as np
from amd_oct_quant import CLASS_NAME_TO_ID, extract_2d_metrics

mask = np.zeros((380, 570), dtype=np.uint8)
mask[120:150, 260:300] = CLASS_NAME_TO_ID["IRF"]

metrics = extract_2d_metrics(mask)
print(metrics["irf_area_px"])
print(metrics["irf_component_count"])
```

### 2. RGB palette mask

`decode_rgb_mask`는 `H × W × 3` RGB array를 integer label mask로 변환한다. 기본 palette는
background `(0,0,0)`, IRF `(0,255,0)`, SRF `(255,0,0)`, PED `(0,0,255)`, SHRM
`(255,255,0)`, IS/OS `(255,0,255)` 순서다.

AMD-SD mask에 압축/보간으로 생긴 중간 RGB 값이 있으므로 모든 pixel을 Euclidean RGB
거리상 가장 가까운 대표색에 배정한다. 같은 거리이면 가장 낮은 class ID를 선택한다.
decoder는 tie pixel 수, 최대 거리, 대표색으로부터 거리별 누적 비율을 `DecodeInfo`로
함께 반환한다. 임의의 새로운 palette 데이터에 이 규칙을 적용하기 전에는 색상과 decoder
적합성을 별도로 감사해야 한다.

```python
from PIL import Image
import numpy as np
from amd_oct_quant import decode_rgb_mask, extract_2d_metrics

rgb = np.asarray(Image.open("mask.png").convert("RGB"))
labels, decoder_info = decode_rgb_mask(rgb)
metrics = extract_2d_metrics(labels)
print(decoder_info.to_dict())
```

### 3. AMD-SD combined PNG

`load_amd_sd_combined_png`는 기본적으로 `1140 × 380` combined PNG를 왼쪽 OCT와 오른쪽
`570 × 380` RGB mask로 분리하고 mask를 decode한다.

```python
from amd_oct_quant import load_amd_sd_combined_png, extract_2d_metrics

oct_rgb, labels, decoder_info = load_amd_sd_combined_png("101_20.png")
metrics = extract_2d_metrics(labels)
```

이 loader의 기본 크기 검사는 AMD-SD 배포 형식에 특화되어 있다. 다른 combined layout은
`split_combined_image`의 expected size 인자를 명시하거나 자신의 loader로 label mask를
만든 뒤 일반 정량 API를 사용한다.

## 설치

이 저장소는 `uv` 환경을 사용한다. medical-image-atlas 루트에서 `uv sync`를 하면 editable로 함께 설치된다. 따로 설치하려면:

```bash
uv pip install --python .venv/bin/python -e domains/retinal/packages/amd-oct-quant
```

설치된 dependency를 그대로 사용하고 네트워크/build isolation을 피하려면 다음 명령을
사용할 수 있다.

```bash
UV_CACHE_DIR=/tmp/amd_oct_quant_uv_cache uv pip install \
  --python .venv/bin/python --no-deps --no-build-isolation \
  -e projects/P002_amd_oct/packages/amd-oct-quant
```

필수 Python 버전은 3.11 이상이다. 런타임 dependency는 NumPy, pandas, Pillow, PyArrow,
PyYAML, SciPy와 scikit-learn이며 `pyproject.toml`에 선언되어 있다.

## CLI 사용법

### 단일 AMD-SD combined PNG

decoder QC와 25개 지표를 JSON으로 stdout에 출력한다.

```bash
.venv/bin/amd-oct-quant one \
  projects/P002_amd_oct/resources/datasets/public_amd/amd_sd/extracted/AMD-SD/images/101/101_20.png
```

### 지표 사전 생성

지표명, 병변, 산식, 단위, zero rule, 임상적 의미, failure condition과 algorithm version을
CSV로 저장한다.

```bash
.venv/bin/amd-oct-quant metric-dictionary \
  --output /tmp/amd_oct_metric_dictionary.csv
```

### AMD-SD manifest batch 추출

```bash
.venv/bin/amd-oct-quant extract-amd-sd \
  --manifest projects/P002_amd_oct/experiments/E016_feasibility/artifacts/migrations/20260812_resource_paths/manifests/amd_sd_samples.csv \
  --project-root /home/jinhyun/prj_ws/prj_jin/oculophenome-xai \
  --output /tmp/amd_sd_metrics.parquet \
  --qc-output /tmp/amd_sd_metrics_qc.json
```

batch pipeline은 `included`, `sample_uid`, `patient_id`, `eye_id`, `eye_side`,
`analysis_split`, `relative_source_path`, `source_sha256` column을 포함한 AMD-SD manifest를
기대한다. `included`가 true인 행만 `sample_uid` 순서로 처리하며, 원본을 수정하지 않는다.
실패한 표본도 `extraction_failure`와 `exclusion_reason`을 붙여 결과에 남긴다.
E016의 최초 manifest에는 리팩터링 전 데이터 경로가 provenance로 동결되어 있으므로,
위 예제는 [경로 이관본](../../experiments/E016_feasibility/artifacts/migrations/20260812_resource_paths/README.md)을
사용한다.

## Python 공개 API

| API | Purpose |
|---|---|
| `decode_rgb_mask` | RGB mask를 결정적 integer label mask로 decode |
| `split_combined_image` | 수평으로 결합된 OCT/mask 영상 분리 |
| `load_amd_sd_combined_png` | AMD-SD combined PNG load, split, decode |
| `extract_2d_metrics` | label mask 한 장에서 25개 표현형 계산 |
| `metric_dictionary` | 지표 정의를 pandas DataFrame으로 반환 |
| `extract_amd_sd_manifest` | AMD-SD manifest batch를 provenance 포함 table로 변환 |
| `validate_metric_record` | 단일 지표 record의 finite/range/binary 규칙 확인 |
| `validate_metric_table` | batch failure, nonfinite, duplicate, mask source 확인 |
| `agreement_statistics` | CCC, ICC(A,1), MAE, Spearman, Bland–Altman 계산 |
| `confusion_matrix`, `metrics_from_confusion` | multiclass label-map의 Dice/IoU/precision/recall 계산 |
| `classification_summary` | macro-F1, balanced accuracy, recall, confusion matrix 및 제한된 QWK 계산 |

`classification_summary`에서 class 3은 `Other/Uninterpretable`로 간주하며 ordinal scale에
놓지 않는다. QWK는 true class가 0/1/2인 행에서 probability도 0/1/2로 제한한 민감도
분석만 반환한다.

## QC와 provenance

정량 결과에는 가능한 경우 다음 정보를 같이 저장한다.

- dataset, analysis split, sample/patient/eye key
- 원본 상대경로와 SHA-256
- 입력 width/height와 spacing 확인상태
- `mask_source`: `ground_truth` 또는 `predicted`
- segmentation model/checkpoint와 metric algorithm version
- decoder rule/tie/distance QC
- extraction failure와 exclusion reason

ground-truth mask 지표와 model-predicted mask 지표는 같은 column 이름을 가질 수 있으므로
`mask_source`, 모델 manifest와 checkpoint hash 없이 합치거나 성능을 주장하지 않는다.
`validate_metric_table`의 batch 규칙은 현재 AMD-SD ground-truth extraction을 기준으로 하며
predicted-mask table에는 목적에 맞는 별도 provenance 검사를 적용해야 한다.

## 평가 통계

`agreement_statistics(reference, estimate)`는 paired finite array에 대해 다음을 반환한다.

- Lin's concordance correlation coefficient(CCC)
- two-way random-effects absolute-agreement single-measure ICC(A,1)
- mean absolute error(MAE)
- Spearman rank correlation
- Bland–Altman bias와 95% limits of agreement

상관계수만으로 일치도를 대신하지 말고 CCC/ICC, 오차와 Bland–Altman을 함께 해석한다.
segmenter 평가는 전체 pixel Dice 외에 positive-only 크기 subgroup, failure rate와 병변량
일치도를 함께 확인하는 것을 권장한다.

## 검증과 테스트

저장소 루트에서 전체 unit test를 실행한다.

```bash
.venv/bin/python -m unittest discover -s projects/P002_amd_oct/packages/amd-oct-quant/tests -v
```

Experiment 016에서 decoder/2D engine은 다음 범위로 검증되었다.

- palette exact/intermediate/tie case와 combined-image split
- empty, one-pixel, diagonal connectivity, multiple component, IS/OS gap synthetic case
- 25개 실제 mask의 독립 구현 대조
- AMD-SD 3,048장 전수 추출과 반복 계산 일치
- segmentation/confusion, agreement와 nonordinal QWK scope unit test

이 검증은 AMD-SD의 annotation convention과 현재 알고리즘에 대한 것이다. 다른 장비,
질환, class palette, 3D volume 또는 실제 물리단위에 대한 타당성을 자동으로 보장하지 않는다.

관련 근거와 결과:

- [Experiment 016 metric report](../../experiments/E016_feasibility/artifacts/reports/metric_engine_summary.md)
- [Metric dictionary CSV](../../experiments/E016_feasibility/artifacts/metric_dictionary.csv)
- [Feasibility report](../../experiments/E016_feasibility/artifacts/reports/feasibility_report.md)

## 패키지 구조

```text
projects/P002_amd_oct/packages/amd-oct-quant/
├── README.md
├── pyproject.toml
├── src/amd_oct_quant/
│   ├── palette.py
│   ├── metrics2d.py
│   ├── pipeline.py
│   ├── qc.py
│   ├── schemas.py
│   ├── agreement.py
│   ├── segmentation_metrics.py
│   ├── classification_metrics.py
│   └── cli.py
└── tests/
```

새 지표는 outcome과 전역상태에 의존하지 않는 pure function으로 구현하고, 단위와 zero
rule을 `metric_dictionary()`에 추가하며, analytic expected value를 갖는 unit test와
provenance/QC 규칙을 함께 추가한다. 3D 또는 longitudinal 지표는 spacing, volume/visit
grouping과 leakage rule이 검증된 뒤 별도 algorithm version으로 확장한다.
