import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publish_script', ROOT / 'scripts/publish_release.py')
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)


class PublishPlanTests(unittest.TestCase):
    def test_new_release_and_exact_rerun(self):
        rules = {'minimum_supported_version': '0.1.0'}
        old = {'latest_version': '0.1.0', 'minimum_supported_version': '0.1.0', 'commit': 'a' * 40}
        self.assertTrue(publish.should_publish('0.2.0', rules, 'b' * 40, None))
        self.assertTrue(publish.should_publish('0.2.0', rules, 'b' * 40, old))
        self.assertFalse(publish.should_publish('0.1.0', rules, 'a' * 40, old))
        for latest, minimum, commit in [('0.0.9', '0.1.0', 'b' * 40),
                                         ('0.1.0', '0.1.0', 'b' * 40),
                                         ('0.2.0', '0.0.1', 'b' * 40)]:
            with self.assertRaises(ValueError):
                publish.should_publish(latest, {'minimum_supported_version': minimum}, commit, old)

    def test_exact_rerun_does_not_tag_build_or_publish(self):
        previous = {'latest_version': '0.2.0', 'minimum_supported_version': '0.1.0', 'commit': 'a' * 40}
        with patch.object(sys, 'argv', ['publish_release.py', '--output', '/unused']), \
             patch.object(publish.releasing, 'check', return_value=('0.2.0', {'minimum_supported_version': '0.1.0'})), \
             patch.object(publish.releasing, 'fetch_policy', return_value=previous), \
             patch.object(publish, 'git', side_effect=['a' * 40, '']), \
             patch.object(publish, 'ensure_tag') as tag, patch.object(publish.subprocess, 'run') as run:
            publish.main()
        tag.assert_not_called()
        run.assert_not_called()


class TagTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.repo = base / 'source'
        self.repo.mkdir()
        self.remote = base / 'remote.git'
        subprocess.run(['git', 'init', '--bare', str(self.remote)], check=True, capture_output=True)
        self.git('init')
        self.git('remote', 'add', 'origin', str(self.remote))
        (self.repo / 'fixture.txt').write_text('Synthetic source')
        self.git('add', '.')
        self.git('commit', '-m', 'Synthetic fixture')
        self.commit = self.git('rev-parse', 'HEAD')
        self.root_patch = patch.object(publish, 'ROOT', self.repo)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'user.name=Synthetic', '-c', 'user.email=test@example.invalid',
                                        *args], cwd=self.repo, text=True, stderr=subprocess.DEVNULL).strip()

    def test_tag_creation_push_and_safe_repeat(self):
        publish.ensure_tag('v0.2.0', self.commit)
        self.assertIn(self.commit, self.git('ls-remote', '--tags', 'origin', 'refs/tags/v0.2.0'))
        publish.ensure_tag('v0.2.0', self.commit)

    def test_existing_remote_tag_cannot_move(self):
        publish.ensure_tag('v0.2.0', self.commit)
        (self.repo / 'fixture.txt').write_text('new source')
        self.git('commit', '-am', 'new fixture')
        newer = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'refusing to move'):
            publish.ensure_tag('v0.2.0', newer)
        self.assertIn(self.commit, self.git('ls-remote', '--tags', 'origin', 'refs/tags/v0.2.0'))

    def test_matching_annotated_tag_is_accepted_and_fetched(self):
        self.git('tag', '-a', 'v0.2.0', '-m', 'Synthetic release')
        self.git('push', 'origin', 'refs/tags/v0.2.0')
        self.git('tag', '-d', 'v0.2.0')
        publish.ensure_tag('v0.2.0', self.commit)
        self.assertEqual(self.git('rev-parse', 'v0.2.0^{commit}'), self.commit)
