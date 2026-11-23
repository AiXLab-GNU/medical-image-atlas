# 망막 영상 정량 지도 웹서비스 설계·구현 계획

2026-11-20 · 소유: P003 프로젝트 공통 패키지

## 이후 요구사항 검토

이 문서는 현재 실행 중인 다중 페이지 샘플 앱의 구현 기록이다. 지식 서비스의 목적과
내용 범위는 이후 작성한 [서비스 요구사항 초안](40_retinal_atlas_service_requirements_v01_ko.md)에서
재검토 중이다. 아래 페이지 구성은 새 요구사항에 대한 확정 설계로 간주하지 않는다.

## 요구사항과 구조

사용자 요청은 독립 폴더에서 실행·배포할 수 있는 다중 페이지 서비스다.
전체 수록을 보류하고 기존 네 실제 영상 샘플과 일반화 분류 청사진만 이관한다.
제목은 ‘망막 영상 정량 지도’, 소개는 한 문장으로 유지한다.

설치형 앱은 `packages/retinal-atlas-web/`가 소유한다. Flask가 페이지별 HTML을
서버에서 렌더링하고 Waitress가 HTTP를 제공한다. 공통 템플릿·CSS·이미지 뷰어와
콘텐츠 JSON을 분리한다. 포털, 설문 DB, 실험 CSV에 런타임 의존하지 않는다.

| URL | 역할 |
| --- | --- |
| `/` | 간단한 소개와 각 영역 진입점 |
| `/blueprint/` | 대상 × 속성 × 관측 방법과 9개 대상군 |
| `/anatomy/` | 해부 구조 샘플 목록 |
| `/anatomy/retinal-layers/` | 정상 OCT, 큰 구조 3개·세부 색상 9개 |
| `/anatomy/choroid/` | 맥락막과 원문 혈관층 그림 |
| `/lesions/` | 병변 샘플 목록 |
| `/lesions/oct/` | OCT 병변의 개별 패널 표시 |
| `/lesions/atrophy/` | 안저·FAF·OCT 위축 비교 |
| `/fundus/` | 안저 전용 콘텐츠의 다음 수록 범위 |
| `/sources/` | 원본 출처·라이선스·표시 방식 |
| `/health` | 이미지 가용성에 따른 준비 상태 |

각 URL은 독립 문서이며 직접 접속·새로고침·뒤로가기를 지원한다.
JS는 색상 전환, 병변 패널 선택, 원본 확대에만 사용한다.
기본 설명·이미지·출처는 JS 없이도 렌더링한다.

원본 네 이미지는 중앙 `resources/`에 그대로 유지한다. 고정 allowlist URL로만
제공한다. 배포에서는 `RETINAL_ATLAS_IMAGE_ROOT`에 해당 디렉터리를 지정하거나
컨테이너에 읽기 전용 마운트한다. 제공 그림 중 정상 OCT는 CC BY-NC-SA 4.0이다.
공개·상업 배포 시 해당 이미지의 라이선스 조건을 따라야 한다.

## 구현 순서

- [x] 앱 라우팅·정적 자료·준비 상태의 실패 테스트 작성 및 실행.
- [x] 데이터 이관, 앱 factory, 페이지 템플릿, 공통 스타일·뷰어 구현.
- [x] 독립 가상환경·잠금 파일·컨테이너와 실행 안내 구성.
- [x] 전체 앱 테스트와 브라우저 직접 진입·탐색·모바일·뷰어 검사.
- [x] localhost 8877 서비스 교체, 이전 단일 HTML은 history로 이동.
- [x] README·STATUS·PROJECT.yaml·활성 링크 갱신, 명명 감사.

## 검증 중점

잘못된 URL과 경로 탈출은 404, 변경 요청은 405다. 이미지가 없으면 health는 503이다.
이미지 루트는 실행 디렉터리와 독립적이다. 네 이미지의 원본 바이트·출처·라이선스를
확인한다. 정상 OCT 색상은 위치 안내이고 병변 표시와 분리하며, 병변 테두리는
원문 패널의 강조라는 범위를 유지한다. 모바일 가로 넘침과 키보드 확대 닫기를 검사한다.

## 완료·검증 기록

- `retinal-atlas-web`의 unittest 6개 통과: 10개 별도 문서, JS 없이 설명·영상·출처,
  네 이미지 원본 바이트·HEAD, 미등록 경로·변경 요청 차단, 누락 시 503, 공통 자산·CSP.
- Chromium에서 최종 8877의 10개 URL을 직접 열고 문서 이동·새로고침·뒤로가기를
  확인했다. 3/9 색상·토글·원본 dialog·Escape·7개 병변 패널 선택 및 마지막 패널의
  자동 스크롤이 동작했다. 390px 전 페이지 가로 넘침·JS 오류는 각각 0건이었다.
- 독립 코드 검토에서 차단·중요 결함은 발견되지 않았다.
- Docker 이미지 빌드 및 비루트 UID 10001 실행 성공. 저장소 코드가 없는 컨테이너에
  네 원본 디렉터리만 읽기 전용 마운트해 10개 페이지와 원본 SHA-256 일치를 확인했다.
  Docker healthcheck는 healthy였다. 검사 컨테이너는 종료했다.
- 새 `retinal-atlas-web.service`가 localhost 8877에서 active, `/health` 200이다.
  기존 포털 8876 `/api/health`도 200이다. 이전 서버·테스트는 패키지로 대체하고 삭제했다.
  현재 unit은 transient이며 재부팅 자동 시작 설정은 별도다.
- 전역 명명 감사에는 기존 `studies/laterality/docs/manuscript/outline.md` 1건이 남는다.
  신규 패키지 경로 위반은 없다.
- P003 code 전체 unittest 11개 실행 중 기존 구조 계약에서 4개 실패가 유지됐다:
  `test_e017_remains_the_only_project_common_experiment`,
  `test_project_manifest_declares_studies_and_common_engine`,
  `test_study_manifests_and_control_documents_are_canonical`의 laterality·DR 두 subtest.
  E122·flip study·늘어난 실험에 관한 이전 기대값 차이이며 새 웹앱 검사는 모두 통과한다.

## 이관과 다음 결정

이전 `docs/concept/retinal_measurement_blueprint_v01_ko.html`은 동일 바이트로
`docs/history/retinal_measurement_blueprint_v01_ko.html`로 이동했다. 현재 콘텐츠는
`src/retinal_atlas_web/data/catalog.json`, 페이지·뷰어 구현은 패키지에만 있다.
현재 범위는 사용자 평가 대기다. 안저 전용 자료·OCTA·전체 개념·190/178의 전수 매핑은
평가 결과에 따라 다음 단계에서 채운다. 외부 도메인·HTTPS 공개 배포를 한 상태는 아니다.
