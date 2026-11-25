# 영어 미러 유지보수 절차 v01

## 구조와 범위

한국어 URL은 그대로이며 대응 영어 URL 앞에 `/en`을 붙인다. 포털은 한국어와 영어 앱 인스턴스를 따로 만들고
마운트 상태를 인스턴스별로 보존한다. 도메인 데이터·등록 표·공급자 파일은 canonical 원문 한 벌만 둔다.
최종 HTML의 본문·접근성 속성·뷰어 JSON, 영어 검색 필드와 서비스가 만든 SVG 모식도 라벨을 번역한다.
외부 번역 API·브라우저 번역 서비스·번역용 인증 키가 필요하지 않다.

## 번역 카탈로그

위치: `portal/packages/medical-atlas-portal-web/src/medical_atlas_portal_web/data/english/`.
이 JSON은 사람이 관리하는 원문→영문 대응표다. 영역 등록 표에서 생성된 atlas JSON을 직접 고치는 것과 다르다.

- `portal.json`, `interface.json`: 포털·공통 UI·검색 결과·오류 화면·메타 설명.
- `names.json`: 원래 제공하던 영문 의학 용어.
- `retinal.json`, `mammography.json`, `pathology.json`: 정의·측정법·관계·캡션·검증 설명.
- `composed.json`: 원문 데이터와 템플릿이 조합하는 완전한 화면 문구.
- `schematics.json`: 서비스 SVG 모식도의 표시 라벨.
- `contexts.json`: 영역 ID 아래에 원문→영문 대응표를 두어 다의어를 보정한다(예: 유두 = optic disc / nipple).

원문이 바뀌면 새 원문을 키로 번역을 추가한다. 숫자·기준값·불확실성·보정 조건·전문가 검증 상태·출처·NC 예외 조건을 유지한다.
가능하면 원문의 문장 전체를 자연스러운 영어 문장으로 대응한다. 실제 한 글자 용어와 조사·낱말 일부를 혼동하지 않는다.
번역 문자열은 평문이며 HTML은 넣지 않는다. 의도적인 코드 목록과 원본 공급자 영상의 글자는 원문을 유지한다.

## 검사

저장소 루트에서:

```bash
portal/packages/medical-atlas-portal-web/.venv/bin/python -B -W ignore::ResourceWarning -m unittest discover -s portal/packages/medical-atlas-portal-web/tests
portal/packages/medical-atlas-portal-web/.venv/bin/python -B -W ignore::ResourceWarning -m medical_atlas_portal_web.export_static --out build/static_site
```

내보내기는 한국어·영어 전체 페이지를 순회하고 필터 조합·검색 페이지·파일을 만든다. 영어 검색 색인은
`en/_static/search_<domain>.json`이다. 공유 이미지·코드·스타일은 같은 정적 파일로 연결하고 번역 SVG는 영어 경로에 쓴다.
`untranslated English text`가 나오면 해당 URL과 원문에 맞는 번역을 추가한다. 링크가 없거나 미번역이 남으면 빌드를 실패시킨다.
언어 선택에 쓰는 `한국어`와 원본 코드 목록은 검사 예외다. 검색어 자체는 사용자의 입력 그대로 유지한다.

두 언어를 `/static_site/` 같은 하위 경로에서 열어 링크·필터·영어 검색·언어 전환을 확인한다.
예: `/static_site/en/mammography/search/?q=chest+wall&section=anatomy#sample`에서 언어를 바꿔 검색어·구역·앵커가 유지되는지 본다.
계산 표시 스위치의 상태 문구와 망막 층 뷰어 범례도 영어여야 한다. 서비스 SVG의 도형·좌표와 원본 영상·코드 바이트는 보존한다.

## 실행과 배포

번역 카탈로그는 프로세스에서 캐시하므로 수정 뒤 `medical-atlas-portal-web.service`를 다시 시작한다.
기존 8875 포트에서 `/en/`을 확인한다. 별도 서버를 운영할 필요가 없다.
GitHub Pages는 기존 `pages.yml`의 테스트·내보내기로 두 언어를 함께 게시한다. 생성된 정적 파일은 커밋하지 않는다.
저장소 지침에 따라 커밋·푸시는 사용자 요청이 있을 때 수행한다.
