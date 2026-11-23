# medical-atlas-portal-web

세 영역 지도(안과·망막 8877, 유방·유방촬영 8879, 전립선·병리 8881)로 들어가는 첫 페이지다(포트 8875).
각 영역 웹 패키지의 `data/*.json`과 `domains/<영역>/DOMAIN.yaml`을 읽어 영역별 항목 수와 대표 그림을 보여 주고,
영역 홈으로 연결한다. 영역 지도 자체는 따로 돌아가는 서비스이며 이 페이지는 데이터를 복사하지 않는다.

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e .
.venv/bin/medical-atlas-portal-web --port 8875
.venv/bin/python -B -m unittest discover -s tests
```

- 영역 주소는 요청한 주소의 호스트에 영역 포트를 붙여 만든다(SSH 터널에서 포트 번호를 그대로 쓰면 동작).
  다른 주소가 필요하면 `MEDICAL_ATLAS_URL_RETINAL`·`MEDICAL_ATLAS_URL_MAMMOGRAPHY`·`MEDICAL_ATLAS_URL_PATHOLOGY`로 지정한다.
- 각 영역 지도의 맨 위 줄은 이 페이지(`MEDICAL_ATLAS_URL_PORTAL`, 기본 포트 8875)와 다른 두 영역으로 가는 링크다.
