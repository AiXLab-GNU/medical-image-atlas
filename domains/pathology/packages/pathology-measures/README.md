# pathology-measures

병리 지도(medical-image-atlas `domains/pathology`, 우선 전립선 H&E)의 측정 ID(`ft_*`)를 계산하는 참조 구현이다. 모든 함수는
`Measurement(feature_id, value, unit, status, note, detail)`을 돌려준다. 화소 크기 `mpp`(µm/px)를 주면 µm²·mm²·mm 단위, 없으면 화소 단위다.

| 모듈 | 측정 |
| --- | --- |
| `tissue` | 조직 검출·면적, 종양·간질·양성 샘·인공물 비율, 종양 면적·최대 길이, 글리슨 패턴 3·4·5 비율, 병변 공통(유무·면적·비율·개수) |
| `glands` | 샘 개수·밀도·평균 크기·원형도, 내강 비율, 샘당 내강 수(사상 패턴 근사) |
| `nuclei` | 헤마톡실린 분리(색 분리), 핵 후보 검출, 핵 밀도·평균 크기·크기 다양성, 헤마톡실린 광학밀도 |
| `texture` | GLCM 대비 |

`registry.REGISTRY`가 측정 ID → 함수·입력·방법을 담는다. 조직 검출 기준과 측정 항목은 pathology-ai E022의 주석 기반 계측을
scikit-image로 다시 쓴 것이다. 핵은 검증된 분할이 아닌 후보이며 임상 진단 도구가 아니다.

```bash
python -m unittest discover -s tests
```
