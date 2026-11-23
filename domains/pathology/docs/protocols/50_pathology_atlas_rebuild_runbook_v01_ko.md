# 병리 영상 지도 재구축 절차 v01

작성: 2026-11-23 · medical-image-atlas 루트에서 실행한다. `P=domains/pathology`.

## 1. 환경

`uv sync`(루트 .venv: tifffile·imagecodecs·zarr·pathology-measures 포함). 웹은
`cd $P/packages/pathology-atlas-web && uv venv .venv && uv pip install --python .venv/bin/python -e .`.

## 2. 원자료(CC BY 4.0)

- PRECISE: https://doi.org/10.5281/zenodo.20721779 — `resources/datasets/public_pathology/precise/`에 `extracted/data/sub-*/ses-*/wsi_h-e/*.ome.tif`
  (H&E와 주석 mask, 27쌍·27 GB)와 `participants.csv`·`label_descriptions.json`·`LICENSE.txt`·`README.md`를 둔다. IHC는 원 zip(52 GB) 안에 있으며 아직 받지 않았다.
- SICAPv2: https://data.mendeley.com/datasets/9xxm58dvs3/1 — `resources/datasets/public_pathology/sicapv2/SICAPv2/`(images·masks·partition, 4.2 GB).
- 2026-11-23에는 서버의 `/srv/rhome/common-data/microsoft-prostate-cancer-data/`에서 파일 수를 맞춰 복사했다(PRECISE 54 · SICAPv2 37,589).

## 3. 만드는 순서

```bash
.venv/bin/python -B $P/code/build_pathology_atlas_catalog.py      # 1) 표 검사·적용 관계·읽기 문서·atlas.json
.venv/bin/python -B $P/code/build_pathology_figures.py            # 2) 그림 17·예시 10(약 20초)
.venv/bin/python -B $P/code/export_pathology_atlas_registry.py    # 3) H·I 생성 표
.venv/bin/python -B $P/code/check_pathology_atlas_registry.py     # 4) 23표 검사
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
- 우선 채울 곳: PRECISE IHC(HMWCK·AMACR) 슬라이드, 신경주위 침범·피막 밖 침범 그림(CC BY 논문), 핵소체·기저세포 판정 함수.
