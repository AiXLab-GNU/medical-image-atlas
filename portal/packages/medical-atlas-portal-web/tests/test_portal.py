"""Portal: one channel (domains mounted under paths) and the port-linked fallback."""
import re
import unittest

from medical_atlas_portal_web import create_app


class MountedTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app({'TESTING': True}).test_client()

    def get(self, url, code=200):
        r = self.client.get(url, base_url='http://example.test:8875')
        self.assertEqual(r.status_code, code, url)
        return r

    def test_index_links_to_mounted_domains(self):
        html = self.get('/').get_data(as_text=True)
        for name, path in (('망막 영상 지도', '/retinal/'), ('유방촬영 영상 지도', '/mammography/'), ('병리 영상 지도', '/pathology/')):
            self.assertIn(name, html)
            self.assertIn(f'href="{path}"', html)
        self.assertEqual(self.get('/health').json['mounted'], ['mammography', 'pathology', 'retinal'])

    def test_domain_pages_get_the_mount_prefix(self):
        for domain in ('retinal', 'mammography', 'pathology'):
            html = self.get(f'/{domain}/lesions/').get_data(as_text=True)
            roots = {m for m in re.findall(r'(?:href|src|action)="(/[^"/]*)', html)}
            self.assertEqual(roots, {f'/{domain}', '/static', '/en'}, domain)                 # every root link stays inside the domain
            self.assertNotIn(f'/{domain}/{domain}/', html)                    # static url_for links not prefixed twice
            self.assertIn('href="http://example.test:8875/"', html)          # bar: back to the portal
            self.assertIn('href="http://example.test:8875/pathology/"', html)

    def test_redirects(self):
        self.assertEqual(self.get('/pathology', 308).headers['Location'], 'http://example.test:8875/pathology/')
        self.assertEqual(self.get('/retinal/fundus/', 301).headers['Location'], '/retinal/images/')   # app redirect keeps the mount

    def test_previews(self):
        html = self.get('/').get_data(as_text=True)
        self.assertIn('/preview/pathology/', html)
        self.get('/preview/pathology/../../atlas.json', 404)
        self.get('/preview/retinal/not_listed.jpg', 404)


class PortOnlyTest(unittest.TestCase):
    def test_links_by_port_when_not_mounted(self):
        client = create_app({'TESTING': True}, mount=False).test_client()
        html = client.get('/', base_url='http://example.test:8875').get_data(as_text=True)
        for port in (8877, 8879, 8881):
            self.assertIn(f'http://example.test:{port}/', html)
        r = client.get('/go/mammography', base_url='http://localhost:8875')
        self.assertEqual(r.headers['Location'], 'http://localhost:8879/')
        self.assertEqual(client.get('/go/unknown').status_code, 404)


if __name__ == '__main__':
    unittest.main()
