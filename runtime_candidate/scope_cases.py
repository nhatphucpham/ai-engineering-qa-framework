"""Live project-source scope checks for both intake kinds and imported publication."""
from contextlib import closing

from .common import digest, require
from .contracts import safe_run
from .fixture_import import TEXT_IDS
from .lifecycle_cases import case, denied
from .process_cases import _accepted


def _assert_scope(c, allowed):
    params = c['intake_params']
    config = c['call']('project_read', c['admin'], project=c['project'])
    with closing(c['factory']()) as app:
        snapshot = app.store.snapshot(c['project'], params['snapshot_ref'])
    target = snapshot['manifest']['coreTarget']
    require((config['configVersion'], config['policyVersion']) == (2, 2)
            and (target['projectConfigVersion'], target['dataPolicyVersion']) == (2, 2)
            and config['config']['sourceIds'] == sorted(allowed)
            and snapshot['manifest']['reportSourceIds'] == sorted(TEXT_IDS)
            and (snapshot['kind'], snapshot['candidate_digest'], snapshot['input_digest']) ==
            (params['kind'], params['candidate_digest'], params['input_digest']), 'E_INTEGRITY')
    return set(snapshot['manifest']['sourceIds'])


def _counts(c):
    # Each case owns an isolated schema. Count the entire graph, including side effects.
    tables = ('intakes', 'runs', 'receipts', 'events', 'executions', 'assessments', 'reports')
    with closing(c['factory']()) as app:
        return {table: app.conn.execute(f'SELECT count(*) AS n FROM rt_{table}').fetchone()['n']
                for table in tables}


def _legacy_intake(c):
    """Install the state an older implementation could leave, using operator fixture SQL."""
    p = c['intake_params']
    intake_id = c['start']['intake_id']
    result = {'intakeId': intake_id, 'candidateDigest': p['candidate_digest'], 'inputDigest': p['input_digest']}
    with closing(c['factory']()) as app, app.store.unit(c['admin'], write=True) as (actor, _):
        app.conn.execute('INSERT INTO rt_intakes VALUES(%s,%s,%s,%s,%s)',
                         (p['project'], intake_id, p['snapshot_ref'], p['kind'], actor['id']))
        app.store.save_receipt(actor, p['project'], 'intake_snapshot', p['key'], p, result)


def _legacy_queue(c):
    """Install one preexisting queued run, initial outbox event and command receipt."""
    project, run_id = c['project'], c['run_id']
    with closing(c['factory']()) as app, app.store.unit(write=True):
        inserted = app.conn.execute('''INSERT INTO rt_runs(project,id,snapshot,owner,grant_id,user_epoch,
            config_version,policy_version,state)
            SELECT project,%s,%s,user_id,id,user_epoch,config_version,policy_version,'queued'
            FROM rt_grants WHERE project=%s AND id=%s AND config_version=2 AND policy_version=2 AND NOT revoked''',
            (run_id, c['intake_params']['snapshot_ref'], project, c['grant']))
        require(inserted.rowcount == 1, 'E_INTEGRITY')
        app.store.event(app.store.run(project, run_id), 'run_state', {'state': 'queued'})
        run = app.store.run(project, run_id)
        app.store.save_receipt({'id': run['owner']}, project, 'run_start', c['start']['key'], c['start'],
                               dict(safe_run(run), accepted=True))


def _negative(ctx, kind):
    omitted = 'artifact-1'
    allowed = TEXT_IDS - {omitted}
    with case(ctx, 'source_scope_' + kind, source_ids=sorted(allowed), intake=False, kind=kind) as c:
        require(omitted in _assert_scope(c, allowed), 'E_INTEGRITY')
        empty = _counts(c)
        require(not any(empty.values()), 'E_INTEGRITY')
        intake = lambda: c['call']('intake_snapshot', c['admin'], **c['intake_params'])
        intake_code = denied(intake, ('E_DENIED',))
        require(_counts(c) == empty, 'E_INTEGRITY')

        _legacy_intake(c)
        legacy = dict(empty, intakes=1, receipts=1)
        require(_counts(c) == legacy, 'E_INTEGRITY')
        replay_code = denied(intake, ('E_DENIED',))
        start = lambda: c['call']('run_start', c['admin'], **c['start'])
        start_code = denied(start, ('E_DENIED',))
        require(_counts(c) == legacy, 'E_INTEGRITY')

        _legacy_queue(c)
        queued = dict(legacy, runs=1, events=1, receipts=2)
        require(_counts(c) == queued, 'E_INTEGRITY')
        project, run_id = c['project'], c['run_id']
        with closing(c['factory']()) as app:
            before = app.store.run(project, run_id)
        require((before['state'], before['version'], before['sequence'], before['attempt'],
                 before['assignment'], before['effect_nonce']) == ('queued', 1, 1, 0, None, None), 'E_INTEGRITY')
        start_replay_code = denied(start, ('E_DENIED',))
        claim_code = denied(lambda: c['call']('worker_claim', c['services']['scheduler'], project=project,
                           run_id=run_id, worker='worker', expected_run_version=1), ('E_DENIED',))
        with closing(c['factory']()) as app:
            require(app.store.run(project, run_id) == before, 'E_INTEGRITY')
        require(_counts(c) == queued, 'E_INTEGRITY')
        return {'status': 'PASS', 'kind': kind, 'configVersion': 2, 'policyVersion': 2,
                'omittedRequiredSafeSource': omitted, 'intakeReply': intake_code, 'newIntakeGraph': empty,
                'legacyStateOrigin': 'operator_fixture_sql', 'legacyIntakeReplayReply': replay_code,
                'legacyStartReply': start_code, 'legacyStartReplayReply': start_replay_code, 'legacyClaimReply': claim_code,
                'legacyIntakeGraphUnchanged': True, 'legacyQueuedRunAndGraphUnchanged': True}


def _positive(ctx):
    optional = 'fixture-optional-safe'
    excluded = {'vf1-execution-record': 'restricted', 'vf1-coverage-policy': 'restricted',
                'fixture-raw-canary': 'raw_secret', 'fixture-taint-canary': 'tainted', optional: 'safe_source'}
    with case(ctx, 'source_scope_positive', lease=90, budget=180, source_ids=sorted(TEXT_IDS),
              include_canaries=True, extra_sources={optional: (b'M50 optional source\n', 'safe_source', 'm50-scope-v1')}) as c:
        registered = _assert_scope(c, TEXT_IDS)
        require(registered - TEXT_IDS == excluded.keys(), 'E_INTEGRITY')
        with closing(c['factory']()) as app:
            sources = app.conn.execute('SELECT id,classification FROM rt_sources').fetchall()
        require({row['id']: row['classification'] for row in sources} ==
                dict.fromkeys(TEXT_IDS, 'safe_source') | excluded, 'E_INTEGRITY')
        body = _accepted(ctx, c)
        result = c['call']('worker_submit', c['services']['worker'], **body)
        scope = {'project': c['project'], 'run_id': c['run_id']}
        report = c['call']('report_read', c['admin'], **scope)
        events = c['client'].events(c['project'], c['run_id'], c['admin'], after=0)
        ready = [row for row in events if row['event'] == 'report_ready']
        linked = {link['artifactId'] for group in report['sourceLinks'] for link in group['links'] if 'artifactId' in link}
        require(result['state'] == 'completed' and result['reportId'] == report['reportId']
                and digest(report['view']) == report['viewSha256']
                and linked and linked <= TEXT_IDS and len(ready) == 1
                and ready[0]['data']['reportId'] == result['reportId'], 'E_INTEGRITY')
        return {'status': 'PASS', 'mode': 'imported', 'configVersion': 2, 'policyVersion': 2,
                'requiredSafeSources': sorted(TEXT_IDS), 'registeredIdsExcludedFromPolicy': excluded,
                'reportReadyEvents': len(ready), 'viewDigest': report['viewSha256']}


def run_cases(ctx):
    checks = ctx['checks']
    checks['I25a'] = _negative(ctx, 'repo_task')
    checks['I25b'] = _negative(ctx, 'handoff')
    checks['I26'] = _positive(ctx)
    return checks
