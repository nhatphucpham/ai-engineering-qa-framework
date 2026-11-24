"""Cross-project ID collisions on the operator's already-running synthetic TLS campaign."""
import base64
from contextlib import closing

from .common import canonical, digest, require, sha, strict_json
from .execution_projection import project as project_inputs
from .fixture_import import ARCHIVE, REVIEW_PATH, REVIEW_SHA, ROOT
from .integration_cases import _account, _denied, _wire


PROJECT = 'crossProject'
SNAPSHOT = 'snapshot_cross'
AUXILIARY = 'fixture-long-safe'
AUDIENCES = ('scheduler', 'worker', 'collector', 'assessor')


def _imported_context(data):
    review = (ROOT / REVIEW_PATH).read_bytes()
    require(sha(review) == REVIEW_SHA, 'E_INTEGRITY')
    origin = ARCHIVE + '/a'
    response_path = origin + '/native-response-2.json'
    response = (ROOT / response_path).read_bytes()
    require(sha(response) == strict_json(review)['files'][response_path], 'E_INTEGRITY')
    # This exact private registered job was independently pinned by the HC1 import.
    job_raw = data['sources']['vf1-coverage-policy'][0]
    require(sha(job_raw) == data['provenance']['originalFileDigests'][origin + '/host-request.json'], 'E_INTEGRITY')
    job = strict_json(job_raw)
    held = {'projectId': PROJECT, 'taskRef': 'crossTask', 'handoffId': 'crossHandoff', 'runId': data['run_id'],
            'projectConfigVersion': 2, 'dataPolicyVersion': 2, 'candidateRevision': job['candidateRevision'],
            'requirementVersion': job['requirementVersion']}
    projected = project_inputs(job, strict_json(response), held)
    manifest = {'origin': origin, 'modeDescription': 'new project context over historical HC1 A',
                'projectionVersion': projected['version'], 'heldContext': held, 'historicalJobSha256': sha(job_raw),
                'historicalProposalSha256': sha(response), 'freshExecution': False, 'freshAssessmentReasoning': False}
    return projected['bundle'], projected['assessment'], manifest


def _publish(ctx):
    call, admin, data = ctx['call'], ctx['admin'], ctx['dataA']
    bundle, assessment, manifest = _imported_context(data)
    scope = {'project': PROJECT, 'run_id': ctx['run_id']}
    call('project_create', admin, project=PROJECT, owner='admin')
    with closing(ctx['factory']()) as app:
        registered = app.register_snapshot(PROJECT, SNAPSHOT, 'repo_task', bundle, sources=data['sources'],
                                           mode='imported', manifest=manifest)
    # An unrelated safe auxiliary source is allowed in A only. Both underlying byte stores agree.
    require(AUXILIARY in data['sources'], 'E_INTEGRITY')
    config = dict(ctx['config'], sourceIds=sorted(set(data['sources']) - {AUXILIARY}),
                  leaseSeconds=300, runSeconds=180)
    configured = call('project_configure', admin, project=PROJECT, expected_config=1, config=config)
    require(configured == {'configVersion': 2, 'policyVersion': 2}, 'E_INTEGRITY')
    grant = call('grant_issue', admin, project=PROJECT, actions=['start'], expected_config=2)['grant']
    ctx['forbidden'].append(grant.encode())
    services = {}
    for kind in AUDIENCES:
        service = call('service_enroll', admin, service='cross_' + kind, kind=kind, projects=[PROJECT])
        services[kind] = service['credential']
        ctx['forbidden'].append(service['credential'].encode())
    intake = call('intake_snapshot', admin, project=PROJECT, key='cross_intake', kind='repo_task',
                  snapshot_ref=SNAPSHOT, candidate_digest=registered['candidateDigest'],
                  input_digest=registered['inputDigest'], expected_config=2)
    started = call('run_start', admin, **scope, key='cross_start', intake_id=intake['intakeId'],
                   grant=grant, expected_config=2)
    require(started['state'] == 'queued' and started['project'] == PROJECT, 'E_INTEGRITY')
    claim = dict(scope, worker='cross_worker', expected_run_version=started['stateVersion'])
    _denied('E_AUTH', call, 'worker_claim', ctx['services']['scheduler'], **claim)
    assignment = call('worker_claim', services['scheduler'], **claim)
    body = dict(scope, assignment=assignment['assignment'], fence=assignment['fence'],
                lease_token=assignment['lease_token'])
    ctx['forbidden'].append(body['lease_token'].encode())
    _denied('E_AUTH', call, 'worker_admit', ctx['services']['worker'], **body)
    admitted = call('worker_admit', services['worker'], **body)
    effect = dict(scope, assignment=body['assignment'], fence=body['fence'], effect_nonce=admitted['effectNonce'])
    ctx['forbidden'].append(admitted['effectNonce'].encode())
    collection = dict(effect, execution={'mode': 'imported', 'inputDigest': registered['inputDigest'],
                                         'origin': manifest['origin']},
                      cleanup={'mode': 'imported', 'noExecutionRequired': True})
    _denied('E_AUTH', call, 'collector_record', ctx['services']['collector'], **collection)
    observed = call('collector_record', services['collector'], **collection)
    acceptance = dict(effect, bundle=bundle, assessment=assessment, bundle_digest=digest(bundle),
                      assessment_digest=digest(assessment), execution_digest=observed['executionDigest'])
    _denied('E_AUTH', call, 'assessment_accept', ctx['services']['assessor'], **acceptance)
    accepted = call('assessment_accept', services['assessor'], **acceptance)
    submission = dict(body, assessment_digest=accepted['assessmentDigest'])
    report = call('worker_submit', services['worker'], **submission)
    require(report['state'] == 'completed' and call('worker_submit', services['worker'], **submission) == report,
            'E_INTEGRITY')
    return manifest['heldContext']


def _read_scope(ctx, project, token, expected_version):
    call, run_id = ctx['call'], ctx['run_id']
    scope = dict(project=project, run_id=run_id)
    report = call('report_read', token, **scope)
    exported = call('report_export', token, **scope)
    view = report['view']
    manifest = exported['manifest']
    require(view == exported['view'] and report['sourceLinks'] == exported['sourceLinks']
            and report['viewSha256'] == digest(view) and report['sourceLinksSha256'] == digest(report['sourceLinks'])
            and view['verification'] == 'failed' and view['hasUnverifiedMandatory'] and view['humanDecision'] == 'pending'
            and report['reportId'] == view['reportId'] == manifest['reportId'] == 'report_' + run_id
            and manifest['project'] == project and manifest['runId'] == run_id
            and manifest['configVersion'] == manifest['policyVersion'] == expected_version
            and exported['manifestSha256'] == digest(manifest), 'E_INTEGRITY')
    criteria = {c['criterionId']: c for c in view['criteria']}
    require(set(criteria) == {g['criterionId'] for g in report['sourceLinks']}, 'E_INTEGRITY')
    resolved = {}
    for group in report['sourceLinks']:
        criterion = criteria[group['criterionId']]
        aliases = set(criterion['evidenceIds'] + criterion['contextEvidenceIds'])
        require({link['evidenceId'] for link in group['links'] if link['kind'] == 'evidence'} == aliases, 'E_INTEGRITY')
        for link in group['links']:
            if 'evidenceId' in link:
                require(link['evidenceId'] in aliases, 'E_INTEGRITY')
            if 'artifactId' not in link:
                require(link.get('reason') == 'restricted', 'E_INTEGRITY')
                continue
            aid = link['artifactId']
            if aid not in resolved:
                resolved[aid] = call('source_read', token, **scope, artifact_id=aid)
            raw, classification, revision = ctx['dataA']['sources'][aid]
            reply = resolved[aid]
            require(reply['text'].encode() == raw and reply['classification'] == classification == 'safe_source'
                    and reply['revision'] == revision == link['revision'] and reply['artifactId'] == aid
                    and sha(raw) == reply['sha256'] == link['sha256'], 'E_INTEGRITY')
    events = ctx['client'].events(project, run_id, token)
    ready = [e for e in events if e['event'] == 'report_ready']
    require(resolved and len(ready) == 1 and ready[0]['data']['reportId'] == report['reportId']
            and [e['id'] for e in events] == list(range(1, len(events) + 1)), 'E_INTEGRITY')
    output = canonical([report, exported, events, resolved])
    for key in ('fixture-raw-canary', 'fixture-taint-canary'):
        raw = ctx['dataA']['sources'][key][0]
        require(all(s not in output for s in (raw, raw.hex().encode(), base64.b64encode(raw))), 'E_INTEGRITY')
    return report['reportId'], len(resolved)


def _independent_rows(ctx, held):
    project, run_id = ctx['project'], ctx['run_id']
    with closing(ctx['factory']()) as app:
        rows = app.conn.execute('''SELECT r.project,r.report_id,r.private_ref,r.bundle_digest,u.state,u.snapshot
            FROM rt_reports r JOIN rt_runs u ON (u.project,u.id)=(r.project,r.run_id)
            WHERE r.project IN (%s,%s) AND r.run_id=%s''', (project, PROJECT, run_id)).fetchall()
        require(len(rows) == 2 and {r['project'] for r in rows} == {project, PROJECT}
                and {r['report_id'] for r in rows} == {'report_' + run_id}
                and {r['state'] for r in rows} == {'completed'}
                and len({r['private_ref']['sha256'] for r in rows}) == 2, 'E_INTEGRITY')
        for row in rows:
            pkg = strict_json(app.blobs.get(row['private_ref']))
            target = pkg['target']
            require(target['projectId'] == row['project'] and target['runId'] == run_id
                    and digest(pkg['payloads']['bundle']) == row['bundle_digest'], 'E_INTEGRITY')
            if row['project'] == PROJECT:
                require(row['snapshot'] == SNAPSHOT and all(target[k] == v for k, v in held.items()), 'E_INTEGRITY')
            else:
                require(row['snapshot'] == 'snapshot_a' and row['bundle_digest'] == digest(ctx['dataA']['bundle']),
                        'E_INTEGRITY')
        counts = app.conn.execute("""SELECT project,count(*) AS n FROM rt_events WHERE run_id=%s
            AND project IN (%s,%s) AND event='report_ready' GROUP BY project""", (run_id, project, PROJECT)).fetchall()
        require({r['project']: r['n'] for r in counts} == {project: 1, PROJECT: 1}, 'E_INTEGRITY')


def _denied_routes(ctx, token, project, run_id):
    scope = dict(project=project, run_id=run_id)
    routes = [('POST', '/v1/run_read', scope), ('POST', '/v1/report_read', scope),
              ('POST', '/v1/report_export', scope),
              ('POST', '/v1/source_read', dict(scope, artifact_id='artifact-1')),
              ('GET', f'/v1/events?project={project}&run={run_id}&after=0', None)]
    for method, path, body in routes:
        status, raw = _wire(ctx, token, method, path, body)
        require(status == 403 and strict_json(raw) == {'error': 'E_DENIED'}, 'E_INTEGRITY')
    return len(routes)


def run_cases(ctx):
    checks = ctx['checks']
    held = _publish(ctx)
    _independent_rows(ctx, held)
    checks['I30'] = {'status': 'PASS', 'mode': 'imported_historical_hc1_a_new_context', 'projects': 2,
                     'sameRunAndReportIds': True, 'distinctPrivateReportPackages': True,
                     'completedReportRows': 2, 'reportReadyEventsPerProject': 1, 'foreignServiceAudiencesDenied': 4}
    first, second = ctx['project'], PROJECT
    a = _account(ctx, 'onlyCrossA', 'Viewer')
    b = _account(dict(ctx, project=second), 'onlyCrossB', 'Viewer')
    first_report, count_a = _read_scope(ctx, first, a, 4)
    second_report, count_b = _read_scope(ctx, second, b, 2)
    require(first_report == second_report and count_a == count_b, 'E_INTEGRITY')
    scope = dict(run_id=ctx['run_id'], artifact_id=AUXILIARY)
    allowed = ctx['call']('source_read', ctx['admin'], project=first, **scope)
    require(allowed['text'].encode() == ctx['dataA']['sources'][AUXILIARY][0], 'E_INTEGRITY')
    _denied('E_DENIED', ctx['call'], 'source_read', ctx['admin'], project=second, **scope)
    checks['I31'] = {'status': 'PASS', 'sameAdminAndSourceIdDifferentPolicy': True,
                     'derivedAliasesAndScopedSourceLinksVerified': True, 'resolvedSafeSourcesPerProject': count_a,
                     'distinctExportProjectAndPolicy': True, 'canariesAbsentFromOrdinaryResults': True}
    denied = 0
    for token, own, foreign in [(a, first, second), (b, second, first)]:
        require(ctx['call']('project_list', token)['projects'] == [own], 'E_INTEGRITY')
        for p, run in [(foreign, ctx['run_id']), ('unknownCrossProject', ctx['run_id']), (own, 'unknownCrossRun')]:
            denied += _denied_routes(ctx, token, p, run)
    checks['I32'] = {'status': 'PASS', 'projectOnlyViewers': 2, 'runReportExportSourceAndSse': True,
                     'foreignAndUnknownTargetsSame403Error': True, 'deniedWireRepliesChecked': denied}
    return {key: checks[key] for key in ('I30', 'I31', 'I32')}
