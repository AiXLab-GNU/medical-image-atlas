"""Bilingual URLs, scientific content, language switching and unmodified provider bytes."""
import re
import unittest
from html.parser import HTMLParser

from medical_atlas_portal_web import create_app


class EnglishMirrorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app({'TESTING': True})
        cls.client = cls.app.test_client()

    def test_english_portal_and_korean_portal_coexist(self):
        en = self.client.get('/en/')
        self.assertEqual(en.status_code, 200)
        html = en.get_data(as_text=True)
        self.assertIn('lang="en"', html)
        self.assertIn('Medical Image Atlas', html)
        for domain in ('retinal', 'mammography', 'pathology'):
            self.assertIn('href="/en/' + domain + '/"', html)
        ko = self.client.get('/').get_data(as_text=True)
        self.assertIn('lang="ko"', ko)
        self.assertIn('의료영상 지도', ko)

    def test_english_domain_pages(self):
        for domain in ('retinal', 'mammography', 'pathology'):
            for page in ('', 'anatomy/', 'lesions/', 'measurements/', 'diseases/', 'imaging/', 'sources/'):
                with self.subTest(domain=domain, page=page):
                    r = self.client.get('/en/' + domain + '/' + page)
                    self.assertEqual(r.status_code, 200)
                    html = r.get_data(as_text=True)
                    self.assertIn('lang="en"', html)
                    self.assertIn('/en/' + domain + '/', html)
                    self.assertNotIn('/en/en/', html)

    def test_switch_preserves_deep_path_and_filters(self):
        url = '/en/mammography/lesions/?img=ffdm&cat=mass'
        html = self.client.get(url).get_data(as_text=True)
        self.assertRegex(html, r'href="/mammography/lesions/\?[^" ]*cat=mass')
        self.assertIn('img=ffdm', html)
        self.assertIn('data-language-switch', html)
        ko = self.client.get('/mammography/lesions/?img=ffdm&cat=mass').get_data(as_text=True)
        self.assertIn('/en/mammography/lesions/?', ko)

    def test_korean_header_has_direct_same_page_english_switch(self):
        for path in ('/', '/retinal/lesions/', '/mammography/measurements/?img=ffdm', '/pathology/validation/'):
            html = self.client.get(path).get_data(as_text=True)
            before_main = html.split('<main', 1)[0]
            self.assertIn('data-language-selector', before_main, path)
            self.assertIn('English</a>', before_main, path)
            self.assertIn('href="/en' + path.replace('&', '&amp;') + '"', before_main, path)
            self.assertEqual(html.count('data-language-selector'), 1)
            if path == '/':
                self.assertIn('data-language-selector', html.split('</header>', 1)[0])
            else:
                bar = html.split('<div class="atlas-bar">', 1)[1].split('<header class="top">', 1)[0]
                self.assertIn('data-language-selector', bar)

    def test_english_search_uses_translated_definition(self):
        r = self.client.get('/en/mammography/search/?q=chest+wall')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Breast', r.get_data(as_text=True))
        self.assertIn('Chest wall', r.get_data(as_text=True))

    def test_dynamic_empty_search_and_error_prose_are_english(self):
        from medical_atlas_portal_web.localization import untranslated_text
        for domain in ('retinal', 'mammography', 'pathology'):
            for suffix in ('search/?q=notfoundword', 'not-a-page/'):
                response = self.client.get('/en/' + domain + '/' + suffix)
                self.assertEqual(untranslated_text(response.get_data(as_text=True)), [])

    def test_redirect_keeps_english_language(self):
        r = self.client.get('/en/retinal/fundus/')
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.headers['Location'], '/en/retinal/images/')
        r = self.client.get('/en')
        self.assertIn(r.status_code, (301, 308))
        self.assertTrue(r.headers['Location'].endswith('/en/'))

    def test_provider_image_bytes_are_shared(self):
        path = '/retinal/figures/fundus_optic_disc.jpg'
        ko = self.client.get(path)
        en = self.client.get('/en' + path)
        self.assertEqual(ko.status_code, 200)
        self.assertEqual(en.status_code, 200)
        self.assertEqual(ko.get_data(), en.get_data())

    def test_proxy_prefix_is_applied_once_to_links_and_language_switches(self):
        r = self.client.get('/en/', environ_overrides={'SCRIPT_NAME': '/atlas'})
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn('href="/atlas/en/retinal/"', html)
        self.assertIn('href="/atlas/" lang="ko"', html)
        self.assertIn('src="/atlas/en/static/language.js"', html)
        self.assertNotIn('/en/atlas/', html)
        self.assertNotIn('/en/en/', html)
        r = self.client.get('/en/retinal/fundus/', environ_overrides={'SCRIPT_NAME': '/atlas'})
        self.assertEqual(r.headers['Location'], '/atlas/en/retinal/images/')

    def test_generated_schematic_labels_translate_without_changing_source(self):
        path = '/retinal/static/schematics/les_hard_exudate-face.svg'
        ko = self.client.get(path)
        en = self.client.get('/en' + path)
        self.assertEqual(en.status_code, 200)
        self.assertIn('경성삼출물', ko.get_data(as_text=True))
        self.assertNotIn('경성삼출물', en.get_data(as_text=True))
        self.assertIn('viewBox="', en.get_data(as_text=True))

    def test_translated_schematic_ranges_and_validators_describe_english_bytes(self):
        path = '/en/retinal/static/schematics/les_hard_exudate-face.svg'
        full = self.client.get(path)
        self.assertIsNotNone(full.headers.get('ETag'))
        self.assertNotIn('Last-Modified', full.headers)
        ranged = self.client.get(path, headers={'Range': 'bytes=0-99'})
        self.assertEqual(ranged.status_code, 200)
        self.assertNotIn('Content-Range', ranged.headers)
        self.assertEqual(ranged.get_data(), full.get_data())
        cached = self.client.get(path, headers={'If-None-Match': full.headers['ETag']})
        self.assertEqual(cached.status_code, 304)
        self.assertEqual(cached.get_data(), b'')

    def test_head_has_same_representation_length_as_get(self):
        for path in ('/en/retinal/lesions/', '/retinal/lesions/'):
            full = self.client.get(path)
            head = self.client.head(path)
            self.assertEqual(head.status_code, full.status_code)
            self.assertEqual(head.content_length, full.content_length)
            self.assertEqual(head.get_data(), b'')

    def test_app_instances_do_not_share_mount_state(self):
        other = create_app({'TESTING': True}, mount=False)
        self.assertEqual(other.test_client().get('/health').json['mounted'], [])
        self.assertEqual(self.client.get('/health').json['mounted'], ['mammography', 'pathology', 'retinal'])
        self.assertEqual(self.client.get('/en/health').json['mounted'], ['mammography', 'pathology', 'retinal'])

    def test_english_errors_have_language_and_safe_switch(self):
        r = self.client.get('/en/mammography/not-a-page/?x=%22%3E%3Cscript%3E')
        self.assertEqual(r.status_code, 404)
        self.assertIn('lang="en"', r.get_data(as_text=True))
        self.assertNotIn('<script></script>', r.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
