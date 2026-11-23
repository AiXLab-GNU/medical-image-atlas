# 병리 영상 지도 (`domains/pathology`) — 전립선

전립선 조직병리(H&E·IHC)에서 **무엇이 보이고, 무엇을 어떻게 재며, 글리슨 등급과 어떤 질병의 근거인지**를 영상 위에 보여 주는 지도다.
망막·유방촬영과 같은 틀(지식 표 → 영상 출처 → 그림·측정 예시 → 웹 서비스)을 쓴다.

| 구성 | 내용 |
| --- | --- |
| 지식 표 | 영상 표현 6 · 해부 21 · 병변 24 · 측정 34(+판정 2) · 질병 9 · 관계 39 · 판정 체계 5(단계 16) · 근거 문헌 20 |
| 영상 | PRECISE(H&E·HMWCK–AMACR IHC 각 27장·화소 주석 7종·µm 보정) + SICAPv2(10× 패치·글리슨 패턴 주석) + PAR(생검 339장의 판독의 3명 등급), 모두 CC BY 4.0 → 그림 28 · 예시 15장(층 51: H&E 11 · IHC 4) |
| 측정 코드 | `packages/pathology-measures` — 31개 함수(조직 구성·패턴 비율·샘 모양·내강·핵·질감, IHC 기저세포 둘레·AMACR, 패턴 면적→글리슨 점수·등급군, kappa) |
| 웹 | `packages/pathology-atlas-web` — 포트 8881 |

- 등록 표: [docs/surveys/pathology_atlas_catalog/README.md](docs/surveys/pathology_atlas_catalog/README.md)
- 스키마: [docs/protocols/40_pathology_atlas_data_schema_v01_ko.md](docs/protocols/40_pathology_atlas_data_schema_v01_ko.md)
- 재구축: [docs/protocols/50_pathology_atlas_rebuild_runbook_v01_ko.md](docs/protocols/50_pathology_atlas_rebuild_runbook_v01_ko.md)

## 현재 한계

- 등급 재현성: PAR 판독의 쌍별 등급군 일치 55–64%·가중 kappa 0.75–0.84, SICAPv2 주석으로 계산한 등급군과 공급자 판정 일치 71.6%·가중 kappa 0.91(질병 페이지 · `i_grading_agreement`).
- IHC 색 분리는 서비스 기준(갈색 DAB OD 0.03 · 적색은 R≫G·B>G)이다. HGPIN은 기저세포가 조각나 둘레 지수가 낮게 나와 침윤암과 가르지 못한다(캡션에 적음).
- 핵은 헤마톡실린 색 분리 후 후보 검출이며 검증된 분할이 아니다. 뭉친 핵이 많은 비정형 관내 증식에서는 핵 측정을 빼고 보였다.
- SICAPv2는 화소 간격이 없어 화소 단위다. 샘당 내강 수는 주석 영역을 샘으로 본 근사라 값이 크다(사상 패턴 비교용).
- 정의·관계는 전문가 검토 전 초안이며 진단 도구가 아니다.
