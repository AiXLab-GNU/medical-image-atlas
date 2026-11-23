# 의료영상 지도 하나의 채널 (`portal/`)

세 영역 지도를 **하나의 서비스·하나의 포트(8875)**로 묶는다. 영역(`domains/<영역>/`)이 아니므로 등록 표·원자료를 두지 않고
웹 패키지 하나만 둔다: [packages/medical-atlas-portal-web](packages/medical-atlas-portal-web/README.md).

| 주소 | 내용 | 웹 패키지 |
| --- | --- | --- |
| `/` | 3개 영역 홈(첫 페이지) | `medical-atlas-portal-web` |
| `/retinal/` | 안과 · 망막 영상 지도의 영역 홈 | `domains/retinal/packages/retinal-atlas-web` |
| `/mammography/` | 유방 · 유방촬영 영상 지도의 영역 홈 | `domains/mammography/packages/mammography-atlas-web` |
| `/pathology/` | 전립선 · 병리 영상 지도의 영역 홈 | `domains/pathology/packages/pathology-atlas-web` |

- 세 영역 앱은 이 프로세스 안에 경로로 붙는다(werkzeug `DispatcherMiddleware`). 영역 앱은 붙은 경로(`request.script_root`)를
  보고 화면의 루트 링크(`href`·`src`·`action="/…"`)와 이동(redirect) 주소 앞에 그 경로를 붙인다. 각 영역 지도 맨 위 줄은 첫 페이지와 다른 영역으로 가는 링크다.
- 영역 앱은 지금도 따로 띄울 수 있다(망막 8877·유방 8879·병리 8881). 그때는 링크가 포트로 연결된다. 따로 띄울 때 영역 앱 동작은 예전과 같다.
- 접속: `ssh -N -L 8875:127.0.0.1:8875 <user>@<server>` 하나로 세 영역을 모두 본다.
