"""Boundary tests: localize visible content without changing executable code or SVG geometry."""
import json
import tempfile
import unittest
from pathlib import Path

from medical_atlas_portal_web.localization import EnglishCatalog, EnglishHTML, english_url


class LocalizationBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        directory = Path(self.tmp.name)
        (directory / 'messages.json').write_text(json.dumps({'정의': 'Definition', '망막': 'Retina',
            '위험': '<script>alert(1)</script>', '개': 'items', '망막 홈으로': 'Open the retinal home', '· 유방': '· Breast', '유방촬영 영상 지도': 'Mammography Image Atlas'}))
        self.catalog = EnglishCatalog(directory)
        self.addCleanup(self.tmp.cleanup)

    def test_visible_text_and_accessible_labels_translate_safely(self):
        source = '<html lang="ko"><body><p title="정의">망막</p><p>위험</p></body></html>'
        html = EnglishHTML(self.catalog, 'localhost').render(source)
        self.assertIn('lang="en"', html)
        self.assertIn('title="Definition"', html)
        self.assertIn('>Retina</p>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertNotIn('<script>', html)

    def test_code_and_json_are_handled_differently(self):
        source = '<pre>망막 = 17</pre><script>const x = "망막";</script><script type="application/json">{"label":"망막","value":17}</script>'
        html = EnglishHTML(self.catalog, 'localhost').render(source)
        self.assertIn('<pre>망막 = 17</pre>', html)
        self.assertIn('const x = "망막";', html)
        self.assertIn('"label": "Retina", "value": 17', html)

    def test_svg_case_and_geometry_are_preserved(self):
        source = '<svg viewBox="0 0 12 12"><linearGradient id="x"></linearGradient><text x="2">망막</text></svg>'
        html = EnglishHTML(self.catalog, 'localhost').render(source)
        self.assertIn('viewBox="0 0 12 12"', html)
        self.assertIn('</linearGradient>', html)
        self.assertIn('<text x="2">Retina</text>', html)

    def test_ampersands_keep_medical_terms_and_escaped_code_safe(self):
        source = '<p>H&E–IHC 망막</p><pre>&lt;script&gt;망막&lt;/script&gt;</pre>'
        html = EnglishHTML(self.catalog, 'localhost').render(source)
        self.assertIn('<p>H&amp;E–IHC Retina</p>', html)
        self.assertIn('<pre>&lt;script&gt;망막&lt;/script&gt;</pre>', html)

    def test_internal_urls_keep_queries_and_external_sources_stay_original(self):
        self.assertEqual(english_url('/retinal/anatomy/?img=oct#layer', 'localhost'), '/en/retinal/anatomy/?img=oct#layer')
        self.assertEqual(english_url('https://example.org/retinal/', 'localhost'), 'https://example.org/retinal/')
        self.assertEqual(english_url('/en/retinal/', 'localhost'), '/en/retinal/')

    def test_rendered_phrase_accepts_already_localized_medical_name(self):
        self.assertEqual(self.catalog.translate('Retina 홈으로'), 'Open the retinal home')

    def test_domain_context_disambiguates_optic_disc_and_nipple(self):
        directory = Path(self.tmp.name)
        (directory / 'contexts.json').write_text(json.dumps({
            'retinal': {'유두': 'Optic disc'}, 'mammography': {'유두': 'Nipple'}}))
        self.assertEqual(EnglishCatalog(directory, domain='retinal').translate('유두'), 'Optic disc')
        self.assertEqual(EnglishCatalog(directory, domain='mammography').translate('유두'), 'Nipple')

    def test_catalog_entities_are_plain_text_before_html_escaping(self):
        directory = Path(self.tmp.name)
        (directory / 'entities.json').write_text(json.dumps({'불완전(&lt;250 µm)': 'Incomplete (&lt;250 µm)'}))
        catalog = EnglishCatalog(directory)
        self.assertEqual(catalog.translate('불완전(<250 µm)'), 'Incomplete (<250 µm)')

    def test_short_label_does_not_consume_prefix_of_longer_medical_title(self):
        self.assertEqual(self.catalog.translate('Error · 유방촬영 영상 지도'),
                         'Error · Mammography Image Atlas')

    def test_short_counter_does_not_corrupt_untranslated_words(self):
        self.assertEqual(self.catalog.translate('개방각'), '개방각')
        self.assertEqual(self.catalog.translate('3개'), '3 items')


if __name__ == '__main__':
    unittest.main()
