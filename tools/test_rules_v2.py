"""V2 corrections and explicit legacy replay; supplied judgments remain synthetic."""

import copy
import unittest

from evaluate_rules import AssessmentError, evaluate
from test_rules import read, scenario_inputs


def inputs(name):
    return scenario_inputs(next(c for c in read('scenarios.json') if c['id'] == name))


def upgrade(docs):
    upgraded = copy.deepcopy(docs)
    upgraded['assessment'].update(assessmentVersion='2.0.0', rulesVersion='p2-rules-2.0.0')
    return upgraded


class RulesV2Tests(unittest.TestCase):
    def test_existing_decision_corpus_under_v2(self):
        for case in read('scenarios.json'):
            with self.subTest(case=case['id']):
                docs = upgrade(scenario_inputs(case))
                if 'expectedError' in case:
                    with self.assertRaises(AssessmentError) as caught:
                        evaluate(**docs)
                    self.assertIn(case['expectedError'], {e['code'] for e in caught.exception.errors})
                    continue
                result = evaluate(**docs)
                expected = case['expected']
                self.assertEqual(result['rulesVersion'], 'p2-rules-2.0.0')
                self.assertEqual(result['verification'], expected['verification'])
                self.assertEqual({c['criterionId']: c['status'] for c in result['criteria']}, expected['statuses'])
                codes = {code for c in result['criteria'] for code in c['reasonCodes']}
                self.assertTrue(set(expected['codes']) <= codes, result)
                for field in ('hasOpenMandatoryCoverage', 'hasUnverifiedMandatory', 'pendingConstraintIds', 'statusScope'):
                    if field in expected:
                        self.assertEqual(result[field], expected[field])

    def test_positive_source_cannot_count_as_integration(self):
        docs = inputs('source-proof-with-accepted-scope')
        self.assertEqual(evaluate(**upgrade(docs))['verification'], 'complete')
        docs['assessment']['criteria'][0]['requiredLevels'] = ['integration']
        for evidence in docs['bundle']['evidence']:
            evidence['level'] = 'integration'
        self.assertEqual(evaluate(**docs)['verification'], 'complete')  # frozen v1 replay
        upgraded = upgrade(docs)
        original = copy.deepcopy(upgraded)
        result = evaluate(**upgraded)
        self.assertEqual(result['verification'], 'incomplete')
        self.assertTrue(result['hasOpenMandatoryCoverage'])
        self.assertIn('REQUIRED_COVERAGE_MISSING', result['criteria'][0]['reasonCodes'])
        self.assertEqual(result, evaluate(**upgraded))
        self.assertEqual(upgraded, original)

    def test_negative_source_keeps_failure_and_missing_execution(self):
        docs = inputs('source-proof-does-not-require-test-fail')
        docs['bundle']['evidence'][1]['level'] = 'integration'
        result = evaluate(**upgrade(docs))
        self.assertEqual(result['verification'], 'failed')
        self.assertTrue(result['hasOpenMandatoryCoverage'])
        self.assertIn('CURRENT_BEHAVIOR_VIOLATION', result['criteria'][0]['reasonCodes'])

    def test_conflict_with_independent_violation(self):
        docs = inputs('comparable-evidence-conflict')
        docs['bundle']['evidence'][0].update(outcome='fail', reason='manager fails')
        docs['assessment']['bindings'][0]['relation'] = 'violates'
        self.assertNotIn('EVIDENCE_CONFLICT', evaluate(**docs)['criteria'][0]['reasonCodes'])
        result = evaluate(**upgrade(docs))
        self.assertEqual(result['verification'], 'failed')
        self.assertTrue(result['hasOpenMandatoryCoverage'])
        self.assertTrue({'EVIDENCE_CONFLICT', 'CURRENT_BEHAVIOR_VIOLATION'} <= set(result['criteria'][0]['reasonCodes']))

    def test_malformed_and_mismatched_versions(self):
        docs = inputs('scoped-integration-coverage')
        bad = [None, [], {}, dict(docs['assessment'], assessmentVersion=[])]
        for version, rules in [('1.0.0', 'p2-rules-2.0.0'), ('2.0.0', 'p2-rules-1.0.0'),
                               ('99.0.0', 'p2-rules-99.0.0')]:
            bad.append(dict(docs['assessment'], assessmentVersion=version, rulesVersion=rules))
        original = copy.deepcopy(bad)
        for index, assessment in enumerate(bad):
            with self.subTest(case=index), self.assertRaises(AssessmentError):
                evaluate(docs['bundle'], assessment)
        self.assertEqual(bad, original)


if __name__ == '__main__':
    unittest.main()
