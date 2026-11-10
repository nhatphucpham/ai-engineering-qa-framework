"""Offline report regressions: source trace, v2 rules, bindings and safe CLI."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evaluate_rules import AssessmentError, ROOT
from project_report import create_report, digest, validate_report
from test_rules import read, scenario_inputs
from test_rules_v2 import inputs, upgrade


class ReportTests(unittest.TestCase):
    def test_entire_decision_corpus(self):
        for case in read('scenarios.json'):
            with self.subTest(case=case['id']):
                docs = upgrade(scenario_inputs(case))
                original = copy.deepcopy(docs)
                if 'expectedError' in case:
                    with self.assertRaises(AssessmentError):
                        create_report(**docs)
                else:
                    report = create_report(**docs)
                    self.assertEqual(report['assessment']['verification'], case['expected']['verification'])
                    self.assertEqual(validate_report(report, **docs), [])
                    self.assertEqual(report['assessment']['humanDecision'], 'pending')
                    self.assertEqual(report['legacyProjection']['status'], 'projection_unsupported')
                self.assertEqual(docs, original)

    def test_collision_missing_stale_and_current_constraint_review(self):
        for name, expected in [('satisfied-claim-without-review', 'incomplete'),
                               ('old-review-not-current-gate', 'incomplete'),
                               ('mandatory-review-satisfied-and-bound', 'complete')]:
            with self.subTest(case=name):
                docs = upgrade(inputs(name))
                report = create_report(**docs)
                self.assertEqual(report['assessment']['verification'], expected)
                self.assertEqual(report['constraintSources'][0]['declaration'], docs['bundle']['handoffs'][0]['constraints'][0])
                if name == 'satisfied-claim-without-review':
                    self.assertIsNone(report['constraintSources'][0]['review'])
                    self.assertEqual(report['assessment']['constraints'][0]['status'], 'pending')
                    self.assertIn('P1_V2_CONSTRAINT_COLLISION', report['legacyProjection']['reasonCodes'])
                elif name == 'old-review-not-current-gate':
                    self.assertEqual(report['constraintSources'][0]['review'], docs['assessment']['constraintReviews'][0])
        docs = upgrade(inputs('mandatory-review-satisfied-and-bound'))
        docs['bundle']['handoffs'][0]['constraints'][0]['state'] = 'pending'
        report = create_report(**docs)
        self.assertEqual(report['assessment']['verification'], 'incomplete')
        self.assertIn('new handoff snapshot', report['actions'][0]['doneWhen'])
        self.assertEqual(report['actions'][0]['state'], 'proposed')
        self.assertIsNone(report['actions'][0]['assigneeRef'])

    def test_traceability_stage_records_risk_and_bindings(self):
        docs = upgrade(inputs('comparable-evidence-conflict'))
        report = create_report(**docs)
        self.assertEqual(report['assessmentContext']['bindings'], docs['assessment']['bindings'])
        self.assertEqual(report['assessmentContext']['risk'], docs['assessment']['risk'])
        self.assertEqual(report['handoffContext']['stageRecords'], docs['bundle']['handoffs'][0]['stageRecords'])
        self.assertEqual(report['criterionSources'][0]['criterion']['claims'], docs['bundle']['handoffs'][0]['criteria'][0]['claims'])
        docs['bundle']['handoffs'][0]['stageRecords'][1].update(state='unknown', evidenceIds=[])
        changed = create_report(**docs)
        self.assertEqual(changed['handoffContext']['stageRecords'][1]['state'], 'unknown')
        self.assertNotEqual(changed['inputBindings'], report['inputBindings'])
        self.assertTrue(validate_report(report, **docs))

    def test_reproducibility_detachment_and_tamper(self):
        docs = upgrade(inputs('scoped-integration-coverage'))
        report = create_report(**docs)
        self.assertEqual(report, create_report(**docs))
        original = copy.deepcopy(docs)
        mutations = [lambda r: r['scope'].update(projectConfigVersion=1.0),
                     lambda r: r['assessment'].update(verification='failed'),
                     lambda r: r['assessment']['criteria'][0]['reasonCodes'].append('FAKE'),
                     lambda r: r['assessmentContext']['bindings'][0].update(comparisonKey='employee-api'),
                     lambda r: r['inputBindings'].update(bundleSha256='0' * 64),
                     lambda r: r.update(reportVersion='99.0.0'),
                     lambda r: r['assessment']['criteria'][0].update(extra='unexpected'),
                     lambda r: r['scope'].update(projectConfigVersion=float('inf'))]
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)):
                changed = copy.deepcopy(report)
                mutate(changed)
                self.assertTrue(validate_report(changed, **docs))
        report['criterionSources'][0]['criterion']['expected'] = 'consumer changed output'
        report['assessmentContext']['bindings'][0]['rationale'] = 'consumer changed mapping'
        self.assertEqual(docs, original)
        self.assertEqual(digest({'b': 2, 'a': 1}), digest({'a': 1, 'b': 2}))

    def test_corrected_rules_and_record_scope(self):
        docs = upgrade(inputs('source-proof-with-accepted-scope'))
        docs['assessment']['criteria'][0]['requiredLevels'] = ['integration']
        for ev in docs['bundle']['evidence']:
            ev['level'] = 'integration'
        report = create_report(**docs)
        self.assertEqual(report['assessment']['verification'], 'incomplete')
        self.assertTrue(report['actions'])
        record = create_report(**upgrade(inputs('explicit-record-scope-only')))
        self.assertEqual(record['assessment']['statusScope'], 'record_only')
        with self.assertRaises(AssessmentError):
            create_report(**inputs('scoped-integration-coverage'))

    def test_actions_follow_the_actual_gap_without_inventing_conflict(self):
        source = create_report(**upgrade(inputs('source-proof-does-not-require-test-fail')))
        self.assertTrue(source['assessment']['hasOpenMandatoryCoverage'])
        self.assertNotIn('EVIDENCE_CONFLICT', source['assessment']['criteria'][0]['reasonCodes'])
        self.assertTrue(any('required evidence levels' in a['description'] for a in source['actions']))
        self.assertFalse(any('conflict' in a['description'].lower() or 'contradictory' in a['doneWhen'].lower()
                             for a in source['actions']))
        mixed = upgrade(inputs('comparable-evidence-conflict'))
        mixed['bundle']['evidence'][0].update(outcome='fail', reason='manager fails')
        mixed['assessment']['bindings'][0]['relation'] = 'violates'
        report = create_report(**mixed)
        self.assertTrue(any('contradictory evidence' in a['doneWhen'] for a in report['actions']))
        blocked = create_report(**upgrade(inputs('blocked-not-defect')))
        self.assertEqual(blocked['actions'][0]['ownerRole'], 'check-owner')
        self.assertIn('rerun the approved check', blocked['actions'][0]['doneWhen'])
        ambiguous = upgrade(inputs('scoped-integration-coverage'))
        ambiguous['bundle']['handoffs'][0]['criteria'][0]['clarification'] = 'ambiguous'
        report = create_report(**ambiguous)
        self.assertEqual(report['actions'][0]['ownerRole'], ambiguous['bundle']['handoffs'][0]['criteria'][0]['ownerRole'])
        self.assertIn('authorized clarification', report['actions'][0]['doneWhen'])
        pending_plan = upgrade(inputs('accepted-current-counterexample'))
        pending_plan['assessment']['risk']['state'] = 'candidate'
        report = create_report(**pending_plan)
        self.assertTrue(any(a['ownerRole'] == 'coverage-policy-owner' for a in report['actions']))
        mismatch = create_report(**upgrade(inputs('fail-with-wrong-binding')))
        self.assertEqual(mismatch['actions'][0]['ownerRole'], 'qa')
        self.assertFalse(any(a['ownerRole'] == 'check-owner' for a in mismatch['actions']))
        risk_only = create_report(**upgrade(inputs('fail-does-not-wait-full-risk-plan')))
        self.assertTrue(any(a['ownerRole'] == 'coverage-policy-owner' for a in risk_only['actions']))
        na = upgrade(inputs('scoped-na-with-owner'))
        na['assessment']['criteria'][0]['naDecision']['actorRef'] = None
        report = create_report(**na)
        self.assertIn('NA_PENDING', report['assessment']['criteria'][0]['reasonCodes'])
        self.assertIn('same candidate', report['actions'][0]['doneWhen'])

    def test_golden_files(self):
        for name in ('complete', 'constraint-collision'):
            folder = ROOT / 'examples/reports/v1' / name
            docs = {kind: json.loads((folder / (kind + '.json')).read_text(encoding='utf-8')) for kind in ('bundle', 'assessment')}
            report = json.loads((folder / 'report.json').read_text(encoding='utf-8'))
            self.assertEqual(validate_report(report, **docs), [])
            expected = 'complete' if name == 'complete' else 'incomplete'
            self.assertEqual(report['assessment']['verification'], expected)

    def test_independent_blockers_get_distinct_actions_without_duplicates(self):
        blocked = upgrade(inputs('blocked-not-defect'))
        blocked['assessment']['risk']['state'] = 'candidate'
        report = create_report(**blocked)
        roles = [a['ownerRole'] for a in report['actions']]
        self.assertEqual(roles.count('check-owner'), 1)
        self.assertEqual(roles.count('coverage-policy-owner'), 1)
        mixed = upgrade(inputs('comparable-evidence-conflict'))
        mixed['bundle']['evidence'][0].update(outcome='fail', reason='manager fails')
        mixed['assessment']['bindings'][0]['relation'] = 'violates'
        mixed['assessment']['risk']['state'] = 'candidate'
        report = create_report(**mixed)
        roles = [a['ownerRole'] for a in report['actions']]
        self.assertEqual(roles.count('coverage-policy-owner'), 1)
        self.assertEqual(sum('contradictory evidence' in a['doneWhen'] for a in report['actions']), 1)
        # An environmental gap in another context must remain visible alongside a conflict.
        mixed['bundle']['evidence'][0].update(outcome='blocked', reason='check environment unavailable')
        report = create_report(**mixed)
        roles = [a['ownerRole'] for a in report['actions']]
        self.assertEqual(roles.count('check-owner'), 1)
        self.assertEqual(roles.count('coverage-policy-owner'), 1)
        self.assertEqual(sum('contradictory evidence' in a['doneWhen'] for a in report['actions']), 1)
        plan_only = upgrade(inputs('scoped-integration-coverage'))
        plan_only['assessment']['risk']['state'] = 'candidate'
        report = create_report(**plan_only)
        self.assertEqual([a['ownerRole'] for a in report['actions']], ['coverage-policy-owner'])

    def test_cli_status_validation_and_safe_errors(self):
        script = str(ROOT / 'tools/project_report.py')
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            bundle, assessment, report_path = [folder / (n + '.json') for n in ('bundle', 'assessment', 'report')]
            for name, code in [('scoped-integration-coverage', 0), ('blocked-not-defect', 1),
                               ('accepted-current-counterexample', 1), ('assessment-for-other-candidate', 2)]:
                with self.subTest(case=name):
                    docs = upgrade(inputs(name))
                    bundle.write_text(json.dumps(docs['bundle']), encoding='utf-8')
                    assessment.write_text(json.dumps(docs['assessment']), encoding='utf-8')
                    run = subprocess.run([sys.executable, '-B', script, str(bundle), str(assessment)], capture_output=True, text=True, timeout=15)
                    self.assertEqual(run.returncode, code, run.stderr)
                    self.assertEqual(json.loads(run.stdout)['processingStatus'], 'input_error' if code == 2 else 'reference_report')
                    self.assertFalse(run.stderr)
            docs = upgrade(inputs('scoped-integration-coverage'))
            bundle.write_text(json.dumps(docs['bundle']), encoding='utf-8')
            assessment.write_text(json.dumps(docs['assessment']), encoding='utf-8')
            report = create_report(**docs)
            report_path.write_text(json.dumps(report), encoding='utf-8')
            command = [sys.executable, '-B', script, str(bundle), str(assessment), '--check', str(report_path)]
            valid = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertTrue(json.loads(valid.stdout)['valid'])
            duplicate_in_valid_report = '{"reportVersion":"WRONG",' + json.dumps(report)[1:]
            for raw in ['{"secret_SENTINEL": NaN}', duplicate_in_valid_report,
                        '{"verification":"complete","verification":"failed"}',
                        '[' * 1200 + '0' + ']' * 1200, '{', 'null']:
                with self.subTest(raw=raw[:20]):
                    report_path.write_text(raw, encoding='utf-8')
                    bad = subprocess.run(command, capture_output=True, text=True, timeout=15)
                    self.assertEqual(bad.returncode, 2, bad.stderr)
                    self.assertEqual(json.loads(bad.stdout)['processingStatus'], 'input_error')
                    self.assertNotIn('secret_SENTINEL', bad.stdout)
                    self.assertFalse(bad.stderr)


if __name__ == '__main__':
    unittest.main()
