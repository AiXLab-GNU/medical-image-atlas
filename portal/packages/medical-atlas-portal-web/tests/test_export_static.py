"""Static export: relative links only, filter pages, browser search, downloads as files."""
import re
import tempfile
import unittest
from pathlib import Path

from medical_atlas_portal_web.export_static import Exporter, file_for, relative, slug


class HelpersTest(unittest.TestCase):
    def test_paths(self):
        self.assertEqual(file_for('/pathology/lesions/', '', True), 'pathology/lesions/index.html')
        self.assertEqual(file_for('/pathology/lesions/', 'img=he&cat=gleason', True),
                         'pathology/lesions/_q/cat-gleason_img-he/index.html')
        self.assertEqual(file_for('/pathology/code/x.py', 'download=1', False), 'pathology/code/x.py')
        self.assertEqual(relative('pathology/lesions/index.html', 'index.html'), '../../')
        self.assertEqual(relative('index.html', 'retinal/index.html'), 'retinal/')
        self.assertEqual(slug('b=2&a=%ED%95%9C'), 'a-~ED~95~9C_b-2')


class ExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / 'site'
        ex = Exporter(cls.out)
        ex.crawl()
        cls.report = ex.write()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_site(self):
        self.assertEqual(self.report['missing'], [])
        self.assertEqual(self.report['untranslated'], [])
        self.assertGreater(self.report['filter_pages'], 100)
        for f in ('index.html', '.nojekyll', '404.html', '_static/static_site.js', '_static/search_pathology.json',
                  'retinal/search/index.html', 'mammography/lesions/_q/cat-mass/index.html'):
            self.assertTrue((self.out / f).is_file(), f)

    def test_english_pages_search_and_shared_assets(self):
        for file in ('en/index.html', 'en/retinal/lesions/index.html',
                     'en/mammography/lesions/_q/cat-mass/index.html',
                     'en/pathology/validation/index.html', 'en/_static/search_mammography.json'):
            self.assertTrue((self.out / file).is_file(), file)
        html = (self.out / 'en/retinal/lesions/index.html').read_text()
        self.assertIn('lang="en"', html)
        self.assertIn('data-domain="retinal"', html)
        self.assertIn('data-language="en"', html)
        self.assertIn('data-root="../../"', html)
        self.assertNotIn('http://localhost', html)
        # Image data must use the Korean tree's canonical files, not duplicate source bytes.
        self.assertFalse((self.out / 'en/retinal/figures/fundus_optic_disc.jpg').exists())
        self.assertTrue((self.out / 'retinal/figures/fundus_optic_disc.jpg').is_file())
        import json
        records = json.loads((self.out / 'en/_static/search_mammography.json').read_text())
        self.assertTrue(any(item['name'] == 'Breast' for item in records))
        self.assertFalse(any(item['path'].startswith('en/') for item in records))

    def test_english_static_not_found_page(self):
        from medical_atlas_portal_web.localization import untranslated_text
        path = self.out / 'en/404.html'
        self.assertTrue(path.is_file())
        html = path.read_text()
        self.assertIn('lang="en"', html)
        self.assertIn('Page not found', html)
        self.assertEqual(untranslated_text(html), [])

    def test_links_are_relative(self):
        for page in list(self.out.rglob('index.html'))[:300]:
            html = page.read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'(?:href|src|action)="(?:/(?!/)|http://localhost)', html), page)
            self.assertIn('static_site.js', html)


if __name__ == '__main__':
    unittest.main()
