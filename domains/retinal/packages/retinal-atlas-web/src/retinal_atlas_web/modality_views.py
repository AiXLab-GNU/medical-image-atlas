"""What each imaging modality covers: en-face field of view and the depth its signal comes from.

Field-of-view shapes are in degrees of visual angle relative to the fovea (x > 0 = nasal, toward the
disc; y > 0 = superior). 1 mm on the retina is taken as about 3.4°, and the disc centre lies about
15° nasal to the fovea. Sizes are typical device presets, not limits of any single instrument.
"""

DISC_OFFSET_DEG = 15.0
MM_TO_DEG = 3.4

# Depth bands of the schematic, inner (vitreous) to outer (sclera).
DEPTH_BANDS = [
    ('vitreous', '유리체', 'ana_vitreous'),
    ('inner', '내망막(신경섬유~내핵층)', 'ana_inner_retina'),
    ('vessels', '망막 혈관·모세혈관망', 'ana_retinal_vasculature'),
    ('outer', '외망막(시세포)', 'ana_outer_retina'),
    ('rpe', 'RPE', 'ana_rpe'),
    ('cc', '브루크막·맥락막모세혈관', 'ana_choriocapillaris'),
    ('choroid', '맥락막 대혈관', 'ana_choroid'),
    ('sclera', '공막', 'ana_sclera'),
]


def _mm(size_mm):
    return round(size_mm * MM_TO_DEG, 1)


MODALITY_VIEWS = {
    'cfp': {
        'imaging_id': 'img_cfp', 'short': '컬러 안저',
        'summary': '백색광을 비춰 돌아온 빛을 컬러로 찍은 한 장의 정면 사진. 깊이는 구분되지 않고 여러 층의 색이 겹쳐 보입니다.',
        'fov': [
            {'shape': 'circle', 'x': 7.5, 'y': 0, 'w': 45, 'label': '표준 45°', 'kind': 'main'},
            {'shape': 'circle', 'x': 7.5, 'y': 0, 'w': 100, 'label': '광각(초광각은 주변부까지)', 'kind': 'wide'},
        ],
        'depth': {'inner': ('part', '혈관·신경섬유 표면 반사'), 'vessels': ('main', '혈관의 붉은 색'),
                  'rpe': ('part', '색소가 바탕색을 만듦'), 'choroid': ('part', '붉은 바탕·주황색 반사')},
        'depth_note': '한 장에 여러 깊이가 합쳐진 투영',
    },
    'oct': {
        'imaging_id': 'img_oct', 'short': 'OCT',
        'summary': '근적외선 간섭으로 깊이 방향 반사를 재서 단면(B-scan)과 입체(volume)를 만든다. 층을 깊이별로 나눠 볼 수 있습니다.',
        'fov': [
            {'shape': 'rect', 'x': 0, 'y': 0, 'w': _mm(6), 'h': _mm(6), 'label': '황반 cube 6×6 mm', 'kind': 'main'},
            {'shape': 'line', 'x': 0, 'y': 0, 'w': _mm(9), 'label': 'B-scan 한 줄', 'kind': 'line'},
            {'shape': 'circle', 'x': DISC_OFFSET_DEG, 'y': 0, 'w': _mm(3.46), 'label': '유두주위 원형 스캔', 'kind': 'main'},
        ],
        'depth': {'vitreous': ('part', '후유리체막'), 'inner': ('main', '층 두께·경계'), 'vessels': ('part', '혈관 그림자'),
                  'outer': ('main', 'ELM·EZ 띠'), 'rpe': ('main', 'RPE 띠'), 'cc': ('main', '브루크막'),
                  'choroid': ('part', '깊은 영상(EDI·SS)에서'), 'sclera': ('part', '맥락막-공막 경계')},
        'depth_note': '깊이 방향으로 분리된 반사(층마다 따로 측정)',
    },
    'octa': {
        'imaging_id': 'img_octa', 'short': 'OCTA',
        'summary': '같은 자리를 여러 번 찍어 움직이는 혈구 신호만 뽑은 혈류 지도. 깊이 구간(슬랩)을 골라 정면으로 봅니다.',
        'fov': [
            {'shape': 'rect', 'x': 0, 'y': 0, 'w': _mm(3), 'h': _mm(3), 'label': '3×3 mm', 'kind': 'main'},
            {'shape': 'rect', 'x': 0, 'y': 0, 'w': _mm(6), 'h': _mm(6), 'label': '6×6 mm', 'kind': 'main'},
            {'shape': 'rect', 'x': 4, 'y': 0, 'w': _mm(12), 'h': _mm(12), 'label': '광각 12×12 mm', 'kind': 'wide'},
        ],
        'depth': {'vessels': ('main', 'SCP·ICP·DCP 슬랩'), 'outer': ('part', '정상은 무혈관(신생혈관 확인)'),
                  'cc': ('main', 'CC 슬랩'), 'choroid': ('part', '투영 잡음이 섞임')},
        'depth_note': '혈류가 있는 깊이만 슬랩으로 나눠 봄',
    },
    'faf': {
        'imaging_id': 'img_faf', 'short': 'FAF',
        'summary': '청색(또는 녹색) 빛으로 RPE의 리포푸신이 내는 자가형광을 찍은 정면 영상. RPE의 건강 상태를 봅니다.',
        'fov': [
            {'shape': 'rect', 'x': 0, 'y': 0, 'w': 30, 'h': 30, 'label': 'SLO 30°', 'kind': 'main'},
            {'shape': 'rect', 'x': 5, 'y': 0, 'w': 55, 'h': 55, 'label': '55°', 'kind': 'main'},
            {'shape': 'circle', 'x': 7.5, 'y': 0, 'w': 100, 'label': '광각 FAF', 'kind': 'wide'},
        ],
        'depth': {'inner': ('block', '황반 색소가 중심와를 어둡게'), 'vessels': ('block', '혈관이 형광을 가림'),
                  'rpe': ('main', '리포푸신 자가형광')},
        'depth_note': 'RPE에서 나는 형광, 앞쪽 구조는 가리는 역할',
    },
    'nir': {
        'imaging_id': 'img_nir', 'short': 'NIR',
        'summary': '근적외선(약 800 nm대) 반사 정면 영상. 깊이 들어가 RPE·맥락막 반사를 보며, OCT를 찍을 때 위치 안내 영상으로 함께 얻습니다.',
        'fov': [
            {'shape': 'rect', 'x': 0, 'y': 0, 'w': 30, 'h': 30, 'label': '30°', 'kind': 'main'},
            {'shape': 'rect', 'x': 5, 'y': 0, 'w': 55, 'h': 55, 'label': '55°', 'kind': 'main'},
        ],
        'depth': {'vessels': ('part', '혈관이 어둡게'), 'outer': ('part', '시세포층 변화'),
                  'rpe': ('main', '색소·드루젠 반사'), 'choroid': ('part', '깊은 반사')},
        'depth_note': '가시광보다 깊은 층(RPE·맥락막) 반사 위주',
    },
    'fa': {
        'imaging_id': 'img_fa', 'short': 'FA',
        'summary': '정맥에 플루오레세인을 넣고 시간에 따라 찍는 조영 영상. 망막 혈관의 충만·누출·무관류를 봅니다.',
        'fov': [
            {'shape': 'rect', 'x': 0, 'y': 0, 'w': 30, 'h': 30, 'label': '30°', 'kind': 'main'},
            {'shape': 'rect', 'x': 5, 'y': 0, 'w': 55, 'h': 55, 'label': '55°', 'kind': 'main'},
            {'shape': 'circle', 'x': 7.5, 'y': 0, 'w': 102, 'label': '광각 102°·초광각', 'kind': 'wide'},
        ],
        'depth': {'vessels': ('main', '혈관 충만·누출·무관류'), 'rpe': ('block', '정상 RPE가 맥락막 형광을 가림'),
                  'cc': ('part', '배경 형광(초기)')},
        'depth_note': '망막 혈관 위주, 맥락막은 RPE에 가려짐',
    },
    'icga': {
        'imaging_id': 'img_icga', 'short': 'ICGA',
        'summary': '인도시아닌그린 조영 영상. 근적외선 형광이라 RPE를 지나 맥락막 혈관과 폴립·맥락막 과투과를 봅니다.',
        'fov': [
            {'shape': 'rect', 'x': 0, 'y': 0, 'w': 30, 'h': 30, 'label': '30°', 'kind': 'main'},
            {'shape': 'rect', 'x': 5, 'y': 0, 'w': 55, 'h': 55, 'label': '55°', 'kind': 'main'},
            {'shape': 'circle', 'x': 7.5, 'y': 0, 'w': 102, 'label': '광각 102°', 'kind': 'wide'},
        ],
        'depth': {'vessels': ('part', '망막 혈관도 보임'), 'cc': ('part', '맥락막모세혈관 충만'),
                  'choroid': ('main', '맥락막 대혈관·폴립·과투과')},
        'depth_note': 'RPE를 통과해 맥락막까지',
    },
}
