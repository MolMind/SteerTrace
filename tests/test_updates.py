import hashlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

from steertrace import updates as u
from steertrace.storage import TraceError


def manifest(minimum='0.1.0', latest='0.2.0', payload=b'archive'):
    return {'schema_version': 'steertrace.update/v1', 'latest_version': latest,
            'minimum_supported_version': minimum, 'reason': 'Synthetic release, not a real update.',
            'release_tag': 'v' + latest, 'commit': 'a' * 40,
            'sha256': hashlib.sha256(payload).hexdigest()}


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'managed'
        self.root.mkdir()
        self.skill = self.base / 'client skills' / 'steer-trace'
        self.skill.mkdir(parents=True)
        (self.skill / 'SKILL.md').write_text('old skill')
        self.source = self.root / 'old-source'
        self.source.mkdir()
        (self.source / 'README.md').write_text('old source')
        self.state = {'version': '0.1.0', 'commit': 'b' * 40, 'source': str(self.source),
                      'python': str(self.base / 'old-python'), 'skill_dir': str(self.skill),
                      'install_root': str(self.root), 'source_hash': u.tree_hash(self.source),
                      'skill_hash': u.tree_hash(self.skill)}
        u.atomic_json(self.root / 'state.json', self.state)

    def cache(self, data, timestamp=None):
        u.atomic_json(self.root / 'update-cache.json', {'checked_at': time.time() if timestamp is None else timestamp,
                                                       'policy': data})

    def archive(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as z:
            for name, text in {'src/steertrace/__init__.py': '__version__ = "0.2.0"',
                               'skills/steer-trace/SKILL.md': 'new skill',
                               'docs/reference/event-schema.md': 'schema',
                               'scripts/update.py': '# bootstrap'}.items():
                z.writestr(name, text)
        return output.getvalue()

    def stage(self, payload, **kwargs):
        with patch.object(u, 'download', return_value=payload), patch.object(u.venv, 'create'), \
             patch.object(u, 'run'), patch.object(u.subprocess, 'check_output', return_value='0.2.0\n'):
            return u.install_release(self.root, self.skill, manifest(payload=payload), self.state, **kwargs)

    def test_success_switches_all_paths_and_preserves_previous(self):
        new = self.stage(self.archive())
        self.assertEqual(new['version'], '0.2.0')
        self.assertNotEqual(new['python'], self.state['python'])
        self.assertEqual(u.read_json(self.root / 'state.json'), new)
        self.assertEqual(u.tree_hash(self.skill), new['skill_hash'])
        self.assertEqual(u.tree_hash(Path(new['source'])), new['source_hash'])
        self.assertEqual((self.skill / 'SKILL.md').read_text(), 'new skill')
        self.assertEqual(u.read_json(self.skill / u.MARKER)['source'], new['source'])
        self.assertTrue(self.source.exists())
        self.assertEqual(len(list(self.root.glob('history/*.json'))), 1)
        self.assertEqual(len(list(self.skill.parent.glob('steer-trace.backup-*'))), 1)

    def test_switch_write_failure_restores_old_skill_and_state(self):
        real = u.atomic_json
        def fail_state(path, value):
            if path == self.root / 'state.json':
                raise OSError('simulated disk failure')
            real(path, value)
        with patch.object(u, 'atomic_json', side_effect=fail_state):
            with self.assertRaises(OSError):
                self.stage(self.archive())
        self.assertEqual((self.skill / 'SKILL.md').read_text(), 'old skill')
        self.assertEqual(u.read_json(self.root / 'state.json'), self.state)

    def test_digest_failure_preserves_active_install(self):
        with patch.object(u, 'download', return_value=b'wrong bytes'):
            with self.assertRaisesRegex(TraceError, 'SHA-256'):
                u.install_release(self.root, self.skill, manifest(), self.state)
        self.assertEqual(u.read_json(self.root / 'state.json'), self.state)
        self.assertFalse(list((self.root / 'releases').iterdir()))

    def test_edit_during_staging_is_preserved(self):
        payload = self.archive()
        def edit(*args, **kwargs):
            (self.skill / 'SKILL.md').write_text('user edited while staging')
            return '0.2.0'
        with patch.object(u, 'download', return_value=payload), patch.object(u.venv, 'create'), \
             patch.object(u, 'run'), patch.object(u.subprocess, 'check_output', side_effect=edit):
            with self.assertRaisesRegex(TraceError, 'changed during staging'):
                u.install_release(self.root, self.skill, manifest(payload=payload), self.state)
        self.assertEqual((self.skill / 'SKILL.md').read_text(), 'user edited while staging')
        self.assertEqual(u.read_json(self.root / 'state.json'), self.state)

    def test_cli_verification_failure_does_not_switch(self):
        payload = self.archive()
        with patch.object(u, 'download', return_value=payload), patch.object(u.venv, 'create'), \
             patch.object(u, 'run'), patch.object(u.subprocess, 'check_output', return_value='0.1.0'):
            with self.assertRaisesRegex(TraceError, 'CLI version'):
                u.install_release(self.root, self.skill, manifest(payload=payload), self.state)
        self.assertEqual(u.read_json(self.root / 'state.json'), self.state)
        self.assertEqual((self.skill / 'SKILL.md').read_text(), 'old skill')

    def test_local_edits_refuse_update_before_download(self):
        for path in (self.skill / 'SKILL.md', self.source / 'README.md'):
            old = path.read_text()
            path.write_text(old + ' custom')
            with patch.object(u, 'download') as download:
                with self.assertRaisesRegex(TraceError, 'Local modifications'):
                    u.install_release(self.root, self.skill, manifest(), self.state)
                download.assert_not_called()
            path.write_text(old)

    def test_supported_offline_can_run_but_is_not_confirmed_current(self):
        with patch.object(u, 'fetch_policy', side_effect=OSError('offline')):
            result = u.update(self.root, check_only=True)
        self.assertTrue(result['can_run'])
        self.assertTrue(result['offline'])
        self.assertIsNone(result['latest_version'])
        self.assertEqual(result['status'], 'offline')
        self.assertFalse((self.root / 'update.lock').exists())

    def test_known_mandatory_update_stays_blocked_offline(self):
        self.cache(manifest(minimum='0.2.0'), timestamp=0)
        with patch.object(u, 'fetch_policy', side_effect=OSError('offline')), \
             patch.object(u, 'install_release', side_effect=OSError('download failed')):
            result = u.update(self.root)
        self.assertFalse(result['can_run'])
        self.assertTrue(result['required'])
        self.assertTrue(result['offline'])
        self.assertEqual(result['status'], 'update_failed')

    def test_optional_failed_update_keeps_supported_install_usable(self):
        self.cache(manifest())
        with patch.object(u, 'install_release', side_effect=OSError('failed')):
            result = u.update(self.root)
        self.assertTrue(result['can_run'])
        self.assertEqual(result['installed_version'], '0.1.0')
        self.assertEqual(result['status'], 'update_failed')

    def test_cache_and_explicit_refresh(self):
        self.cache(manifest())
        with patch.object(u, 'fetch_policy', return_value=manifest()) as fetch:
            u.update(self.root, check_only=True)
            fetch.assert_not_called()
            u.update(self.root, check_only=True, force_check=True)
            fetch.assert_called_once()

    def test_minimum_cannot_be_relaxed_by_remote_regression(self):
        self.cache(manifest(minimum='0.2.0'))
        with patch.object(u, 'fetch_policy', return_value=manifest()):
            result = u.update(self.root, check_only=True, force_check=True)
        self.assertFalse(result['can_run'])
        self.assertTrue(result['required'])

    def test_initial_offline_cannot_claim_installation(self):
        (self.root / 'state.json').unlink()
        with patch.object(u, 'fetch_policy', side_effect=OSError('offline')):
            result = u.update(self.root, self.skill)
        self.assertFalse(result['can_run'])
        self.assertIsNone(result['installed_version'])

    def test_existing_unmanaged_copy_requires_matching_adoption_source(self):
        with patch.object(u, 'download') as download:
            with self.assertRaisesRegex(TraceError, '--adopt-from'):
                u.install_release(self.root, self.skill, manifest(), None)
            download.assert_not_called()
        adoption = self.base / 'legacy'
        (adoption / 'skills/steer-trace').mkdir(parents=True)
        (adoption / 'skills/steer-trace/SKILL.md').write_text('old skill')
        with patch.object(u, 'download', return_value=self.archive()), patch.object(u.venv, 'create'), \
             patch.object(u, 'run'), patch.object(u.subprocess, 'check_output', return_value='0.2.0'):
            state = u.install_release(self.root, self.skill, manifest(payload=self.archive()), None, adoption)
        self.assertEqual(state['version'], '0.2.0')

    def test_concurrent_update_is_refused(self):
        (self.root / 'update.lock').touch()
        with self.assertRaisesRegex(TraceError, 'Another update'):
            u.update(self.root)
        self.assertTrue((self.root / 'update.lock').exists())

    def test_zip_traversal_and_symlinks_refused(self):
        for name in ('../escape', '/absolute', 'C:/file', 'folder\\file'):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as z:
                z.writestr(name, 'bad')
            with self.assertRaisesRegex(TraceError, 'Unsafe'):
                u.unpack(stream.getvalue(), self.root / 'extracted')
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as z:
            info = zipfile.ZipInfo('link')
            info.external_attr = 0o120777 << 16
            z.writestr(info, '../target')
        with self.assertRaisesRegex(TraceError, 'Unsafe'):
            u.unpack(stream.getvalue(), self.root / 'extracted')

    def test_manifest_rejects_invalid_versions_and_digest(self):
        for key, bad in [('latest_version', 'v0.2.0'), ('minimum_supported_version', '1.0.0'),
                         ('release_tag', 'main'), ('sha256', ''), ('commit', 'branch'), ('reason', '')]:
            data = manifest()
            data[key] = bad
            with self.assertRaises(TraceError):
                u.policy(data)

    def test_fixed_release_urls_and_no_user_data(self):
        metadata = {'tag_name': 'v0.2.0', 'draft': False, 'prerelease': False}
        with patch.object(u, 'download', side_effect=[json.dumps(metadata).encode(), json.dumps(manifest()).encode()]) as get:
            self.assertEqual(u.fetch_policy(), manifest())
        self.assertEqual(get.call_args_list[0].args[0], u.LATEST)
        self.assertEqual(get.call_args_list[1].args[0], u.REPOSITORY + '/releases/download/v0.2.0/steertrace-update.json')


if __name__ == '__main__':
    unittest.main()
