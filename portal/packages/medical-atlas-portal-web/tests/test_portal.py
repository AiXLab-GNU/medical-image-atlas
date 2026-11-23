"""Portal page: three domain cards, links built from the request host, previews limited to listed files."""
import unittest

from medical_atlas_portal_web import create_app


class PortalTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app({'TESTING': True}).test_client()

    def test_index_lists_three_domains(self):
        r = self.client.get('/', base_url='http://example.test:8875')
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        for name, port in (('망막 영상 지도', 8877), ('유방촬영 영상 지도', 8879), ('병리 영상 지도', 8881)):
            self.assertIn(name, html)
            self.assertIn(f'http://example.test:{port}/', html)
        self.assertIn('3개 영역 홈', html)

    def test_previews(self):
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('/preview/pathology/', html)
        self.assertEqual(self.client.get('/preview/pathology/../../atlas.json').status_code, 404)
        self.assertEqual(self.client.get('/preview/retinal/not_listed.jpg').status_code, 404)

    def test_go_redirects(self):
        r = self.client.get('/go/mammography', base_url='http://localhost:8875')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers['Location'], 'http://localhost:8879/')
        self.assertEqual(self.client.get('/go/unknown').status_code, 404)


if __name__ == '__main__':
    unittest.main()
