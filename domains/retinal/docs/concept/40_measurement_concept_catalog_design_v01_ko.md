# 측정 개념 목록 독립 페이지 설계·실행 기록

2026-11-20 · P003 project-common · 기존 E017 및 E115/E118 정의의 탐색용 재분류

## 목적과 범위

사용자가 승인한 측정 개념→구현별 항목 구조를 독립 한국어 HTML로 제공한다.
190개 목록과 178개 목록을 출처별로 보존하면서, 같은 측정 대상을 탐색용 개념으로
묶는다. 개념 묶음은 임상적으로 검증된 독립 개념 수나 계산 동등성 판정이 아니다.
368은 두 출처의 등록 행 수이며 중복 제거된 지표 수가 아니다.

## 접근과 구현 선택

- 개념 설명만 적는 정적 문서는 구현 출처를 대조하기 어렵다.
- 기존 190개 Atlas를 확장하면 역사적 범위와 새로운 분류가 혼재한다.
- 선택: 기존 포털에 별도 route를 추가하고, 외부 의존성 없는 독립 HTML을 생성한다.
  검색·분야·출처·양쪽 목록 연결 필터, 개념별 펼침 표, JSON 내려받기를 제공한다.

페이지와 생성기는 프로젝트 소유다. Study의 동결 정의·원값·결과는 읽기만 한다.
페이지에는 측정 정의와 출처만 포함하며 원영상·환자 정보·성능 및 사례값을 싣지 않는다.
출처 파일의 SHA-256을 생성 자료에 기록한다. 새 개념 ID는 이 탐색 분류에만 쓰며
E118의 CM/MC ID를 대체하지 않는다. 같은 이름·분야만으로 계산 동등성을 선언하지 않는다.

## 파일과 실행 계획

- [x] `code/tests/test_measurement_concept_catalog.py`: 출처별 전수 보존, 개념 대응과
  비동등 측정 분리, 공개 필드 제한, 미등록 항목 실패를 검증한다.
- [x] `code/build_measurement_concept_catalog.py`: 표준 라이브러리만으로 두 CSV를 읽고
  명시적 개념 분류와 재현 가능한 단일 HTML을 생성한다.
- [x] `docs/concept/ophthalmic_measurement_concepts_v01_ko.html`: 검색 가능한 독립 페이지.
- [x] 포털 allowlist route, 프로젝트 README·STATUS·PROJECT.yaml에 진입점을 등록한다.
- [x] 전수 대응·링크·HTML/JS·포털 회귀·명명 감사를 실행한다.

## 검증 경계와 실행 기록

사전 명명 감사: 기존 `studies/laterality/docs/manuscript/outline.md` 1건 위반.
기존 작업이 많은 현재 checkout에서 요청 페이지를 추가하며 기존 수정은 보존한다.
외부 호스팅·원격 업로드 없이 저장소와 포털 경로를 준비했다.
기존 임상 gate와 각 실험의 해석 제한은 변경하지 않는다.

## 실행 판단과 검증

- 현재 checkout에서 작업: 기존 미커밋 연구자료를 입력으로 사용하고 요청한 저장소의
  포털에서 바로 열기 위해 기존 파일 수정은 좁은 삽입으로 제한했다.
- 서비스 반영: 실행 중인 8876 포털은 새 allowlist를 읽지 않아 처음에는 404였다.
  승인된 `systemctl --user restart oculophenome-research-portal.service` 실행 후 새 페이지와
  `/api/health` 모두 HTTP 200을 확인했다. 외부 공개·계정·설문 변경은 없다.
- 결과: 62개 탐색 묶음, 양쪽 목록에 연결된 묶음 16개, 출처별 등록 190/178행.
- 단위 검사 4개 및 새 portal route 검사 통과. 개념 연결은 단순 이름 일치가 아니라
  정의를 따른다. 독립 검토에서 발견한 `v_length_density` 오분류는 길이 밀도 정의를
  확인하고 실패하는 회귀 사례를 먼저 추가한 뒤 `skeleton_density`로 교정했다.
- Chromium에서 전체 표시·검색·동시 필터·빈 결과·초기화·분야 이동·전체 펼침/접기·
  hash 링크·JSON 저장·390px 모바일 가로 넘침 등을 포함한 14개 시나리오 통과.
- 전체 포털 검사: 20개 중 18개 통과. 기존 study 수 2를 기대하지만 현재 3인
  `CatalogTest.test_catalog_reads_canonical_project_sources`와
  `PortalApiTest.test_health_static_and_survey_workflow`는 실패한다.
- 프로젝트 code 전체 검사: 11개 실행, 기존 구조 계약 3개 test method에서 4개 실패
  (E122 공통 실험 추가, flip study 추가, laterality/DR 실험 목록 증가에 따른 기대값 불일치).
  `test_e017_remains_the_only_project_common_experiment`,
  `test_project_manifest_declares_studies_and_common_engine`,
  `test_study_manifests_and_control_documents_are_canonical`이며 본 페이지 변경으로
  해당 소유 구조를 바꾸지 않았다.
- 명명 감사: 새 경로 위반 없음. 전역 감사에는 사전 검사와 같은 기존 `outline.md`
  1건이 남는다. 요청 파일의 `git diff --check`는 통과했다. 전역 diff에는 기존
  원고 SVG의 trailing whitespace가 있어 기존 그림은 수정하지 않았다.
