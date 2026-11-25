"""Issuer pins, lineage policy and existing core acceptance of candidate data only."""
from datetime import datetime, timezone
import re

from jsonschema import Draft202012Validator
from runtime_candidate.common import identifier
from runtime_candidate.execution_projection import project
from runtime_candidate.publication import prepare
from spikes.vf1.core_bridge import validate_job

from .common import VERSION, LIMIT, PROFILES, canonical, digest, exact, integer, need, parse, sha

OFFER_FIELDS = ('version attemptId port profile target assignment fence effectNonce job jobDigest '
                'executionDigest sourceManifest responseContract responseContractDigest policyPin budget deadlineUtc')
TARGET_FIELDS = ('projectId runId handoffId taskRef candidateRevision requirementVersion '
                 'projectConfigVersion dataPolicyVersion')


def response_contract(job):
    from spikes.hc1.orchestrator import response_contract as existing
    value = existing(job)
    value['version'] = 'm50-native-response-contract-1.0.0'
    relation = ('Evidence-review reference rule: the bridge includes only observations referenced by bindings in its handoff. '
                'Therefore evidenceReviews must contain each bound evidenceId exactly once and no unbound observation IDs. '
                'You may inspect any offered observation while reasoning, but omit its evidenceReview unless a binding uses it. '
                'Do not invent a binding merely to retain an unused review. This is a reference-integrity rule, not a requested QA conclusion.')
    value['instructions'] += '\n\n' + relation
    value['schema']['properties']['evidenceReviews']['description'] = relation
    return value


def timestamp(value):
    need(isinstance(value, str) and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', value))
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
    except ValueError as exc:
        from .common import Rejected
        raise Rejected('E_INPUT') from exc


def hex_string(value, size):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(size) + '}', value) is not None


def validate_offer(offer):
    exact(offer, OFFER_FIELDS)
    need(offer['version'] == VERSION and offer['port'] in PROFILES
         and offer['profile'] == PROFILES[offer['port']])
    need(len(canonical(offer)) <= LIMIT)
    identifier(offer['attemptId'])
    exact(offer['target'], TARGET_FIELDS)
    for key in ('projectId', 'runId'):
        identifier(offer['target'][key])
    for key in ('handoffId', 'taskRef'):
        need(isinstance(offer['target'][key], str) and 0 < len(offer['target'][key]) <= 96 and
             re.fullmatch(r'[A-Za-z][A-Za-z0-9._-]{0,95}', offer['target'][key]))
    for key in ('candidateRevision', 'requirementVersion'):
        need(isinstance(offer['target'][key], str) and 0 < len(offer['target'][key]) <= 160)
    for key in ('projectConfigVersion', 'dataPolicyVersion'):
        need(integer(offer['target'][key], 1))
    need(hex_string(offer['assignment'], 32) and hex_string(offer['effectNonce'], 32) and integer(offer['fence'], 1))
    for key in ('jobDigest', 'executionDigest', 'responseContractDigest'):
        need(hex_string(offer[key], 64))
    need(digest(offer['job']) == offer['jobDigest'] and
         digest(offer['responseContract']) == offer['responseContractDigest'], 'E_INTEGRITY')
    validate_job(offer['job'], offer['jobDigest'])
    need(offer['job']['runId'] == offer['target']['runId'] and
         offer['job']['candidateRevision'] == offer['target']['candidateRevision'] and
         offer['job']['requirementVersion'] == offer['target']['requirementVersion'], 'E_INTEGRITY')
    exact(offer['responseContract'], 'version schema instructions')
    # Only the source-owned wrapper is accepted. Never resolve caller-provided $refs.
    need(digest(offer['responseContract']) == digest(response_contract(offer['job'])), 'E_INTEGRITY')
    exact(offer['policyPin'], 'configVersion policyVersion scopeDigest capabilityDigest')
    need(offer['policyPin']['configVersion'] == offer['target']['projectConfigVersion'] and
         offer['policyPin']['policyVersion'] == offer['target']['dataPolicyVersion'])
    need(integer(offer['policyPin']['configVersion'], 1) and integer(offer['policyPin']['policyVersion'], 1))
    need(all(hex_string(offer['policyPin'][k], 64) for k in ('scopeDigest', 'capabilityDigest')))
    exact(offer['budget'], 'maxInvocations maxSubmissions inputTokenBound maxOutputTokens maxResponseBytes usageMode')
    budget = offer['budget']
    need(type(budget['maxInvocations']) is int and budget['maxInvocations'] == 1 and
         type(budget['maxSubmissions']) is int and budget['maxSubmissions'] == 1 and
         type(budget['maxResponseBytes']) is int and budget['maxResponseBytes'] == LIMIT and
         budget['usageMode'] == 'authored_fixture' and
         all(integer(budget[k], 1) for k in ('inputTokenBound', 'maxOutputTokens')), 'E_BUDGET')
    timestamp(offer['deadlineUtc'])
    manifest = offer['sourceManifest']
    need(isinstance(manifest, list) and 1 <= len(manifest) <= 64)
    seen = set()
    for row in manifest:
        exact(row, 'artifactId revision sha256 bytes lineageIds classification')
        identifier(row['artifactId'])
        need(row['artifactId'] not in seen and hex_string(row['sha256'], 64) and integer(row['bytes']))
        need(isinstance(row['revision'], str) and 0 < len(row['revision']) <= 256)
        seen.add(row['artifactId'])
        need(row['classification'] in ('safe', 'restricted', 'secret_tainted'))
        need(isinstance(row['lineageIds'], list) and all(isinstance(x, str) for x in row['lineageIds'])
             and row['lineageIds'] == sorted(set(row['lineageIds'])))
    need(all(set(row['lineageIds']) <= seen for row in manifest), 'E_POLICY')


def check_scope(offer, registration, authority):
    need(authority['enabled'] and offer['port'] in authority['ports'] and
         authority['configVersion'] == offer['target']['projectConfigVersion'] and
         authority['policyVersion'] == offer['target']['dataPolicyVersion'], 'E_POLICY')
    need(offer['policyPin']['scopeDigest'] == digest(registration['scope']) and
         offer['policyPin']['capabilityDigest'] == digest(registration['capability']), 'E_POLICY')
    need(registration['scope']['projectId'] == offer['target']['projectId'] and
         registration['scope']['port'] == offer['port'] and
         registration['scope']['sourceManifest'] == offer['sourceManifest'], 'E_POLICY')
    need(hex_string(registration['scope'].get('expectedBundleDigest'), 64) and
         registration['scope'].get('omittedCheckIds') == ['Baseline.test_api_page_and_size'], 'E_POLICY')
    capability = registration['capability']
    need(isinstance(capability, dict) and all(k in capability for k in
         ('enrolled', 'isolatedContext', 'noTools', 'noOutbound', 'routeSelector', 'modelSelector',
          'enrollmentSelector', 'responseModelMap', 'requireModelEcho')), 'E_CAPABILITY')
    need(all(isinstance(capability[k], str) and 0 < len(capability[k]) <= 256 for k in
         ('routeSelector', 'modelSelector', 'enrollmentSelector')), 'E_CAPABILITY')
    need(type(capability['requireModelEcho']) is bool and isinstance(capability['responseModelMap'], list) and
         all(isinstance(s, str) and 0 < len(s) <= 256 for s in capability['responseModelMap']), 'E_CAPABILITY')
    need(offer['port'] == 'local_host' or (capability['requireModelEcho'] is True and capability['responseModelMap']), 'E_CAPABILITY')
    need(authority['enrolled'] and all(capability[k] is True for k in
         ('enrolled', 'isolatedContext', 'noTools', 'noOutbound')), 'E_CAPABILITY')
    sources = registration['sources']
    need(isinstance(sources, dict) and {'contextRecord', 'outcomeRecord'} <= set(sources), 'E_POLICY')
    need({row['artifactId'] for row in offer['sourceManifest']} == set(sources), 'E_POLICY')
    for row in offer['sourceManifest']:
        source = sources[row['artifactId']]
        raw = bytes.fromhex(source['hex'])
        need(source['classification'] == 'safe_source' and row['classification'] == 'safe' and
             row['artifactId'] in authority['sourceIds'], 'E_POLICY')
        need((sha(raw), len(raw), source['revision'], source['lineageIds']) ==
             (row['sha256'], row['bytes'], row['revision'], row['lineageIds']), 'E_INTEGRITY')
    # Full context pins ALL observation/metadata bytes; their independent outcome origins
    # and source ancestry are retained in the registered manifest, not inferred from labels.
    need(bytes.fromhex(sources['contextRecord']['hex']) == canonical(offer['job']) and
         offer['executionDigest'] == offer['job']['executionSha256'] == sha(bytes.fromhex(sources['outcomeRecord']['hex'])), 'E_INTEGRITY')
    outcomes = parse(bytes.fromhex(sources['outcomeRecord']['hex']))
    need(outcomes == {'version': 'rc1-authored-observations-1', 'mode': 'authored_fixture',
                      'observations': offer['job']['observations']}, 'E_INTEGRITY')
    required = {a['id'] for a in offer['job']['artifacts']} | {'outcomeRecord'}
    need(set(sources['contextRecord']['lineageIds']) == required, 'E_POLICY')
    for artifact in offer['job']['artifacts']:
        need(artifact['id'] in sources and bytes.fromhex(sources[artifact['id']]['hex']) == artifact['text'].encode('utf-8'), 'E_INTEGRITY')
    # Memoize DAG traversal, but reject cyclic ancestry rather than trusting a safe loop.
    visited = set()
    def visit(aid, stack):
        need(aid not in stack, 'E_POLICY')
        if aid in visited:
            return
        for parent in sources[aid]['lineageIds']:
            visit(parent, stack | {aid})
        visited.add(aid)
    for row in offer['sourceManifest']:
        visit(row['artifactId'], set())


def validate_candidate(offer, candidate, expected_bundle_digest):
    need(Draft202012Validator(offer['responseContract']['schema']).is_valid(candidate), 'E_CANDIDATE')
    projected = project(offer['job'], candidate, offer['target'])
    publication = prepare(projected['bundle'], projected['assessment'],
                          expected_bundle_digest=expected_bundle_digest,
                          expected_assessment_digest=digest(projected['assessment']),
                          run_id=offer['target']['runId'], report_id='report_' + offer['target']['runId'])
    return {'validationOnly': True, 'bundleDigest': digest(projected['bundle']),
            'assessmentDigest': digest(projected['assessment']), 'verification': publication.view['verification'],
            'humanDecision': publication.view['humanDecision'],
            'statuses': [r['status'] for r in publication.view['criteria']],
            'hasUnverifiedMandatory': publication.view['hasUnverifiedMandatory']}
