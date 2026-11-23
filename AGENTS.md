# medical-image-atlas 작업 지침

- 구조: `domains/<영역>/`마다 `DOMAIN.yaml`·`code/`·`docs/`·`packages/`·`references/`·`resources/`(링크 보기)를 둔다. 영역 공용
  원자료와 그림은 루트 `resources/datasets/`에 한 번만 둔다. 영역을 새로 만들 때 쓰지 않는 빈 폴더는 만들지 않는다.
- 이름: 파일·폴더는 ASCII `lower_snake_case`(배포 패키지는 kebab-case). 문서는 `<10|20|30|40|50|60|70|80|90>_<주제>_<종류>_vNN[_ko].md`.
  `final2`·`latest`·`misc`·`temp`·`new`·`copy` 같은 이름과 `_vNN` 사본을 만들지 않는다. 고칠 때는 같은 파일을 고친다.
- 영상: 공개하는 영상은 CC BY 4.0·CC0 1.0만 쓰고 출처 줄을 단다. 제한 자료(FGADR, HYAMD, MAPLES-DR·MESSIDOR 영상, Tianjin,
  기관 내부 자료, 유방촬영의 VinDr-Mammo·EMBED·INbreast·OPTIMAM)와 GPL 자료(PAPILA)·비영리 조건 자료(BCS-DBT 등)·CC BY 3.0 자료(CBIS-DDSM)는 쓰지 않는다. 공급자 파일명과 바이트를 바꾸지 않고 SHA-256을 등록 표에 고정한다.
- 출처·라이선스·체크섬은 영역 등록 표(G)에만 적는다. 생성 표·생성 JSON은 손으로 고치지 않는다.
- 고친 뒤: 영역의 등록 표 내보내기·검사, 코드 테스트, 웹 테스트를 돌리고 `STATUS.md`에 적는다. 커밋은 요청이 있을 때만 한다.
- 개인정보(이메일 등)를 외부 서비스 요청에 넣지 않는다.
