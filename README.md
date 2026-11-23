# medical-image-atlas

의료 영상에서 **무엇이 보이고, 무엇을 어떻게 재며, 어떤 질병의 근거인지**를 영상 위에 보여 주는 영상 지도 저장소다.
영역(domain)마다 같은 틀(지식 표 → 영상 출처 → 그림·측정 예시 → 웹 서비스)을 쓴다.

| 영역 | 상태 | 진입점 |
| --- | --- | --- |
| 망막(`domains/retinal/`) | 운영 v01 — 측정 160개, 영상 종류 8가지 모두 예시, 웹 8877 | [영역 README](domains/retinal/README.md) |
| 유방촬영(`domains/mammography/`) | v01 — 측정 61개(함수 40), 예시 16장(FFDM·DBT·CEM), 웹 8879 | [영역 README](domains/mammography/README.md) |
| 병리(`domains/pathology/`, 전립선) | v01 — 측정 32개(함수 25), PRECISE·SICAPv2 예시 10장, IHC 영상 준비 중, 웹 8881 | [영역 README](domains/pathology/README.md) |

## 구조

```text
medical-image-atlas/
├── README.md · STATUS.md · AGENTS.md · pyproject.toml   # 생성 코드 공용 환경(uv)
├── resources/datasets/        # 원자료와 지도 그림을 한 번만 둠(저장소 안 파일)
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
cd domains/retinal/packages/retinal-atlas-web && uv sync && .venv/bin/python -B -m retinal_atlas_web --port 8877
cd domains/mammography/packages/mammography-atlas-web && uv venv .venv && uv pip install --python .venv/bin/python -e . && .venv/bin/python -B -m mammography_atlas_web --port 8879
cd domains/pathology/packages/pathology-atlas-web && uv venv .venv && uv pip install --python .venv/bin/python -e . && .venv/bin/python -B -m pathology_atlas_web --port 8881
```

전체 재구축과 항목을 늘리는 방법은 영역의 재구축 절차서(망막: `domains/retinal/docs/protocols/50_retinal_atlas_rebuild_runbook_v01_ko.md`, 유방촬영: `domains/mammography/docs/protocols/50_mammography_atlas_rebuild_runbook_v01_ko.md`, 병리: `domains/pathology/docs/protocols/50_pathology_atlas_rebuild_runbook_v01_ko.md`)를 따른다.
