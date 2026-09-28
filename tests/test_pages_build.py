"""Pages artifact has the assets the root HTML actually loads."""
import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


class PagesBuildTests(unittest.TestCase):
    def test_pages_build_contains_root_assets_and_backend_configuration(self):
        with TemporaryDirectory() as ignored:
            env = dict(os.environ, AIOS_BACKEND_URL='https://preview-8000.app.github.dev')
            subprocess.run(['bash', 'scripts/build-review.sh'], cwd=ROOT, env=env, check=True, capture_output=True)
            out = ROOT / 'dist' / 'review'
            for name in ('index.html', 'app.js', 'app.css', 'runtime-config.js', 'ui/index.html', 'ui/app.js'):
                self.assertTrue((out / name).is_file(), name)
            self.assertIn('https://preview-8000.app.github.dev', (out / 'runtime-config.js').read_text())
            self.assertIn('runtime-config.js', (out / 'index.html').read_text())


if __name__ == '__main__':
    unittest.main()
