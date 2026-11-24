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

## 두 가지 운용: 동적·정적

같은 원본(지식 표·그림·템플릿·Flask 앱)에서 두 결과물을 만든다. 정적 결과물은 커밋하지 않는다(`build/`, git 제외).

| | 동적 버전 | 정적 버전 |
| --- | --- | --- |
| 만드는 법 | `medical-atlas-portal-web --port 8875` | `medical-atlas-export-static` → `build/static_site/` |
| 올리는 곳 | 파이썬이 돌아가는 서버(연구실 서버 8875) | 아무 정적 웹서버(GitHub Pages, 학교 웹서버, 폴더째 복사) |
| 주소 경로 | `/`·`/retinal/`… (붙은 경로는 자동) | 모든 링크가 상대 경로라 어느 경로에 놓아도 동작 |
| 목록 필터(`?img=`·`?cat=`·`?level=`…) | 서버가 거름 | 링크로 닿는 모든 조합을 미리 만든 페이지(`<경로>/_q/<조건>/`) |
| 검색·목록 이름 찾기(`?q=`) | 서버가 찾음 | 브라우저가 `_static/search_<영역>.json`에서 같은 규칙으로 찾음 |
| 코드 내려받기 | 서버가 파일을 보냄 | 미리 저장한 파일(`download` 링크) |
| 서버가 꼭 필요한 기능 | 넣을 수 있음 | 넣을 수 없음 |

정적 사이트 확인: `python3 -m http.server 8874 --bind 127.0.0.1 --directory build/static_site` 후 `http://127.0.0.1:8874/`
(`build`에서 띄우면 `http://127.0.0.1:8874/static_site/` — 하위 경로에 놓인 경우도 링크가 상대 경로라 그대로 동작한다).

GitHub Pages: `.github/workflows/pages.yml`이 main에 push할 때마다(또는 Actions 탭에서 수동 실행) 정적 버전을 만들어 게시한다.
처음 한 번 저장소 Settings → Pages → Build and deployment → Source를 **GitHub Actions**로 바꾼다.
