# 망막 영상 정량 지도 웹서비스

망막 영상의 해부 구조 72개와 병변·소견 106개를 항목별 독립 URL로 제공하는 Flask/Waitress 앱.
포털과 실험 실행 코드 없이 설치·실행한다. 실제 영상은 공개 원문 그림 4장이며 항목과 연결된다.
내용은 목록 초안이며 항목마다 근거와 검토 상태를 표시한다.

## 실행

이 폴더에서:

```bash
uv sync --frozen
uv run --frozen retinal-atlas-web --port 8877
```

주소: <http://127.0.0.1:8877/>. 저장소 밖에서 실행할 때도 설치된 CLI나
`.venv/bin/python -m retinal_atlas_web`를 사용하면 된다. 기본 host는 loopback이다.

다른 서버에서는 먼저 이미지 루트를 지정한다. 원본 파일명은 아래 네 개를 유지한다.

```bash
export RETINAL_ATLAS_IMAGE_ROOT=/data/retinal_concept_reference_images
retinal-atlas-web --host 127.0.0.1 --port 8877
```

- `diagnostics-16-01555-g011.jpg`
- `679a4fcbad112.png`
- `journal.pone.0099690.g001.png`
- `jcm-11-03266-g002-550.jpg`
- `fnins-18-1415575-g001.webp`

저장소에서는 프로젝트의 `resources/datasets/retinal_concept_reference_images` 상대
resource view를 자동 탐색한다. 원본은 루트 `resources/`에 한 번만 보존하며 앱 폴더로
복사하지 않는다. `/health`는 네 이미지가 준비되면 200, 누락되면 503을 반환한다.

SSH 접속을 쓰는 경우 클라이언트에서:

```bash
ssh -N -L 8877:127.0.0.1:8877 <user>@<server>
```

## 페이지

| URL | 내용 |
| --- | --- |
| `/` | 소개·검색·두 진입점(해부학 지도, 병변 목록) |
| `/anatomy/` | 해부학 지도: 큰 구조 트리, 영역·구조·층·혈관·위치 기준 묶음, 영상 종류 필터 |
| `/anatomy/<항목>/` | 해부 구조 상세(예: `/anatomy/rnfl/`) |
| `/lesions/` | 병변 목록: 소견 묶음·영상 종류·이름 필터 |
| `/lesions/<항목>/` | 병변 상세(예: `/lesions/microaneurysm/`) |
| `/diseases/`, `/diseases/<질병>/` | 질병 목록과 상세: 진단·중증도·경과 관찰 등 역할별 소견을 어디서·어떤 영상으로·무엇을 측정하는지와 연결 |
| `/imaging/`, `/imaging/<영상>/` | 영상 종류(안저·OCT·OCTA·FAF·NIR·FA·ICGA): 정면 촬영 범위와 신호 깊이 모식도, 실제 영상(출처·라이선스), 보이는 구조·병변, 그 영상으로 재는 측정 |
| `/images/`, `/images/<영상>/` | 실제 영상 4장의 영상 읽기 페이지 |
| `/figures/<파일>` | 실제 영상·mask 겹침 그림(목록에 등록된 파일만) |
| `/search/?q=` | 한영 이름·약어·정의 검색 |
| `/sources/` | 영상 출처·라이선스와 정의·분류 문헌 |

항목 상세는 실제 영상(위치 표시 또는 원문 패널 잘라 보기) → 정의·위치·볼 수 있는 영상 → 영상별로 보이는 모습 →
관찰 특징·측정할 수 있는 속성 → 관련 병변·질병 → 출처와 검토 상태 순서다. 기본 내용은 JS 없이 표시된다.
예전 샘플 주소(`/anatomy/retinal-layers/`, `/lesions/oct/`, `/lesions/atrophy/`, `/fundus/`)는 `/images/`로 넘긴다.

콘텐츠 파일:

- `data/atlas.json`: 해부 구조·병변 항목. 프로젝트의 조사 표(`docs/surveys/retinal_atlas_catalog/`)에서
  `code/build_retinal_atlas_catalog.py`가 생성한다. 손으로 고치지 않는다.
- `data/catalog.json`: 실제 영상 4장의 영상 읽기 내용.
- `data/image_links.json`: 영상 위 표시(점·패널·전체)와 항목 ID의 연결.
- `data/masked_figures.json`: 실제 영상·mask 그림 152쌍의 항목 연결·출처·라이선스·변환(픽셀 없음). 그림 파일은
  `RETINAL_ATLAS_MASKED_ROOT`(기본: 프로젝트 `resources/datasets/retinal_atlas_masked_figures`)에서 읽는다.
  영상 종류 페이지의 실제 영상(`/modality-figures/<이름>`)은 `data/modality_figures.json`에 선언된 파일만
  `RETINAL_ATLAS_MODALITY_ROOT`(기본: 프로젝트 `resources/datasets/retinal_atlas_modality_figures`)에서 읽는다.
  `code/build_atlas_masked_figures.py`가 IDRiD·Refined IDRiD(CC BY 4.0)·AMD-SD(CC0)에서 생성한다.
- `data/measurement_examples.json`: 측정 목록의 표시 예시 89장(안저·광각 안저·FA·FAF·근적외선·ICGA·OCT·OCTA, 영상 종류·부위별)과
  측정 층 239개로 측정 160개를, 지도에서 측정마다 정한 영상 종류 모두에서 덮는다. 층마다 retinal-measures 함수를 실제로 실행한 값을
  담고(계산 코드가 없는 정성 항목은 상태 `reading`의 판독 층), 측정 목록에서 스위치로 켜고 끈다. 그림 파일은
  `RETINAL_ATLAS_MEASURE_ROOT`(기본: 프로젝트 `resources/datasets/retinal_atlas_measurement_examples`)에서 읽으며
  `code/build_measurement_examples.py`가 생성한다.
- 측정의 대상 질병(`app.measurement_diseases`): `atlas.json`의 질병 관계·등급 단계가 측정을 직접 가리키면 그 질병을, 아니면 측정 대상
  병변·구조의 질병 관계를 써서 측정 목록 줄과 측정 코드 페이지에 표시한다. 관계 원본은 `docs/surveys/retinal_atlas_catalog/e_disease_findings_v01.csv`다.
- 측정 코드 내려받기(`/code/<패키지>.zip`, `/code/<패키지>/<파일>`, `/measurements/code/<측정 ID>/`):
  `RETINAL_ATLAS_PACKAGES_ROOT`(기본: 프로젝트 `packages/`)의 retinal-measures·ophthalmic-quantification 원본을 복사 없이
  그대로 내려준다. 경로가 없으면(예: 컨테이너) 링크를 보이지 않는다. `.py·.md·.toml` 등 소스만, 패키지 안 경로만 허용한다.
- `templates/_schematic.html`: 직접 그린 오른눈 후극부 모식도(SVG). 후극부·황반·중심와·시신경유두·컵·유두주위 망막·
  혈관 아케이드 등 20개 항목에서 해당 영역을 강조하고 하위 영역은 점선으로 보여준다. 실제 영상이 아니며 비율은 대략적이다.
- `templates/_oct_schematic.html`: 중심와를 지나는 OCT 수평 단면 모식도. 유리체부터 공막까지 층·band·경계와 측정 구간
  37개 항목을 강조한다. `code/build_oct_schematic.py`가 생성하므로 손으로 고치지 않는다.

`src/retinal_atlas_web/app.py`는 factory와 라우트, `templates/`는 페이지, `static/`은 공통 CSS·뷰어를 소유한다.

## 검사와 배포

```bash
uv run --frozen python -B -m unittest discover -s tests -v
docker build -t retinal-atlas-web:0.1.0 .
docker run --rm --name retinal-atlas-web -p 127.0.0.1:8877:8877 \
  --mount type=bind,src=/absolute/image/directory,dst=/data/retinal_concept_reference_images,readonly \
  retinal-atlas-web:0.1.0
```

이미지 디렉터리는 UID 10001이 읽을 수 있어야 한다. 컨테이너에는 원본을 포함하지
않는다. `uv.lock`과 해시가 포함된 `requirements.txt`는 같은 의존성 집합을 잠근다.
배포 시 Waitress 앞의 reverse proxy에서 도메인·HTTPS를 구성할 수 있다.
현재 서버 운영은 로컬 포트 8877이며 외부 도메인 배포를 완료한 상태는 아니다.

정상 OCT(Prus-Ludwig 외 2026, Diagnostics 16:1555, Figure 11)와 나머지 세 그림은 CC BY 4.0이다. 「정상 망막층(다른 예)」의
Yorston 2025 그림만 CC BY-NC-SA 4.0 예외(LICENSE-docs.md)로, 서비스 표시 없이 원문 그대로 싣고 「비영리 전용」 배지를 단다.
이미지의 출처 표시를 보존한다. 색상 점과 금색 패널 테두리는 설명용이며
병변 분할이나 실제 계측 결과가 아니다.

설계·운영 기록: [프로젝트 문서](../../docs/concept/40_retinal_atlas_web_architecture_v01_ko.md).

## 현재 로컬 운영

8877은 사용자 transient systemd unit `retinal-atlas-web.service`로 실행한다.
`Restart=on-failure`를 사용하며 `systemctl --user status retinal-atlas-web.service`와
`systemctl --user restart retinal-atlas-web.service`로 관리한다.
재부팅 자동 시작용 영구 unit은 설치하지 않았다. 재부팅 후에는 위 실행 명령으로
시작한다. 이전 `oculophenome-quantification-maps.service`는 중지했다.

## 다음 설계 검토

[서비스 요구사항·개념 설계](../../docs/concept/40_retinal_atlas_service_requirements_v01_ko.md)는
해부학·병변·임상 활용·계측 기술·진단 도구 사용·관계 지도를 정의하는 검토 초안이다.
현재 구현 범위와 구분한다. 새 요구에 따른 화면 변경은 아직 적용하지 않았다.
