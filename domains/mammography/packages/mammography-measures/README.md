# mammography-measures

유방촬영 지도(medical-image-atlas `domains/mammography`)의 측정 ID(`ft_*`)를 계산하는 참조 구현이다. 모든 함수는
`Measurement(feature_id, value, unit, status, note, detail)`을 돌려준다. 화소 크기(mm)를 주지 않으면 길이·면적은 화소 단위다.

| 모듈 | 측정 |
| --- | --- |
| `breast` | 유방 경계·유두·대흉근(MLO)·후유두선, 유방 면적, 치밀 조직 면적·밀도 백분율, 대흉근 면적·각도, 후유두선 길이 |
| `mass` | 종괴 최대 지름·면적·원형도·볼록도·반지름 변동·침상 지수·경계 선명도·대비 |
| `calcification` | 석회화 검출(top-hat + MAD), 개수·범위·밀집도·크기·크기 다양성·길쭉함·분지·선형 배열·최근접 거리·대비 |
| `distortion` | 침상선 수렴 지수, 구조왜곡 범위, 비대칭 면적, 좌우 치밀 조직 차이, 공통 유무·개수·크기 |
| `enhancement` | CEM 증강 강도 비(병변 ÷ 둘레 띠), 비종괴 증강 범위, 판독 원 안 증강 영역 추정 |
| `location` | 유두에서의 거리, 깊이 3구역, 한 영상의 절반 위치, 사분면·시계 방향(CC·MLO 짝) |

유두는 윤곽의 국소 돌출부를 찾은 뒤 원영상의 작은 영역에서 어두운 끝점을 보정한다. 전역 최외곽점과 유두가 다른 경우를 구분하지만, 여전히 서비스 추정이며 전문가 기준점으로 검증한 검출기는 아니다. MLO의 대흉근 경계도 자동 추정이므로 PNL 길이를 검증된 임상값으로 해석하지 않는다.

`registry.REGISTRY`가 측정 ID → 함수·입력·방법·참고 문헌을 담는다. 질량·석회화 계측은 mammography-xai E124의 원 해상도
형태 계측을 scikit-image·scipy로 다시 쓴 것이다. 임상 검증 도구가 아니다.

```bash
python -m unittest discover -s tests
```
