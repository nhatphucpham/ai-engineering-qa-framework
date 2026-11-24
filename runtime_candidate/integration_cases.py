"""Serialized integration campaign extensions. Call only on an isolated operator-owned fixture."""
import base64
import http.client
import multiprocessing
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager

from .common import VERSION, Error, canonical, require, sha, strict_json
from .fixture_import import load_hc1
from .transport import CHUNK_SIZE, CandidateClient, serve


def _denied(code, function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except Error as exc:
        require(exc.code == code, 'E_INTEGRITY')
        return
    raise AssertionError('Expected fixed error ' + code)


def _account(ctx, name, role):
    call, admin = ctx['call'], ctx['admin']
    initial, changed = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    ctx['forbidden'].extend((initial.encode(), changed.encode()))
    call('account_create', admin, user=name, password=initial)
    restricted = call('session_login', user=name, password=initial)
    ctx['forbidden'].extend(restricted[key].encode() for key in ('access', 'refresh'))
    _denied('E_AUTH', call, 'session_read', restricted['access'])
    call('session_change_password', restricted['access'], old=initial, new=changed)
    session = call('session_login', user=name, password=changed)
    ctx['forbidden'].extend(session[key].encode() for key in ('access', 'refresh'))
    call('account_set_role', admin, project=ctx['project'], user=name, role=role)
    return session['access']


def _start_client(pipe, port, cert):
    """Spawn target. Send credentials through the private parent pipe, never a CLI/log."""
    with closing(pipe):
        try:
            client = CandidateClient('127.0.0.1', port, cert, timeout=30)
            pipe.send('ready')
            token, body = pipe.recv()
            pipe.send(('ok', client.call('run_start', token, body)))
        except Exception:
            pipe.send(('error', None))


def _race_start(ctx, token, body):
    spawn = multiprocessing.get_context('spawn')
    children, pipes = [], []
    with closing(ctx['factory']()) as blocker, closing(ctx['factory']()) as observer:
        try:
            for _ in range(2):
                parent, child = spawn.Pipe()
                pipes.append(parent)
                try:
                    process = spawn.Process(target=_start_client, args=(child, ctx['server_port'], ctx['certificate']))
                    process.start()
                    children.append(process)
                finally:
                    child.close()
            for pipe in pipes:
                require(pipe.poll(30) and pipe.recv() == 'ready', 'E_DEPENDENCY')
            with blocker.identity.tx():
                holder = blocker.conn.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
                for pipe in pipes:
                    pipe.send((token, dict(body, version=VERSION)))
                deadline = time.monotonic() + 15
                # Identify both backends waiting behind this exact holder, including the
                # second client's wait on the first client's queued row lock.
                while time.monotonic() < deadline:
                    row = observer.conn.execute('''WITH RECURSIVE blocked(pid) AS (
                        SELECT %s::integer UNION
                        SELECT a.pid FROM pg_stat_activity a JOIN blocked b
                        ON b.pid=ANY(pg_blocking_pids(a.pid)) WHERE a.datname=current_database()
                    ) SELECT count(*)-1 AS waiters FROM blocked''', (holder,)).fetchone()
                    if row['waiters'] == 2:
                        break
                    time.sleep(0.025)
                else:
                    raise AssertionError('Both request backends did not reach the held control lock')
            replies = []
            for pipe in pipes:
                require(pipe.poll(30), 'E_DEPENDENCY')
                status, result = pipe.recv()
                require(status == 'ok', 'E_INTEGRITY')
                replies.append(result)
            require(replies[0] == replies[1] and replies[0]['state'] == 'queued'
                    and replies[0]['sequenceWatermark'] == 1 and replies[0]['runId'] == body['run_id'], 'E_INTEGRITY')
            for process in children:
                process.join(10)
                require(process.exitcode == 0, 'E_DEPENDENCY')
        finally:
            for pipe in pipes:
                pipe.close()
            for process in children:
                if process.is_alive():
                    process.terminate()
                process.join(10)
                if not process.is_alive():
                    process.close()
        counts = observer.conn.execute('''SELECT
            (SELECT count(*) FROM rt_runs WHERE project=%s AND id=%s) AS runs,
            (SELECT count(*) FROM rt_events WHERE project=%s AND run_id=%s) AS events,
            (SELECT count(*) FROM rt_receipts WHERE actor=%s AND project=%s AND key=%s AND operation='run_start') AS receipts''',
            (body['project'], body['run_id'], body['project'], body['run_id'], 'runnerCase', body['project'], body['key'])).fetchone()
        require(counts == {'runs': 1, 'events': 1, 'receipts': 1}, 'E_INTEGRITY')
        return counts


def _wire(ctx, token, method, target, body=None, *, port=None):
    endpoint = port or ctx['server_port']
    headers = {'Host': f'127.0.0.1:{endpoint}', 'Authorization': 'Bearer ' + token}
    payload = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        payload = canonical(dict(body, version=VERSION))
    with closing(http.client.HTTPSConnection('127.0.0.1', endpoint, context=ctx['client'].tls, timeout=30)) as connection:
        connection.request(method, target, body=payload, headers=headers)
        with closing(connection.getresponse()) as response:
            return response.status, response.read()


def _race_and_cancel(ctx, runner, second, viewer):
    call, project = ctx['call'], ctx['project']
    data = load_hc1('b', include_canaries=True)
    run_id = data['run_id']
    with closing(ctx['factory']()) as app:
        registration = app.register_snapshot(project, 'snapshot_b', 'handoff', data['bundle'],
                                             sources=data['sources'], mode='imported', manifest=data['provenance'])
    grants = [call('grant_issue', token, project=project, expected_config=2,
                   actions=['start', 'cancel'])['grant'] for token in (runner, second)]
    ctx['forbidden'].extend(grant.encode() for grant in grants)
    intake = call('intake_snapshot', runner, project=project, key='intake_b', kind='handoff', snapshot_ref='snapshot_b',
                  candidate_digest=registration['candidateDigest'], input_digest=registration['inputDigest'], expected_config=2)
    body = dict(project=project, run_id=run_id, grant=grants[0], expected_config=2, intake_id=intake['intakeId'], key='start_b')
    counts = _race_start(ctx, runner, body)
    scope = dict(project=project, run_id=run_id)
    _denied('E_DENIED', call, 'grant_issue', viewer, project=project, expected_config=2, actions=['cancel'])
    _denied('E_DENIED', call, 'run_cancel', second, **scope, grant=grants[1], key='foreign_cancel', expected_version=1)
    cancelled = call('run_cancel', runner, **scope, key='cancel_b', grant=grants[0], expected_version=1)
    require(cancelled['state'] == 'cancelled' and cancelled['sequenceWatermark'] == 2, 'E_INTEGRITY')
    events = ctx['client'].events(project, run_id, runner)
    require([(e['id'], e['data']['state']) for e in events] == [(1, 'queued'), (2, 'cancelled')], 'E_INTEGRITY')
    history = ctx['client'].events(project, ctx['run_id'], viewer)
    require(history[-1]['event'] == 'report_ready' and history[-1]['id'] > 2, 'E_INTEGRITY')
    _denied('E_RESYNC_REQUIRED', ctx['client'].events, project, run_id, runner, history[-1]['id'])
    require(ctx['client'].events(project, run_id, runner, 1) == events[1:]
            and ctx['client'].events(project, run_id, runner, 2) == [], 'E_INTEGRITY')
    meta = {'status': 'PASS', 'inputKind': 'historical_handoff', 'separateClientProcesses': 2,
            'requestBackendsObservedWaiting': 2, 'beforeCancelCounts': counts,
            'foreignRunnerCancelDenied': True, 'ownerRunnerCancelState': cancelled['state'],
            'separateRunWatermarks': [history[-1]['id'], events[-1]['id']]}
    return meta, body


def _follow_sources(ctx, viewer):
    scope = dict(project=ctx['project'], run_id=ctx['run_id'])
    report = ctx['call']('report_read', viewer, **scope)
    outcomes = {e['id']: e['outcome'] for e in report['view']['sources']}
    groups = {g['criterionId']: g['links'] for g in report['sourceLinks']}
    expected = {('test_ui_select_from_first_page', 'pass'), ('test_reset_from_third_page', 'fail'),
                ('test_reset_with_recorded_api_call', 'fail')}
    resolved = []
    for criterion in report['view']['criteria']:
        links = groups[criterion['criterionId']]
        claim = next(link for link in links if link['kind'] == 'requirement')
        source = ctx['call']('source_read', viewer, **scope, artifact_id=claim['artifactId'])
        require(sha(source['text'].encode()) == claim['sha256'] and source['revision'] == claim['revision']
                and claim['locator'] in source['text'], 'E_INTEGRITY')
        if claim['locator'] != 'AC-02':
            continue
        for alias in criterion['evidenceIds']:
            matches = [link for link in links if link['kind'] == 'check_definition' and link['evidenceId'] == alias]
            require(len(matches) == 1, 'E_INTEGRITY')
            link = matches[0]
            source = ctx['call']('source_read', viewer, **scope, artifact_id=link['artifactId'])
            raw = source['text'].encode()
            require(sha(raw) == source['sha256'] == link['sha256'] and source['revision'] == link['revision'], 'E_INTEGRITY')
            first = int(link['locator'].split('-')[0][1:])
            method = source['text'].splitlines()[first - 1].strip().removeprefix('def ').split('(')[0]
            resolved.append((method, outcomes[alias]))
    require(len(resolved) == 3 and set(resolved) == expected, 'E_INTEGRITY')
    return {'status': 'PASS', 'criterionRequirementLinksFollowed': len(report['view']['criteria']),
            'checkDefinitionsFollowed': len(resolved), 'approvedBytesAndRevisionMatched': True,
            'matchingObservedCheckOutcomes': ['pass', 'fail', 'fail']}


def _restricted_routes(ctx, roles):
    scope = dict(project=ctx['project'], run_id=ctx['run_id'])
    canaries = ('fixture-raw-canary', 'fixture-taint-canary')
    denied_bytes = []
    for aid in canaries:
        raw, _, _ = ctx['dataA']['sources'][aid]
        denied_bytes.extend([raw, base64.b64encode(raw), raw.hex().encode()])
    total = label_checks = scanned_bodies = 0
    for token in roles.values():
        ordinary = [_wire(ctx, token, 'POST', '/v1/' + op, scope) for op in ('report_read', 'report_export')]
        stream = f"/v1/events?project={scope['project']}&run={scope['run_id']}&after=0"
        ordinary.append(_wire(ctx, token, 'GET', stream))
        for status, raw in ordinary:
            require(status == 200 and raw and not any(marker in raw for marker in denied_bytes), 'E_INTEGRITY')
            scanned_bodies += 1
        for aid in canaries:
            request = dict(scope, artifact_id=aid)
            _denied('E_DENIED', ctx['call'], 'source_read', token, **request)
            for label in ('redacted', 'authorized'):
                _denied('E_INPUT', ctx['call'], 'source_read', token, **request, **{label: True})
                label_checks += 1
            for op in ('report_read', 'report_export', 'events'):
                fields = dict(request, after=0) if op == 'events' else request
                _denied('E_INPUT', ctx['call'], op, token, **fields)
            status, body = _wire(ctx, token, 'POST', '/v1/attachment', request)
            require(status == 404 and strict_json(body) == {'error': 'E_ROUTE'}, 'E_INTEGRITY')
            total += 5
    return {'status': 'PASS', 'roles': sorted(roles), 'canaryClassifications': ['raw_secret', 'tainted'],
            'routeChecks': total, 'sourceRead': 'E_DENIED', 'reportExportAndEventsExtraSelector': 'E_INPUT',
            'attachmentRoute': 'not_exposed_HTTP404', 'extraLabelInputRejections': label_checks,
            'rawJsonAndSseBodiesScanned': scanned_bodies, 'canaryRepresentationsAbsent': ['raw', 'base64', 'hex']}


@contextmanager
def _gated_server(ctx, op, ordinal):
    paused, resume, denied = threading.Event(), threading.Event(), threading.Event()

    class Gate:
        def __init__(self):
            self.app = ctx['factory']()
            self.dispatch = self.app.dispatch
            self.close = self.app.close
            self.index = 0

        @contextmanager
        def release_unit(self, operation, token, body, result):
            self.index += 1
            gated = operation == op and self.index == ordinal
            if gated:
                paused.set()  # No application unit/DB lock held at the pause.
                require(resume.wait(20), 'E_DEPENDENCY')
            try:
                with self.app.release_unit(operation, token, body, result):
                    yield
            except Error as exc:
                if gated and exc.code in ('E_DENIED', 'E_STALE'):
                    denied.set()
                raise

    server = serve(Gate, ctx['certificate'], ctx['private_key'])
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.025})
    thread.start()
    try:
        yield server.server_address[1], paused, resume, denied
    finally:
        resume.set()
        server.shutdown()
        server.server_close()
        thread.join(5)
        require(not thread.is_alive(), 'E_DEPENDENCY')


def _revoke_during_read(ctx, viewer):
    scope = dict(project=ctx['project'], run_id=ctx['run_id'], artifact_id='fixture-long-safe')
    expected = canonical(ctx['call']('source_read', viewer, **scope))
    require(len(expected) > CHUNK_SIZE and ctx['dataA']['sources']['fixture-long-safe'][0] ==
            b'SAFE-M50-LINE\n' * 1500, 'E_INTEGRITY')
    actual = {}
    for op, ordinal, fields in [('source_read', 3, scope), ('project_list', 1, {})]:
        with ThreadPoolExecutor(max_workers=1) as pool, _gated_server(ctx, op, ordinal) as (port, pause, resume, denied):
            future = pool.submit(_wire, ctx, viewer, 'POST', '/v1/' + op, fields, port=port)
            try:
                require(pause.wait(15), 'E_DEPENDENCY')
                ctx['call']('account_set_role', ctx['admin'], project=ctx['project'], user='viewerCase', role=None)
            finally:
                resume.set()
            try:
                if op == 'source_read':
                    try:
                        future.result(timeout=20)
                    except http.client.IncompleteRead as exc:
                        require(exc.partial == expected[:CHUNK_SIZE] and exc.expected == len(expected) - CHUNK_SIZE,
                                'E_INTEGRITY')
                        actual['sourceBytesBeforeDenial'] = len(exc.partial)
                    else:
                        raise AssertionError('Revoked source response was complete')
                else:
                    status, raw = future.result(timeout=20)
                    require(status == 409 and strict_json(raw) == {'error': 'E_STALE'}, 'E_INTEGRITY')
                    actual['staleProjectListDeniedBeforeHeaders'] = True
                require(denied.wait(2), 'E_INTEGRITY')
                require(ctx['project'] not in ctx['call']('project_list', viewer)['projects'], 'E_INTEGRITY')
            finally:
                ctx['call']('account_set_role', ctx['admin'], project=ctx['project'], user='viewerCase', role='Viewer')
    return dict(actual, status='PASS', partialSourceRejected=True, independentRevocationClient=True)


def _toggle(ctx, owner, runner, start):
    call, project = ctx['call'], ctx['project']
    disabled = call('project_configure', owner, project=project, expected_config=2, config=dict(ctx['config'], enabled=False))
    require(disabled == {'configVersion': 3, 'policyVersion': 3}, 'E_INTEGRITY')
    _denied('E_DENIED', call, 'project_read', ctx['admin'], project=project)
    _denied('E_DENIED', call, 'run_start', runner, **start)
    require(project not in call('project_list', owner)['projects'], 'E_INTEGRITY')
    enabled = call('project_configure', ctx['admin'], project=project, expected_config=3, config=dict(ctx['config'], enabled=True))
    require(enabled == {'configVersion': 4, 'policyVersion': 4}, 'E_INTEGRITY')
    require(project in call('project_list', owner)['projects'] and
            call('project_read', owner, project=project)['configVersion'] == 4, 'E_INTEGRITY')
    _denied('E_DENIED', call, 'run_start', runner, **start)
    return {'status': 'PASS', 'disabledAt': disabled['configVersion'], 'restoredAt': enabled['configVersion'],
            'disabledProjectHiddenAndReadsDenied': True, 'oldGrantDeniedAfterEnable': True}


def run_cases(ctx):
    """Use the caller's serial disposable campaign. Return evidence without credentials or content."""
    owner = _account(ctx, 'ownerCase', 'Owner')
    runner = _account(ctx, 'runnerCase', 'Runner')
    second = _account(ctx, 'runnerTwoCase', 'Runner')
    viewer = _account(ctx, 'viewerCase', 'Viewer')
    race, start = _race_and_cancel(ctx, runner, second, viewer)
    result = {'I06': race}
    ctx.get('checks', {}).update(result)
    for key, action in [('I07', lambda: _follow_sources(ctx, viewer)),
                        ('I08', lambda: _restricted_routes(ctx, {'Admin': ctx['admin'], 'Owner': owner, 'Runner': runner, 'Viewer': viewer})),
                        ('I09', lambda: _revoke_during_read(ctx, viewer)),
                        ('I10', lambda: _toggle(ctx, owner, runner, start))]:
        result[key] = action()
        ctx.get('checks', {}).update({key: result[key]})
    return result
