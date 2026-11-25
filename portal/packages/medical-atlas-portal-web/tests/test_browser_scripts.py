"""Run client scripts against browser boundary fixtures; assert resulting navigation URLs."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which('node'), 'Node.js is needed for browser-script tests')
class LanguageScriptTest(unittest.TestCase):
    def run_switch(self, current, target):
        script = Path(__file__).parents[1] / 'src/medical_atlas_portal_web/static/language.js'
        program = r'''const fs = require('fs');
const vm = require('vm');
const [script, current, target] = process.argv.slice(1);
const page = new URL(current);
const handlers = {};
const link = {href:target, addEventListener:(type, fn) => {handlers[type] = fn;}};
vm.runInNewContext(fs.readFileSync(script, 'utf8'), {
  document:{querySelectorAll:() => [link]}, location:page, URL
});
const initial = link.href;
page.hash = '#changed';
handlers.click();
process.stdout.write(JSON.stringify([initial, link.href]));'''
        result = subprocess.run(['node', '-e', program, str(script), current, target],
                                check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def test_static_search_switch_keeps_query_section_and_hash(self):
        initial, clicked = self.run_switch(
            'http://localhost/project/en/retinal/search/?q=chest+wall&section=anatomy#layer',
            'http://localhost/project/retinal/search/')
        self.assertEqual(initial, 'http://localhost/project/retinal/search/?q=chest+wall&section=anatomy#layer')
        self.assertTrue(clicked.endswith('&section=anatomy#changed'))

    def test_prebuilt_filter_path_is_not_replaced_with_query(self):
        initial, _ = self.run_switch(
            'http://localhost/project/en/mammography/lesions/_q/cat-mass/#item',
            'http://localhost/project/mammography/lesions/_q/cat-mass/')
        self.assertEqual(initial, 'http://localhost/project/mammography/lesions/_q/cat-mass/#item')


if __name__ == '__main__':
    unittest.main()
