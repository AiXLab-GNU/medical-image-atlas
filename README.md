# medical-image-atlas

의료 영상에서 **무엇이 보이고, 무엇을 어떻게 재며, 어떤 질병의 근거인지**를 영상 위에 보여 주는 영상 지도 저장소다.
영역(domain)마다 같은 틀(지식 표 → 영상 출처 → 그림·측정 예시 → 웹 서비스)을 쓴다.

**하나의 채널**: [`portal/`](portal/README.md)의 웹 8875 하나로 세 영역을 모두 본다 — `/`는 3개 영역 홈, `/retinal/`·`/mammography/`·`/pathology/`는 각 영역 홈.
각 지도 맨 위 줄에서 첫 페이지와 다른 영역으로 옮겨 간다. 영역 지도는 따로 띄울 수도 있다(8877·8879·8881).
같은 원본에서 **정적 버전**도 만든다(`medical-atlas-export-static` → `build/static_site/`, 서버 없이 GitHub Pages 등에 올림) — 차이는 [portal README](portal/README.md#두-가지-운용-동적정적).

| 영역 | 상태 | 진입점 |
| --- | --- | --- |
| 하나의 채널(`portal/`) | 3개 영역 홈 + 세 영역 지도를 경로로 붙여 웹 8875 하나로 서비스 | [portal README](portal/README.md) |
| 망막(`domains/retinal/`) | 운영 v01 — 측정 160개, 영상 종류 8가지 모두 예시, 웹 8877 | [영역 README](domains/retinal/README.md) |
| 유방촬영(`domains/mammography/`) | v01 — 측정 61개(함수 40), 예시 16장(FFDM·DBT·CEM), 웹 8879 | [영역 README](domains/mammography/README.md) |
| 병리(`domains/pathology/`, 전립선) | v01 — 측정 34개(함수 32), H&E·IHC 예시 16장, 논문 패널 25, 등급 판독 일치도(PAR·SICAPv2), 측정 검증 페이지, 웹 8881 | [영역 README](domains/pathology/README.md) |

## 구조

```text
medical-image-atlas/
├── README.md · STATUS.md · AGENTS.md · pyproject.toml   # 생성 코드 공용 환경(uv)
├── resources/datasets/        # 원자료와 지도 그림을 한 번만 둠(저장소 안 파일)
├── portal/packages/medical-atlas-portal-web/   # 하나의 채널: 3개 영역 홈 + 세 영역 앱을 경로로 붙임(8875)
└── domains/<영역>/
    ├── DOMAIN.yaml            # 영역 표지·진입점(웹 앱이 이 파일로 영역 루트를 찾음)
    ├── code/                  # 생성 코드·등록 표 검사와 테스트
    ├── docs/                  # concept · surveys(등록 표) · protocols(스키마·재구축) · history
    ├── packages/              # 웹 앱·측정 패키지
    ├── references/            # 다른 저장소에서 가져온 동결 입력
    └── resources/datasets/    # ../../../resources/datasets 를 가리키는 상대 링크 보기
```

## 시작

```bash
uv sync                                          # 생성 코드 환경(.venv)
# 하나의 채널(권장): portal/packages/medical-atlas-portal-web/README.md 대로 설치한 뒤
cd portal/packages/medical-atlas-portal-web && .venv/bin/medical-atlas-portal-web --port 8875
# 영역 하나만 따로 띄울 때
cd domains/retinal/packages/retinal-atlas-web && uv sync && .venv/bin/python -B -m retinal_atlas_web --port 8877
cd domains/mammography/packages/mammography-atlas-web && uv venv .venv && uv pip install --python .venv/bin/python -e . && .venv/bin/python -B -m mammography_atlas_web --port 8879
cd domains/pathology/packages/pathology-atlas-web && uv venv .venv && uv pip install --python .venv/bin/python -e . && .venv/bin/python -B -m pathology_atlas_web --port 8881
```

전체 재구축과 항목을 늘리는 방법은 영역의 재구축 절차서(망막: `domains/retinal/docs/protocols/50_retinal_atlas_rebuild_runbook_v01_ko.md`, 유방촬영: `domains/mammography/docs/protocols/50_mammography_atlas_rebuild_runbook_v01_ko.md`, 병리: `domains/pathology/docs/protocols/50_pathology_atlas_rebuild_runbook_v01_ko.md`)를 따른다.

## 만든 곳 · 라이선스 · 인용

- AiXLab · 경상국립대학교 (연구책임자 Jin Hyun Kim, PhD · jin.kim@gnu.ac.kr). 첫 페이지의 소개 문구는 `portal/packages/medical-atlas-portal-web/src/medical_atlas_portal_web/data/site_info.json`에서 고친다.
- 코드는 MIT([LICENSE](LICENSE)), 지식 표·문서·서비스가 그린 모식도와 겹침은 CC BY 4.0, 공개 영상은 각 원 라이선스(CC BY 4.0·CC0 1.0)를 따른다 — [LICENSE-docs.md](LICENSE-docs.md).
- 인용 정보: [CITATION.cff](CITATION.cff). Zenodo 기록 정보: [.zenodo.json](.zenodo.json) — GitHub 릴리스를 만들면 Zenodo가 그 판에 DOI를 준다.
