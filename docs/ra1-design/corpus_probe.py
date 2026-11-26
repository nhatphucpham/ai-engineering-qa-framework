"""Pure imported-corpus feasibility only. No Application, DB, network or execution."""
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from runtime_candidate.common import VERSION, Error, canonical, digest, sha, strict_json
from runtime_candidate.blobs import descriptor
from runtime_candidate.execution_projection import project
from runtime_candidate.lineage import report_lineage
from runtime_candidate.publication import prepare
from runtime_candidate.storage import Store
from runtime_candidate.readside import _public_source, _registered_inputs, _source_links
from spikes.p4d_rc1.corpus import OBSERVATIONS, authored_response
from spikes.vf1.core_bridge import ARTIFACT_KINDS
from spikes.vf1.run_vf1 import build_job, OMITTED

ROOT = Path(__file__).resolve().parents[2]


def build():
    case = ROOT / 'examples/mock/06-filter-pagination'
    payloads = {'case/' + relative: (case / relative).read_bytes() for relative in ARTIFACT_KINDS}
    record = {'version': 'ra1-authored-record-1.0.0', 'origin': 'authored_fixture',
        'runId': 'ra1Run', 'jobId': 'ra1FixtureJob', 'status': 'complete',
        'finishedAt': '2026-11-26T00:00:00Z', 'inputHashes': {p: sha(raw) for p, raw in payloads.items()},
        'execution': {'observations': [{'testId': test, 'outcome': outcome, 'traceText': ''}
                                      for test, outcome in OBSERVATIONS + [(OMITTED, 'pass')]]},
        'ingestionIntervention': {'withheldTestIds': [OMITTED], 'appliedBeforeHostRequest': True}}
    raw_record = canonical(record)
    job = build_job(record, sha(raw_record), [OMITTED], payloads)
    response = authored_response(job)
    target = {'projectId': 'ra1Project', 'runId': record['runId'], 'handoffId': 'ra1Handoff', 'taskRef': 'ra1Task',
              'candidateRevision': job['candidateRevision'], 'requirementVersion': job['requirementVersion'],
              'projectConfigVersion': 2, 'dataPolicyVersion': 2}
    projected = project(job, response, target)
    bundle = projected['bundle']
    by_id = {a['id']: a for a in job['artifacts']}
    sources = {}
    for artifact in bundle['artifacts']:
        aid = artifact['id']
        if aid == 'vf1-execution-record':
            raw, classification = raw_record, 'restricted'
        elif aid == 'vf1-coverage-policy':
            raw, classification = canonical(job), 'restricted'
        else:
            raw, classification = by_id[aid]['text'].encode('utf-8'), 'safe_source'
        assert sha(raw) == artifact['sha256']
        sources[aid] = (raw, classification, artifact['revision'])
    collector = {'mode': 'imported', 'inputDigest': digest(bundle), 'fixtureId': 'ra1Fixture',
                 'jobDigest': digest(job), 'rawRecordSha256': sha(raw_record)}
    return {'record': record, 'job': job, 'response': response, 'target': target, 'projected': projected,
            'sources': sources, 'collector': collector, 'payloads': payloads}


class MemoryRegistry:
    """An explicit data shim for pure readside functions, NOT a database/API mock proof."""
    def __init__(self, sources):
        self.sources = sources
        self.blobs = self

    def source_record(self, run, aid):
        raw, classification, revision = self.sources[aid]
        return {'id': aid, 'ref': descriptor(raw), 'classification': classification, 'revision': revision}

    def get(self, ref):
        return next(raw for raw, _, _ in self.sources.values() if descriptor(raw) == ref)


def run():
    f = build()
    rows = []
    def check(identifier, condition):
        rows.append({'id': identifier, 'status': 'PASS' if condition else 'FAIL'})
        assert condition, identifier
    schema = strict_json((ROOT / 'schemas/ra1-authored-record-v1.schema.json').read_bytes())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    check('D01_closed_authored_frame', validator.is_valid(f['record']))
    check('D02_no_private_trace_or_unknown_field', all(o['traceText'] == '' for o in f['record']['execution']['observations']))
    check('D03_exact_source_hashes', f['record']['inputHashes'] == {p: sha(raw) for p, raw in f['payloads'].items()})
    check('D04_rebuild_and_literal_reasons', all(o['reason'] == ('fail' if o['outcome'] == 'fail' else None)
                                              for o in f['job']['observations']))
    check('D05_withheld_is_authored_not_executed', len(f['record']['execution']['observations']) == 6 and
          len(f['job']['observations']) == 5 and OMITTED not in {o['testId'] for o in f['job']['observations']})
    bundle, assessment = f['projected']['bundle'], f['projected']['assessment']
    lineage = report_lineage(bundle, f['sources'])
    check('D06_private_aliases_remain_restricted', lineage['profile'] == 'vf1_fixed_outcome_metadata_v1' and
          set(lineage['restrictedOrigins']) == {'vf1-execution-record', 'vf1-coverage-policy'})
    prepared = prepare(bundle, assessment, expected_bundle_digest=digest(bundle), expected_assessment_digest=digest(assessment),
                       run_id='ra1Run', report_id='report_ra1Run')
    check('D07_failed_and_gap_pending', [c['status'] for c in prepared.view['criteria']] ==
          ['verified', 'failed', 'failed', 'unverified'] and prepared.view['humanDecision'] == 'pending')
    check('D08_digest_domains', f['job']['executionSha256'] == sha(canonical(f['record'])) and
          f['collector']['inputDigest'] == digest(bundle) and digest(f['collector']) != f['job']['executionSha256'])
    packet = {'version': VERSION, 'project': 'ra1Project', 'run_id': 'ra1Run', 'assignment': '1' * 32,
              'fence': 1, 'effect_nonce': '2' * 32, 'bundle': bundle, 'assessment': assessment,
              'bundle_digest': digest(bundle), 'assessment_digest': digest(assessment),
              'execution_digest': digest(f['collector'])}
    check('D09_private_packet_fits_bound_shape_only', len(canonical(packet)) <= 65536)
    run = {'project': 'ra1Project', 'id': 'ra1Run', 'snapshot': 'ra1Snapshot'}
    manifest = {'mode': 'imported', 'sourceIds': sorted(f['sources']), 'reportSourceIds': lineage['sourceIds'], 'reportProjection': lineage}
    app = MemoryRegistry(f['sources'])
    _, refs, profile = _registered_inputs(app, run, bundle, manifest, lineage['sourceIds'], lineage)
    check('D10_pure_readside_data_compatibility_not_API', profile == lineage['profile'] and len(refs) == 8)
    denied = []
    for aid in ('vf1-execution-record', 'vf1-coverage-policy'):
        try:
            _public_source(app, run, manifest, set(f['sources']), aid)
        except Error as exc:
            denied.append(exc.code == 'E_DENIED')
    check('D11_private_alias_source_reads_denied_pure', denied == [True, True])
    changed = dict(f['sources'])
    raw, _, revision = changed['vf1-coverage-policy']; changed['vf1-coverage-policy'] = (raw, 'safe_source', revision)
    try:
        _registered_inputs(MemoryRegistry(changed), run, bundle, manifest, set(changed), lineage)
    except Error as exc:
        denied_reclass = exc.code == 'E_DENIED'
    else:
        denied_reclass = False
    check('D12_reclassification_not_permission', denied_reclass)
    for label, mutation in [('trace', lambda r: r['execution']['observations'][0].update(traceText='private canary')),
                            ('unknown', lambda r: r.update(secret='private canary'))]:
        changed_record = deepcopy(f['record']); mutation(changed_record)
        check('D13_schema_denies_' + label, not validator.is_valid(changed_record))
    check('D14_old_projection_does_not_show_imported',
          {s['provenanceKind'] for s in prepared.view['sources']} == {'execution'})
    provenance = {'evidenceMode': 'imported', 'observationOrigin': 'authored_fixture',
                  'reasoningOrigin': 'authored_fixture', 'executionObserved': False,
                  'humanDecision': 'pending', 'fixtureId': 'ra1Fixture'}
    delivered = deepcopy(prepared.view)
    delivered.update(viewVersion='ra1-view-1.0.0', provenance=provenance)
    for source in delivered['sources']:
        source.update(provenanceKind='imported', observationOrigin='authored_fixture')
    links = _source_links(prepared.view, prepared.lineage, prepared.package, f['sources'], refs, profile)
    detached_manifest = {'version': 'ra1-export-1.0.0', 'project': 'ra1Project', 'runId': 'ra1Run',
        'reportId': 'report_ra1Run', 'configVersion': f['target']['projectConfigVersion'], 'policyVersion': f['target']['dataPolicyVersion'],
        'classification': 'target_scoped_derived_view', 'entries': [
        {'kind': 'report_view', **descriptor(canonical(delivered))},
        {'kind': 'source_links', **descriptor(canonical(links))},
        {'kind': 'provenance', **descriptor(canonical(provenance))}]}
    check('D15_planned_delivery_labels_and_new_hash', all(s['provenanceKind'] == 'imported' for s in delivered['sources'])
          and sha(canonical(delivered)) != sha(canonical(prepared.view)))
    tampered = deepcopy(delivered); tampered['provenance']['evidenceMode'] = 'execution'
    check('D16_detached_provenance_tamper_mismatches',
          descriptor(canonical(tampered)) != {k: v for k, v in detached_manifest['entries'][0].items() if k != 'kind'})
    exported = {'version': 'ra1-read-1.0.0', 'operation': 'report_export', 'result': {
        'view': delivered, 'sourceLinks': links, 'sourceLinksSha256': digest(links), 'provenance': provenance,
        'manifest': detached_manifest, 'manifestSha256': digest(detached_manifest)}}
    check('D17_planned_detached_export_bound', len(canonical(exported)) <= 65536 and
          {r['kind'] for r in detached_manifest['entries']} == {'report_view', 'source_links', 'provenance'})
    for key in ('jobId', 'finishedAt'):
        changed_record = deepcopy(f['record']); changed_record[key] += '\n'
        check('D18_schema_denies_final_LF_' + key, not validator.is_valid(changed_record))
    changed_record = deepcopy(f['record']); changed_record['inputHashes']['case/head/api.py'] += '\n'
    check('D19_schema_denies_final_LF_hash', not validator.is_valid(changed_record))
    # Static frozen source_scope only; no Store/Application construction or API dispatch.
    scope_snapshot = {'manifest': {'reportSourceIds': lineage['sourceIds']}}
    initial = {'config_version': 1, 'policy_version': 1, 'payload': {'sourceIds': []}}
    try:
        Store.source_scope(scope_snapshot, initial)
    except Error as exc:
        denied_initial = exc.code == 'E_DENIED'
    else:
        denied_initial = False
    check('D20_fresh_v1_empty_scope_denies_pure', denied_initial)
    registered_ids = set(f['sources'])
    configured_ids = sorted(lineage['sourceIds'])
    configured = {'config_version': initial['config_version'] + 1,
                  'policy_version': initial['policy_version'] + 1, 'payload': {'sourceIds': configured_ids}}
    Store.source_scope(scope_snapshot, configured)
    check('D21_register_then_configure_target2_pure', len(configured_ids) == 8 and
          set(configured_ids) <= registered_ids and
          (configured['config_version'], configured['policy_version']) ==
          (f['target']['projectConfigVersion'], f['target']['dataPolicyVersion']) == (2, 2))
    stale_target = dict(f['target'], projectConfigVersion=1, dataPolicyVersion=1)
    check('D22_v1_target_stale_after_configure_pure',
          (stale_target['projectConfigVersion'], stale_target['dataPolicyVersion']) !=
          (configured['config_version'], configured['policy_version']))
    check('D23_delivery_versions_match_frozen_target',
          detached_manifest['configVersion'] == f['target']['projectConfigVersion'] and
          detached_manifest['policyVersion'] == f['target']['dataPolicyVersion'])
    field_origins = {key: ('safe_source_bytes' if key == 'artifacts' else 'approved_requirement_fields' if key == 'selectedCriteria'
                          else 'closed_authored_outcomes' if key == 'observations' else 'registered_closed_frame_or_profile')
                     for key in f['job']}
    return {'scope': 'pure schema/bytes/projection/readside-data feasibility; no real API/auth/DB/release proof',
            'checks': rows, 'status': 'PASS', 'fieldOriginMap': field_origins,
            'jobDigest': digest(f['job']), 'rawRecordSha256': sha(canonical(f['record'])),
            'expectedBundleDigest': digest(bundle), 'collectorExecutionDigest': digest(f['collector']),
            'fixtureJobId': f['record']['jobId'], 'effectJobId': 'NOT_ASSIGNED: requires future worker_admit',
            'deliveryProjectionProof': {'scope': 'hypothetical pure data transform only, not an implemented route/export',
                'baseSourcesProvenance': 'execution', 'plannedViewSha256': sha(canonical(delivered)),
                'plannedDetachedManifestSha256': digest(detached_manifest)},
            'expectedAssessmentPacketBytes': len(canonical(packet)), 'sourcePins': {
                aid: {'sha256': sha(raw), 'bytes': len(raw), 'classification': classification, 'revision': revision}
                for aid, (raw, classification, revision) in f['sources'].items()},
            'preflightPlan': {'scope': 'pure data predicates, no actual registration/configure/intake/start proof',
                'order': ['project_create1/1', 'register_frozen_target2/2_and_sources', 'project_configure_CAS1_to2',
                          'assert_config2_policy2', 'ra_policy_and_grant2/2', 'intake2', 'run_start2'],
                'configuredSourceIds': configured_ids, 'target': f['target'],
                'perPortCaseIsolation': 'fresh exclusive namespace; never reuse completed run'},
            'actualApplicationOperations': 0, 'actualExecution': False}
