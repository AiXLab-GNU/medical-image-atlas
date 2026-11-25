# 유방촬영 영상 지도 재구축 절차 v01

작성: 2026-11-23 · 저장소 루트(medical-image-atlas)에서 실행한다. `M=domains/mammography`.

## 1. 환경

```bash
uv sync                                                       # 루트 .venv: numpy·scipy·scikit-image·pillow·pandas·openpyxl + mammography-measures(editable)
cd $M/packages/mammography-atlas-web && uv venv .venv && uv pip install --python .venv/bin/python -e . && cd -
```

## 2. 원자료(DMID, CC BY 4.0)

`resources/datasets/public_mammography/dmid/`에 공급자 파일을 그대로 둔다(`README.md`, `provider_archives/SHA256SUMS`).

```bash
D=resources/datasets/public_mammography/dmid/provider_archives; mkdir -p $D
# figshare 24522883 v2: ROI Masks.zip(43077142) · Reports.zip(43077244) · Metadata.xlsx(43078363)
#                       Pixel-level annotation.zip(43079566) · TIFF Images.zip(43082470)
curl -L -o "$D/TIFF Images.zip" https://ndownloader.figshare.com/files/43082470   # 나머지도 같은 방식
sha256sum -c $D/SHA256SUMS
```

압축은 `extracted/<이름>/`에 푼다. `TIFF Images.zip`은 ZIP64라 `unzip`이 실패하므로 Python `zipfile`로 푼다.
DICOM Images.zip(4.9 GB)은 받지 않는다(화소 간격이 없는 8비트 2차 캡처).

## 3. 만드는 순서

```bash
.venv/bin/python -B $M/code/build_mammography_atlas_catalog.py      # 1) 표 검사·적용 관계·읽기 문서·atlas.json
.venv/bin/python -B $M/code/build_mammography_figures.py            # 2) 그림 65·예시 16(약 1분, DBT·CEM·논문 패널은 build_mammography_paper_examples.py)
.venv/bin/python -B $M/code/export_mammography_atlas_registry.py    # 3) H·I 생성 표
.venv/bin/python -B $M/code/check_mammography_atlas_registry.py     # 4) 23표 검사(0 errors)
.venv/bin/python -B -m unittest discover -s $M/code/tests           # 5) 등록 표 테스트
(cd $M/packages/mammography-measures && ../../../../.venv/bin/python -B -m unittest discover -s tests)
(cd $M/packages/mammography-atlas-web && .venv/bin/python -B -m unittest discover -s tests)
```

## 4. 서비스

```bash
cd $M/packages/mammography-atlas-web
systemd-run --user --unit=mammography-atlas-web --property=Restart=on-failure --working-directory="$PWD" \
  "$PWD/.venv/bin/mammography-atlas-web" --host 127.0.0.1 --port 8879
# 접속(클라이언트): ssh -N -L 8879:127.0.0.1:8879 <user>@<server>
```

8878은 oculophenome-xai E118 지도 서버가 쓰고 있어 8879를 쓴다. 재부팅 뒤에는 위 명령으로 다시 시작한다.

## 5. 넓히는 방법

- 항목·측정·질병을 늘릴 때: A–E 표를 고치고 1)부터 다시 실행한다. ID는 바꾸지 않는다.
- 측정 함수를 늘릴 때: `packages/mammography-measures`에 함수를 넣고 `registry.py`에 `feature_id`를 등록한 뒤 테스트를 더한다.
- 영상을 늘릴 때: CC BY 2.0 이상·CC0 1.0 자료만 `g_image_sources`에 등록한다. 논문 그림은 원본 파일명 그대로
  `resources/datasets/mammography_atlas_provider_figures/`(새로 만듦)에 두고 `g_provider_figures`에 SHA-256을 고정한다.
- 논문 그림: Europe PMC에서 `LICENSE:"cc by"`로 찾고 PMC OA S3(`pmc-oa-opendata`)에서 원본 파일을 받아 `resources/datasets/mammography_atlas_provider_figures/`에 원래 이름으로 둔다. 생성기는 SHA-256이 표와 다르면 멈춘다. 저자의 노란 원·파란 화살표는 측정 입력에서 지우고(가장 가까운 표시 없는 화소로 채움) 화면에는 그대로 둔다.
- 우선 채울 곳: DBT 석회화 분포, 액와 림프절·피부 두께 함수, 자세 품질 판정.
