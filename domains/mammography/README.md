# 유방촬영 영상 지도 (`domains/mammography`)

2D 디지털 유방촬영(FFDM)·디지털 유방단층합성(DBT)·조영증강 유방촬영(CEM)에서 **무엇이 보이고, 무엇을 어떻게 재며, 어떤 판정과
질병의 근거인지**를 영상 위에 보여 주는 지도다. 망막 지도와 같은 틀(지식 표 → 영상 출처 → 그림·측정 예시 → 웹 서비스)을 쓴다.

| 구성 | 내용 |
| --- | --- |
| 지식 표 | 영상 표현 13 · 해부 28 · 병변 37 · 측정 61(+판정 1) · 질병 21 · 질병–소견 관계 74 · 판정 체계 10(단계 44) · 근거 문헌 25 |
| 영상 | DMID(Oza 외 2023, CC BY 4.0) 510장 + CC BY 4.0 논문 그림 8장(DBT 4 · CEM 4) → 항목 그림 32 · 측정 표시 예시 16장(층 59: FFDM 9 · DBT 3 · CEM 4) |
| 측정 코드 | `packages/mammography-measures` — 40개 측정 함수(유방 경계·밀도·대흉근·후유두선, 종괴 모양·경계, 석회화 군집, 구조왜곡, 위치, CEM 증강 강도 비·비종괴 증강 범위) |
| 웹 | `packages/mammography-atlas-web` — 포트 8879 |

- 등록 표: [docs/surveys/mammography_atlas_catalog/README.md](docs/surveys/mammography_atlas_catalog/README.md)
- 스키마: [docs/protocols/40_mammography_atlas_data_schema_v01_ko.md](docs/protocols/40_mammography_atlas_data_schema_v01_ko.md)
- 재구축: [docs/protocols/50_mammography_atlas_rebuild_runbook_v01_ko.md](docs/protocols/50_mammography_atlas_rebuild_runbook_v01_ko.md)
- 읽기 문서: [docs/surveys/10_mammography_atlas_catalog_survey_v01_ko.md](docs/surveys/10_mammography_atlas_catalog_survey_v01_ko.md)

## 현재 한계

- DMID에 화소 간격이 없어 길이·면적은 화소 단위다. 환자 번호가 없어 CC·MLO 짝 예시는 연속 번호를 같은 유방으로 가정했다.
- DBT·CEM은 CC BY 논문 그림으로 채웠다. 병변 범위는 저자의 원·화살표 주변을 서비스가 추정한 것이고(저자 ROI가 있는 석회화 제외), 뚜렷함·양상·BPE·구성은 저자 서술을 판독 값으로 옮겼다. DBT 석회화 분포 1개만 남았다(저자가 분포를 서술하지 않음).
- DBT 구조왜곡의 침상선 수렴 지수는 그림 해상도에서 무작위 수준(약 0.25)과 비슷하게 나온다. 중심 위치에 민감해 화살표 끝 주변 9점 중앙값을 쓰고 범위를 함께 적었다(간이 지수의 한계를 보여 주는 예).
- 해부 표시(유방 경계·대흉근·치밀 조직·유두)는 서비스 자동 추정이며, 정의·관계는 전문가 검토 전 초안이다.
- 측정 코드는 mammography-xai E124의 형태 계측을 이 저장소에서 다시 쓴 것이다(그 저장소와 연결 없음).
