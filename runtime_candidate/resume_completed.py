"""Read/restore the exact committed f2 result; no new QA/model/publish invocation."""
from contextlib import closing
import ast
import re
import secrets
import sys
import uuid
from pathlib import Path

from qa_core.application import check_report_package
from .application import Application
from .checkpoint import backup, restore
from .checkpoint_cases import listener
from .common import VERSION, Error, canonical, digest, require, sha, strict_json
from .database import stop_database
from .execution_projection import project as project_inputs
from .publication import prepare
from .run_integration import ROOT, call


def immutable_graph(app):
    tables = ('rt_projects', 'rt_configs', 'rt_sources', 'rt_snapshots', 'rt_grants', 'rt_services',
              'rt_credentials', 'rt_intakes', 'rt_runs', 'rt_executions', 'rt_assessments',
              'rt_reports', 'rt_events', 'rt_receipts')
    with app.store.unit():
        result = {}
        for table in tables:
            rows = app.conn.execute(f'SELECT to_jsonb(t) AS value FROM {table} t ORDER BY to_jsonb(t)::text').fetchall()
            result[table] = {'count': len(rows), 'sha256': digest([r['value'] for r in rows])}
        return result


def denied(function, code):
    try:
        function()
    except Error as exc:
        require(exc.code == code, 'E_INTEGRITY')
        return exc.code
    raise Error('E_INTEGRITY')


def traverse(client, token, scope, expected_view, sources):
    report = call(client, 'report_read', token, **scope)
    exported = call(client, 'report_export', token, **scope)
    require(report['view'] == expected_view == exported['view'] and report['sourceLinks'] == exported['sourceLinks']
            and report['viewSha256'] == digest(expected_view)
            and report['sourceLinksSha256'] == digest(report['sourceLinks']), 'E_INTEGRITY')
    require(expected_view['humanDecision'] == 'pending' and expected_view['verification'] == 'failed', 'E_INTEGRITY')
    resolved = {}
    for group in report['sourceLinks']:
        for link in group['links']:
            if 'artifactId' not in link:
                require(link['reason'] == 'restricted', 'E_INTEGRITY')
                continue
            aid = link['artifactId']
            if aid not in resolved:
                resolved[aid] = call(client, 'source_read', token, **scope, artifact_id=aid)
            source = resolved[aid]
            expected_source = sources[aid]
            require(source['text'].encode() == expected_source['raw'] and sha(expected_source['raw']) == link['sha256'] == source['sha256']
                    and source['revision'] == link['revision'] == expected_source['revision'], 'E_INTEGRITY')
    require('artifact-7' in resolved and any(link.get('artifactId') == 'artifact-7' and link['kind'] == 'check_definition'
            for group in report['sourceLinks'] for link in group['links']), 'E_INTEGRITY')
    module = ast.parse(resolved['artifact-7']['text'])
    method = next(method for cls in module.body if isinstance(cls, ast.ClassDef) and cls.name == 'Historical'
                  for method in cls.body if isinstance(method, ast.FunctionDef) and method.name == 'test_reset_from_third_page')
    require((method.lineno, method.end_lineno) == (8, 12)
            and any(link.get('artifactId') == 'artifact-7' and link['kind'] == 'check_definition' and link.get('locator') == 'L8-L12'
                    for group in report['sourceLinks'] for link in group['links']), 'E_INTEGRITY')
    for aid in ('vf1-execution-record', 'vf1-coverage-policy'):
        denied(lambda: call(client, 'source_read', token, **scope, artifact_id=aid), 'E_DENIED')
    events = client.events(scope['project'], scope['run_id'], token)
    require(len([e for e in events if e['event'] == 'report_ready']) == 1, 'E_INTEGRITY')
    return report, {'resolvedSafeArtifacts': sorted(resolved), 'eventWatermark': events[-1]['id'],
                    'privateOriginsDenied': True, 'historicalProducerReached': True}


def experiment(work, checks, forbidden, origin):
    require(re.fullmatch('[a-z0-9][a-z0-9-]{1,79}', origin), 'E_INPUT')
    source_work = ROOT / '.cache/s6/m50' / origin
    original_evidence = (ROOT / 'docs/m50-results' / (origin + '.json')).read_bytes()
    evidence = strict_json(original_evidence)
    require(evidence['status'] == 'ERROR' and evidence['databaseStopped'] is True
            and evidence['checks']['F02']['status'] == 'PASS', 'E_INPUT')
    offer_raw, response_raw = (source_work / 'native-offer.json').read_bytes(), (source_work / 'native-response-1.json').read_bytes()
    offer, response = strict_json(offer_raw), strict_json(response_raw)
    dispatch = strict_json((source_work / 'native-dispatch.json').read_bytes())
    ready = strict_json((source_work / 'native-ready-1.json').read_bytes())
    job = offer['request']
    require(ready == {'nativeTask': dispatch['nativeTask'], 'jobDigest': digest(job), 'offerSha256': sha(offer_raw),
                      'responseSha256': sha(response_raw), 'observedNativeCompletion': True}
            and dispatch['offerSha256'] == sha(offer_raw) and evidence['checks']['F02']['jobDigest'] == digest(job), 'E_INTEGRITY')
    raw = (source_work / 'fresh_execution/execution.json').read_bytes()
    require(sha(raw) == job['executionSha256'] == evidence['checks']['F02']['enrichedRecordSha256'], 'E_INTEGRITY')
    roots = [p for p in source_work.glob('id_*') if p.is_dir()]
    require(len(roots) == 1, 'E_INPUT')
    root, schema = roots[0], roots[0].name
    with closing(Application(schema, root)) as app:
        with app.store.unit():
            run = app.conn.execute('SELECT * FROM rt_runs WHERE id=%s', (job['runId'],)).fetchone()
            require(run is not None and run['state'] == 'completed' and not run['incident'], 'E_INTEGRITY')
            scope = {'project': run['project'], 'run_id': run['id']}
            target = app.store.snapshot(run['project'], run['snapshot'])['manifest']['coreTarget']
            projected = project_inputs(job, response, target)
            expected = prepare(projected['bundle'], projected['assessment'], expected_bundle_digest=digest(projected['bundle']),
                               expected_assessment_digest=digest(projected['assessment']), run_id=run['id'], report_id='report_' + run['id'])
            report_row = app.conn.execute('SELECT * FROM rt_reports WHERE project=%s AND run_id=%s', tuple(scope.values())).fetchone()
            accepted = app.conn.execute('SELECT * FROM rt_assessments WHERE project=%s AND run_id=%s', tuple(scope.values())).fetchone()
            require(report_row['private_ref'] == expected.private_ref and app.blobs.get(report_row['private_ref']) == expected.private_bytes
                    and (accepted['bundle_digest'], accepted['assessment_digest']) == (digest(projected['bundle']), digest(projected['assessment'])), 'E_INTEGRITY')
            original_refs = run['effect_witness']['observation']
            require(app.blobs.get(original_refs['rawRef']) == raw and app.blobs.get(original_refs['jobRef']) == canonical(job), 'E_INTEGRITY')
        frozen = immutable_graph(app)
        user = 'resume' + uuid.uuid4().hex[:12]
        password, changed = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        forbidden.extend((password.encode(), changed.encode()))
        # Restricted disposable fixture bootstrap, not a normal-user recovery route.
        from identity import PH
        with app.store.unit(write=True):
            app.conn.execute('INSERT INTO accounts(id,password_hash,admin) VALUES(%s,%s,true)', (user, PH.hash(password)))
            app.identity.audit(user, 'fixture_resume_bootstrap')
        require(immutable_graph(app) == frozen, 'E_INTEGRITY')
    from .test_transport import make_test_certificate
    cert, key = make_test_certificate(work)
    ctx = {'certificate': cert, 'private_key': key}
    with listener(ctx, schema, root) as client:
        restricted = call(client, 'session_login', user=user, password=password)
        forbidden.extend((restricted['access'].encode(), restricted['refresh'].encode())); token = restricted['access']
        call(client, 'session_change_password', token, old=password, new=changed)
        session = call(client, 'session_login', user=user, password=changed)
        forbidden.extend((session['access'].encode(), session['refresh'].encode())); token = session['access']
        artifact_rows = {a['id']: a for a in projected['bundle']['artifacts']}
        sources = {a['id']: {'raw': a['text'].encode(), 'revision': artifact_rows[a['id']]['revision']} for a in job['artifacts']}
        report, journey = traverse(client, token, scope, expected.view, sources)
        checks['R01'] = {'status': 'PASS', 'originalRun': origin, 'nativeTask': dispatch['nativeTask'],
                         'originalEvidenceSha256': sha(original_evidence), 'originalPrivatePackageReference': expected.private_ref,
                         'nativeProposalSha256': sha(response_raw), 'offerSha256': sha(offer_raw),
                         'newExecutionAssessmentOrSubmit': False, 'viewSha256': report['viewSha256'],
                         'verification': expected.view['verification'], 'humanDecision': 'pending', **journey}
        with closing(Application(schema, root)) as source:
            require(immutable_graph(source) == frozen, 'E_INTEGRITY')
            archive = work / 'populated_backup'; receipt = backup(source.store, archive)
            next_schema, next_root = 'id_' + uuid.uuid4().hex, work / 'active_restore'
            result = restore(source.store, archive, checkpoint=receipt, target_schema=next_schema, target_root=next_root, activate=True)
            require(result['state'] == 'active_restore', 'E_INTEGRITY')
            denied(lambda: call(client, 'report_read', token, **scope), 'E_UNRESOLVED')
    from local import start, read_config
    with listener(ctx, next_schema, next_root) as client:
        restored, restored_journey = traverse(client, token, scope, expected.view, sources)
        require(restored == report, 'E_INTEGRITY')
        with closing(Application(next_schema, next_root)) as app:
            require(immutable_graph(app) == frozen, 'E_INTEGRITY')
            require(app.blobs.get(original_refs['rawRef']) == raw and app.blobs.get(original_refs['jobRef']) == canonical(job)
                    and app.blobs.get(expected.private_ref) == expected.private_bytes, 'E_INTEGRITY')
        checks['R02'] = {'status': 'PASS', 'actualPopulatedWitnessCheckpointRestore': True, 'blobCount': receipt['blobCount'],
                         'rawAndJobRefsExact': True, 'immutableApplicationGraphPreserved': True, 'oldOriginDenied': True,
                         'fixtureAuthScope': 'new disposable Admin; public mandatory password change and issued session'}
        config = read_config(False); before = (Path(config['data']) / 'postmaster.pid').read_text().splitlines()[0]
        stopped = stop_database(); start()
        after = (Path(config['data']) / 'postmaster.pid').read_text().splitlines()[0]
        require(before != after, 'E_INTEGRITY')
        replay, _ = traverse(client, token, scope, expected.view, sources)
        require(replay == report, 'E_INTEGRITY')
        with closing(Application(next_schema, next_root)) as app, app.store.unit():
            package = strict_json(app.blobs.get(expected.private_ref))
            require(not check_report_package(package, expected_bundle_sha256=digest(projected['bundle']),
                    expected_assessment_sha256=digest(projected['assessment']), run_id=run['id'], report_id=expected.view['reportId']), 'E_INTEGRITY')
        checks['R03'] = {'status': 'PASS', 'actualDatabaseRestart': True, 'postgresPidBefore': int(before), 'postgresPidAfter': int(after),
                         'maintenanceStop': stopped, 'samePrivatePackageCoreReplay': True, 'sameOrdinaryReportAfterRestart': True,
                         'oneOriginalReportReady': True, 'originalCompletedRunNotResubmitted': True}
    return {'originalCampaign': origin, 'originalRunId': run['id'], 'originalNativeTask': dispatch['nativeTask'],
            'newProducerRun': False, 'restoredSchema': next_schema}


if __name__ == '__main__':
    from .run_integration import main
    require(len(sys.argv) == 3, 'E_INPUT')
    original = sys.argv.pop()
    raise SystemExit(main(experiment_fn=lambda work, checks, forbidden: experiment(work, checks, forbidden, original)))
