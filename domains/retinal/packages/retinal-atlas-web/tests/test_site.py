"""Behavioral checks for the server-rendered retinal atlas."""
from pathlib import Path
import json
import tempfile
import unittest

from retinal_atlas_web import create_app
from retinal_atlas_web.app import _example_modality as _mod


PROJECT = Path(__file__).resolve().parents[3]
IMAGES = PROJECT / 'resources/datasets/retinal_concept_reference_images'
DATA = Path(__file__).resolve().parents[1] / 'src/retinal_atlas_web/data'
ATLAS = json.loads((DATA / 'atlas.json').read_text(encoding='utf-8'))
LINKS = json.loads((DATA / 'image_links.json').read_text(encoding='utf-8'))
PAGES = {
    '/': '망막 영상 지도',
    '/anatomy/': '해부학 지도',
    '/lesions/': '병변 목록',
    '/images/': '영상 읽기',
    '/images/retinal-layers/': '정상 망막',
    '/images/choroid/': '맥락막의 경계',
    '/images/oct/': '낭성 공간',
    '/images/atrophy/': '위축',
    '/sources/': '출처와 라이선스',
    '/search/?q=출혈': '검색',
}


def item_url(item):
    return f"/{item['section']}/{item['slug']}/"


class SiteTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'IMAGE_ROOT': IMAGES})
        self.client = self.app.test_client()

    def test_main_pages_are_server_rendered(self):
        for path, title in PAGES.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn(title, html)
                self.assertNotIn('<iframe', html)

    def test_every_atlas_item_has_its_own_page(self):
        for item in ATLAS['items'].values():
            with self.subTest(item=item['id']):
                response = self.client.get(item_url(item))
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn(item['name'], html)
                self.assertIn('볼 수 있는 영상', html)
                self.assertIn('class="ip-def"', html)
                self.assertIn('aria-current="page"', html)

    def test_item_page_shows_definition_features_and_review_state(self):
        html = self.client.get('/lesions/intraretinal-fluid/').get_data(as_text=True)
        for text in ['신경망막 안에 고인 액체 공간', '영상별로 보이는 모습', '측정할 수 있는 속성',
                     '망막내액 부피', '관련 질병', '출처와 검토 상태', 'µm']:
            self.assertIn(text, html)
        self.assertNotIn('병변 존재(공통)', html)

    def test_image_marks_link_to_existing_items_and_render_on_item_pages(self):
        for sample, marks in LINKS.items():
            for mark in marks:
                with self.subTest(sample=sample, item=mark['item']):
                    self.assertIn(mark['item'], ATLAS['items'])
                    html = self.client.get(item_url(ATLAS['items'][mark['item']])).get_data(as_text=True)
                    self.assertIn('item-figure', html)
        html = self.client.get('/lesions/dril/').get_data(as_text=True)
        self.assertIn('class="crop"', html)
        html = self.client.get('/anatomy/rnfl/').get_data(as_text=True)
        self.assertIn('mark-overlay', html)

    def test_masked_real_figures_render_with_toggle_and_attribution(self):
        masked = json.loads((DATA / 'masked_figures.json').read_text(encoding='utf-8'))['figures']
        self.assertGreaterEqual(len(masked), 10)
        for fig in masked:
            with self.subTest(figure=fig['id']):
                self.assertIn(fig['license'], {'CC BY 4.0', 'CC0 1.0'})
                for name in (fig['base'], fig['overlay']):
                    self.assertEqual(self.client.get('/figures/' + name).status_code, 200)
                for item_id in fig['items']:
                    html = self.client.get(item_url(ATLAS['items'][item_id])).get_data(as_text=True)
                    self.assertIn('/figures/' + fig['overlay'], html)
                    self.assertIn("표시 전 · 원 영상", html)
                    self.assertIn(fig['license'], html)
        self.assertEqual(self.client.get('/figures/../atlas.json').status_code, 404)
        self.assertEqual(self.client.get('/figures/unknown.png').status_code, 404)

    def test_disease_pages_link_findings_to_where_imaging_and_measures(self):
        index = self.client.get('/diseases/').get_data(as_text=True)
        for text in ['판정 체계', '국제 DR 중증도 척도(ICDR)', '5단계', 'META-PM', 'class="dc-ns"']:
            self.assertIn(text, index)
        for text in ['당뇨 관련', '약물 독성', '유전 망막질환', '하이드록시클로로퀸 망막병증', '근거 필요']:
            self.assertIn(text, index + self.client.get('/diseases/hcq-retinopathy/').get_data(as_text=True))
        for disease in ATLAS['diseases'].values():
            with self.subTest(disease=disease['id']):
                response = self.client.get(f"/diseases/{disease['slug']}/")
                self.assertEqual(response.status_code, 200)
                self.assertIn('판정 단계', response.get_data(as_text=True))
        html = self.client.get('/diseases/npdr/').get_data(as_text=True)
        for text in ['단계 판정에 쓰는 소견', '어디서', '어떤 영상으로', '무엇을 측정', '사분면별 출혈 개수', 'ICDR 2003',
                     '판정 단계', '국제 DR 중증도 척도', '4-2-1 규칙', 'ladder-step current']:
            self.assertIn(text, html)
        dr = self.client.get('/diseases/dr/').get_data(as_text=True)
        for text in ['증식성 DR (PDR)', '중증 NPDR', '중등도 NPDR', '경도 NPDR', '다음 중 하나라도 있으면', '처음 맞는 단계']:
            self.assertIn(text, dr)
        self.assertIn('ladder-step current', self.client.get('/diseases/crvo-ischemic/').get_data(as_text=True))
        self.assertIn('다음 중 2개 이상이면', self.client.get('/diseases/pcv/').get_data(as_text=True))
        dme = self.client.get('/diseases/dme/').get_data(as_text=True)
        for text in ['국제 DME 중증도 척도', '임상적으로 유의한 황반부종', '중심 침범 DME (CI-DME)', '500 µm']:
            self.assertIn(text, dme)
        lesion = self.client.get('/lesions/hard-exudate/').get_data(as_text=True)
        self.assertIn('href="/diseases/', lesion)

    def test_measurements_show_target_diseases(self):
        from retinal_atlas_web.disease_links import measurement_diseases
        links = measurement_diseases(ATLAS)
        measures = [f for f in ATLAS['features'].values() if f['role'] == 'measurement']
        self.assertGreaterEqual(sum(1 for f in measures if links.get(f['id'])), 130)
        self.assertIn('dis_glaucoma', {d['id'] for d in links['ft_cup_area']})          # added relation
        self.assertTrue(any(d['via'] is None for d in links['ft_cdr_vertical']))        # direct relation
        html = self.client.get('/measurements/').get_data(as_text=True)
        self.assertIn('대상 질병', html)
        self.assertIn('href="/diseases/' + ATLAS['diseases']['dis_glaucoma']['slug'] + '/"', html)
        self.assertIn('공통 지표 · 특정 질병 없음', html)
        page = self.client.get('/measurements/code/ft_cup_area/').get_data(as_text=True)
        self.assertIn('이 측정을 쓰는 질병', page)
        self.assertIn(ATLAS['diseases']['dis_glaucoma']['name'], page)

    def test_measurement_examples_toggle_layers_with_computed_values(self):
        html = self.client.get('/measurements/').get_data(as_text=True)
        examples = json.loads((DATA / 'measurement_examples.json').read_text(encoding='utf-8'))['examples']
        self.assertGreaterEqual(len({e['modality'] for e in examples}), 3)
        self.assertEqual(len({e['id'] for e in examples}), len(examples))      # one image set per example id
        for ex in examples:
            self.assertIn(f'id="{ex["id"]}"', html)
            for layer in ex['layers']:
                self.assertIn(f'data-layer="{ex["id"]}-{layer["key"]}"', html)
                self.assertEqual(self.client.get(f'/measure-figures/{layer["file"]}').status_code, 200)
        self.assertIn('measure-examples.js', html)
        self.assertIn('실행 전', html)
        self.assertEqual(self.client.get('/measure-figures/../atlas.json').status_code, 404)
        # every measurement in the list has an image example; reading-only layers carry no function
        measures = {f['id'] for f in ATLAS['features'].values() if f['role'] == 'measurement'}
        shown = {f['id'] for ex in examples for la in ex['layers'] for f in la['features']}
        self.assertEqual(measures - shown, set())
        for ex in examples:
            for la in ex['layers']:
                if any(f['status'] == 'reading' for f in la['features']):
                    self.assertEqual(la['function'], '')
                else:
                    self.assertTrue(la['function'])
        self.assertIn('판독 항목 · 계산 코드 없음', html)
        # per image type, measurements that apply but have no example are listed as not implemented
        for mod in {e['modality'] for e in examples}:
            applies = {f['id'] for f in ATLAS['features'].values() if f['role'] == 'measurement'
                       and any(_mod(i) == mod for i in f['imaging'])}
            on_cards = {f['id'] for e in examples if e['modality'] == mod for la in e['layers'] for f in la['features']}
            if applies - on_cards:
                card = html.split(f'id="pending-{mod}"')[1].split('</article>')[0]
                self.assertEqual(card.count('class="mx-item is-pending"'), len(applies - on_cards))
                self.assertIn('측정할 것', card)
                self.assertIn('미구현', card)

    def test_measurement_code_links_download_source(self):
        html = self.client.get('/measurements/').get_data(as_text=True)
        self.assertIn('/code/retinal-measures.zip', html)
        page = self.client.get('/measurements/code/ft_cdr_vertical/').get_data(as_text=True)
        self.assertIn('def cup_disc_ratio', page)
        self.assertIn('/code/retinal-measures/src/retinal_measures/optic_disc.py?download=1', page)
        archive = self.client.get('/code/retinal-measures.zip')
        self.assertEqual(archive.status_code, 200)
        import io, zipfile
        names = zipfile.ZipFile(io.BytesIO(archive.data)).namelist()
        self.assertTrue(any(n.endswith('/pyproject.toml') for n in names))
        self.assertFalse(any('__pycache__' in n for n in names))
        self.assertEqual(self.client.get('/code/retinal-measures/../../PROJECT.yaml').status_code, 404)
        self.assertEqual(self.client.get('/code/unknown.zip').status_code, 404)
        self.assertIn('def ', self.client.get('/code/retinal-measures/src/retinal_measures/lesions.py').get_data(as_text=True))

    def test_measurement_list_shows_only_what_to_measure_with_automation_state(self):
        measures = [f for f in ATLAS['features'].values() if f['role'] == 'measurement']
        html = self.client.get('/measurements/').get_data(as_text=True)
        self.assertEqual(html.count('class="ms-row"'), len(measures))
        for text in ['정성', '정량', '영상만으로 자동', 'mask 입력 필요', '구현 없음', '계산 구현이 있는 측정']:
            self.assertIn(text, html)
        for criterion in ['META-PM 범주', 'PVR 등급', '1500', '4-2-1', 'DRCR']:
            self.assertNotIn(criterion, html.split('<main')[1])
        ready = self.client.get('/measurements/?level=ready').get_data(as_text=True)
        self.assertLess(ready.count('class="ms-row"'), html.count('class="ms-row"'))
        self.assertGreater(ready.count('class="ms-row"'), 0)
        quals = self.client.get('/measurements/?kind=qualitative').get_data(as_text=True)
        self.assertEqual(quals.count('class="ms-row"'), sum(1 for f in measures if f['type'] == 'qualitative'))
        self.assertIn('META-PM', self.client.get('/diseases/pathologic-myopia/').get_data(as_text=True))
        faf = self.client.get('/measurements/?img=faf').get_data(as_text=True)
        self.assertIn('영상 종류별로 보기', html)
        self.assertLess(faf.count('class="ms-row"'), html.count('class="ms-row"'))
        self.assertGreater(faf.count('class="ms-row"'), 0)
        self.assertIn('FAF 영상으로 재는 측정', faf)
        grouped = self.client.get('/measurements/?by=imaging').get_data(as_text=True)
        for key in ['cfp', 'oct', 'octa', 'faf', 'nir', 'fa', 'icga']:
            self.assertIn(f'id="ms-m-{key}"', grouped)
        self.assertGreaterEqual(grouped.count('class="ms-row"'), html.count('class="ms-row"'))
        packaged = [f for f in measures if f['impl'].get('package')]
        self.assertIn(f'<b>{len(packaged)}</b>', html)
        self.assertIn('측정 함수 있음', html)
        self.assertIn('retinal_measures.lesions.quadrant_counts', html)
        item = self.client.get('/lesions/intraretinal-fluid/').get_data(as_text=True)
        self.assertIn('retinal_measures.oct_lesions.volume', item)

    def test_modality_pages_show_coverage_real_images_and_links(self):
        manifest = json.loads((DATA / 'modality_figures.json').read_text(encoding='utf-8'))['figures']
        index = self.client.get('/imaging/').get_data(as_text=True)
        for key in ['cfp', 'oct', 'octa', 'faf', 'nir', 'fa', 'icga']:
            with self.subTest(modality=key):
                self.assertIn(f'href="/imaging/{key}/"', index)
                html = self.client.get(f'/imaging/{key}/').get_data(as_text=True)
                for text in ['보이는 영역', '정면에서 찍히는 범위', '신호가 오는 깊이', '실제 영상', 'class="mv-fov"',
                             'class="mv-depth"', '이 영상에서 보이는 구조와 병변']:
                    self.assertIn(text, html)
                figs = [f for f in manifest if f['modality'] == key]
                self.assertGreaterEqual(len(figs), 1)
                for fig in figs:
                    prefix = '/modality-figures/' if fig['served'] == 'modality' else '/figures/'
                    self.assertIn(prefix + fig['file'], html)
                    self.assertIn(fig['license'], html)
                    with self.client.get(prefix + fig['file']) as image:
                        self.assertEqual(image.status_code, 200)
        self.assertEqual(self.client.get('/imaging/unknown/').status_code, 404)
        self.assertEqual(self.client.get('/modality-figures/README.md').status_code, 404)
        self.assertEqual(self.client.get('/modality-figures/../source_manifest.json').status_code, 404)
        self.assertIn('href="/imaging/oct/"', self.client.get('/lesions/intraretinal-fluid/').get_data(as_text=True))

    def test_vessel_items_have_schematic_and_coloured_real_image(self):
        masked = json.loads((DATA / 'masked_figures.json').read_text(encoding='utf-8'))['figures']
        with_real = {i for f in masked for i in f['items']}
        vessels = [i for i in ATLAS['items'].values() if i['section'] == 'anatomy' and i.get('axis') == 'vessel']
        self.assertGreaterEqual(len(vessels), 12)
        for item in vessels:
            with self.subTest(item=item['id']):
                html = self.client.get(item_url(item)).get_data(as_text=True)
                self.assertIn('vessel-schematic', html)
                if item['id'] != 'ana_radial_peripapillary_capillaries':
                    self.assertIn(item['id'], with_real)
                    self.assertIn("표시 전 · 원 영상", html)
        html = self.client.get('/anatomy/retinal-arterioles/').get_data(as_text=True)
        self.assertIn('ml-artery', html)
        self.assertIn('Fundus-AVSeg-7C', html)

    def test_every_item_has_a_schematic_or_image(self):
        for item in ATLAS['items'].values():
            with self.subTest(item=item['id']):
                html = self.client.get(item_url(item)).get_data(as_text=True)
                self.assertNotIn('figure-empty', html)
        html = self.client.get('/lesions/subretinal-fluid/').get_data(as_text=True)
        self.assertIn('/static/schematics/les_subretinal_fluid-oct.svg', html)
        with self.client.get('/static/schematics/les_subretinal_fluid-oct.svg') as svg:
            self.assertEqual(svg.status_code, 200)
            self.assertNotIn(b'style=', svg.data)

    def test_filters_and_search_narrow_lists(self):
        everything = self.client.get('/lesions/').get_data(as_text=True)
        hemorrhage = self.client.get('/lesions/?group=hemorrhage').get_data(as_text=True)
        self.assertGreater(everything.count('class="lesion-card"'), hemorrhage.count('class="lesion-card"'))
        self.assertGreater(hemorrhage.count('class="lesion-card"'), 0)
        category = self.client.get('/lesions/?cat=fluid').get_data(as_text=True)
        self.assertIn('망막내액', category)
        self.assertNotIn('미세동맥류', category.split('<main')[1])
        self.assertIn('점·얼룩 출혈', hemorrhage)
        self.assertNotIn('드루젠', hemorrhage.split('<main')[1])
        octa = self.client.get('/anatomy/?img=octa').get_data(as_text=True)
        self.assertIn('중심와 무혈관 구역', octa)
        self.assertNotIn('>신경절세포층<', octa)
        result = self.client.get('/search/?q=RNFL').get_data(as_text=True)
        self.assertIn('신경섬유층', result)

    def test_legacy_sample_urls_redirect(self):
        for old, new in {'/anatomy/retinal-layers/': '/images/retinal-layers/', '/lesions/oct/': '/images/oct/',
                         '/lesions/atrophy/': '/images/atrophy/', '/fundus/': '/images/'}.items():
            response = self.client.get(old)
            self.assertEqual(response.status_code, 301, old)
            self.assertTrue(response.headers['Location'].endswith(new))
        self.assertIn('맥락막', self.client.get('/anatomy/choroid/').get_data(as_text=True))

    def test_sample_content_and_attribution_exist_without_javascript(self):
        for path in ['/images/retinal-layers/', '/images/choroid/', '/images/oct/', '/images/atrophy/']:
            html = self.client.get(path).get_data(as_text=True)
            self.assertIn('id="sample-image"', html)
            self.assertIn('먼저, 어디를 보는 사진인가요?', html)
            self.assertIn('creativecommons.org/licenses/', html)
            self.assertIn('이 영상에서 볼 수 있는 항목', html)
        self.assertIn('CC BY-NC-SA 4.0', self.client.get('/images/retinal-layers/').get_data(as_text=True))

    def test_image_allowlist_preserves_original_bytes_and_head(self):
        pairs = {'retina_layers.png': '679a4fcbad112.png',
                 'choroid.png': 'journal.pone.0099690.g001.png',
                 'oct_lesions.jpg': 'jcm-11-03266-g002-550.jpg',
                 'atrophy.webp': 'fnins-18-1415575-g001.webp'}
        for alias, original in pairs.items():
            with self.subTest(alias=alias):
                response = self.client.get('/sample-images/' + alias)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, (IMAGES / original).read_bytes())
                head = self.client.head('/sample-images/' + alias)
                self.assertEqual(head.status_code, 200)
                self.assertEqual(head.content_length, len(response.data))
                head.close()
                response.close()

    def test_undeclared_files_and_writes_are_unavailable(self):
        for path in ['/PROJECT.yaml', '/sample-images/source_manifest.json',
                     '/sample-images/../source_manifest.json', '/anatomy/unknown/', '/lesions/rnfl/',
                     '/images/unknown/', '/static/../../app.py', '/api/survey']:
            self.assertEqual(self.client.get(path).status_code, 404, path)
        self.assertEqual(self.client.post('/').status_code, 405)

    def test_health_reports_missing_images(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['items'], len(ATLAS['items']))
        with tempfile.TemporaryDirectory() as empty:
            client = create_app({'TESTING': True, 'IMAGE_ROOT': empty}).test_client()
            self.assertEqual(client.get('/health').status_code, 503)
            self.assertEqual(client.get('/sample-images/choroid.png').status_code, 503)

    def test_scripts_and_styles_have_self_only_policy(self):
        response = self.client.get('/lesions/microaneurysm/')
        policy = response.headers['Content-Security-Policy']
        self.assertIn("script-src 'self'", policy)
        self.assertNotIn('unsafe-inline', policy)
        self.assertNotIn(' style="', response.get_data(as_text=True))
        for asset in ['site.css', 'viewer.js']:
            with self.client.get('/static/' + asset) as asset_response:
                self.assertEqual(asset_response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
