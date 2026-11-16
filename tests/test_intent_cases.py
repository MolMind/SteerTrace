"""Exercise approval-centered AI criticism with the existing pipeline, not semantic scoring."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from steertrace.importer import import_conversation
from steertrace.pipeline import prepare
from steertrace.report import render
from steertrace.storage import file_digest, write_json
from steertrace.validation import validate

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'examples/quality/intent'


class IntentCasesTests(unittest.TestCase):
    def test_strengths_can_stand_alone_and_advice_can_add_distinct_evidence(self):
        cases = json.loads((ROOT / 'examples/synthetic/advice-boundary-cases.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            for case in cases:
                with self.subTest(case=case['id']):
                    source = Path(temp) / (case['id'] + '.json')
                    write_json(source, case['messages'])
                    normalized = Path(temp) / (case['id'] + '-normalized.json')
                    write_json(normalized, import_conversation(source))
                    run = Path(temp) / case['id']
                    analysis = case['analysis']
                    analysis['run_id'] = prepare(normalized, ROOT, [], run)['run_id']
                    html, result = render(run, analysis)
                    self.assertTrue(result['valid'], result)
                    self.assertIn('值得肯定的已有做法', html)
                    self.assertIn(analysis['review']['keep_doing'][0], html)
                    if case['id'] == 'completed':
                        self.assertEqual(analysis['recommendations'], [])
                        self.assertIn('本次未提出额外建议', html)
                    else:
                        self.assertIn('有新增价值的建议', html)
                        self.assertIn(analysis['recommendations'][0]['next_check'], html)

    def test_complete_collaborations_import_and_keep_pair_evidence_isolated(self):
        cases = json.loads((CORPUS / 'cases.json').read_text())
        pairs = {}
        with tempfile.TemporaryDirectory() as temp:
            for index, case in enumerate(cases):
                with self.subTest(case=case['id']):
                    pairs.setdefault(case['pair_id'], []).append(case)
                    source = Path(temp) / f'{index}.json'
                    write_json(source, case['messages'])
                    conversation = import_conversation(source)
                    self.assertEqual(len(conversation['messages']), 14)
                    normalized = Path(temp) / f"{index}-normalized.json"
                    write_json(normalized, conversation)
                    manifest = prepare(normalized, ROOT, [], Path(temp) / f'run-{index}')
                    self.assertEqual(manifest['document_count'], 0)
        self.assertEqual(len(pairs), 3)
        for pair in pairs.values():
            self.assertEqual(len(pair), 2)
            self.assertEqual(pair[0]['split'], pair[1]['split'])
            self.assertEqual(sum(a != b for a, b in zip(pair[0]['messages'], pair[1]['messages'])), 1)
            self.assertNotEqual(pair[0]['expected'], pair[1]['expected'])

    def test_brief_approval_can_anchor_ai_omission_and_concrete_advice(self):
        case = json.loads((CORPUS / 'cases.json').read_text())[0]
        analysis = json.loads((CORPUS / 'analysis-example.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            source, run = Path(temp) / 'conversation.json', Path(temp) / 'run'
            write_json(source, case['messages'])
            normalized = Path(temp) / "normalized.json"
            write_json(normalized, import_conversation(source))
            analysis['run_id'] = prepare(normalized, ROOT, [], run)['run_id']
            html, result = render(run, analysis)
            self.assertTrue(result['valid'], result)
            self.assertIn('归因：AI 表达或执行', html)
            self.assertIn(analysis['recommendations'][0]['next_check'], html)
            # Brief approval must still not establish authorship of the AI plan.
            invalid = copy.deepcopy(analysis)
            invalid['events'][0]['ownership'] = 'human_proposed'
            result = validate(run, invalid)
            self.assertFalse(result['valid'])

    def test_frozen_comparators_have_matching_provenance(self):
        provenance = json.loads((CORPUS / 'provenance.json').read_text())
        for name, expected in provenance['files'].items():
            self.assertEqual(file_digest(CORPUS / 'comparators' / name), expected)
