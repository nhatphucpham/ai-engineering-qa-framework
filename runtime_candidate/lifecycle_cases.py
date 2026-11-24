"""Actual TLS lifecycle/budget regressions using explicitly imported historical inputs."""
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import secrets
import threading
import time
import uuid

from .application import Application, DEFAULT_CONFIG
from .common import VERSION, Error, digest, require
from .fixture_import import load_hc1
from .transport import CandidateClient, serve


def _call(client, op, token=None, **p):
    return client.call(op, token, dict(p, version=VERSION))


def denied(action, codes):
    try:
        action()
    except Error as exc:
        require(exc.code in codes, 'E_INTEGRITY')
        return exc.code
    raise AssertionError('Expected live authority denial')


@contextmanager
def case(ctx, name, *, lease=5, budget=30, mode='imported', config_version=2, source_ids=None, intake=True, kind='handoff',
         include_canaries=False, extra_sources=None):
    schema = 'id_' + uuid.uuid4().hex
    root = ctx['workspace'] / ('lifecycle_' + name)
    app = Application(schema, root, create=True)
    initial, password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    ctx['forbidden'].extend((initial.encode(), password.encode()))
    app.identity.bootstrap('admin', initial); app.close()
    factory = lambda: Application(schema, root)
    server = serve(factory, ctx['certificate'], ctx['private_key'])
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    client = CandidateClient('127.0.0.1', server.server_address[1], ctx['certificate'])
    try:
        access = _call(client, 'session_login', user='admin', password=initial)['access']
        ctx['forbidden'].append(access.encode())
        _call(client, 'session_change_password', access, old=initial, new=password)
        access = _call(client, 'session_login', user='admin', password=password)['access']
        ctx['forbidden'].append(access.encode())
        data = load_hc1('a', config_version=config_version, policy_version=config_version, include_canaries=include_canaries)
        data['sources'].update(extra_sources or {})
        project, run_id = data['project'], data['run_id']
        _call(client, 'project_create', access, project=project, owner='admin')
        app = factory()
        try:
            registered = app.register_snapshot(project, 'snapshot', kind, data['bundle'], sources=data['sources'],
                                               mode=mode, manifest=data['provenance'])
        finally:
            app.close()
        config = dict(DEFAULT_CONFIG, sourceIds=sorted(data['sources']) if source_ids is None else source_ids, leaseSeconds=lease, runSeconds=budget)
        _call(client, 'project_configure', access, project=project, expected_config=1, config=config)
        grant = _call(client, 'grant_issue', access, project=project, actions=['start', 'cancel', 'read'], expected_config=2)['grant']
        services = {}
        for role in ('scheduler', 'worker', 'collector', 'assessor'):
            services[role] = _call(client, 'service_enroll', access, service=role, kind=role, projects=[project])['credential']
            ctx['forbidden'].append(services[role].encode())
        intake_params = dict(project=project, key='intake', kind=kind, snapshot_ref='snapshot',
                             candidate_digest=registered['candidateDigest'], input_digest=registered['inputDigest'], expected_config=2)
        accepted = _call(client, 'intake_snapshot', access, **intake_params) if intake else {'intakeId': 'legacy_intake'}
        body = dict(project=project, run_id=run_id, key='start', intake_id=accepted['intakeId'], grant=grant, expected_config=2)
        yield {'client': client, 'call': lambda op, token=None, **p: _call(client, op, token, **p), 'factory': factory,
               'schema': schema, 'state_root': root, 'project': project, 'run_id': run_id, 'admin': access, 'data': data,
               'services': services, 'start': body, 'grant': grant, 'registered': registered, 'intake_params': intake_params}
    finally:
        server.shutdown(); server.server_close(); thread.join(5)


def claim(c):
    c['call']('run_start', c['admin'], **c['start'])
    assignment = c['call']('worker_claim', c['services']['scheduler'], project=c['project'], run_id=c['run_id'],
                          worker='worker', expected_run_version=1)
    body = {key: assignment[key] for key in ('assignment', 'fence', 'lease_token')}
    body.update(project=c['project'], run_id=c['run_id'])
    admission = c['call']('worker_admit', c['services']['worker'], **body)
    collection = {key: body[key] for key in ('project', 'run_id', 'assignment', 'fence')}
    collection.update(effect_nonce=admission['effectNonce'], execution={'mode': 'imported',
                      'inputDigest': c['registered']['inputDigest'], 'origin': c['data']['provenance']['origin']},
                      cleanup={'mode': 'imported', 'noExecutionRequired': True})
    return assignment, body, admission, collection


def run_cases(ctx):
    checks = ctx.get('checks', {})
    with case(ctx, 'lease') as c:
        assignment, body, _, collection = claim(c)
        ctx['forbidden'].append(body['lease_token'].encode())
        old = datetime.fromisoformat(assignment['leaseExpiresAt'])
        time.sleep(.12)
        renewed = c['call']('worker_renew', c['services']['worker'], **body)
        require(datetime.fromisoformat(renewed['leaseExpiresAt']) > old, 'E_INTEGRITY')
        app = c['factory']()
        try:
            row = app.store.run(c['project'], c['run_id'])
            require(datetime.fromisoformat(renewed['leaseExpiresAt']) <= row['run_deadline'], 'E_INTEGRITY')
        finally:
            app.close()
        time.sleep(5.15)
        denied(lambda: c['call']('worker_renew', c['services']['worker'], **body), ('E_STALE',))
        late = c['call']('collector_record', c['services']['collector'], **collection)
        require(late['cleanupOnly'] and not late['accepted'], 'E_INTEGRITY')
        state = c['call']('run_read', c['admin'], project=c['project'], run_id=c['run_id'])
        require(state['state'] == 'failed' and not state['incidentOpen'], 'E_INTEGRITY')
        again = c['call']('collector_record', c['services']['collector'], **collection)
        require(again == late, 'E_INTEGRITY')
        denied(lambda: c['call']('worker_submit', c['services']['worker'], **body, assessment_digest='a' * 64), ('E_STALE',))
        checks['I11'] = {'status': 'PASS', 'healthyRenewalAdvanced': True, 'leaseExpiryOnDatabaseClock': True,
                         'lateCleanupOnly': True, 'failedHistoryPreserved': True, 'mode': 'imported'}
    with case(ctx, 'budget', lease=20, budget=5) as c:
        assignment, body, _, collection = claim(c)
        ctx['forbidden'].append(body['lease_token'].encode())
        app = c['factory']()
        try:
            run = app.store.run(c['project'], c['run_id'])
            require(run['lease_expires'] <= run['run_deadline'], 'E_INTEGRITY')
        finally:
            app.close()
        time.sleep(5.15)
        denied(lambda: c['call']('worker_renew', c['services']['worker'], **body), ('E_STALE',))
        require(c['call']('collector_record', c['services']['collector'], **collection)['cleanupOnly'], 'E_INTEGRITY')
        checks['I12'] = {'status': 'PASS', 'absoluteRunBudgetClampsLongLease': True, 'expiryNeverRevived': True, 'mode': 'imported'}
    for after_collection in (False, True):
        with case(ctx, 'cancel_after' if after_collection else 'cancel_before', lease=30) as c:
            _, body, _, collection = claim(c)
            ctx['forbidden'].append(body['lease_token'].encode())
            if after_collection:
                c['call']('collector_record', c['services']['collector'], **collection)
            snapshot = c['call']('run_read', c['admin'], project=c['project'], run_id=c['run_id'])
            # Reusing the start idempotency key for a cancel must conflict, not perform a second command.
            denied(lambda: c['call']('run_cancel', c['admin'], project=c['project'], run_id=c['run_id'],
                   key='start', grant=c['grant'], expected_version=snapshot['stateVersion']), ('E_CONFLICT',))
            cancelled = c['call']('run_cancel', c['admin'], project=c['project'], run_id=c['run_id'],
                                key='cancel', grant=c['grant'], expected_version=snapshot['stateVersion'])
            require(cancelled['state'] == ('cancelled' if after_collection else 'stopping'), 'E_INTEGRITY')
            if not after_collection:
                late = c['call']('collector_record', c['services']['collector'], **collection)
                require(late['cleanupOnly'] and not late['accepted'], 'E_INTEGRITY')
            final = c['call']('run_read', c['admin'], project=c['project'], run_id=c['run_id'])
            require(final['state'] == 'cancelled' and not final['incidentOpen'], 'E_INTEGRITY')
            accepted = dict(project=c['project'], run_id=c['run_id'], assignment=body['assignment'], fence=body['fence'],
                            effect_nonce=collection['effect_nonce'], bundle=c['data']['bundle'], assessment=c['data']['assessment'],
                            bundle_digest=digest(c['data']['bundle']), assessment_digest=digest(c['data']['assessment']),
                            execution_digest=digest(collection['execution']))
            denied(lambda: c['call']('assessment_accept', c['services']['assessor'], **accepted), ('E_STALE',))
            checks['I13b' if after_collection else 'I13a'] = {'status': 'PASS', 'cancelAfterCollection': after_collection,
                'terminalOnlyAfterIndependentCleanup': True, 'startKeyCannotCancel': True, 'noAssessmentRevival': True, 'mode': 'imported'}
    with case(ctx, 'revoke', lease=30) as c:
        _, body, _, collection = claim(c)
        ctx['forbidden'].append(body['lease_token'].encode())
        c['call']('service_revoke', c['admin'], service='worker')
        denied(lambda: c['call']('worker_renew', c['services']['worker'], **body), ('E_AUTH',))
        late = c['call']('collector_record', c['services']['collector'], **collection)
        require(late['cleanupOnly'] and not late['accepted'], 'E_INTEGRITY')
        require(c['call']('run_read', c['admin'], project=c['project'], run_id=c['run_id'])['state'] == 'failed', 'E_INTEGRITY')
        checks['I14'] = {'status': 'PASS', 'revokedAssignedWorkerBlocksProgress': True,
                         'independentCollectorMayResolveCleanupOnly': True, 'mode': 'imported'}
    with case(ctx, 'stale_config', config_version=1) as c:
        denied(lambda: c['call']('run_start', c['admin'], **c['start']), ('E_STALE',))
        checks['I15'] = {'status': 'PASS', 'staleInputConfigCannotStartUnderNewPolicy': True}
    return checks
