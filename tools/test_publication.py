"""Closed staged publication graph/replay tests; not persistence or policy enforcement."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qa_core.application import stage_report_package, check_report_package
from qa_core.contracts import ROOT, validate
from qa_core.reports import digest
from qa_core.rules import AssessmentError
from test_rules import read, scenario_inputs
from test_rules_v2 import inputs, upgrade
from test_runtime_reports import with_run


FOLDER = ROOT / 'examples/reports/publication-v1'


def stage(docs, run_id='run', report_id='runtime-report'):
    return stage_report_package(**docs, run_id=run_id, report_id=report_id)


def anchors(docs, run_id='run', report_id='runtime-report'):
    return {'expected_bundle_sha256': digest(docs['bundle']),
            'expected_assessment_sha256': digest(docs['assessment']),
            'run_id': run_id, 'report_id': report_id}


def golden_inputs(name):
    folder = ROOT / 'examples/reports/runtime-v1' / name
    return {key: json.loads((folder / (key + '.json')).read_text(encoding='utf-8'))
            for key in ('bundle', 'assessment')}


class PublicationTests(unittest.TestCase):
    def test_decision_corpus_remains_derived_and_inputs_unchanged(self):
        for case in read('scenarios.json'):
            with self.subTest(case=case['id']):
                docs = with_run(upgrade(scenario_inputs(case)))
                original = digest(docs)
                if 'expectedError' in case:
                    with self.assertRaises(AssessmentError):
                        stage(docs)
                else:
                    package = stage(docs)
                    report = package['payloads']['prepared']['report']
                    self.assertEqual(report['content']['assessment']['verification'], case['expected']['verification'])
                    self.assertEqual(check_report_package(package, **anchors(docs)), [])
                    self.assertEqual(package['payloads']['bundle'], docs['bundle'])
                    self.assertEqual(package['payloads']['assessment'], docs['assessment'])
                    self.assertEqual(package['graph']['completedRunCandidate']['state'], 'completed')
                self.assertEqual(digest(docs), original)

    def test_graph_semantics_and_constraints_survive_round_trip(self):
        for name, expected in [('complete', 'complete'), ('constraint-collision', 'incomplete'), ('failed-pending', 'failed')]:
            with self.subTest(name=name):
                docs = golden_inputs(name)
                package = json.loads(json.dumps(stage(docs)))
                self.assertEqual(package['publicationState'], 'staged')
                graph = package['graph']
                self.assertEqual(graph['completedRunCandidate']['stateVersion'], 5)
                self.assertIsNone(graph['completedRunCandidate']['lease'])
                self.assertEqual(graph['completedRunCandidate']['reportId'], 'runtime-report')
                self.assertEqual(graph['reportReadyCandidate']['referenceIds'], ['runtime-report'])
                self.assertEqual(graph['reportReadyCandidate']['runStateVersion'], 5)
                self.assertEqual(graph['reportReadyCandidate']['sequence'], 2)
                self.assertEqual(graph['reportReference']['runId'], 'run')
                self.assertEqual(docs['bundle']['runs'][0]['state'], 'checking')
                content = package['payloads']['prepared']['report']['content']
                self.assertEqual(content['assessment']['verification'], expected)
                self.assertEqual(content['assessment']['humanDecision'], 'pending')
                self.assertEqual(content['assessmentContext']['bindings'], docs['assessment']['bindings'])
                self.assertEqual([item['declaration'] for item in content['constraintSources']],
                                 docs['bundle']['handoffs'][0]['constraints'])
                self.assertEqual([item['evidence'] for item in content['evidenceSources']], docs['bundle']['evidence'])
                if name != 'complete':
                    self.assertEqual(content['constraintSources'][0]['declaration']['state'], 'satisfied')
                    self.assertEqual(content['assessment']['constraints'][0]['status'], 'pending')
                self.assertEqual(check_report_package(package, **anchors(docs)), [])

    def test_manifest_is_whole_input_metadata_and_exact_canonical_bytes(self):
        docs = golden_inputs('complete')
        docs['bundle']['tasks'][0]['title'] = 'Unicode tiếng Việt 😀'
        package = stage(docs)
        self.assertEqual([entry['slot'] for entry in package['manifest']['entries']], ['bundle', 'assessment', 'prepared'])
        for entry in package['manifest']['entries']:
            value = package['payloads'][entry['slot']]
            raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
            self.assertEqual(entry['canonicalByteLength'], len(raw))
            self.assertEqual(entry['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(package['handling'], {'storageClass': 'restricted_internal_replay', 'inputScope': 'whole_bundle',
                                               'outboundAuthorization': 'not_evaluated', 'artifactBytesIncluded': False})
        second_project = copy.deepcopy(docs['bundle']['projects'][0])
        second_project.update(id='other-project', checks=[])
        docs['bundle']['projects'].append(second_project)
        docs['bundle']['tasks'].append({'id': 'other-task', 'projectId': 'other-project',
                                        'title': 'Other scope retained, not target-only export', 'externalRef': None})
        self.assertEqual(validate(docs['bundle']), [])
        package = stage(docs)
        self.assertEqual(package['target']['projectId'], 'proj')
        self.assertEqual(package['containedScopes']['projectIds'], ['other-project', 'proj'])
        self.assertEqual(package['containedScopes']['tasks'], [{'projectId': 'other-project', 'taskRef': 'other-task'},
                                                              {'projectId': 'proj', 'taskRef': 'task'}])
        self.assertEqual(package['payloads']['bundle'], docs['bundle'])
        self.assertEqual(check_report_package(package, **anchors(docs)), [])

    def test_independent_input_anchors_reject_consistently_rewritten_package(self):
        docs = golden_inputs('constraint-collision')
        before = anchors(docs)
        changed = copy.deepcopy(docs)
        changed['bundle']['tasks'][0]['title'] = 'Different supplied snapshot'
        rewritten = stage(changed)  # All digests, report and graph coherently recomputed.
        self.assertEqual(check_report_package(rewritten, **before)[0]['code'], 'E_PUBLICATION_BINDING')
        self.assertEqual(check_report_package(rewritten, **anchors(changed)), [])  # Consistency, not truth.
        changed = copy.deepcopy(docs)
        changed['assessment']['risk']['rationale'] += ' Other judgment'
        self.assertEqual(check_report_package(stage(changed), **before)[0]['code'], 'E_PUBLICATION_BINDING')
        package = stage(docs)
        for override in ({'run_id': 'other-run'}, {'report_id': 'other-report'},
                         {'expected_bundle_sha256': '0' * 64}, {'expected_assessment_sha256': '0' * 64}):
            self.assertTrue(check_report_package(package, **{**before, **override}))

    def test_tamper_missing_extra_duplicate_and_rehashed_payloads(self):
        docs = golden_inputs('constraint-collision')
        package = stage(docs)
        cases = [
            (['packageVersion'], '2.0.0'), (['publicationState'], 'published'),
            (['handling', 'outboundAuthorization'], 'allowed'),
            (['target', 'runId'], 'other-run'), (['target', 'reportId'], 'runtime-report\n'),
            (['containedScopes', 'projectIds'], ['some-project']),
            (['manifest', 'algorithm'], 'sha256-file-bytes'),
            (['manifest', 'entries', 0, 'sha256'], '0' * 64),
            (['manifest', 'entries', 1, 'canonicalByteLength'], 1),
            (['manifest', 'entries', 1, 'slot'], 'bundle'),
            (['graph', 'completedRunCandidate', 'state'], 'checking'),
            (['graph', 'completedRunCandidate', 'attempt'], 2),
            (['graph', 'completedRunCandidate', 'stateVersion'], 4),
            (['graph', 'completedRunCandidate', 'lease'], docs['bundle']['runs'][0]['lease']),
            (['graph', 'reportReference', 'reportSha256'], '0' * 64),
            (['graph', 'reportReference', 'runId'], 'other-run'),
            (['graph', 'reportReadyCandidate', 'runId'], 'other-run'),
            (['graph', 'reportReadyCandidate', 'sequence'], 1),
            (['graph', 'reportReadyCandidate', 'referenceIds'], []),
            (['graph', 'reportReadyCandidate', 'referenceIds'], ['runtime-report', 'other-report']),
            (['payloads', 'prepared', 'report', 'content', 'assessment', 'verification'], 'complete'),
        ]
        for path, value in cases:
            changed = copy.deepcopy(package)
            target = changed
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            with self.subTest(path=path):
                self.assertTrue(check_report_package(changed, **anchors(docs)))
        for modify in ('missing', 'extra', 'extra-entry', 'rehashed'):
            changed = copy.deepcopy(package)
            if modify == 'missing':
                del changed['payloads']['assessment']
            elif modify == 'extra':
                changed['payloads']['raw-log'] = {'data': 'PRIVATE'}
            elif modify == 'extra-entry':
                changed['manifest']['entries'].append(copy.deepcopy(changed['manifest']['entries'][0]))
            else:
                prepared = changed['payloads']['prepared']
                prepared['report']['content']['assessment']['verification'] = 'complete'
                raw = json.dumps(prepared, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                changed['manifest']['entries'][2].update(sha256=hashlib.sha256(raw).hexdigest(), canonicalByteLength=len(raw))
                changed['graph']['reportReference']['reportSha256'] = digest(prepared['report'])
            with self.subTest(modify=modify):
                self.assertTrue(check_report_package(changed, **anchors(docs)))

    def test_detachment_repeatability_exact_run_and_numeric_successor(self):
        docs = golden_inputs('complete')
        docs['bundle']['runs'][0]['stateVersion'] = 9007199254740992.0
        docs['bundle']['progress'][0]['sequence'] = 9007199254740992.0
        other = copy.deepcopy(docs['bundle']['runs'][0])
        other.update(id='other-run', attempt=2)
        docs['bundle']['runs'].append(other)
        before = digest(docs)
        first, second = stage(docs), stage(docs, 'other-run', 'other-report')
        self.assertEqual(first['graph']['completedRunCandidate']['stateVersion'], 9007199254740993)
        self.assertEqual(first['graph']['reportReadyCandidate']['sequence'], 9007199254740993)
        self.assertEqual(second['graph']['reportReadyCandidate']['sequence'], 1)
        self.assertEqual(second['graph']['completedRunCandidate']['attempt'], 2)
        self.assertTrue(check_report_package(second, **anchors(docs)))
        self.assertEqual(check_report_package(second, **anchors(docs, 'other-run', 'other-report')), [])
        self.assertEqual(digest(first), digest(stage(docs)))
        first['payloads']['bundle']['tasks'][0]['title'] = 'mutated'
        first['graph']['completedRunCandidate']['initiator']['principalRef'] = 'mutated'
        self.assertEqual(digest(docs), before)

    def test_goldens_cli_and_safe_strict_json_errors(self):
        for name, code in [('complete', 0), ('constraint-collision', 1), ('failed-pending', 1)]:
            docs = golden_inputs(name)
            golden_path = FOLDER / (name + '.json')
            golden = json.loads(golden_path.read_text(encoding='utf-8'))
            self.assertEqual(digest(stage(docs)), digest(golden))
            folder = ROOT / 'examples/reports/runtime-v1' / name
            args = [sys.executable, '-B', str(ROOT / 'tools/package_runtime_report.py'), str(folder / 'bundle.json'),
                    str(folder / 'assessment.json'), '--run-id', 'run', '--report-id', 'runtime-report']
            output = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(output.returncode, code, output.stderr)
            self.assertEqual(json.loads(output.stdout), golden)
            checked = subprocess.run(args + ['--check', str(golden_path)], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(json.loads(checked.stdout)['processingStatus'], 'package_validated')
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'bad.json'
            for raw in ('{"PRIVATE":1,"PRIVATE":2}', '{"PRIVATE":NaN}', '{', '[' * 2500 + '0' + ']' * 2500):
                bad.write_text(raw, encoding='utf-8')
                for command in ([*args[:3], str(bad), *args[4:]], args + ['--check', str(bad)]):
                    output = subprocess.run(command, capture_output=True, text=True)
                    self.assertEqual(output.returncode, 2)
                    self.assertNotIn('PRIVATE', output.stdout + output.stderr)
                    self.assertEqual(output.stderr, '')
                    self.assertEqual(json.loads(output.stdout)['processingStatus'], 'input_error')


if __name__ == '__main__':
    unittest.main()
