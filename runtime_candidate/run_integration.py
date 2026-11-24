"""Actual isolated TLS/PostgreSQL integration, imported evidence is explicitly historical."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'spikes/s2')]
from local import start, stop, read_config, command, inventory
from runtime_candidate.application import Application, DEFAULT_CONFIG
from runtime_candidate.database import stop_database
from runtime_candidate.common import VERSION, Error, canonical, digest, strict_json, sha, require

import json
import base64
import secrets
import subprocess
import threading
import time
import uuid


def call(client, op, token=None, **params):
    return client.call(op, token, dict(params, version=VERSION))


def experiment(workspace, checks, forbidden):
    # Initialize identity first so maintained Argon2's pinned dependency origins remain explicit.
    schema = 'id_' + uuid.uuid4().hex
    state_root = workspace / schema
    app = Application(schema, state_root, create=True)
    password, changed = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    forbidden.extend((password.encode(), changed.encode()))
    app.identity.bootstrap('admin', password)
    app.close()
    sys.path.insert(0, str(ROOT / '.cache/s6/deps'))
    from runtime_candidate.test_transport import make_test_certificate
    from runtime_candidate.transport import CandidateClient, serve
    from runtime_candidate.fixture_import import load_hc1
    certificate, private_key = make_test_certificate(workspace)
    factory = lambda: Application(schema, state_root)
    server = serve(factory, certificate, private_key)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    client = CandidateClient('127.0.0.1', server.server_address[1], certificate)
    try:
        tokens = call(client, 'session_login', user='admin', password=password)
        forbidden.extend((tokens['access'].encode(), tokens['refresh'].encode()))
        call(client, 'session_change_password', tokens['access'], old=password, new=changed)
        admin = call(client, 'session_login', user='admin', password=changed)['access']; forbidden.append(admin.encode())
        current = call(client, 'session_read', admin)
        require(current['user'] == 'admin' and current['isAdmin'], 'E_INTEGRITY')
        checks['I01'] = {'status': 'PASS', 'actualTlsIssuedSession': True, 'mandatoryPasswordChange': True,
                         'userServiceAudiences': 'enforced by application; further negatives below'}
        data = load_hc1('a', config_version=2, policy_version=2, include_canaries=True)
        data['sources']['fixture-long-safe'] = (b'SAFE-M50-LINE\n' * 1500, 'safe_source', 'm50-fixture-v1')
        project, run_id = data['project'], data['run_id']
        call(client, 'project_create', admin, project=project, owner='admin')
        app = factory()
        try:
            registered = app.register_snapshot(project, 'snapshot_a', 'repo_task', data['bundle'], sources=data['sources'],
                                               mode='imported', manifest=data['provenance'])
        finally:
            app.close()
        config = dict(DEFAULT_CONFIG, sourceIds=sorted(data['sources']), leaseSeconds=300)
        call(client, 'project_configure', admin, project=project, expected_config=1, config=config)
        grant = call(client, 'grant_issue', admin, project=project, actions=['start', 'cancel', 'read', 'report', 'source', 'export', 'stream'], expected_config=2)['grant']
        services = {}
        for name, kind in [('scheduler', 'scheduler'), ('worker', 'worker'), ('collector', 'collector'), ('assessor', 'assessor')]:
            services[name] = call(client, 'service_enroll', admin, service=name, kind=kind, projects=[project])['credential']
            forbidden.append(services[name].encode())
        intake = call(client, 'intake_snapshot', admin, project=project, key='intake_a', kind='repo_task', snapshot_ref='snapshot_a',
                      candidate_digest=registered['candidateDigest'], input_digest=registered['inputDigest'], expected_config=2)
        start_body = dict(project=project, key='start_a', run_id=run_id, intake_id=intake['intakeId'], grant=grant, expected_config=2)
        started = call(client, 'run_start', admin, **start_body)
        require(call(client, 'run_start', admin, **start_body) == started, 'E_INTEGRITY')
        require(started['state'] == 'queued' and started['sequenceWatermark'] == 1, 'E_INTEGRITY')
        try:
            call(client, 'run_start', admin, **dict(start_body, run_id='different_run'))
            raise AssertionError('Conflicting idempotency accepted')
        except Error as exc:
            require(exc.code == 'E_CONFLICT', 'E_INTEGRITY')
        checks['I02'] = {'status': 'PASS', 'actualStartAndSameReceipt': True, 'conflictDenied': True,
                         'inputMode': 'imported historical HC1, no new checks or reasoning'}
        assignment = call(client, 'worker_claim', services['scheduler'], project=project, worker='worker', expected_run_version=1, run_id=run_id)
        worker_body = {key: assignment[key] for key in ('assignment', 'fence', 'lease_token')}
        worker_body.update(project=project, run_id=run_id)
        forbidden.append(worker_body['lease_token'].encode())
        admitted = call(client, 'worker_admit', services['worker'], **worker_body)
        try:
            call(client, 'worker_admit', services['worker'], **worker_body)
            raise AssertionError('Duplicate execution permit accepted')
        except Error as exc:
            require(exc.code == 'E_CONFLICT', 'E_INTEGRITY')
        collection = dict(project=project, run_id=run_id, assignment=assignment['assignment'], fence=assignment['fence'],
                          effect_nonce=admitted['effectNonce'], execution={'mode': 'imported', 'inputDigest': registered['inputDigest'],
                          'origin': data['provenance']['origin']}, cleanup={'mode': 'imported', 'noExecutionRequired': True})
        try:
            call(client, 'collector_record', services['worker'], **collection)
            raise AssertionError('Worker self-attested collection accepted')
        except Error as exc:
            require(exc.code == 'E_AUTH', 'E_INTEGRITY')
        observed = call(client, 'collector_record', services['collector'], **collection)
        acceptance = {key: collection[key] for key in ('project', 'run_id', 'assignment', 'fence', 'effect_nonce')}
        acceptance.update(bundle=data['bundle'], assessment=data['assessment'], bundle_digest=digest(data['bundle']),
                          assessment_digest=digest(data['assessment']), execution_digest=observed['executionDigest'])
        try:
            call(client, 'assessment_accept', services['worker'], **acceptance)
            raise AssertionError('Worker accepted its own assessment')
        except Error as exc:
            require(exc.code == 'E_AUTH', 'E_INTEGRITY')
        accepted = call(client, 'assessment_accept', services['assessor'], **acceptance)
        result = call(client, 'worker_submit', services['worker'], **worker_body, assessment_digest=accepted['assessmentDigest'])
        duplicate = call(client, 'worker_submit', services['worker'], **worker_body, assessment_digest=accepted['assessmentDigest'])
        require(duplicate == result and result['state'] == 'completed', 'E_INTEGRITY')
        checks['I03'] = {'status': 'PASS', 'separateCollectorAssessorWorker': True, 'workerCannotSelfAccept': True,
                         'oneUseAdmission': True, 'importedCollectionNotExecution': True}
        report = call(client, 'report_read', admin, project=project, run_id=run_id)
        require(report['view']['verification'] == 'failed' and report['view']['hasUnverifiedMandatory']
                and report['view']['humanDecision'] == 'pending', 'E_INTEGRITY')
        exported = call(client, 'report_export', admin, project=project, run_id=run_id)
        require(exported['view'] == report['view'] and 'payloads' not in exported and 'package' not in exported, 'E_INTEGRITY')
        events = client.events(project, run_id, admin, after=0)
        require([r['id'] for r in events] == list(range(1, len(events) + 1))
                and len([r for r in events if r['event'] == 'report_ready']) == 1, 'E_INTEGRITY')
        app = factory()
        try:
            counts = app.conn.execute('SELECT count(*) AS n FROM rt_reports WHERE project=%s AND run_id=%s', (project, run_id)).fetchone()['n']
            require(counts == 1 and app.store.run(project, run_id)['state'] == 'completed', 'E_INTEGRITY')
        finally:
            app.close()
        checks['I04'] = {'status': 'PASS', 'atomicReportCompletedOutbox': True, 'reportCount': counts,
                         'reportReadyEvents': 1, 'failedAndGapPreserved': True, 'humanDecision': 'pending',
                         'ordinaryExportNarrow': True, 'eventCount': len(events)}
        # A client disconnect does not cancel. Stop/restart the actual HTTP application listener.
        old_port = server.server_address[1]
        server.shutdown(); server.server_close(); thread.join(5)
        server = serve(factory, certificate, private_key)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        client = CandidateClient('127.0.0.1', server.server_address[1], certificate)
        require(call(client, 'report_read', admin, project=project, run_id=run_id) == report, 'E_INTEGRITY')
        require(client.events(project, run_id, admin, after=events[-1]['id']) == [], 'E_INTEGRITY')
        checks['I05'] = {'status': 'PASS', 'actualListenerRestart': True, 'samePinnedReportAfterRestart': True,
                         'snapshotAndReplayWatermark': True, 'oldPort': old_port, 'newPort': server.server_address[1]}
        context = {'client': client, 'call': lambda op, token=None, **params: call(client, op, token, **params),
                   'factory': factory, 'schema': schema, 'state_root': state_root, 'workspace': workspace,
                   'certificate': certificate, 'private_key': private_key, 'server_port': server.server_address[1],
                   'admin': admin, 'project': project, 'run_id': run_id, 'config': config, 'dataA': data,
                   'forbidden': forbidden, 'report': report, 'grant': grant, 'services': services}
        context['checks'] = checks
        from runtime_candidate.integration_cases import run_cases as read_cases
        checks.update(read_cases(context))
        from runtime_candidate.lifecycle_cases import run_cases as lifecycle_cases
        checks.update(lifecycle_cases(context))
        from runtime_candidate.process_cases import run_cases as process_cases
        checks.update(process_cases(context))
        from runtime_candidate.crossproject_cases import run_cases as crossproject_cases
        checks.update(crossproject_cases(context))
        from runtime_candidate.scope_cases import run_cases as scope_cases
        checks.update(scope_cases(context))
        from runtime_candidate.checkpoint_cases import run_cases as checkpoint_cases
        checks.update(checkpoint_cases(context))
        return {'schema': schema, 'stateRoot': str(state_root.relative_to(ROOT)), 'project': project, 'runId': run_id}
    finally:
        server.shutdown(); server.server_close(); thread.join(5)


def source_pins():
    files = [p for p in (ROOT / 'runtime_candidate').glob('*') if p.is_file() and p.suffix in ('.py', '.sql')]
    files += list((ROOT / 'qa_core').glob('*.py')) + list((ROOT / 'schemas').glob('*.json'))
    files += list((ROOT / 'runtime_candidate/fixtures').glob('*.json'))
    files += [ROOT / p for p in ('spikes/s6b/identity.py', 'spikes/s6b/preflight_b.py', 'spikes/s6b/schema.sql',
                                'spikes/s2/local.py', 'spikes/vf1/core_bridge.py', 'spikes/vf1/run_vf1.py')]
    for relative in ('spikes/vf1', 'spikes/hc1', 'spikes/s4', 'spikes/s4b'):
        files += list((ROOT / relative).glob('*.py'))
    files.append(ROOT / 'spikes/hc1/HOST-INSTRUCTIONS.md')
    files += list((ROOT / 'spikes/s4f').glob('*.py'))
    files += [ROOT / 'spikes/m50_worker' / name for name in
              ('__init__.py', 'controller.py', 'profile_unit.py', 'linux_profile.py', 'qa_executor.py')
              if (ROOT / 'spikes/m50_worker' / name).is_file()]
    files += [ROOT / 'docs/S4-F-PROTOCOL.md', ROOT / 'docs/M50-WORKER-CONTROLLER-PROTOCOL.md']
    from spikes.vf1.core_bridge import ARTIFACT_KINDS
    files += [ROOT / 'examples/mock/06-filter-pagination' / relative for relative in ARTIFACT_KINDS]
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(set(files))}


def main(*, experiment_fn=experiment):
    require(len(sys.argv) == 2, 'E_INPUT')
    destination = ROOT / 'docs/m50-results' / sys.argv[1]
    require(destination.suffix == '.json' and destination.parent.resolve() == (ROOT / 'docs/m50-results').resolve()
            and not destination.exists(), 'E_INPUT')
    workspace = ROOT / '.cache/s6/m50' / destination.stem
    workspace.mkdir(parents=True, exist_ok=False)
    evidence = {'version': VERSION, 'classification': 'synthetic-only', 'status': 'RUNNING', 'checks': {}, 'inputsBefore': source_pins()}
    forbidden = []; begin = time.monotonic(); started = False
    try:
        evidence['preflight'] = inventory()
        require(evidence['preflight']['toolchainReady'], 'E_DEPENDENCY')
        config = read_config(False)
        try:
            command('pg_ctl', '-D', config['data'], 'status')
            raise Error('E_UNRESOLVED')
        except subprocess.CalledProcessError as exc:
            require(exc.returncode == 3, 'E_DEPENDENCY')
        start(); started = True
        evidence['scope'] = experiment_fn(workspace, evidence['checks'], forbidden)
        evidence['inputsAfter'] = source_pins()
        require(evidence['inputsBefore'] == evidence['inputsAfter'], 'E_INTEGRITY')
        evidence['status'] = 'PASS'
    except Exception as exc:
        evidence['status'] = 'ERROR'; evidence['errorType'] = type(exc).__name__
        import traceback
        diagnostic = traceback.format_exc().encode('utf-8')
        require(not any(secret in diagnostic for secret in forbidden), 'E_INTEGRITY')
        (workspace / 'error.txt').write_bytes(diagnostic)
    finally:
        if started:
            try:
                # This campaign verified STOPPED before starting the marker-bound fixture.
                try:
                    command('pg_ctl', '-D', read_config(False)['data'], 'status')
                except subprocess.CalledProcessError as exc:
                    require(exc.returncode == 3, 'E_UNRESOLVED')
                else:
                    evidence['databaseStopObservation'] = stop_database()
                try:
                    command('pg_ctl', '-D', read_config(False)['data'], 'status')
                except subprocess.CalledProcessError as exc:
                    require(exc.returncode == 3, 'E_UNRESOLVED')
                    evidence['databaseStopped'] = True
                else:
                    raise Error('E_UNRESOLVED')
            except Exception:
                evidence['status'] = 'ERROR'; evidence['databaseStopped'] = False; evidence['cleanupError'] = 'E_UNRESOLVED'
        else:
            evidence['databaseStopped'] = None
    evidence['elapsedSeconds'] = time.monotonic() - begin
    encoded = canonical(evidence)
    require(not any(secret in encoded or secret.hex().encode() in encoded or base64.b64encode(secret) in encoded for secret in forbidden), 'E_INTEGRITY')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(encoded)
    print(json.dumps({'status': evidence['status'], 'checks': {key: row['status'] for key, row in evidence['checks'].items()},
                      'elapsedSeconds': evidence['elapsedSeconds']}))
    return 0 if evidence['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
