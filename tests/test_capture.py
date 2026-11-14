import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from steertrace.capture import capture, locate
from steertrace.storage import TraceError


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'history.json'
        self.rows = [{'id': 'u1', 'role': 'user', 'content': 'goal'},
                     {'id': 'a1', 'role': 'assistant', 'content': 'answer'},
                     {'id': 'u2', 'role': 'user', 'content': 'analyze this'},
                     {'id': 'a2', 'role': 'assistant', 'content': 'analysis activity'}]
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.rows))

    def test_excludes_invocation_and_all_later_messages(self):
        data = capture(self.path, 'auto', before_id='u2')
        self.assertEqual([m['id'] for m in data['messages']], ['u1', 'a1'])
        self.assertEqual(data['selection']['excluded_from_message_id'], 'u2')

    def test_full_text_boundary(self):
        self.assertEqual(len(capture(self.path, 'auto', before_text='analyze this')['messages']), 2)
        with self.assertRaises(TraceError): capture(self.path, 'auto', before_text='analyze')

    def test_duplicate_text_fails_instead_of_guessing(self):
        self.rows[0]['content'] = 'analyze this'; self.save()
        with self.assertRaises(TraceError): capture(self.path, 'auto', before_text='analyze this')
        self.assertEqual(len(capture(self.path, 'auto', before_id='u2')['messages']), 2)

    def test_missing_assistant_or_empty_boundary_fails(self):
        for mid in ['missing', 'a1', 'u1']:
            with self.assertRaises(TraceError): capture(self.path, 'auto', before_id=mid)
        with self.assertRaises(TraceError): capture(self.path, 'auto')

    def test_resolves_identified_session_not_latest(self):
        (self.root / 'rollout-other.jsonl').touch()
        target = self.root / 'rollout-current-id.jsonl'; target.touch()
        with patch.dict('os.environ', {'CODEX_THREAD_ID': 'current-id'}):
            self.assertEqual(locate('codex', None, self.root), target)
        with self.assertRaises(TraceError): locate('codex', 'missing', self.root)
        with self.assertRaises(TraceError): locate('claude', '../*', self.root)
        (self.root / 'duplicate-current-id.jsonl').touch()
        with self.assertRaises(TraceError): locate('codex', 'current-id', self.root)

    def test_harness_uses_final_messages_and_excludes_tools(self):
        self.path = self.root / 'harness.jsonl'
        rows = [{'type': 'user/message', 'surfaceOp': 'append', 'data': {'id':'u1','source':{'kind':'user'},'content':'goal'}},
                {'type': 'assistant/message', 'surfaceOp': 'append', 'data': {'message': {'id':'a1','content':[{'type':'text','text':'answer'}]}}},
                {'type': 'user/message', 'surfaceOp': 'append', 'data': {'id':'tool','source':{'kind':'tool'},'content':'tool result'}},
                {'type': 'user/message', 'surfaceOp': 'append', 'data': {'id':'u2','source':{'kind':'user'},'content':'analyze this'}}]
        self.path.write_text('\n'.join(json.dumps(r) for r in rows))
        data = capture(self.path, 'auto', before_id='u2')
        self.assertEqual([m['id'] for m in data['messages']], ['u1','a1'])
        self.assertEqual(data['source'], 'harness')
        rows[0]['surfaceOp'] = 'replace'
        self.path.write_text('\n'.join(json.dumps(r) for r in rows))
        with self.assertRaises(TraceError): capture(self.path, 'harness', before_id='u2')

    def test_cli_capture_and_failure_without_output(self):
        import subprocess
        import sys
        output = self.root / 'selected.json'
        result = subprocess.run([sys.executable, '-m', 'steertrace', 'capture',
                                 '--input', str(self.path), '--before-message-id', 'u2',
                                 '--output', str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(output.read_text())['messages']), 2)
        missing = self.root / 'missing.json'
        result = subprocess.run([sys.executable, '-m', 'steertrace', 'capture',
                                 '--input', str(self.path), '--before-message-id', 'absent',
                                 '--output', str(missing)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(missing.exists())
