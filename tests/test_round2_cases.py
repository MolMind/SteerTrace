"""Round-two evidence isolation and long-dialogue import invariants."""
import json
from pathlib import Path
import tempfile
import unittest

from steertrace.importer import import_conversation
from steertrace.pipeline import prepare
from steertrace.storage import write_json

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'examples/quality/round2'


class RoundTwoCasesTests(unittest.TestCase):
    def test_long_dialogue_pairs_change_exactly_one_message(self):
        cases = json.loads((CORPUS / 'cases.json').read_text())
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({c['id'] for c in cases}), 12)
        pairs, families, policies = {}, {}, []
        with tempfile.TemporaryDirectory() as tmp:
            for i, case in enumerate(cases):
                with self.subTest(case=case['id']):
                    self.assertGreaterEqual(len(case['messages']), 14)
                    self.assertIn(case['split'], ('dev', 'holdout'))
                    policy = case['direction_policy']
                    self.assertIn(policy['mode'], ('required', 'unnecessary', 'insufficient'))
                    self.assertTrue(policy['reason'].strip())
                    policies.append(policy['mode'])
                    pairs.setdefault(case['pair_id'], []).append(case)
                    families.setdefault(case['family'], set()).add(case['split'])
                    source = Path(tmp) / f'{i}.json'
                    normalized = Path(tmp) / f'{i}-normalized.json'
                    write_json(source, case['messages'])
                    conversation = import_conversation(source)
                    self.assertEqual(len(conversation['messages']), len(case['messages']))
                    write_json(normalized, conversation)
                    prepare(normalized, ROOT, [], Path(tmp) / f'run-{i}')
        self.assertEqual(len(pairs), 6)
        self.assertEqual(len(families), 6)
        self.assertTrue(all(len(splits) == 1 for splits in families.values()))
        self.assertEqual({c['split'] for c in cases}, {'dev', 'holdout'})
        self.assertGreaterEqual(policies.count('unnecessary'), 2)
        self.assertGreaterEqual(policies.count('insufficient'), 2)
        for pair_id, pair in pairs.items():
            with self.subTest(pair=pair_id):
                self.assertEqual(len(pair), 2)
                a, b = pair
                self.assertEqual(a['family'], b['family'])
                self.assertEqual(a['split'], b['split'])
                self.assertEqual(len(a['messages']), len(b['messages']))
                self.assertEqual([(m['id'], m['role']) for m in a['messages']],
                                 [(m['id'], m['role']) for m in b['messages']])
                self.assertEqual(sum(x['content'] != y['content'] for x, y in zip(a['messages'], b['messages'])), 1)
                self.assertNotEqual(a['expected'], b['expected'])

    def test_prior_comparator_is_preserved(self):
        self.assertEqual((CORPUS / 'comparators/before.md').read_bytes(),
                         (ROOT / 'examples/quality/comparators/steertrace.md').read_bytes())
