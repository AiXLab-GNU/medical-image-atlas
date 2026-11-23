# pathology-atlas-web

병리 영상 지도(전립선) 웹 서비스(Flask + Waitress). 망막·유방촬영 지도와 같은 화면 틀과 디자인을 쓴다.

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e .
.venv/bin/pathology-atlas-web --host 127.0.0.1 --port 8881     # 접속: ssh -N -L 8881:127.0.0.1:8881 <user>@<server>
.venv/bin/python -B -m unittest discover -s tests
```

| URL | 내용 |
| --- | --- |
| `/` | 홈(양성 샘·글리슨 패턴 모식도, 지도 구성) |
| `/anatomy/` | 전립선 구역 · 샘과 간질 · 세포 · 측정 기준 |
| `/lesions/` | 선암·글리슨 패턴 · 성장 양상 · 관내·상피내 병변 · 침범 · 암 모방 양성 병변 · 인공물 |
| `/measurements/` | 측정 목록, 영상에 측정을 표시하는 예(스위치), IHC 미구현 측정과 이유, 코드 내려받기 |
| `/diseases/` | 글리슨 패턴 · ISUP 등급군 · pT 병기 · 관내암 기준과 소견 |
| `/imaging/` | H&E · IHC |
| `/health` | 그림 파일 준비 상태(JSON) |

데이터: `data/atlas.json`(카탈로그 생성기), `data/masked_figures.json`·`data/measurement_examples.json`(그림 생성기). 그림 파일은
영역 `resources/datasets/`의 상대 링크에서 읽는다. 운영: 사용자 transient unit `pathology-atlas-web.service`(포트 8881).
