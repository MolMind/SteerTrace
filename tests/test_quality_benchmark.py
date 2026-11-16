import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('compare_quality', Path(__file__).resolve().parents[1] / 'scripts/compare_quality.py')
q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(q)


class QualityBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.case = {'id': 'c1', 'family': 'causal', 'split': 'holdout', 'messages': [{'id': 'u1', 'role': 'user', 'content': '发生故障，原因未定。'}], 'expected': {'must_find': ['SECRET ANSWER'], 'must_avoid': ['blame']}}
        q.write(self.root / 'cases.json', [self.case])
        (self.root / 'comparators').mkdir()
        for name in ('alpha', 'beta'):
            (self.root / 'comparators' / (name + '.md')).write_text('分析给定记录。')
        self.run = self.root / 'run'
        q.prepare(self.root / 'cases.json', self.root / 'comparators', self.run)
        self.obj = {'headline': '原因未定', 'findings': [{'claim': '不能确定原因', 'evidence': ['u1'], 'qualification': '记录有限'}], 'directions': [], 'limitations': ['单次记录']}

    def put_outputs(self):
        for name in ('alpha', 'beta'):
            q.write(self.run / 'outputs' / name / 'c1.json', self.obj)

    def ratings(self, blind):
        rows = q.read(blind / 'ratings.template.json')
        for r in rows:
            r['scores'] = {d: 3 for d in q.DIMENSIONS}
            r['rationale'] = [{'quote': '不能确定原因', 'reason': '未制造根因'}]
        return rows

    def test_generation_does_not_leak_expected_answers(self):
        prompt = (self.run / 'generation/alpha/c1.md').read_text()
        self.assertIn('发生故障', prompt)
        self.assertNotIn('SECRET ANSWER', prompt)
        self.assertNotIn('must_find', prompt)

    def test_blind_hides_identity_and_summary_is_paired(self):
        self.put_outputs()
        b = self.run / 'blind'
        q.blind(self.run, b)
        self.assertNotIn('alpha', (b / 'submissions.json').read_text())
        rows = self.ratings(b)
        q.write(self.run / 'ratings.json', rows)
        result = q.summarize(self.run, b, self.run / 'ratings.json')
        self.assertEqual(result['paired_results'][0]['ties'], 1)
        self.assertEqual(result['paired_results'][0]['cases'][0]['common_dimensions'], list(q.DIMENSIONS))
        self.assertEqual(result['paired_results'][0]['cases'][0]['score_delta_a_minus_b'], 0)
        self.assertEqual(result['by_split']['holdout']['paired_results'][0]['ties'], 1)
        self.assertEqual(result['comparators']['alpha']['dimensions']['clarity']['n'], 1)

    def test_missing_outputs_not_zero_scores(self):
        q.write(self.run / 'outputs/alpha/c1.json', self.obj)
        with self.assertRaisesRegex(ValueError, 'Missing outputs'):
            q.blind(self.run, self.run / 'b')
        b = self.run / 'b'
        q.blind(self.run, b, allow_missing=True)
        q.write(self.run / 'ratings.json', self.ratings(b))
        result = q.summarize(self.run, b, self.run / 'ratings.json')
        self.assertEqual(result['comparators']['beta']['coverage'], 0)
        self.assertIsNone(result['comparators']['beta']['dimensions']['clarity']['mean'])
        self.assertEqual(result['paired_results'][0]['unpaired_cases'], 1)

    def test_duplicate_json_keys_rejected(self):
        p = self.run / 'duplicate.json'
        p.write_text('{"headline":"a","headline":"b"}')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            q.read(p)

    def test_unknown_evidence_rejected(self):
        self.obj['findings'][0]['evidence'] = ['invented']
        self.put_outputs()
        with self.assertRaisesRegex(ValueError, 'evidence ID'):
            q.blind(self.run, self.run / 'b')

    def test_missing_duplicate_invalid_ratings_rejected(self):
        self.put_outputs()
        b = self.run / 'b'
        q.blind(self.run, b)
        rows = self.ratings(b)
        variants = [rows[:1], rows + [rows[0]], [None], ['not a rating']]
        bad = json.loads(json.dumps(rows))
        bad[0]['scores']['clarity'] = 5
        variants.append(bad)
        bad = json.loads(json.dumps(rows))
        bad[0]['rationale'][0]['quote'] = 'not in output'
        variants.append(bad)
        bad = json.loads(json.dumps(rows))
        bad[0]['scores']['tradeoffs'] = None
        variants.append(bad)
        for i, variant in enumerate(variants):
            path = self.run / ('rating%s.json' % i)
            q.write(path, variant)
            with self.subTest(i=i), self.assertRaises(ValueError):
                q.summarize(self.run, b, path)

    def test_pairwise_uses_only_common_applicable_dimensions(self):
        self.put_outputs()
        b = self.run / 'b'
        q.blind(self.run, b)
        rows = self.ratings(b)
        rows[0]['scores'] = {d: None for d in q.DIMENSIONS}
        rows[0]['not_applicable'] = {d: '不适用' for d in q.DIMENSIONS}
        q.write(self.run / 'ratings.json', rows)
        result = q.summarize(self.run, b, self.run / 'ratings.json')
        self.assertEqual(result['matched_dimensions']['clarity']['n_cases'], 0)
        self.assertIsNone(result['matched_dimensions']['clarity']['comparators']['alpha'])
        self.assertEqual(result['paired_results'][0]['no_common_dimensions'], 1)
        self.assertEqual(result['paired_results'][0]['ties'], 0)

    def test_minimal_pair_ratings_validate_identity_quotes_and_coverage(self):
        cases = [dict(self.case, pair_id='p'), dict(self.case, id='c2', pair_id='p')]
        q.write(self.root / 'pairs.json', cases)
        run = self.root / 'pair-run'
        q.prepare(self.root / 'pairs.json', self.root / 'comparators', run)
        for name in ('alpha', 'beta'):
            for case in cases:
                q.write(run / 'outputs' / name / (case['id'] + '.json'), self.obj)
        b = run / 'blind'
        q.blind(run, b)
        mapping = q.read(b / 'private/mapping.json')['mapping']
        ids = [sid for sid, identity in mapping.items() if identity['comparator'] == 'alpha']
        row = {'pair_id': 'p', 'submission_ids': ids, 'assessment': 'uncertain',
               'reason': '示例只检查评分结构',
               'quotes': [{'submission_id': sid, 'quote': '不能确定原因'} for sid in ids]}
        q.write(run / 'pairs-rated.json', [row])
        result = q.summarize_pairs(run, b, run / 'pairs-rated.json')
        self.assertEqual(result['comparators']['alpha']['uncertain'], 1)
        self.assertEqual(result['comparators']['beta']['missing'], 1)
        bad_quote = json.loads(json.dumps(row))
        bad_quote['quotes'][0]['quote'] = '捏造的输出'
        crossed = json.loads(json.dumps(row))
        crossed['submission_ids'][1] = next(sid for sid, identity in mapping.items() if identity['comparator'] == 'beta')
        for i, rows in enumerate(([bad_quote], [crossed], [row, row])):
            path = run / ('bad-pair-%d.json' % i)
            q.write(path, rows)
            with self.subTest(i=i), self.assertRaises(ValueError):
                q.summarize_pairs(run, b, path)

    def test_frozen_output_change_is_rejected(self):
        self.put_outputs()
        b = self.run / 'b'
        q.blind(self.run, b)
        q.write(self.run / 'ratings.json', self.ratings(b))
        submissions = q.read(b / 'submissions.json')
        submissions[0]['output']['headline'] = 'changed'
        (b / 'submissions.json').write_text(json.dumps(submissions))
        with self.assertRaisesRegex(ValueError, 'changed'):
            q.summarize(self.run, b, self.run / 'ratings.json')


if __name__ == '__main__':
    unittest.main()

class RepeatedQualityTests(unittest.TestCase):
    setUp = QualityBenchmarkTests.setUp
    ratings = QualityBenchmarkTests.ratings
    def make_v2(self, mode='required'):
        case = dict(self.case, direction_policy={'mode': mode, 'reason': '预先冻结的适用性'}, pair_id='pair')
        cases = [case, dict(case, id='c2')]
        q.write(self.root / 'v2-cases.json', cases)
        run = self.root / 'v2-run'
        m = q.prepare(self.root / 'v2-cases.json', self.root / 'comparators', run, repeats=3, opaque=True)
        for task in m['tasks']:
            q.write(run / 'outputs' / q.task_path(m, task, '.json'), self.obj)
        b = run / 'blind'
        q.blind(run, b)
        rows = self.ratings(b)
        for row in rows:
            row['direction_assessment'] = 'omitted' if mode == 'required' else 'appropriate_empty'
            for d in ('direction_value', 'testability'):
                row['scores'][d] = 0 if mode == 'required' else None
                if mode != 'required':
                    row['not_applicable'][d] = '材料无需新增方向'
        return run, b, rows, m

    def test_repeated_opaque_generation_and_same_repeat_pairing(self):
        run, b, rows, m = self.make_v2()
        self.assertEqual(len(m['tasks']), 12)
        for task in m['tasks']:
            path = run / 'generation' / q.task_path(m, task, '.md')
            self.assertRegex(path.stem, r'^T\d{4}$')
            prompt = path.read_text()
            for secret in ('SECRET ANSWER', 'direction_policy', 'must_find', 'holdout', 'pair_id'):
                self.assertNotIn(secret, prompt)
        q.write(run / 'ratings.json', rows)
        result = q.summarize(run, b, run / 'ratings.json')
        self.assertEqual(result['comparators']['alpha']['outputs'], 6)
        self.assertEqual(result['comparators']['alpha']['direction_assessments']['omitted'], 6)
        self.assertEqual(result['matched_dimensions']['clarity']['n_outputs'], 6)
        self.assertEqual(result['matched_dimensions']['clarity']['n_cases'], 2)
        self.assertEqual(result['paired_results'][0]['ties'], 6)
        self.assertEqual(result['by_repeat']['1']['paired_results'][0]['ties'], 2)

    def test_policy_cannot_skip_required_omission(self):
        run, b, rows, _ = self.make_v2()
        rows[0]['scores']['testability'] = None
        rows[0]['not_applicable']['testability'] = '输出没有建议'
        q.write(run / 'bad.json', rows)
        with self.assertRaisesRegex(ValueError, 'Required direction omitted'):
            q.summarize(run, b, run / 'bad.json')

    def test_appropriate_empty_direction_is_not_penalized(self):
        run, b, rows, _ = self.make_v2('unnecessary')
        q.write(run / 'ratings.json', rows)
        result = q.summarize(run, b, run / 'ratings.json')
        self.assertIsNone(result['comparators']['alpha']['dimensions']['testability']['mean'])
        self.assertEqual(result['comparators']['alpha']['direction_assessments']['appropriate_empty'], 6)

    def test_all_v2_frozen_fields_detect_changes(self):
        run, b, rows, manifest = self.make_v2()
        mutations = [lambda m: m.update(output_contract='different'),
                     lambda m: m['rubric'].update(anchors={}),
                     lambda m: m['tasks'][0].update(repeat=99),
                     lambda m: m['cases'][0]['direction_policy'].update(mode='unnecessary')]
        for change in mutations:
            altered = json.loads(json.dumps(manifest))
            change(altered)
            (run / 'manifest.json').write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError, 'changed'):
                q.load_manifest(run)
        (run / 'manifest.json').write_text(json.dumps(manifest))

    def test_minimal_pairs_require_same_repeat_and_keep_repeated_coverage(self):
        run, b, rows, m = self.make_v2()
        mapping = q.read(b / 'private/mapping.json')['mapping']
        rows = []
        for rep in range(1, 4):
            ids = [sid for sid, v in mapping.items() if v['comparator'] == 'alpha' and v['repeat'] == rep]
            rows.append({'pair_id': 'pair', 'submission_ids': ids, 'assessment': 'uncertain', 'reason': '仅检查结构',
                         'quotes': [{'submission_id': sid, 'quote': '不能确定原因'} for sid in ids]})
        q.write(run / 'pairs.json', rows)
        result = q.summarize_pairs(run, b, run / 'pairs.json')
        self.assertEqual(result['comparators']['alpha']['rated'], 3)
        self.assertEqual(result['comparators']['alpha']['expected'], 3)
        self.assertEqual(result['comparators']['beta']['missing'], 3)
        rows[0]['submission_ids'][1] = rows[1]['submission_ids'][1]
        q.write(run / 'cross-repeat.json', rows)
        with self.assertRaisesRegex(ValueError, 'Pair crosses repeats'):
            q.summarize_pairs(run, b, run / 'cross-repeat.json')

    def test_nonempty_directions_cannot_escape_scoring_with_null(self):
        self.obj['directions'] = [{'text': '核对原因', 'context': '故障调查', 'verification_signal': '隔离复测反例'}]
        run, b, rows, _ = self.make_v2('insufficient')
        for row in rows:
            row['direction_assessment'] = 'supported'
            for d in ('direction_value', 'testability'):
                row['scores'][d] = 3
        rows[0]['scores']['testability'] = None
        rows[0]['not_applicable']['testability'] = '尝试跳过'
        q.write(run / 'bad-null.json', rows)
        with self.assertRaisesRegex(ValueError, 'Nonempty directions'):
            q.summarize(run, b, run / 'bad-null.json')

    def test_modified_generation_prompt_is_detected(self):
        run, b, rows, m = self.make_v2()
        path = run / 'generation' / q.task_path(m, m['tasks'][0], '.md')
        path.write_text(path.read_text() + ' modified')
        with self.assertRaisesRegex(ValueError, 'Generation prompt changed'):
            q.load_manifest(run)
