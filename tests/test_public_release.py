from pathlib import Path
import unittest
from zipfile import ZipFile

from desktop_simulator.leaderboard_client import LeaderboardAPI
from desktop_simulator.platform_support import APP_VERSION


ROOT = Path(__file__).resolve().parents[1]


class PublicReleaseTests(unittest.TestCase):
    def test_release_version_and_https_only_api(self):
        self.assertEqual(APP_VERSION, '30.0')
        with self.assertRaises(ValueError):
            LeaderboardAPI('http://47.236.21.46')

    def test_submission_template_has_fixed_entrypoint(self):
        folder = ROOT / 'examples' / 'strategy_template'
        namespace = {}
        exec(compile((folder / 'strategy.py').read_text(), 'strategy.py', 'exec'), namespace)
        self.assertTrue(callable(namespace['run']))

        target = folder / 'source.zip'
        if target.exists():
            target.unlink()
        exec(compile((folder / 'make_zip.py').read_text(), 'make_zip.py', 'exec'), {'__file__': str(folder / 'make_zip.py')})
        try:
            with ZipFile(target) as archive:
                self.assertEqual(sorted(archive.namelist()), ['README.md', 'strategy.py'])
                self.assertIn(b'def run(api):', archive.read('strategy.py'))
        finally:
            target.unlink(missing_ok=True)

    def test_private_runtime_is_not_present(self):
        forbidden = (
            'Q3_Q4_LOCAL_SIMULATOR_V1', 'generator.py', 'q4_generator.py',
            'environment.py', 'leaderboard.sqlite3',
        )
        paths = {path.name for path in ROOT.rglob('*') if path.is_file() and '.git' not in path.parts}
        for name in forbidden:
            self.assertNotIn(name, paths)
        for name in ('data', 'backend', 'evaluator', 'submissions', 'artifacts'):
            self.assertFalse((ROOT / name).exists(), name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
