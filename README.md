# medical-image-atlas

의료 영상에서 **무엇이 보이고, 무엇을 어떻게 재며, 어떤 질병의 근거인지**를 영상 위에 보여 주는 영상 지도 저장소다.
영역(domain)마다 같은 틀(지식 표 → 영상 출처 → 그림·측정 예시 → 웹 서비스)을 쓴다.

첫 페이지(3개 영역 홈)는 [`portal/`](portal/README.md)의 웹 8875다. 여기서 안과·유방·전립선 지도로 들어가고, 각 지도의 `/`는 그 영역의 홈이다.
각 지도 맨 위 줄에서 첫 페이지와 다른 영역으로 옮겨 갈 수 있다.

| 영역 | 상태 | 진입점 |
| --- | --- | --- |
| 첫 페이지(`portal/`) | 세 영역 카드(항목 수·대표 그림)와 영역 홈 링크, 웹 8875 | [portal README](portal/README.md) |
| 망막(`domains/retinal/`) | 운영 v01 — 측정 160개, 영상 종류 8가지 모두 예시, 웹 8877 | [영역 README](domains/retinal/README.md) |
| 유방촬영(`domains/mammography/`) | v01 — 측정 61개(함수 40), 예시 16장(FFDM·DBT·CEM), 웹 8879 | [영역 README](domains/mammography/README.md) |
| 병리(`domains/pathology/`, 전립선) | v01 — 측정 34개(함수 32), H&E·IHC 예시 16장, 논문 패널 25, 등급 판독 일치도(PAR·SICAPv2), 측정 검증 페이지, 웹 8881 | [영역 README](domains/pathology/README.md) |

## 구조

```text
medical-image-atlas/
├── README.md · STATUS.md · AGENTS.md · pyproject.toml   # 생성 코드 공용 환경(uv)
├── resources/datasets/        # 원자료와 지도 그림을 한 번만 둠(저장소 안 파일)
├── portal/packages/medical-atlas-portal-web/   # 3개 영역 홈(첫 페이지, 영역 데이터를 읽기만 함)
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
cd portal/packages/medical-atlas-portal-web && uv venv .venv && uv pip install --python .venv/bin/python -e . && .venv/bin/medical-atlas-portal-web --port 8875
cd domains/retinal/packages/retinal-atlas-web && uv sync && .venv/bin/python -B -m retinal_atlas_web --port 8877
cd domains/mammography/packages/mammography-atlas-web && uv venv .venv && uv pip install --python .venv/bin/python -e . && .venv/bin/python -B -m mammography_atlas_web --port 8879
cd domains/pathology/packages/pathology-atlas-web && uv venv .venv && uv pip install --python .venv/bin/python -e . && .venv/bin/python -B -m pathology_atlas_web --port 8881
```

전체 재구축과 항목을 늘리는 방법은 영역의 재구축 절차서(망막: `domains/retinal/docs/protocols/50_retinal_atlas_rebuild_runbook_v01_ko.md`, 유방촬영: `domains/mammography/docs/protocols/50_mammography_atlas_rebuild_runbook_v01_ko.md`, 병리: `domains/pathology/docs/protocols/50_pathology_atlas_rebuild_runbook_v01_ko.md`)를 따른다.
