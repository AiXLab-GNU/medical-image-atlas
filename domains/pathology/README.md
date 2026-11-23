# 병리 영상 지도 (`domains/pathology`) — 전립선

전립선 조직병리(H&E·IHC)에서 **무엇이 보이고, 무엇을 어떻게 재며, 글리슨 등급과 어떤 질병의 근거인지**를 영상 위에 보여 주는 지도다.
망막·유방촬영과 같은 틀(지식 표 → 영상 출처 → 그림·측정 예시 → 웹 서비스)을 쓴다.

| 구성 | 내용 |
| --- | --- |
| 지식 표 | 영상 표현 6 · 해부 21 · 병변 24 · 측정 32(+판정 2) · 질병 9 · 관계 34 · 판정 체계 5(단계 16) · 근거 문헌 19 |
| 영상 | PRECISE(H&E 27장·화소 주석 7종·µm 보정) + SICAPv2(10× 패치·글리슨 패턴 주석), 모두 CC BY 4.0 → 그림 17 · 예시 10장(층 34) |
| 측정 코드 | `packages/pathology-measures` — 25개 함수(조직 구성·패턴 비율·샘 모양·내강·핵·질감) |
| 웹 | `packages/pathology-atlas-web` — 포트 8881 |

- 등록 표: [docs/surveys/pathology_atlas_catalog/README.md](docs/surveys/pathology_atlas_catalog/README.md)
- 스키마: [docs/protocols/40_pathology_atlas_data_schema_v01_ko.md](docs/protocols/40_pathology_atlas_data_schema_v01_ko.md)
- 재구축: [docs/protocols/50_pathology_atlas_rebuild_runbook_v01_ko.md](docs/protocols/50_pathology_atlas_rebuild_runbook_v01_ko.md)

## 현재 한계

- IHC 영상이 없다(PRECISE IHC는 원 zip 52 GB 안에 있어 아직 받지 않음) → IHC 측정은 "미구현"으로 표시.
- 핵은 헤마톡실린 색 분리 후 후보 검출이며 검증된 분할이 아니다. 뭉친 핵이 많은 비정형 관내 증식에서는 핵 측정을 빼고 보였다.
- SICAPv2는 화소 간격이 없어 화소 단위다. 샘당 내강 수는 주석 영역을 샘으로 본 근사라 값이 크다(사상 패턴 비교용).
- 정의·관계는 전문가 검토 전 초안이며 진단 도구가 아니다.
