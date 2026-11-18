"""Pure adapter regression tests. Outcomes below are authored inputs for these tests."""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from qa_core.application import check_prepared_report
from qa_core.rules import AssessmentError
from spikes.vf1 import core_bridge as bridge


FIXTURE = Path(__file__).resolve().parents[2] / 'examples/mock/06-filter-pagination'
UNIT_PAGING = 'Baseline.test_service_pagination_and_out_of_range'
CATEGORY = 'Baseline.test_service_category_and_case'
HISTORICAL_RESET = 'Historical.test_reset_from_third_page'
PROBE_RESET = 'Probe.test_reset_with_recorded_api_call'
PROBE_CACHE = 'Probe.test_cache_across_categories'


def job(run, observations):
    artifacts = []
    path_ids = {}
    for index, (path, kind) in enumerate(bridge.ARTIFACT_KINDS.items(), 1):
        data = (FIXTURE / path).read_bytes()
        aid = path_ids[path] = f'artifact-{index}'
        artifacts.append({'id': aid, 'kind': kind, 'relativePath': path,
                          'sha256': sha256(data).hexdigest(), 'text': data.decode('utf-8')})
    requirement = artifacts[0]
    criteria = [{'id': cid, 'expected': bridge.requirement_row(requirement, cid)[1], 'locator': cid}
                for cid in bridge.LEVELS]
    collected = []
    for index, (test, outcome) in enumerate(observations, 1):
        path, level = bridge.CHECKS[test]
        collected.append({'id': f'{run}.ev-{index}', 'testId': test, 'outcome': outcome, 'level': level,
                          'checkArtifactId': path_ids[path],
                          'reason': None if outcome == 'pass' else 'Authored harness outcome detail'})
    return {'version': bridge.JOB_VERSION, 'classification': 'synthetic-only', 'runId': run,
            'jobId': f'{run}.job', 'candidateRevision': bridge.CANDIDATE,
            'requirementVersion': bridge.REQUIREMENT, 'observedAt': '2026-11-18T03:04:05Z',
            'executionRef': f'{run}.execution', 'executionSha256': 'a' * 64,
            'artifacts': artifacts, 'selectedCriteria': criteria,
            'policy': {'minimumLevelsByCriterion': bridge.LEVELS.copy()}, 'observations': collected}


def response(request, assignments):
    requirement = request['artifacts'][0]
    criteria, reviews, bindings = [], [], []
    for cid, floor in bridge.LEVELS.items():
        source = {'sourceArtifactId': requirement['id'], 'locator': cid}
        criteria.append({
            'criterionId': cid, 'planState': 'accepted', 'scopeDescription': f'Harness test scope for {cid}',
            'requiredLevels': [floor], 'allowedProvenance': ['execution'],
            'obligations': [{'id': 'obligation', 'description': 'Harness obligation',
                             'requiredComparisonKeys': ['comparison'], **source}],
            'comparisonContexts': [{'id': 'comparison', 'description': 'Harness comparison', **source}],
            'applicability': 'applicable', 'naDecision': None,
        })
    seen = set()
    for cid, test, relation in assignments:
        eid = next(item['id'] for item in request['observations'] if item['testId'] == test)
        if eid not in seen:
            seen.add(eid)
            reviews.append({'evidenceId': eid, 'integrity': 'matched', 'attribution': 'accepted',
                            'scope': 'accepted', 'rationale': 'Harness evidence review'})
        bindings.append({'criterionId': cid, 'obligationId': 'obligation', 'evidenceId': eid, 'relation': relation,
                         'judgment': 'accepted', 'rationale': 'Harness adjudication', 'comparisonKey': 'comparison'})
    return {'version': bridge.RESPONSE_VERSION, 'runId': request['runId'], 'jobId': request['jobId'],
            'jobDigest': bridge.job_digest(request),
            'risk': {'tier': 'medium', 'state': 'accepted', 'rationale': 'Harness risk rationale'},
            'criteria': criteria, 'evidenceReviews': reviews, 'bindings': bindings}


def derive(request, proposal, held_digest=None):
    return bridge.derive(request, proposal, expected_job_digest=held_digest or bridge.job_digest(request),
                         report_id=f"{request['runId']}.report")


class CoreBridgeTest(unittest.TestCase):
    def assert_rejected(self, code, request, proposal, held_digest=None):
        with self.assertRaises(bridge.BridgeError) as caught:
            derive(request, proposal, held_digest)
        self.assertEqual(caught.exception.code, code)

    def test_core_derives_paired_report_and_limits_view_to_cited_sources(self):
        observations = [(CATEGORY, 'pass'), (HISTORICAL_RESET, 'fail'), (PROBE_RESET, 'fail'),
                        (PROBE_CACHE, 'fail'), (UNIT_PAGING, 'pass')]
        assignments = [('AC-01', CATEGORY, 'supports'), ('AC-02', HISTORICAL_RESET, 'violates'),
                       ('AC-02', PROBE_RESET, 'violates'), ('AC-03', PROBE_CACHE, 'violates'),
                       ('AC-04', UNIT_PAGING, 'supports')]
        a = job('run-a', observations + [(bridge.API_PAGE_CHECK, 'pass'),
                                        ('Baseline.test_empty_category', 'pass')])
        b = job('run-b', observations)
        full = derive(a, response(a, assignments + [('AC-04', bridge.API_PAGE_CHECK, 'supports')]))
        partial = derive(b, response(b, assignments))
        for request, result in ((a, full), (b, partial)):
            bundle, assessment, prepared, view = (result[key] for key in ('bundle', 'assessment', 'prepared', 'view'))
            self.assertEqual([], check_prepared_report(prepared, bundle, assessment, run_id=request['runId'],
                                                       report_id=view['reportId']))
            self.assertEqual(bundle['runs'][0]['state'], 'analyzing')
            self.assertEqual(bundle['reports'], [])
            self.assertEqual(bundle['progress'], [])
            self.assertEqual(prepared['report']['publicationState'], 'proposed')
            self.assertEqual(view['verification'], 'failed')
            self.assertEqual(view['humanDecision'], 'pending')
            self.assertEqual(view['executionRef'], request['executionRef'])
            self.assertEqual(view['executionSha256'], request['executionSha256'])
            statuses = {item['criterionId']: item['status'] for item in view['criteria']}
            self.assertEqual([statuses[cid] for cid in ('AC-01', 'AC-02', 'AC-03')], ['verified', 'failed', 'failed'])
            cited = {item['id']: item for item in view['evidence']}
            source_refs = {(item['artifactId'], item['locator']): item for item in view['sourceExcerpts']}
            self.assertTrue(all(eid.startswith(request['runId'] + '.') for eid in cited))
            self.assertNotIn('Baseline.test_empty_category', {item['testId'] for item in cited.values()})
            for proof in cited.values():
                snippet = source_refs[(proof['checkArtifactId'], proof['checkLocator'])]
                artifact = next(item for item in request['artifacts'] if item['id'] == proof['checkArtifactId'])
                self.assertEqual(snippet['sha256'], artifact['sha256'])
                self.assertIn('def ' + proof['testId'].split('.')[1], snippet['text'])
                self.assertEqual(proof['executionRef'], request['executionRef'])
            fixes = [a for a in view['actions'] if a['ownerRole'] == 'developer']
            self.assertEqual([a['criterionIds'] for a in fixes], [['AC-02'], ['AC-03']])
            self.assertNotIn('completion', view)
            self.assertNotIn('Authored harness outcome detail', str(view))
        self.assertEqual(full['view']['criteria'][3]['status'], 'verified')
        self.assertEqual(partial['view']['criteria'][3]['status'], 'unverified')
        self.assertIn('REQUIRED_COVERAGE_MISSING', partial['view']['criteria'][3]['reasonCodes'])
        self.assertTrue(partial['view']['hasUnverifiedMandatory'])
        self.assertTrue(partial['view']['hasOpenMandatoryCoverage'])

    def test_positive_api_support_rejects_other_integration_checks(self):
        case = 'Baseline.test_api_repeat_same_request'
        request = job('run-a', [(case, 'pass')])
        proposal = response(request, [('AC-04', case, 'supports')])
        self.assert_rejected('E_VF1_POLICY', request, proposal)

    def test_stale_response_and_caller_held_digest(self):
        a, b = job('run-a', []), job('run-b', [])
        proposal = response(a, [])
        self.assert_rejected('E_VF1_RESPONSE_BINDING', b, proposal)
        for field in ('jobId', 'runId', 'jobDigest'):
            with self.subTest(field=field):
                self.assert_rejected('E_VF1_RESPONSE_BINDING', a, dict(proposal, **{field: 'mismatch'}))
        old = bridge.job_digest(a)
        a['executionSha256'] = 'c' * 64
        self.assert_rejected('E_VF1_JOB_DIGEST', a, response(a, []), old)
        wrong = dict(a, candidateRevision='mock-06-base-v1')
        self.assert_rejected('E_VF1_SCOPE', wrong, response(wrong, []))

    def test_artifact_bytes_and_offered_refs(self):
        request = job('run-a', [(CATEGORY, 'pass')])
        proposal = response(request, [('AC-01', CATEGORY, 'supports')])
        corrupted = deepcopy(request)
        corrupted['artifacts'][1]['text'] += '\n# changed bytes'
        self.assert_rejected('E_VF1_ARTIFACT_HASH', corrupted, response(corrupted, []))
        for part in ('bindings', 'evidenceReviews'):
            with self.subTest(part=part):
                changed = deepcopy(proposal)
                changed[part][0]['evidenceId'] = 'from-sibling-run'
                self.assert_rejected('E_VF1_REFERENCE', request, changed)
        proposal['criteria'][0]['obligations'][0]['sourceArtifactId'] = 'unoffered'
        self.assert_rejected('E_VF1_REFERENCE', request, proposal)

    def test_requires_exact_proposal_shape_and_preserves_policy(self):
        request = job('run-a', [])
        proposal = response(request, [])
        self.assert_rejected('E_VF1_RESPONSE', request, dict(proposal, humanDecision='approved'))
        proposal['criteria'][3]['requiredLevels'] = ['unit']
        self.assert_rejected('E_VF1_POLICY', request, proposal)
        proposal['criteria'][3]['requiredLevels'] = ['integration']
        proposal['criteria'][0]['allowedProvenance'] = ['source_reasoning']
        self.assert_rejected('E_VF1_POLICY', request, proposal)

    def test_fail_error_skipped_and_missing_are_distinct(self):
        for outcome, relation, expected, reason in (
            ('pass', 'supports', 'verified', 'SCOPED_COVERAGE_SATISFIED'),
            ('fail', 'violates', 'failed', 'CURRENT_BEHAVIOR_VIOLATION'),
            ('error', 'inconclusive', 'unverified', 'OUTCOME_ERROR'),
            ('skipped', 'inconclusive', 'unverified', 'OUTCOME_SKIPPED'),
            (None, None, 'unverified', 'REQUIRED_COVERAGE_MISSING'),
        ):
            with self.subTest(outcome=outcome):
                request = job('run-a', [(CATEGORY, outcome)] if outcome else [])
                assignments = [('AC-01', CATEGORY, relation)] if outcome else []
                view = derive(request, response(request, assignments))['view']
                self.assertEqual(view['criteria'][0]['status'], expected)
                self.assertIn(reason, view['criteria'][0]['reasonCodes'])
                if outcome in ('pass', 'fail', 'error', 'skipped'):
                    wrong_relation = 'violates' if outcome == 'pass' else 'supports'
                    rejected = response(request, [('AC-01', CATEGORY, wrong_relation)])
                    self.assert_rejected('E_VF1_OUTCOME', request, rejected)

    def test_duplicate_observations_and_untrusted_check_level_rejected(self):
        request = job('run-a', [(CATEGORY, 'pass'), (UNIT_PAGING, 'pass')])
        proposal = response(request, [])
        duplicate = deepcopy(request)
        duplicate['observations'][1]['id'] = duplicate['observations'][0]['id']
        self.assert_rejected('E_VF1_OBSERVATION', duplicate, proposal)
        request['observations'][0]['level'] = 'integration'
        self.assert_rejected('E_VF1_CHECK', request, proposal)

    def test_core_still_checks_binding_graph_and_view_is_detached(self):
        request = job('run-a', [(CATEGORY, 'pass')])
        proposal = response(request, [('AC-01', CATEGORY, 'supports')])
        result = derive(request, proposal)
        result['view']['criteria'][0]['requiredLevels'].append('integration')
        self.assertEqual(proposal['criteria'][0]['requiredLevels'], ['unit'])
        self.assertEqual(result['assessment']['criteria'][0]['requiredLevels'], ['unit'])
        proposal['bindings'][0]['obligationId'] = 'missing-obligation'
        with self.assertRaises(AssessmentError) as caught:
            derive(request, proposal)
        self.assertIn('E_ASSESSMENT_REFERENCE', [error['code'] for error in caught.exception.errors])


if __name__ == '__main__':
    unittest.main()
