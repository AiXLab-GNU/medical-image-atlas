# resources

영상 원자료와 지도 산출 그림을 한 번만 두는 곳이다. 영역(`domains/<영역>/resources/`)에는 여기를 가리키는 상대 링크만 둔다.

| 경로 | 내용 | 형태 |
| --- | --- | --- |
| `datasets/retinal_atlas_masked_figures/` | 망막 항목 페이지 그림(원 영상·mask 겹침) 152쌍 | 저장소 안 파일(생성물) |
| `datasets/retinal_atlas_modality_figures/` | 망막 영상 종류 그림과 `provider_figures/` 논문 그림 원본(SHA-256 고정) | 저장소 안 파일 |
| `datasets/retinal_atlas_measurement_examples/` | 망막 측정 표시 예시 89장·층 239개 | 저장소 안 파일(생성물) |
| `datasets/retinal_concept_reference_images/` | 개념 청사진 평가용 공개 논문 그림 4장 | 저장소 안 파일 |
| `datasets/public_dr/{IDRiD,refined_idrid,fundus_avseg_7c,uwf_dr_2026}` | 공개 안저·광각 데이터셋 | 저장소 안 복사본 |
| `datasets/public_glaucoma/chaksu`, `public_myopia/palm` | Chákṣu, PALM | 저장소 안 복사본 |
| `datasets/public_amd/{amd_sd,amd_dme_3d_oct,octid,octid_mh}` | AMD-SD, AMD/DME 3D OCT, OCTID | 저장소 안 복사본 |
| `datasets/olives/zenodo_7105232` | OLIVES | 저장소 안 복사본 |
| `datasets/public_mammography/dmid` | DMID 유방촬영 510장·ROI·보고서(CC BY 4.0, figshare 원본 zip + 푼 파일, 15 GB) | 저장소 안 파일(git 제외) |
| `datasets/mammography_atlas_masked_figures/` | 유방촬영 항목 페이지 그림 32쌍 | 저장소 안 파일(생성물) |
| `datasets/mammography_atlas_measurement_examples/` | 유방촬영 측정 표시 예시 16장·층 59개 | 저장소 안 파일(생성물) |
| `datasets/public_pathology/{precise,sicapv2,par}` | 전립선: PRECISE H&E·IHC 각 27장·주석(53 GB), SICAPv2 패치·글리슨 주석(4.2 GB), PAR 판독의 등급 표와 예시 슬라이드 5장(3.5 GB), 모두 CC BY 4.0 | 저장소 안 파일(git 제외) |
| `datasets/pathology_atlas_masked_figures/` | 병리 항목 페이지 그림 28쌍 | 저장소 안 파일(생성물) |
| `datasets/pathology_atlas_measurement_examples/` | 병리 측정 표시 예시 15장·층 51개 | 저장소 안 파일(생성물) |
| `datasets/mammography_atlas_provider_figures/` | DBT·CEM CC BY 4.0 논문 그림 8장(원본 파일명, SHA-256은 `g_provider_figures`) | 저장소 안 파일 |

공개 원자료(약 105 GB)는 2026-11-23 oculophenome-xai에서 이 저장소로 복사했다. 다른 저장소를 가리키는 링크는 없고,
이 저장소만으로 운영한다. 다른 곳에서 재구축할 때는 각 경로에 원자료를 직접 받는다
(목록과 출처: `domains/retinal/docs/surveys/retinal_atlas_catalog/g_image_sources_v01.csv`의 `kind=dataset`). 원자료가 없어도
웹 서비스는 위의 저장소 안 그림만으로 돈다. 원자료는 용량 때문에 git에 넣지 않는다(`.gitignore`).
