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
        self.assertGreater(self.report['filter_pages'], 100)
        for f in ('index.html', '.nojekyll', '404.html', '_static/static_site.js', '_static/search_pathology.json',
                  'retinal/search/index.html', 'mammography/lesions/_q/cat-mass/index.html'):
            self.assertTrue((self.out / f).is_file(), f)

    def test_links_are_relative(self):
        for page in list(self.out.rglob('index.html'))[:300]:
            html = page.read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'(?:href|src|action)="(?:/(?!/)|http://localhost)', html), page)
            self.assertIn('static_site.js', html)


if __name__ == '__main__':
    unittest.main()
