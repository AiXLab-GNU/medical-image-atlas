# 의료영상 지도 첫 페이지 (`portal/`)

세 영역 지도를 한 페이지에서 고르는 입구다. 영역(`domains/<영역>/`)이 아니므로 등록 표·원자료를 두지 않고,
웹 패키지 하나만 둔다: [packages/medical-atlas-portal-web](packages/medical-atlas-portal-web/README.md) — 포트 8875.

| 영역 | 지도 | 포트 |
| --- | --- | --- |
| 안과 | 망막 영상 지도(`domains/retinal`) | 8877 |
| 유방 | 유방촬영 영상 지도(`domains/mammography`) | 8879 |
| 전립선 | 병리 영상 지도(`domains/pathology`) | 8881 |

홈은 두 층이다: 이 페이지가 **3개 영역 홈**이고, 각 영역 지도의 `/`가 **영역 홈**이다. 영역 지도 맨 위 줄에서
이 페이지와 다른 영역으로 갈 수 있다.
