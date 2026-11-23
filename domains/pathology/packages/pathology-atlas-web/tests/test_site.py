"""Page, data and security checks of the mammography atlas web app."""
from __future__ import annotations

import re
import unittest

from pathology_atlas_web import create_app
from pathology_atlas_web.app import MODALITIES, load_content, modality_of, pending_by_modality


class SiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.content = load_content()

    def get(self, url, code=200):
        r = self.client.get(url)
        self.assertEqual(r.status_code, code, url)
        return r.get_data(as_text=True)

    def test_main_pages(self):
        for url in ['/', '/anatomy/', '/lesions/', '/measurements/', '/diseases/', '/imaging/', '/sources/',
                    '/search/?q=사상', '/measurements/?level=ready', '/measurements/?img=ihc']:
            self.get(url)
        self.get('/no-such-page/', 404)

    def test_every_item_and_disease_page(self):
        for item in self.content['items'].values():
            self.get(f"/{item['section']}/{item['slug']}/")
        for d in self.content['diseases'].values():
            self.get(f"/diseases/{d['slug']}/")
        for key, _ in MODALITIES:
            self.get(f'/imaging/{key}/')

    def test_every_measurement_code_page(self):
        for fid, f in self.content['atlas']['features'].items():
            if f['role'] == 'measurement':
                self.get(f'/measurements/code/{fid}/')

    def test_images_are_served(self):
        self.assertEqual(self.client.get('/health').status_code, 200)
        fig = self.content['masked'][0]
        self.assertEqual(self.client.get(f"/figures/{fig['base']}").status_code, 200)
        ex = self.content['measure_examples'][0]
        self.assertEqual(self.client.get(f"/measure-figures/{ex['layers'][0]['file']}").status_code, 200)
        self.get('/figures/../atlas.json', 404)

    def test_security_headers(self):
        r = self.client.get('/')
        self.assertIn("script-src 'self'", r.headers['Content-Security-Policy'])
        self.assertNotIn('<script>', r.get_data(as_text=True))
        self.assertNotIn(' style="', r.get_data(as_text=True))

    def test_measurement_tabs_match_cards(self):
        html = self.get('/measurements/')
        cards = set(re.findall(r'<article class="mx-card[^"]*" id="([^"]+)"', html))
        targets = set(re.findall(r'data-example="([^"]+)"', html))
        self.assertLessEqual(targets, cards)
        self.assertTrue(any(c.startswith('ex_ihc') for c in cards))
        self.assertIn('pending-he', cards)
        self.assertTrue(any(c.startswith('ex_he') for c in cards))

    def test_pending_rows_are_not_shown(self):
        atlas = self.content['atlas']
        pending = pending_by_modality(atlas['features'], self.content['items'], self.content['measure_examples'])
        shown = {(ex['modality'], f['id']) for ex in self.content['measure_examples'] for la in ex['layers'] for f in la['features']}
        for mod, groups in pending.items():
            for g in groups:
                for r in g['rows']:
                    self.assertNotIn((mod, r['feature']['id']), shown)
                    self.assertIn(mod, {modality_of(i) for i in r['feature']['imaging']})

    def test_measurement_list_hides_criteria(self):
        html = self.get('/measurements/')
        self.assertNotIn('글리슨 점수 9–10', html)

    def test_only_open_licences_on_pages(self):
        for fig in self.content['masked']:
            self.assertIn(fig['license'], {'CC BY 4.0', 'CC0 1.0'})
        for ex in self.content['measure_examples']:
            self.assertIn(ex['license'], {'CC BY 4.0', 'CC0 1.0'})


if __name__ == '__main__':
    unittest.main()
