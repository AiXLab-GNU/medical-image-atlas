# medical-atlas-portal-web

의료영상 지도 하나의 채널(포트 8875): `/`는 3개 영역 홈, `/retinal/`·`/mammography/`·`/pathology/`는 같은 프로세스에 붙인
세 영역 지도다. 첫 페이지는 각 영역 웹 패키지의 `data/*.json`과 `domains/<영역>/DOMAIN.yaml`을 읽어 항목 수와 대표 그림을 보이며,
데이터를 복사하지 않는다.

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e .
for d in retinal mammography pathology; do
  uv pip install --python .venv/bin/python -e ../../../domains/$d/packages/$d-atlas-web
done
.venv/bin/medical-atlas-portal-web --port 8875
.venv/bin/python -B -m unittest discover -s tests
```

서비스(사용자 systemd):

```bash
P=$PWD
systemd-run --user --unit=medical-atlas-portal-web --property=Restart=on-failure --working-directory="$P" \
  "$P/.venv/bin/medical-atlas-portal-web" --host 127.0.0.1 --port 8875
```

- 영역 웹 패키지가 이 환경에 없으면 그 영역은 붙이지 않고 포트 링크(요청 호스트 + 8877/8879/8881)로 대신한다(`/health`의 `mounted`).
- `MEDICAL_ATLAS_URL_<PORTAL|RETINAL|MAMMOGRAPHY|PATHOLOGY>`로 링크 주소를 바꿀 수 있다.
- 영역 앱을 고친 뒤에는 이 서비스를 다시 시작한다(편집 가능 설치라 재설치는 필요 없다).

정적 버전: `.venv/bin/medical-atlas-export-static [--out 경로]`(기본 `<저장소>/build/static_site/`, 약 10초·75 MB). 같은 앱을 프로세스 안에서 돌려 `/`부터 모든 링크를 따라가 저장하고,
링크를 상대 경로로 바꾸며, 필터 조합 페이지·브라우저 검색(`static/static_site.js`)·`.nojekyll`·`404.html`을 넣는다. 닿지 않는 주소가 있으면 실패한다(`tests/test_export_static.py`).
