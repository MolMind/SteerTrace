"""Corpus invariants and importability; not a semantic quality test."""
import json
from pathlib import Path
import tempfile
import unittest

from steertrace.importer import import_conversation
from steertrace.pipeline import prepare
from steertrace.storage import file_digest, write_json

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'examples' / 'quality'


class QualityCorpusTests(unittest.TestCase):
    def test_cases_are_importable_with_isolated_evidence(self):
        cases = json.loads((CORPUS / 'cases.json').read_text())
        self.assertGreaterEqual(len(cases), 24)
        self.assertEqual(len({case['id'] for case in cases}), len(cases))
        with tempfile.TemporaryDirectory() as temp:
            for i, case in enumerate(cases):
                with self.subTest(case=case['id']):
                    path = Path(temp) / f'{i}.json'
                    write_json(path, case['messages'])
                    normalized = import_conversation(path)
                    self.assertEqual(len(normalized['messages']), len(case['messages']))
                    write_json(Path(temp) / f'{i}-normalized.json', normalized)
                    manifest = prepare(Path(temp) / f'{i}-normalized.json', ROOT, [], Path(temp) / f'run-{i}')
                    self.assertEqual(manifest['document_count'], 0)
                    for field in ('must_find', 'must_avoid'):
                        checks = case['expected'][field]
                        self.assertTrue(checks)
                        self.assertTrue(all(isinstance(x, str) and x.strip() for x in checks))

    def test_holdout_families_do_not_leak_and_pairs_change_evidence(self):
        cases = json.loads((CORPUS / 'cases.json').read_text())
        families, pairs = {}, {}
        for case in cases:
            self.assertIn(case['split'], ('dev', 'holdout'))
            families.setdefault(case['family'], set()).add(case['split'])
            if case.get('pair_id'):
                pairs.setdefault(case['pair_id'], []).append(case)
        self.assertGreaterEqual(len(pairs), 6)
        self.assertEqual({c['split'] for c in cases}, {'dev', 'holdout'})
        self.assertTrue(all(len(splits) == 1 for splits in families.values()))
        for pair_id, pair in pairs.items():
            with self.subTest(pair=pair_id):
                self.assertEqual(len(pair), 2)
                self.assertEqual(pair[0]['family'], pair[1]['family'])
                self.assertNotEqual(pair[0]['messages'], pair[1]['messages'])
                self.assertNotEqual(pair[0]['expected'], pair[1]['expected'])

    def test_external_comparator_source_is_pinned_and_intact(self):
        provenance = json.loads((CORPUS / 'sources' / 'provenance.json').read_text())
        self.assertEqual(provenance['license'], 'MIT')
        self.assertEqual(len(provenance['commit']), 40)
        for name, source in provenance['files'].items():
            with self.subTest(source=name):
                self.assertIn(provenance['commit'], source['url'])
                self.assertEqual(file_digest(CORPUS / 'sources' / name), source['sha256'])
