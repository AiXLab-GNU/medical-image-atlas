# 병리 영상 지도 (`domains/pathology`) — 전립선

전립선 조직병리(H&E·IHC)에서 **무엇이 보이고, 무엇을 어떻게 재며, 글리슨 등급과 어떤 질병의 근거인지**를 영상 위에 보여 주는 지도다.
망막·유방촬영과 같은 틀(지식 표 → 영상 출처 → 그림·측정 예시 → 웹 서비스)을 쓴다.

| 구성 | 내용 |
| --- | --- |
| 지식 표 | 영상 표현 6 · 해부 21 · 병변 24 · 측정 34(+판정 2) · 질병 9 · 관계 39 · 판정 체계 5(단계 16) · 근거 문헌 20 |
| 영상 | PRECISE(H&E·HMWCK–AMACR IHC 각 27장·화소 주석 7종·µm 보정) + SICAPv2(10× 패치·글리슨 패턴 주석) + PAR(생검 339장의 판독의 3명 등급), 모두 CC BY 4.0, 그리고 CC BY 4.0 논문 9편의 H&E 패널 25개 → 그림 54 · 예시 16장(층 61: H&E 12 · IHC 4) |
| 측정 코드 | `packages/pathology-measures` — 등록 함수 32개(조직 구성·패턴 비율·샘 분할·샘 모양·내강·핵·질감, IHC 기저세포 둘레·조각 밀도·AMACR, 패턴 면적→글리슨 점수·등급군, kappa)와 보조 모듈 `stain`(Macenko 정규화)·`register`(H&E–IHC 정합) |
| 측정 검증 | `code/evaluate_pathology_measures.py` → 웹 `/validation/` · 표 `i_measure_validation` |
| 웹 | `packages/pathology-atlas-web` — 포트 8881 |

- 등록 표: [docs/surveys/pathology_atlas_catalog/README.md](docs/surveys/pathology_atlas_catalog/README.md)
- 스키마: [docs/protocols/40_pathology_atlas_data_schema_v01_ko.md](docs/protocols/40_pathology_atlas_data_schema_v01_ko.md)
- 재구축: [docs/protocols/50_pathology_atlas_rebuild_runbook_v01_ko.md](docs/protocols/50_pathology_atlas_rebuild_runbook_v01_ko.md)

## 현재 한계

- 등급 재현성: PAR 판독의 쌍별 등급군 일치 55–64%·가중 kappa 0.75–0.84. SICAPv2 주석으로 계산한 등급군과 공급자 판정 일치 74.8%(±1 이내 94.8%, kappa 0.692, 가중 kappa 0.942) — ISUP 생검 규칙의 '더 낮은 소량 패턴 제외'를 바로잡고 30 화소 미만 패턴 조각을 뺀 값이다(이 화소 기준은 같은 자료로 정함). 규칙별 비교는 질병 페이지와 `i_grading_agreement`.
- IHC 색 분리는 서비스 기준(갈색 DAB OD 0.03 · 적색은 R≫G·B>G)이다. 기저세포 유무는 샘 경계 100 µm당 갈색 조각(≥15 µm²) 수 0.35를 기준으로 본다. 슬라이드별 가장 큰 영역(53 창)에서 정하고 2–4번째 영역(132 창)에서 확인했다(AUC 0.995, 침윤암 없음 50/52, 나머지 있음 78/80). 같은 슬라이드라 외부 검증은 아니다. IHC 화소 간격은 0.177 µm/px로 H&E(0.243)와 다르다.
- 샘 분할(`glands.segment_glands`)은 헤마톡실린을 6 µm 흐린 뒤 조직 전체 Otsu로 상피를 잡고 닫힌 내강을 채운 연결 성분이다. 양성 샘 주석과 대조하면 화소 Dice 0.733이지만 샘 단위 F1은 0.17(IoU≥0.5)이다 — 붙은 샘을 묶고 큰 내강을 다 채우지 못한다. 샘 개수·샘별 값은 참고용이다. Macenko 정규화는 Dice를 낮춰(0.707) 쓰지 않는다.
- 논문 그림 패널은 표시 없이 저자 캡션대로 싣는다. 신경주위 침범 그림은 전립선 선양낭성암 증례이고, 결절성 과형성은 아직 그림이 없다.
- H&E–IHC 정합(`register.align`)은 조직 조각 단위 강체 정합이다(조직 Dice 중앙값 0.655, 0.7 이상 12/27 슬라이드). 연속 절편의 샘은 하나하나 대응하지 않아 '같은 부위' 비교에만 쓴다.
- 핵소체: 40× 자동 검출을 시도했으나 종양과 양성 샘을 가르지 못해(AUC 0.28) 판독 항목으로 둔다(`nuclei.nucleolus_prominence`, 실험용·등록 안 함).
- 핵은 헤마톡실린 색 분리 후 후보 검출이며 검증된 분할이 아니다. 뭉친 핵이 많은 비정형 관내 증식에서는 핵 측정을 빼고 보였다.
- SICAPv2는 화소 간격이 없어 화소 단위다. 샘당 내강 수는 주석 영역을 샘으로 본 근사라 값이 크다(사상 패턴 비교용).
- 정의·관계는 전문가 검토 전 초안이며 진단 도구가 아니다.
