"""Map one caller-pinned synthetic VF1 job and host response into the existing core."""

import ast
from copy import deepcopy
from hashlib import sha256
import re

from qa_core.application import prepare_report
from qa_core.contracts import utc_timestamp
from qa_core.reports import digest
from qa_core.rules import ASSESSMENT_VALIDATOR_V2


JOB_VERSION = 'vf1-job-1.0.0'
RESPONSE_VERSION = 'vf1-host-response-1.0.0'
CANDIDATE = 'mock-06-head-v1'
REQUIREMENT = 'mock-req-06-v1'
LEVELS = {'AC-01': 'unit', 'AC-02': 'integration', 'AC-03': 'integration', 'AC-04': 'integration'}
ARTIFACT_KINDS = {
    'requirements.md': 'requirement',
    'head/api.py': 'source', 'head/data.py': 'source', 'head/service.py': 'source', 'head/ui.py': 'source',
    'tests/test_baseline.py': 'test', 'tests/test_historical.py': 'test', 'expected/test_probe.py': 'test',
}
BASELINE = 'tests/test_baseline.py'
API_PAGE_CHECK = 'Baseline.test_api_page_and_size'
CHECKS = {
    'Baseline.test_service_category_and_case': (BASELINE, 'unit'),
    'Baseline.test_service_pagination_and_out_of_range': (BASELINE, 'unit'),
    'Baseline.test_empty_category': (BASELINE, 'unit'),
    'Baseline.test_api_repeat_same_request': (BASELINE, 'integration'),
    API_PAGE_CHECK: (BASELINE, 'integration'),
    'Baseline.test_ui_select_from_first_page': (BASELINE, 'integration'),
    'Historical.test_reset_from_third_page': ('tests/test_historical.py', 'integration'),
    'Probe.test_reset_with_recorded_api_call': ('expected/test_probe.py', 'integration'),
    'Probe.test_cache_across_categories': ('expected/test_probe.py', 'integration'),
}
OUTCOME_LABELS = {
    'pass': None,
    'fail': 'Assertion failure',
    'error': 'Check execution error',
    'skipped': 'Check skipped',
}
PROJECT = 'vf1-synthetic-project'
TASK = 'vf1-mock-06'
POLICY_ARTIFACT = 'vf1-coverage-policy'
EXECUTION_ARTIFACT = 'vf1-execution-record'
HOST = 'vf1-host-mediated-reasoning'
NOTICE = 'Synthetic VF1 experiment. Assessment judgments are supplied by the local host reasoning session.'
ID = re.compile(r'[A-Za-z][A-Za-z0-9._-]{0,95}')
SHA256 = re.compile(r'[0-9a-f]{64}')
LINES = re.compile(r'L([1-9][0-9]{0,3})(?:-L([1-9][0-9]{0,3}))?')
UTC_Z = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z')


class BridgeError(ValueError):
    def __init__(self, code, explanation):
        self.code = code
        super().__init__(f'{code}: {explanation}')


def require(condition, code, explanation):
    if not condition:
        raise BridgeError(code, explanation)


def exact_keys(value, keys, code):
    require(isinstance(value, dict) and set(value) == set(keys.split()), code, 'Unexpected record fields')


def matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def job_digest(job):
    """Use the core's finite, sorted UTF-8 JSON SHA-256 serialization."""
    try:
        return digest(job)
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise BridgeError('E_VF1_JSON', 'Expected finite UTF-8 JSON') from exc


def requirement_row(artifact, criterion_id):
    rows = [(index, line.strip()) for index, line in enumerate(artifact['text'].splitlines(), 1)
            if line.startswith(f'| {criterion_id} | ')]
    require(len(rows) == 1, 'E_VF1_SCOPE', 'Criterion must resolve to one offered requirement row')
    index, row = rows[0]
    return index, row.split('|', 2)[2].removesuffix('|').strip()


def excerpt(artifact, locator):
    lines = artifact['text'].splitlines()
    if artifact['kind'] == 'requirement' and locator in LEVELS:
        first, _ = requirement_row(artifact, locator)
        last = first
    else:
        span = LINES.fullmatch(locator)
        require(span is not None, 'E_VF1_LOCATOR', 'Use an offered requirement anchor or source line range')
        first = int(span[1])
        last = int(span[2] or span[1])
    require(first <= last <= len(lines) and last - first < 40,
            'E_VF1_LOCATOR', 'Excerpt exceeds offered lines or the 40-line view limit')
    return {'artifactId': artifact['id'], 'relativePath': artifact['relativePath'],
            'sha256': artifact['sha256'], 'locator': locator, 'startLine': first, 'endLine': last,
            'text': '\n'.join(lines[first - 1:last])}


def check_spans(artifact):
    try:
        parsed = ast.parse(artifact['text'])
    except SyntaxError as exc:
        raise BridgeError('E_VF1_CHECK', 'Offered check source could not be parsed') from exc
    return {f'{cls.name}.{method.name}': f'L{method.lineno}-L{method.end_lineno}'
            for cls in parsed.body if isinstance(cls, ast.ClassDef)
            for method in cls.body if isinstance(method, ast.FunctionDef)}


def validate_job(job, expected_job_digest):
    exact_keys(job, 'version classification runId jobId candidateRevision requirementVersion observedAt '
               'executionRef executionSha256 artifacts selectedCriteria policy observations', 'E_VF1_JOB')
    require(job_digest(job) == expected_job_digest, 'E_VF1_JOB_DIGEST', 'Job differs from caller-held digest')
    require((job['version'], job['classification'], job['candidateRevision'], job['requirementVersion'])
            == (JOB_VERSION, 'synthetic-only', CANDIDATE, REQUIREMENT),
            'E_VF1_SCOPE', 'Job must be the selected synthetic candidate and requirement')
    require(all(matches(ID, job[key]) for key in ('runId', 'jobId', 'executionRef')),
            'E_VF1_ID', 'Invalid run, job or execution identity')
    require(matches(SHA256, job['executionSha256']), 'E_VF1_EXECUTION', 'Invalid execution record pin')
    require(matches(UTC_Z, job['observedAt']), 'E_VF1_EXECUTION', 'Observation time requires UTC Z')
    try:
        utc_timestamp(job['observedAt'])
    except ValueError as exc:
        raise BridgeError('E_VF1_EXECUTION', 'Invalid observation time') from exc
    require(job['policy'] == {'minimumLevelsByCriterion': LEVELS}, 'E_VF1_POLICY', 'Coverage policy differs')
    require(isinstance(job['artifacts'], list) and isinstance(job['selectedCriteria'], list)
            and isinstance(job['observations'], list), 'E_VF1_JOB', 'Expected JSON arrays')

    artifacts, paths = {}, set()
    for item in job['artifacts']:
        exact_keys(item, 'id kind relativePath sha256 text', 'E_VF1_ARTIFACT')
        aid, path = item['id'], item['relativePath']
        require(matches(ID, aid) and aid not in artifacts and aid not in (POLICY_ARTIFACT, EXECUTION_ARTIFACT),
                'E_VF1_ARTIFACT', 'Invalid or duplicate artifact identity')
        require(isinstance(path, str) and path in ARTIFACT_KINDS and path not in paths
                and item['kind'] == ARTIFACT_KINDS[path], 'E_VF1_ARTIFACT', 'Unexpected or duplicate artifact path')
        require(isinstance(item['text'], str) and sha256(item['text'].encode('utf-8')).hexdigest() == item['sha256'],
                'E_VF1_ARTIFACT_HASH', 'Offered UTF-8 bytes differ from the artifact pin')
        artifacts[aid] = item
        paths.add(path)
    require(paths == set(ARTIFACT_KINDS), 'E_VF1_ARTIFACT', 'Frozen fixture inventory differs')
    requirement = next(item for item in artifacts.values() if item['kind'] == 'requirement')
    selected = set()
    for criterion in job['selectedCriteria']:
        exact_keys(criterion, 'id expected locator', 'E_VF1_SCOPE')
        cid = criterion['id']
        require(isinstance(cid, str) and cid in LEVELS and cid not in selected,
                'E_VF1_SCOPE', 'Unexpected or duplicate selected criterion')
        _, expected = requirement_row(requirement, cid)
        require(criterion['locator'] == cid and criterion['expected'] == expected,
                'E_VF1_SCOPE', 'Selected criterion differs from the pinned requirement row')
        selected.add(cid)
    require(selected == set(LEVELS), 'E_VF1_SCOPE', 'Selected criterion inventory differs')

    spans = {aid: check_spans(item) for aid, item in artifacts.items() if item['kind'] == 'test'}
    observations, seen_tests, locators = {}, set(), {}
    for item in job['observations']:
        exact_keys(item, 'id testId outcome level checkArtifactId reason', 'E_VF1_OBSERVATION')
        eid, tid, aid = item['id'], item['testId'], item['checkArtifactId']
        require(matches(ID, eid) and eid not in observations, 'E_VF1_OBSERVATION', 'Invalid or duplicate observation ID')
        require(isinstance(tid, str) and tid in CHECKS and tid not in seen_tests,
                'E_VF1_CHECK', 'Unexpected or duplicate configured check')
        path, level = CHECKS[tid]
        require(matches(ID, aid) and aid in spans and artifacts[aid]['relativePath'] == path
                and tid in spans[aid] and item['level'] == level, 'E_VF1_CHECK', 'Check artifact or level differs')
        outcome, reason = item['outcome'], item['reason']
        require(isinstance(outcome, str) and outcome in OUTCOME_LABELS and
                (reason is None if outcome == 'pass' else isinstance(reason, str) and 0 < len(reason) <= 256),
                'E_VF1_OUTCOME', 'Expected pass without reason, or fail/error/skipped with a short reason')
        observations[eid] = item
        seen_tests.add(tid)
        locators[eid] = spans[aid][tid]
    return artifacts, requirement, observations, locators


def response_assessment(job, response, expected_digest, artifacts, observations):
    exact_keys(response, 'version runId jobId jobDigest risk criteria evidenceReviews bindings', 'E_VF1_RESPONSE')
    require(response['version'] == RESPONSE_VERSION, 'E_VF1_RESPONSE', 'Unsupported response version')
    require((response['runId'], response['jobId'], response['jobDigest']) ==
            (job['runId'], job['jobId'], expected_digest),
            'E_VF1_RESPONSE_BINDING', 'Response does not identify the held request')
    job_digest(response)
    assessment = {
        'assessmentVersion': '2.0.0', 'rulesVersion': 'p2-rules-2.0.0', 'classification': 'synthetic-only',
        'specimenNotice': NOTICE, 'projectId': PROJECT, 'handoffId': job['jobId'],
        'candidateRevision': CANDIDATE, 'evaluationMode': 'execution_review',
        'policySourceArtifactId': POLICY_ARTIFACT, 'assessorRef': HOST,
        'projectConfigVersion': 1, 'dataPolicyVersion': 1, 'constraintReviews': [],
        **{key: deepcopy(response[key]) for key in ('risk', 'criteria', 'evidenceReviews', 'bindings')},
    }
    require(ASSESSMENT_VALIDATOR_V2.is_valid(assessment), 'E_VF1_ASSESSMENT', 'Invalid P2 v2 host proposal')
    plans = assessment['criteria']
    require(len(plans) == len(LEVELS) and {plan['criterionId'] for plan in plans} == set(LEVELS),
            'E_VF1_SCOPE', 'Declare exactly one plan per selected criterion')
    for plan in plans:
        cid = plan['criterionId']
        require(LEVELS[cid] in plan['requiredLevels'] and plan['allowedProvenance'] == ['execution'],
                'E_VF1_POLICY', 'Plan must preserve the minimum level and execution provenance')
        require(plan['applicability'] == 'applicable' and plan['naDecision'] is None,
                'E_VF1_POLICY', 'This selected scope requires applicable plans')
        for ref in plan['obligations'] + plan['comparisonContexts']:
            aid = ref['sourceArtifactId']
            require(aid in artifacts, 'E_VF1_REFERENCE', 'Plan reference was never offered')
            excerpt(artifacts[aid], ref['locator'])
    require(all(review['evidenceId'] in observations for review in assessment['evidenceReviews']),
            'E_VF1_REFERENCE', 'Evidence review was never offered')
    for binding in assessment['bindings']:
        observation = observations.get(binding['evidenceId'])
        require(observation is not None, 'E_VF1_REFERENCE', 'Binding evidence was never offered')
        relation, outcome = binding['relation'], observation['outcome']
        require(relation == 'inconclusive' or (relation, outcome) in (('supports', 'pass'), ('violates', 'fail')),
                'E_VF1_OUTCOME', 'Binding relation contradicts the collected outcome')
        if binding['criterionId'] == 'AC-04' and relation == 'supports' and observation['level'] == 'integration':
            require(observation['testId'] == API_PAGE_CHECK,
                    'E_VF1_POLICY', 'AC-04 integration support requires the fixed-category API pagination check')
    return assessment


def contract_bundle(job, assessment, artifacts, requirement, observations):
    job_id, run_id = job['jobId'], job['runId']
    episode_artifacts = [
        {'id': item['id'], 'kind': 'source' if item['kind'] == 'test' else item['kind'],
         'revision': REQUIREMENT if item['kind'] == 'requirement' else CANDIDATE,
         'relativePath': item['relativePath'], 'sha256': item['sha256']}
        for item in artifacts.values()
    ] + [
        {'id': EXECUTION_ARTIFACT, 'kind': 'test_output', 'revision': CANDIDATE,
         'relativePath': 'execution.json', 'sha256': job['executionSha256']},
        {'id': POLICY_ARTIFACT, 'kind': 'requirement', 'revision': JOB_VERSION,
         'relativePath': 'host-request.json', 'sha256': job_digest(job)},
    ]
    evidence = []
    for eid, obs in observations.items():
        criterion_ids = sorted({binding['criterionId'] for binding in assessment['bindings']
                                if binding['evidenceId'] == eid})
        # P1 only represents evidence mapped to at least one criterion.
        if not criterion_ids:
            continue
        evidence.append({
            'id': eid, 'projectId': PROJECT, 'handoffId': job_id, 'criterionIds': criterion_ids,
            'revision': CANDIDATE, 'checkId': obs['testId'], 'level': obs['level'], 'outcome': obs['outcome'],
            'provenance': {'kind': 'execution', 'actorRef': 'vf1-local-collector',
                           'environment': 'VF1 disposable component-check worker', 'observedAt': job['observedAt'],
                           'sourceArtifactId': EXECUTION_ARTIFACT},
            'reason': obs['reason'], 'executionRef': job['executionRef'],
        })
    criteria = [{'id': item['id'], 'expected': item['expected'], 'mandatory': True, 'clarification': 'clear',
                 'ownerRole': 'domain-owner', 'claims': [{'artifactId': requirement['id'], 'locator': item['locator'],
                                                         'statement': item['expected']}]}
                for item in job['selectedCriteria']]
    return {
        'contractVersion': '2.0.0', 'classification': 'synthetic-only', 'specimenNotice': NOTICE,
        'projects': [{
            'id': PROJECT, 'configVersion': 1, 'name': 'Synthetic VF1 MOCK-06',
            'runtime': {'mode': 'agent_local', 'connectorRef': HOST},
            'dataPolicy': {'version': 1, 'allowedArtifactKinds': ['requirement', 'source', 'test_output'],
                           'allowedPaths': [item['relativePath'] for item in episode_artifacts],
                           'deniedPaths': [], 'allowedProviders': []},
            'triggers': {'manual': True, 'kinds': [], 'githubIngress': []},
            # These schema-required placeholders carry no live resource, permission or budget.
            'budgets': {'runTimeoutSeconds': 1, 'maxAttempts': 1, 'maxConcurrentRuns': 1,
                        'maxModelInputTokens': 1, 'maxModelOutputTokens': 1},
            'checks': [],
            'repository': {'provider': 'github', 'repositoryRef': 'vf1-unconfigured',
                           'credentialRef': 'vf1-unconfigured'},
            'requirementConflictPolicy': 'ask_owner_continue_independent',
            'editPolicy': {'sourceEdits': False, 'testEdits': False},
        }],
        'tasks': [{'id': TASK, 'projectId': PROJECT, 'title': 'MOCK-06 catalog filter and pagination',
                   'externalRef': None}],
        'artifacts': [dict(item, projectId=PROJECT, taskRef=TASK) for item in episode_artifacts],
        'handoffs': [{
            'id': job_id, 'projectId': PROJECT, 'taskRef': TASK, 'intake': 'repo_task',
            'candidateRevision': CANDIDATE, 'requirementVersion': REQUIREMENT,
            'decisionMoment': 'qc_to_reviewer', 'requestedDecision': 'Review behavior and gaps in selected scope',
            'actors': {'developerRef': None, 'qcRef': None, 'reviewerRef': None},
            'riskRationale': assessment['risk']['rationale'], 'criteria': criteria, 'constraints': [],
            'stageRecords': [{'stage': stage, 'state': 'unknown', 'evidenceIds': []}
                             for stage in ('developer_self_test', 'qc')],
            'knownIssues': [], 'diffArtifactIds': [],
            'sourceArtifactIds': [item['id'] for item in artifacts.values() if item['kind'] == 'source'],
        }],
        'runs': [{
            'id': run_id, 'projectId': PROJECT, 'handoffId': job_id, 'candidateRevision': CANDIDATE,
            'projectConfigVersion': 1, 'dataPolicyVersion': 1, 'state': 'analyzing', 'stateVersion': 1,
            'attempt': 1, 'triggerEventId': None, 'lease': {'workerId': HOST, 'fencingToken': 1,
                                                          'expiresAt': job['observedAt']},
            'waitingReasons': [], 'terminalReason': None, 'reportId': None,
            'initiator': {'kind': 'user', 'principalRef': 'vf1-local-session'}, 'rerunOfRunId': None,
        }],
        'evidence': evidence, 'memberships': [], 'events': [], 'commands': [], 'reports': [],
        'workerResults': [], 'progress': [],
    }


def narrow_view(job, report, artifacts, requirement, observations, locators):
    content = report['content']
    evaluated = content['assessment']
    refs, evidence_ids = {}, set()
    criteria = []
    for result, sources in zip(evaluated['criteria'], content['criterionSources'], strict=True):
        cid, plan = result['criterionId'], sources['plan']
        source_refs = dict.fromkeys([(requirement['id'], cid)] + [
            (ref['sourceArtifactId'], ref['locator']) for ref in plan['obligations'] + plan['comparisonContexts']
        ])
        bindings = [{key: binding[key] for key in ('obligationId', 'evidenceId', 'relation', 'judgment',
                                                  'rationale', 'comparisonKey')}
                    for binding in content['assessmentContext']['bindings'] if binding['criterionId'] == cid]
        for binding in bindings:
            eid = binding['evidenceId']
            evidence_ids.add(eid)
            source_refs[(observations[eid]['checkArtifactId'], locators[eid])] = None
        refs.update(source_refs)
        criteria.append({
            **{key: result[key] for key in ('criterionId', 'status', 'scopeDescription', 'reasonCodes',
                                            'hasOpenCoverage', 'evidenceIds', 'contextEvidenceIds')},
            'expected': sources['criterion']['expected'], 'requiredLevels': plan['requiredLevels'],
            'sourceRefs': [{'artifactId': aid, 'locator': locator} for aid, locator in source_refs],
            'bindings': bindings,
        })
    evidence = [{key: item[key] for key in ('id', 'testId', 'level', 'outcome', 'checkArtifactId')}
                | {'reason': OUTCOME_LABELS[item['outcome']], 'executionRef': job['executionRef'],
                   'checkLocator': locators[item['id']]}
                for item in observations.values() if item['id'] in evidence_ids]
    return {
        'viewVersion': 'vf1-view-1.0.0', 'classification': 'synthetic-only',
        **{key: job[key] for key in ('runId', 'jobId', 'candidateRevision', 'requirementVersion',
                                     'executionRef', 'executionSha256', 'observedAt')},
        'jobDigest': job_digest(job), 'reportId': report['id'],
        **{key: evaluated[key] for key in ('verification', 'hasUnverifiedMandatory',
                                           'hasOpenMandatoryCoverage', 'humanDecision')},
        'criteria': criteria, 'evidence': evidence,
        'actions': [{key: action[key] for key in ('id', 'criterionIds', 'ownerRole', 'state', 'description', 'doneWhen')}
                    for action in content['actions']],
        'sourceExcerpts': [excerpt(artifacts[aid], locator) for aid, locator in refs],
    }


def derive(job, response, *, expected_job_digest, report_id):
    """Return detached records for the local experiment, with no lifecycle or I/O effects."""
    require(matches(ID, report_id), 'E_VF1_ID', 'Invalid caller-selected report identity')
    artifacts, requirement, observations, locators = validate_job(job, expected_job_digest)
    assessment = response_assessment(job, response, expected_job_digest, artifacts, observations)
    bundle = contract_bundle(job, assessment, artifacts, requirement, observations)
    prepared = prepare_report(bundle, assessment, run_id=job['runId'], report_id=report_id)
    view = narrow_view(job, prepared['report'], artifacts, requirement, observations, locators)
    return {'bundle': bundle, 'assessment': assessment, 'prepared': prepared, 'view': deepcopy(view)}
