# 병리 영상 지도 재구축 절차 v01

작성: 2026-11-23 · medical-image-atlas 루트에서 실행한다. `P=domains/pathology`.

## 1. 환경

`uv sync`(루트 .venv: tifffile·imagecodecs·zarr·pathology-measures 포함). 웹은
`cd $P/packages/pathology-atlas-web && uv venv .venv && uv pip install --python .venv/bin/python -e .`.

## 2. 원자료(CC BY 4.0)

- PRECISE: https://doi.org/10.5281/zenodo.20721779 — `resources/datasets/public_pathology/precise/`에 `extracted/data/sub-*/ses-*/wsi_h-e/*.ome.tif`
  (H&E와 주석 mask 27쌍)와 `wsi_hmwck-amacr/*.ome.tif`(IHC와 주석 27쌍, 원 zip `data.zip`에서 풂, 모두 53 GB), `participants.csv`·`label_descriptions.json`·`LICENSE.txt`·`README.md`를 둔다.
- SICAPv2: https://data.mendeley.com/datasets/9xxm58dvs3/1 — `resources/datasets/public_pathology/sicapv2/SICAPv2/`(images·masks·partition, 4.2 GB).
- PAR: https://doi.org/10.6019/S-BIAD2323 — `resources/datasets/public_pathology/par/`에 `slide_labels.tsv`와 모든 판독의가 같은 등급을 준 예시 슬라이드 5장(`hamamatsu/*.ndpi`, 원본 그대로)만 둔다.
- 2026-11-23에는 서버의 `/srv/rhome/common-data/microsoft-prostate-cancer-data/`에서 파일 수를 맞춰 복사했다(PRECISE 54 · SICAPv2 37,589).

## 3. 만드는 순서

```bash
.venv/bin/python -B $P/code/build_pathology_atlas_catalog.py      # 1) 표 검사·적용 관계·읽기 문서·atlas.json
.venv/bin/python -B $P/code/build_pathology_figures.py            # 2) 그림 68(논문 패널 35)·예시 16(층 61)·grading.json(약 2분; 등급 build_pathology_grading.py, 논문 패널 build_pathology_paper_figures.py)
.venv/bin/python -B $P/code/evaluate_pathology_measures.py       # 3) 측정 검증 validation.json(코어 다수로 수 분)
.venv/bin/python -B $P/code/export_pathology_atlas_registry.py    # 4) H·I 생성 표
.venv/bin/python -B $P/code/check_pathology_atlas_registry.py     # 5) 25표 검사
.venv/bin/python -B -m unittest discover -s $P/code/tests
(cd $P/packages/pathology-measures && ../../../../.venv/bin/python -B -m unittest discover -s tests)
(cd $P/packages/pathology-atlas-web && .venv/bin/python -B -m unittest discover -s tests)
```

## 4. 서비스

```bash
cd $P/packages/pathology-atlas-web
systemd-run --user --unit=pathology-atlas-web --property=Restart=on-failure --working-directory="$PWD" \
  "$PWD/.venv/bin/pathology-atlas-web" --host 127.0.0.1 --port 8881
```

8880은 다른 서버가 쓰고 있어 8881을 쓴다.

## 5. 넓히는 방법

- 다른 장기(유방·대장 등): 같은 영역 안에 `lesion_group`과 질병·판정 체계를 더하고, 장기별 데이터셋을 G 표에 등록한다.
- 우선 채울 곳: 신경주위 침범·피막 밖 침범 그림(CC BY 논문), 40× 핵소체 검출, H&E–IHC 연속 절편 정합.
