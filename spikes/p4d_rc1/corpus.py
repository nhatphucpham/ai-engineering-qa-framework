"""New authored outcome/proposal fixtures; source-only MOCK-06 bytes remain unchanged."""
from copy import deepcopy
from pathlib import Path

from spikes.vf1 import core_bridge as bridge
from .common import VERSION, LIMIT, PROFILES, canonical, digest, sha
from .contracts import response_contract, timestamp

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'examples/mock/06-filter-pagination'
NOW = timestamp('2026-11-25T00:00:00Z')
DEADLINE = '2026-11-25T00:02:00Z'
OBSERVATIONS = [('Baseline.test_service_category_and_case', 'pass'),
                ('Historical.test_reset_from_third_page', 'fail'),
                ('Probe.test_reset_with_recorded_api_call', 'fail'),
                ('Probe.test_cache_across_categories', 'fail'),
                ('Baseline.test_service_pagination_and_out_of_range', 'pass')]
SOURCES = {
    'local_host': 'docs/HC1-PROTOCOL.md',
    'openai': 'https://developers.openai.com/api/reference/resources/responses/methods/create',
    'anthropic': 'https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons',
}


def make(port, *, attempt='attemptA', run='rc1Run', risk_rationale=None, config_version=1, policy_version=1):
    artifacts, by_path = [], {}
    sources = {}
    for index, (relative, kind) in enumerate(bridge.ARTIFACT_KINDS.items(), 1):
        raw = (FIXTURE / relative).read_bytes()
        aid = f'artifact-{index}'
        by_path[relative] = aid
        artifacts.append({'id': aid, 'kind': kind, 'relativePath': relative,
                          'sha256': sha(raw), 'text': raw.decode('utf-8')})
        sources[aid] = {'hex': raw.hex(), 'classification': 'safe_source',
                        'revision': bridge.REQUIREMENT if kind == 'requirement' else bridge.CANDIDATE,
                        'lineageIds': []}
    observations = []
    for index, (test, outcome) in enumerate(OBSERVATIONS, 1):
        relative, level = bridge.CHECKS[test]
        observations.append({'id': f'{run}-e{index}', 'testId': test, 'outcome': outcome, 'level': level,
                             'checkArtifactId': by_path[relative],
                             'reason': None if outcome == 'pass' else 'Authored assertion outcome; no check executed'})
    outcome_bytes = canonical({'version': 'rc1-authored-observations-1', 'mode': 'authored_fixture',
                               'observations': observations})
    job = {'version': bridge.JOB_VERSION, 'classification': 'synthetic-only', 'runId': run,
           'jobId': run + '.job', 'candidateRevision': bridge.CANDIDATE, 'requirementVersion': bridge.REQUIREMENT,
           'observedAt': '2026-11-25T00:00:00Z', 'executionRef': run + '.authored-outcomes',
           'executionSha256': sha(outcome_bytes), 'artifacts': artifacts,
           'selectedCriteria': [{'id': cid, 'expected': bridge.requirement_row(artifacts[0], cid)[1], 'locator': cid}
                                for cid in bridge.LEVELS],
           'policy': {'minimumLevelsByCriterion': deepcopy(bridge.LEVELS)}, 'observations': observations}
    sources['outcomeRecord'] = {'hex': outcome_bytes.hex(), 'classification': 'safe_source',
                              'revision': 'rc1-authored-v1', 'lineageIds': sorted(by_path.values())}
    sources['contextRecord'] = {'hex': canonical(job).hex(), 'classification': 'safe_source',
                              'revision': 'rc1-authored-v1', 'lineageIds': sorted(sources)}
    manifest = [{'artifactId': aid, 'revision': s['revision'], 'sha256': sha(bytes.fromhex(s['hex'])),
                 'bytes': len(bytes.fromhex(s['hex'])), 'lineageIds': list(s['lineageIds']), 'classification': 'safe'}
                for aid, s in sorted(sources.items())]
    capability = {'enrolled': True, 'isolatedContext': True, 'noTools': True, 'noOutbound': True,
                  'routeSelector': 'authoredRouteA', 'modelSelector': 'authoredModelA',
                  'enrollmentSelector': 'authoredEnrollmentA', 'responseModelMap': ['authoredModelA'],
                  'requireModelEcho': port != 'local_host'}
    contract = response_contract(job)
    candidate = authored_response(job)
    if risk_rationale is not None:
        candidate['risk']['rationale'] = risk_rationale
    target = {'projectId': 'rc1Project', 'runId': run, 'handoffId': 'rc1Handoff', 'taskRef': 'rc1Task',
              'candidateRevision': bridge.CANDIDATE, 'requirementVersion': bridge.REQUIREMENT,
              'projectConfigVersion': config_version, 'dataPolicyVersion': policy_version}
    from runtime_candidate.execution_projection import project
    expected_bundle = project(job, candidate, target)['bundle']
    scope = {'projectId': 'rc1Project', 'port': port, 'sourceManifest': manifest,
             'expectedBundleDigest': digest(expected_bundle), 'omittedCheckIds': [bridge.API_PAGE_CHECK]}
    offer = {'version': VERSION, 'attemptId': attempt, 'port': port, 'profile': PROFILES[port],
             'target': target,
             'assignment': '1' * 32, 'fence': 1, 'effectNonce': '2' * 32,
             'job': job, 'jobDigest': digest(job), 'executionDigest': sha(outcome_bytes),
             'sourceManifest': manifest, 'responseContract': contract, 'responseContractDigest': digest(contract),
             'policyPin': {'configVersion': config_version, 'policyVersion': policy_version, 'scopeDigest': digest(scope),
                           'capabilityDigest': digest(capability)},
             'budget': {'maxInvocations': 1, 'maxSubmissions': 1, 'inputTokenBound': 100, 'maxOutputTokens': 100,
                        'maxResponseBytes': LIMIT, 'usageMode': 'authored_fixture'}, 'deadlineUtc': DEADLINE}
    return {'offer': offer, 'sources': sources, 'capability': capability, 'proposal': candidate,
            'expectedBundle': expected_bundle, 'scope': scope,
            'profileSource': {'profile': PROFILES[port], 'origin': 'authored_fixture',
                              'url': SOURCES[port], 'consultedDate': '2026-11-25'}}


def authored_response(job):
    criteria, reviews, bindings = [], [], []
    for cid, level in bridge.LEVELS.items():
        source = {'sourceArtifactId': job['artifacts'][0]['id'], 'locator': cid}
        criteria.append({'criterionId': cid, 'planState': 'accepted', 'scopeDescription': 'Authored mapping fixture',
            'requiredLevels': [level], 'allowedProvenance': ['execution'],
            'obligations': [{'id': 'obligation', 'description': 'Authored obligation',
                             'requiredComparisonKeys': ['comparison'], **source}],
            'comparisonContexts': [{'id': 'comparison', 'description': 'Authored context', **source}],
            'applicability': 'applicable', 'naDecision': None})
    assignments = [('AC-01', OBSERVATIONS[0][0], 'supports'), ('AC-02', OBSERVATIONS[1][0], 'violates'),
                   ('AC-02', OBSERVATIONS[2][0], 'violates'), ('AC-03', OBSERVATIONS[3][0], 'violates'),
                   ('AC-04', OBSERVATIONS[4][0], 'supports')]
    for cid, test, relation in assignments:
        eid = next(o['id'] for o in job['observations'] if o['testId'] == test)
        reviews.append({'evidenceId': eid, 'integrity': 'matched', 'attribution': 'accepted',
                        'scope': 'accepted', 'rationale': 'Authored judgment, not actual reasoning'})
        bindings.append({'criterionId': cid, 'obligationId': 'obligation', 'evidenceId': eid,
                         'relation': relation, 'judgment': 'accepted', 'rationale': 'Authored mapping',
                         'comparisonKey': 'comparison'})
    return {'version': bridge.RESPONSE_VERSION, 'runId': job['runId'], 'jobId': job['jobId'],
            'jobDigest': digest(job), 'risk': {'tier': 'medium', 'state': 'accepted', 'rationale': 'Authored risk'},
            'criteria': criteria, 'evidenceReviews': reviews, 'bindings': bindings}


def event(fixture, *, usage=(12, 7), proposal=None):
    """Each provider's independent positive wire fixture. No cross-provider fake."""
    port = fixture['offer']['port']
    candidate = fixture['proposal'] if proposal is None else proposal
    text = canonical(candidate).decode('utf-8')
    if port == 'local_host':
        return {'kind': 'completion', 'body': text.encode('utf-8'),
                'usageCounts': None if usage is None else {'inputTokens': usage[0], 'outputTokens': usage[1]}}
    counts = None if usage is None else {'input_tokens': usage[0], 'output_tokens': usage[1]}
    if port == 'openai':
        data = {'object': 'response', 'status': 'completed', 'error': None, 'incomplete_details': None,
                'model': 'authoredModelA', 'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': text}]}], 'usage': counts}
    else:
        data = {'type': 'message', 'role': 'assistant', 'stop_reason': 'end_turn', 'model': 'authoredModelA',
                'content': [{'type': 'text', 'text': text}], 'usage': counts}
    return {'kind': 'http', 'status': 200, 'body': canonical(data), 'requestId': 'authoredRequest'}
