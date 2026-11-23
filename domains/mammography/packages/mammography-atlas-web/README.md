# mammography-atlas-web

유방촬영 영상 지도 웹 서비스(Flask + Waitress). 망막 지도(`retinal-atlas-web`)와 같은 화면 틀과 디자인을 쓴다.

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e .
.venv/bin/mammography-atlas-web --host 127.0.0.1 --port 8879     # 접속: ssh -N -L 8879:127.0.0.1:8879 <user>@<server>
.venv/bin/python -B -m unittest discover -s tests
```

| URL | 내용 |
| --- | --- |
| `/` | 홈(CC·MLO 모식도, 지도 구성) |
| `/anatomy/` | 위치 구역 · 조직층 · 측정 기준(클릭 가능한 CC·MLO 모식도) |
| `/lesions/` | 종괴 · 석회화 · 구조왜곡·비대칭 · 동반 소견 · 치료 흔적 · CEM 증강 |
| `/measurements/` | 측정 목록, 영상에 측정을 표시하는 예(스위치), DBT·CEM 미구현 측정과 이유, 코드 내려받기 |
| `/diseases/` | 질병별 판정 체계(BI-RADS 범주·유방 구성·석회화·AJCC T 등)와 소견 |
| `/imaging/` | FFDM · DBT · CEM |
| `/health` | 그림 파일 준비 상태(JSON) |

데이터: `data/atlas.json`(카탈로그 생성기), `data/masked_figures.json`·`data/measurement_examples.json`(그림 생성기). 그림 파일은
영역 `resources/datasets/`의 상대 링크(`mammography_atlas_masked_figures`·`mammography_atlas_measurement_examples`)에서 읽는다.
현재 운영은 사용자 transient unit `mammography-atlas-web.service`(포트 8879, Restart=on-failure)다. 재부팅 뒤에는 다시 시작한다.
