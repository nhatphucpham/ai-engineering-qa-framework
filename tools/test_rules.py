"""P2 decision-table regressions, not runtime/domain truth evaluation."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evaluate_rules import AssessmentError, ROOT, evaluate, validate_transition


FOLDER = ROOT / 'examples/rules/v1'


def read(name):
    return json.loads((FOLDER / name).read_text(encoding='utf-8'))


def scenario_inputs(scenario):
    docs = {'bundle': copy.deepcopy(read('base-bundle.json')),
            'assessment': copy.deepcopy(read('base-assessment.json'))}
    for change in scenario['changes']:
        parts = change['path'].strip('/').split('/')
        target = docs[change['target']]
        for part in parts[:-1]:
            target = target[int(part)] if isinstance(target, list) else target[part]
        key = int(parts[-1]) if isinstance(target, list) else parts[-1]
        if change['op'] == 'remove':
            del target[key]
        else:
            target[key] = change['value']
    return docs


class RuleTests(unittest.TestCase):
    def test_decision_table(self):
        for scenario in read('scenarios.json'):
            with self.subTest(scenario=scenario['id']):
                docs = scenario_inputs(scenario)
                if 'expectedError' in scenario:
                    with self.assertRaises(AssessmentError) as caught:
                        evaluate(**docs)
                    self.assertIn(scenario['expectedError'], {e['code'] for e in caught.exception.errors})
                    continue
                result = evaluate(**docs)
                expected = scenario['expected']
                self.assertEqual(result['verification'], expected['verification'])
                self.assertEqual({c['criterionId']: c['status'] for c in result['criteria']}, expected['statuses'])
                codes = set().union(*(set(c['reasonCodes']) for c in result['criteria']))
                self.assertTrue(set(expected['codes']) <= codes, result)
                for field in ('hasOpenMandatoryCoverage', 'hasUnverifiedMandatory', 'pendingConstraintIds', 'statusScope'):
                    if field in expected:
                        self.assertEqual(result[field], expected[field], result)
                self.assertEqual(result['humanDecision'], 'pending')

    def test_lifecycle_table(self):
        for scenario in read('lifecycle-cases.json'):
            with self.subTest(scenario=scenario['id']):
                errors = validate_transition(scenario['entity'], scenario['from'], scenario['to'], scenario['context'])
                self.assertEqual(set(errors), set(scenario['expectedErrors']))

    def test_reproducible_rule_result(self):
        bundle, assessment = read('base-bundle.json'), read('base-assessment.json')
        original = copy.deepcopy((bundle, assessment))
        first = evaluate(bundle, assessment)
        self.assertEqual(first, evaluate(bundle, assessment))
        self.assertEqual((bundle, assessment), original)

    def test_cli_exit_semantics(self):
        cases = {c['id']: c for c in read('scenarios.json')}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name, exit_code, status in [('scoped-integration-coverage', 0, 'evaluated'),
                                            ('blocked-not-defect', 1, 'evaluated'),
                                            ('accepted-current-counterexample', 1, 'evaluated'),
                                            ('assessment-for-other-candidate', 2, 'input_error')]:
                with self.subTest(case=name):
                    docs = scenario_inputs(cases[name])
                    for kind, document in docs.items():
                        (folder / (kind + '.json')).write_text(json.dumps(document), encoding='utf-8')
                    process = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/evaluate_rules.py'),
                                              str(folder / 'bundle.json'), str(folder / 'assessment.json')],
                                             capture_output=True, text=True, timeout=15)
                    self.assertEqual(process.returncode, exit_code, process.stderr)
                    self.assertEqual(json.loads(process.stdout)['processingStatus'], status)


if __name__ == '__main__':
    unittest.main()
