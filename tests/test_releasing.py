import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_script', ROOT / 'scripts/release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        for name in ('src/steertrace/__init__.py', 'pyproject.toml', 'release-policy.json', 'CHANGELOG.md'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        (self.root / 'src/steertrace/__init__.py').write_text('__version__ = "0.2.0"\n')
        (self.root / 'release-policy.json').write_text(json.dumps({'minimum_supported_version': '0.1.0', 'reason': 'Synthetic optional update.'}))
        (self.root / 'CHANGELOG.md').write_text('# Changelog\n\n## 0.2.0\n\nSynthetic release.\n')
        self.patch = patch.object(release, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def invoke(self, *args):
        with patch.object(sys, 'argv', ['release.py', *args]):
            release.main()

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'user.name=Synthetic Test', '-c',
                                        'user.email=test@example.invalid', *args], cwd=self.root,
                                       text=True, stderr=subprocess.DEVNULL).strip()

    def test_bump_updates_single_version_changelog_and_policy(self):
        before = release.current()
        numbers = list(map(int, before.split('.')))
        numbers[2] += 1
        expected = '.'.join(map(str, numbers))
        self.invoke('--bump', 'patch', '--reason', 'Synthetic fix; optional upgrade.')
        self.assertEqual(release.current(), expected)
        self.assertEqual(release.check()[0], expected)
        self.assertIn('attr = "steertrace.__version__"', (self.root / 'pyproject.toml').read_text())

    def test_minimum_version_cannot_decrease(self):
        with self.assertRaises(ValueError):
            self.invoke('--bump', 'minor', '--reason', 'Synthetic', '--minimum-supported', '0.0.0')
        self.assertEqual(release.current(), '0.2.0')

    def test_build_binds_archive_to_clean_tagged_commit(self):
        self.git('init')
        self.git('add', '.')
        self.git('commit', '-m', 'Synthetic fixture')
        self.git('tag', 'v' + release.current())
        output = self.root.parent / 'assets'
        self.invoke('--build', str(output))
        metadata = json.loads((output / 'steertrace-update.json').read_text())
        archive = output / ('steertrace-' + release.current() + '.zip')
        self.assertEqual(metadata['sha256'], hashlib.sha256(archive.read_bytes()).hexdigest())
        self.assertEqual(metadata['commit'], self.git('rev-parse', 'HEAD'))
        with zipfile.ZipFile(archive) as z:
            self.assertIn('pyproject.toml', z.namelist())
        (self.root / 'CHANGELOG.md').write_text('uncommitted')
        with self.assertRaises(ValueError):
            self.invoke('--build', str(self.root.parent / 'bad-assets'))

    def test_remote_existing_version_cannot_be_republished(self):
        with patch.object(release, 'fetch_policy', return_value={'latest_version': '0.2.0', 'minimum_supported_version': '0.1.0'}):
            with self.assertRaisesRegex(ValueError, 'exceed'):
                self.invoke('--check-remote')

    def test_remote_minimum_cannot_be_reduced(self):
        with patch.object(release, 'fetch_policy', return_value={'latest_version': '0.1.9', 'minimum_supported_version': '0.1.9'}):
            with self.assertRaisesRegex(ValueError, 'cannot decrease'):
                self.invoke('--check-remote')

    def test_first_release_404_allowed_but_missing_asset_or_network_fails(self):
        url = 'https://api.github.com/repos/MolMind/SteerTrace/releases/latest'
        with patch.object(release, 'fetch_policy', side_effect=urllib.error.HTTPError(url, 404, 'Not Found', {}, None)):
            self.invoke('--check-remote')
        for error in (OSError('offline'), urllib.error.HTTPError('https://github.com/missing-asset', 404, 'Not Found', {}, None)):
            with patch.object(release, 'fetch_policy', side_effect=error):
                with self.assertRaises((OSError, urllib.error.HTTPError)):
                    self.invoke('--check-remote')

    def test_missing_changelog_is_not_releasable(self):
        (self.root / 'CHANGELOG.md').write_text('# Changelog\n')
        with self.assertRaisesRegex(ValueError, 'CHANGELOG'):
            release.check()
