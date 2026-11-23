# 정량화 지도 독립 사이트 설계·운영

2026-11-20 · P003 프로젝트 공용 웹 표시물

## 현재 운영

이 문서 아래 내용은 초기 정적 서버 구현의 역사 기록이다. 현재는
[`packages/retinal-atlas-web/`](../../packages/retinal-atlas-web/README.md)의 다중 페이지
Flask/Waitress 서비스로 대체했다. 이전 정적 서버와 테스트는 새 앱으로 이관했으며
아래 옛 실행 명령은 사용하지 않는다. 현재 설정·검증은
[웹서비스 설계](40_retinal_atlas_web_architecture_v01_ko.md)에 기록한다.

## 사용자 요청과 범위

정량화 지도만 별도 사이트에서 사용하도록 프로젝트 포털과 실행·화면·주소를 분리한다.
기존 측정 개념 목록, 전체 지표 관계 지도, 질병 지도, 초기 Atlas, 합성 계산 예제를
전용 첫 화면과 공통 탐색 메뉴 아래 연결한다. 이는 웹 서비스 분리이며 새로운 연구
질문·study·실험을 만드는 구조 변경이 아니다.

## 구현 선택

기존 포털의 별도 메뉴만 추가하면 포털 서버에 계속 의존한다. 완전히 다른 frontend로
각 지도를 다시 만들면 이미 검증한 상호작용과 동결 provenance를 유지하기 어렵다.
따라서 Python 표준 라이브러리로 독립 읽기 전용 서버를 만들고 canonical HTML 다섯 개를
명시적 경로로 제공한다. 전용 첫 화면은 공통 메뉴와 iframe 작업 공간을 제공하며
각 화면을 새 탭에서 여는 동작도 지원한다. 원본 파일을 복사하거나 symlink하지 않는다.

## 파일과 검증 계획

- [x] `code/tests/test_quantification_map_site.py`: 정해진 HTML 제공, HEAD·GET 일치,
  경로 탐색·임의 파일·포털 API 비노출, POST 거절을 실제 HTTP 요청으로 검증한다.
- [x] `code/serve_quantification_maps.py`: 포털 모듈·DB를 사용하지 않는 독립 서버.
- [x] `docs/concept/ophthalmic_quantification_maps_v01_ko.html`: 독립 홈·공통 메뉴·지도 작업 공간.
- [x] README·STATUS·PROJECT.yaml에 실행 진입점과 별도 포트를 등록한다.
- [x] 전체 메뉴·iframe 상호작용·hash 링크·모바일·원본 불변·명명 감사를 확인한다.

## 실행과 접속

저장소 루트에서 실행한다.

```bash
.venv/bin/python -B projects/P003_ophthalmic_foundation_model_validation/code/serve_quantification_maps.py --port 8877
```

서버의 loopback에서만 제공한다. 로컬 PC의 SSH 터널:

```bash
ssh -N -L 8877:127.0.0.1:8877 jinhyun@158.130.55.26
```

브라우저: `http://127.0.0.1:8877/`

현재 `oculophenome-quantification-maps.service`라는 사용자 transient systemd 서비스로
실행 중이며 `Restart=on-failure`를 사용한다. 재부팅 자동 시작용 영구 unit 설치는 하지
않았다. 재부팅 후에는 위 Python 명령으로 다시 실행할 수 있다. 서비스 상태와 중지는
`systemctl --user status oculophenome-quantification-maps.service`,
`systemctl --user stop oculophenome-quantification-maps.service`로 확인·수행한다.

전용 서버는 프로젝트 포털의 로그인·설문·관리자 API를 제공하지 않는다. `/health`는
전용 서비스 상태만 반환한다. 등록된 HTML 이외의 저장소·resources·환자자료를 제공하지 않는다.
초기 190개 화면의 수치는 역사적 범위이며 최신 프로젝트 전체 지표 수로 표시하지 않는다.
62개 개념 묶음 및 양쪽 연결 16개는 탐색 분류 초안이고 계산 동등성 판정이 아니다.

## 검증 기록

작업 전 포트 8877은 사용되지 않았고 기존 프로젝트 포털은 8876에서 실행 중이었다.
기존 프로젝트 구조 계약·포털 study 집계·명명 감사 실패는
[측정 개념 페이지 검증 기록](40_measurement_concept_catalog_design_v01_ko.md)에 기록돼 있다.

- 독립 서버 HTTP 검사 3개 통과: 여섯 canonical HTML byte 일치·원본 hash 불변,
  HEAD·GET·health, 경로 탐색 및 저장소/포털 API 차단, POST 405를 확인했다.
- Chromium 실제 8877 접속에서 다섯 화면·개념 검색·공통 메뉴·지도 내부 페이지 이동·
  홈 복귀·hash 직접 접속·새 탭·모바일 가로 넘침을 확인했다. JavaScript 오류와
  8876 포털로의 네트워크 요청 모두 0건이다.
- 8877 `/`·`/health`, 기존 8876 `/api/health` 모두 HTTP 200을 확인했다.
- code 전체 검사 14개를 실행했다. 새 서버 3개·기존 개념 목록 4개는 통과했다.
  기존 `test_study_layout_contract`의 `test_e017_remains_the_only_project_common_experiment`,
  `test_project_manifest_declares_studies_and_common_engine`,
  `test_study_manifests_and_control_documents_are_canonical`에서 이전과 같은 4개 실패가
  남는다. E122·flip study·실험 증가에 따른 기존 기대값 차이이며 소유 구조는 바꾸지 않았다.
- 전역 명명 감사는 기존 `studies/laterality/docs/manuscript/outline.md` 1건만 보고한다.
  새 파일 위반은 없으며 요청한 통제 문서의 `git diff --check`는 통과했다.
