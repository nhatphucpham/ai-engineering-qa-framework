"""Runtime report slice: semantic expectations, exact-run graph and frozen compatibility."""

import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qa_core.application import prepare_report, check_prepared_report
from qa_core.contracts import ROOT, validate
from qa_core.reports import create_report, digest
from qa_core.rules import AssessmentError
from qa_core.runtime import validate_runtime_report
from test_rules import read, scenario_inputs
from test_rules_v2 import inputs, upgrade


FOLDER = ROOT / 'examples/reports/runtime-v1'


def with_run(docs):
    docs = copy.deepcopy(docs)
    template = json.loads((ROOT / 'examples/contracts/v2/valid-worker-claim.json').read_text(encoding='utf-8'))
    run = template['runs'][0]
    run.update(triggerEventId=None, initiator={'kind': 'user', 'principalRef': 'synthetic-runner'})
    docs['bundle']['runs'] = [run]
    docs['bundle']['progress'] = template['progress']
    return docs


def prepare(docs, run_id='run', report_id='runtime-report'):
    return prepare_report(**docs, run_id=run_id, report_id=report_id)


class RuntimeReportTests(unittest.TestCase):
    def test_existing_publication_and_terminal_runs_are_rejected(self):
        docs = with_run(upgrade(inputs('scoped-integration-coverage')))
        legacy = json.loads((ROOT / 'examples/contracts/v2/valid-handoff.json').read_text(encoding='utf-8'))
        docs['bundle']['reports'] = copy.deepcopy(legacy['reports'])
        for mode in ('report-only', 'report-ready', 'nonnull-ref', 'completed'):
            changed = copy.deepcopy(docs)
            if mode != 'report-only':
                event = copy.deepcopy(changed['bundle']['progress'][0])
                event.update(id='prior-ready', type='report_ready', sequence=2, referenceIds=['report'])
                changed['bundle']['progress'].append(event)
            if mode in ('nonnull-ref', 'completed'):
                changed['bundle']['runs'][0]['reportId'] = 'report'
            if mode == 'completed':
                changed['bundle']['runs'][0].update(state='completed', lease=None)
            self.assertEqual(validate(changed['bundle']), [])
            with self.subTest(mode=mode), self.assertRaises(AssessmentError):
                prepare(changed, report_id='another-report')
        # Prior report/ready for another run must not block this run.
        other = copy.deepcopy(docs['bundle']['runs'][0])
        other['id'] = 'other-run'
        docs['bundle']['runs'].append(other)
        docs['bundle']['reports'][0]['runId'] = 'other-run'
        event = copy.deepcopy(docs['bundle']['progress'][0])
        event.update(id='other-ready', runId='other-run', type='report_ready', referenceIds=['report'])
        docs['bundle']['progress'].append(event)
        self.assertEqual(validate(docs['bundle']), [])
        self.assertEqual(prepare(docs)['completion']['eventProposal']['sequence'], 2)

    def test_integer_successors_are_exact_and_json_representable(self):
        docs = with_run(upgrade(inputs('scoped-integration-coverage')))
        docs['bundle']['runs'][0]['stateVersion'] = 9007199254740992.0
        docs['bundle']['progress'][0]['sequence'] = 9007199254740992.0
        other = copy.deepcopy(docs['bundle']['runs'][0])
        other.update(id='other-run', stateVersion=4)
        docs['bundle']['runs'].append(other)
        event = copy.deepcopy(docs['bundle']['progress'][0])
        event.update(id='other-progress', runId='other-run', sequence=9007199254740994.0)
        docs['bundle']['progress'].append(event)
        self.assertEqual(validate(docs['bundle']), [])
        proposal = prepare(docs)
        self.assertEqual(proposal['completion']['runMutation']['stateVersion'], 9007199254740993)
        self.assertIs(type(proposal['completion']['runMutation']['stateVersion']), int)
        self.assertEqual(proposal['completion']['eventProposal']['sequence'], 9007199254740993)
        self.assertEqual(check_prepared_report(proposal, **docs, run_id='run', report_id='runtime-report'), [])
        self.assertEqual(prepare(docs, 'other-run', 'other-report')['completion']['eventProposal']['sequence'],
                         9007199254740995)
        limit = sys.get_int_max_str_digits()
        if limit:
            for field in ('stateVersion', 'sequence'):
                changed = with_run(upgrade(inputs('scoped-integration-coverage')))
                target = changed['bundle']['runs'][0] if field == 'stateVersion' else changed['bundle']['progress'][0]
                target[field] = 10 ** limit - 1
                json.dumps(changed)  # Raw input is representable; successor is not.
                with self.subTest(field=field), self.assertRaises(AssessmentError) as caught:
                    prepare(changed)
                self.assertEqual(caught.exception.errors[0]['code'], 'E_COMPLETION_JSON')
            with tempfile.TemporaryDirectory() as tmp:
                bp, ap = (Path(tmp) / name for name in ('bundle.json', 'assessment.json'))
                bp.write_text(json.dumps(changed['bundle']), encoding='utf-8')
                ap.write_text(json.dumps(changed['assessment']), encoding='utf-8')
                output = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/prepare_runtime_report.py'),
                                         str(bp), str(ap), '--run-id', 'run', '--report-id', 'runtime-report'],
                                        capture_output=True, text=True)
                self.assertEqual(output.returncode, 2)
                self.assertEqual(output.stderr, '')
                self.assertEqual(json.loads(output.stdout)['processingStatus'], 'input_error')

    def test_new_report_ids_reject_final_newline_without_changing_legacy_ids(self):
        docs = with_run(upgrade(inputs('scoped-integration-coverage')))
        for report_id in ('report\n', 'r' * 96 + '\n', 'r' * 97, 'report\r\n'):
            with self.subTest(report_id=repr(report_id)), self.assertRaises(AssessmentError):
                prepare(docs, report_id=report_id)
        prepared = prepare(docs, report_id='r' * 96)
        self.assertEqual(check_prepared_report(prepared, **docs, run_id='run', report_id='r' * 96), [])
        for path in ('report', 'mutation', 'event'):
            changed = copy.deepcopy(prepared)
            if path == 'report':
                changed['report']['id'] += '\n'
            elif path == 'mutation':
                changed['completion']['runMutation']['reportId'] += '\n'
            else:
                changed['completion']['eventProposal']['referenceIds'][0] += '\n'
            self.assertEqual(check_prepared_report(changed, **docs, run_id='run', report_id='r' * 96)[0]['code'],
                             'E_COMPLETION_SCHEMA')
        # Legacy P1 IDs keep their historical matching semantics in the new binding.
        docs['bundle']['runs'][0]['id'] = 'run\n'
        docs['bundle']['progress'][0]['runId'] = 'run\n'
        self.assertEqual(validate(docs['bundle']), [])
        self.assertEqual(prepare(docs, 'run\n')['report']['runBinding']['id'], 'run\n')

    def test_p1_compatibility_import_and_module_cli(self):
        process = subprocess.run([sys.executable, '-B', '-c', 'from tools.validate_contracts import validate'],
                                 cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        process = subprocess.run([sys.executable, '-B', '-m', 'tools.validate_contracts',
                                  'examples/contracts/v2/valid-handoff.json'],
                                 cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(json.loads(process.stdout)['valid'])

    def test_decision_corpus_and_raw_input_preservation(self):
        for case in read('scenarios.json'):
            with self.subTest(case=case['id']):
                docs = with_run(upgrade(scenario_inputs(case)))
                before = digest(docs)
                if 'expectedError' in case:
                    with self.assertRaises(AssessmentError):
                        prepare(docs)
                else:
                    proposal = prepare(docs)
                    report = proposal['report']
                    self.assertEqual(report['content'], create_report(**docs))
                    self.assertEqual(report['content']['assessment']['verification'], case['expected']['verification'])
                    self.assertEqual(check_prepared_report(proposal, **docs, run_id='run', report_id='runtime-report'), [])
                    self.assertEqual(report['content']['assessment']['humanDecision'], 'pending')
                    self.assertEqual(proposal['completion']['runMutation']['state'], 'completed')
                self.assertEqual(digest(docs), before)

    def test_constraints_and_failed_precedence(self):
        cases = [('satisfied-claim-without-review', 'incomplete', 'satisfied', 'pending'),
                 ('old-review-not-current-gate', 'incomplete', 'satisfied', 'pending'),
                 ('mandatory-review-satisfied-and-bound', 'complete', 'satisfied', 'satisfied'),
                 ('optional-constraint-not-required-gate', 'complete', 'pending', 'pending')]
        for name, expected, declared, effective in cases:
            with self.subTest(case=name):
                docs = with_run(upgrade(inputs(name)))
                content = prepare(docs)['report']['content']
                self.assertEqual(content['assessment']['verification'], expected)
                self.assertEqual(content['constraintSources'][0]['declaration']['state'], declared)
                self.assertEqual(content['assessment']['constraints'][0]['status'], effective)
                self.assertEqual(content['assessment']['criteria'][0]['status'], 'verified')
        docs = with_run(upgrade(inputs('accepted-current-counterexample')))
        collision = inputs('satisfied-claim-without-review')['bundle']['handoffs'][0]['constraints']
        docs['bundle']['handoffs'][0]['constraints'] = copy.deepcopy(collision)
        content = prepare(docs)['report']['content']
        self.assertEqual(content['assessment']['verification'], 'failed')
        self.assertEqual(content['assessment']['pendingConstraintIds'], [collision[0]['id']])
        self.assertTrue(any(a['constraintIds'] for a in content['actions']))
        # A review cannot silently resolve a raw pending declaration.
        docs = with_run(upgrade(inputs('mandatory-review-satisfied-and-bound')))
        docs['bundle']['handoffs'][0]['constraints'][0]['state'] = 'pending'
        self.assertEqual(prepare(docs)['report']['content']['assessment']['verification'], 'incomplete')
        for judgment in ('candidate', 'disputed'):
            docs = with_run(upgrade(inputs('mandatory-review-satisfied-and-bound')))
            docs['assessment']['constraintReviews'][0]['judgment'] = judgment
            with self.subTest(judgment=judgment):
                self.assertEqual(prepare(docs)['report']['content']['assessment']['verification'], 'incomplete')

    def test_exact_run_identity_versions_attempt_and_sequence(self):
        docs = with_run(upgrade(inputs('scoped-integration-coverage')))
        other = copy.deepcopy(docs['bundle']['runs'][0])
        other.update(id='other-run', stateVersion=9, attempt=2)
        docs['bundle']['runs'].append(other)
        event = copy.deepcopy(docs['bundle']['progress'][0])
        event.update(id='other-progress', runId='other-run', runStateVersion=9, sequence=50)
        docs['bundle']['progress'].append(event)
        first, second = prepare(docs), prepare(docs, 'other-run', 'other-report')
        self.assertEqual(first['completion']['eventProposal']['sequence'], 2)
        self.assertEqual(second['completion']['eventProposal']['sequence'], 51)
        self.assertEqual(second['completion']['expectedAttempt'], 2)
        self.assertEqual(second['completion']['runMutation']['stateVersion'], 10)
        self.assertEqual(second['completion']['eventProposal']['referenceIds'], ['other-report'])
        self.assertTrue(validate_runtime_report(second['report'], **docs, run_id='run', report_id='runtime-report'))
        changed = copy.deepcopy(docs)
        changed['bundle']['runs'][0]['attempt'] += 1
        self.assertTrue(check_prepared_report(first, **changed, run_id='run', report_id='runtime-report'))
        # Even a lease-token-only change invalidates the bound input snapshot.
        changed = copy.deepcopy(docs)
        changed['bundle']['runs'][0]['lease']['fencingToken'] += 1
        self.assertTrue(check_prepared_report(first, **changed, run_id='run', report_id='runtime-report'))

    def test_lifecycle_fail_closed_and_revision_scope(self):
        for state in ('queued', 'claimed', 'collecting', 'validating', 'waiting_input',
                      'waiting_permission', 'cancelling', 'failed', 'cancelled'):
            with self.subTest(state=state):
                docs = with_run(upgrade(inputs('scoped-integration-coverage')))
                run = docs['bundle']['runs'][0]
                run['state'] = state
                if state in ('queued', 'waiting_input', 'waiting_permission', 'failed', 'cancelled'):
                    run['lease'] = None
                if state.startswith('waiting'):
                    run['waitingReasons'] = ['synthetic-gap']
                self.assertEqual(validate(docs['bundle']), [])
                with self.assertRaises(AssessmentError):
                    prepare(docs)
        for field, value in [('candidateRevision', 'other-revision'), ('projectId', 'other-project'),
                             ('handoffId', 'other-handoff'), ('projectConfigVersion', 2), ('dataPolicyVersion', 2)]:
            docs = with_run(upgrade(inputs('scoped-integration-coverage')))
            docs['bundle']['runs'][0][field] = value
            with self.subTest(field=field), self.assertRaises(AssessmentError):
                prepare(docs)
        docs = with_run(upgrade(inputs('scoped-integration-coverage')))
        docs['bundle']['runs'][0]['state'] = 'analyzing'
        self.assertEqual(prepare(docs)['completion']['runMutation']['state'], 'completed')
        with self.assertRaises(AssessmentError):
            prepare(docs, 'absent')
        with self.assertRaises(AssessmentError):
            prepare(docs, report_id='invalid/id')

    def test_tamper_detachment_and_finite_json(self):
        docs = with_run(upgrade(inputs('satisfied-claim-without-review')))
        prepared = prepare(docs)
        mutations = [
            (['report', 'runtimeReportVersion'], '2.0.0'),
            (['report', 'id'], 'different-report'),
            (['report', 'publicationState'], 'persisted'),
            (['report', 'content', 'assessment', 'verification'], 'complete'),
            (['report', 'content', 'assessment', 'humanDecision'], 'approved'),
            (['report', 'content', 'constraintSources', 0, 'declaration', 'state'], 'pending'),
            (['report', 'content', 'assessment', 'constraints', 0, 'status'], 'satisfied'),
            (['report', 'content', 'assessmentContext', 'bindings', 0, 'rationale'], 'changed'),
            (['completion', 'runId'], 'other-run'),
            (['completion', 'expectedRunVersion'], 3),
            (['completion', 'expectedAttempt'], 2),
            (['completion', 'runMutation', 'stateVersion'], 4),
            (['completion', 'runMutation', 'reportId'], 'other-report'),
            (['completion', 'runMutation', 'lease'], {}),
            (['completion', 'reportSha256'], '0' * 64),
            (['completion', 'eventProposal', 'sequence'], 1),
            (['completion', 'eventProposal', 'runStateVersion'], 4),
            (['completion', 'eventProposal', 'referenceIds'], []),
            (['completion', 'eventProposal', 'referenceIds'], ['runtime-report', 'other-report']),
            (['completion', 'extra'], True),
        ]
        for path, value in mutations:
            changed = copy.deepcopy(prepared)
            target = changed
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            with self.subTest(path=path):
                self.assertTrue(check_prepared_report(changed, **docs, run_id='run', report_id='runtime-report'))
        before = digest(docs)
        prepared['report']['content']['criterionSources'][0]['criterion']['expected'] = 'mutated'
        self.assertEqual(digest(docs), before)
        self.assertNotEqual(prepared, prepare(docs))
        docs['assessment']['risk']['rationale'] = float('nan')
        with self.assertRaises(AssessmentError):
            prepare(docs)

    def test_goldens_and_cli(self):
        for name, code in [('complete', 0), ('constraint-collision', 1), ('failed-pending', 1)]:
            folder = FOLDER / name
            docs = {key: json.loads((folder / (key + '.json')).read_text(encoding='utf-8'))
                    for key in ('bundle', 'assessment')}
            golden = json.loads((folder / 'prepared.json').read_text(encoding='utf-8'))
            self.assertEqual(digest(prepare(docs)), digest(golden))
            args = [sys.executable, '-B', str(ROOT / 'tools/prepare_runtime_report.py'),
                    str(folder / 'bundle.json'), str(folder / 'assessment.json'),
                    '--run-id', 'run', '--report-id', 'runtime-report']
            output = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(output.returncode, code, output.stderr)
            self.assertEqual(json.loads(output.stdout), golden)
            output = subprocess.run(args + ['--check', str(folder / 'prepared.json')], capture_output=True, text=True)
            self.assertEqual(output.returncode, 0, output.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'
            for text in ('{"secret":"PRIVATE","secret":2}', '{"secret":NaN}', '{'):
                path.write_text(text, encoding='utf-8')
                output = subprocess.run([*args[:3], str(path), *args[4:]], capture_output=True, text=True)
                self.assertEqual(output.returncode, 2)
                self.assertNotIn('PRIVATE', output.stdout + output.stderr)
                self.assertEqual(output.stderr, '')
                self.assertEqual(json.loads(output.stdout)['processingStatus'], 'input_error')

    def test_core_has_no_tool_or_adapter_imports(self):
        for path in (ROOT / 'qa_core').glob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level:
                    continue
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ''] if isinstance(node, ast.ImportFrom) else []
                for name in names:
                    self.assertIn(name.split('.')[0], {'copy', 'json', 'hashlib', 'datetime', 'pathlib', 'jsonschema', 'referencing'})


if __name__ == '__main__':
    unittest.main()
