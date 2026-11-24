"""Process-loss acceptance on isolated imported lifecycle fixtures. Operator orchestrates serially."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
import http.client
import multiprocessing
import os
import ssl
import time
from unittest.mock import patch

from .application import Application
from .common import VERSION, Error, digest, require, strict_json
from .lifecycle_cases import case, claim, denied
from .publication import prepare
from .transport import CandidateClient, serve


def _fault_server(pipe):
    """Bootstrap over a private pipe; fault selection is never an HTTP input."""
    with closing(pipe):
        schema, root, cert, key, point = pipe.recv()
        def notify(stage):
            if point == 'partial_stage' and stage == 'publication_stage_begin':
                from . import blobs
                original = blobs._write
                def stop_mid_write(stream, raw):
                    count = len(raw) // 2
                    require(0 < count < len(raw), 'E_INTEGRITY')
                    original(stream, raw[:count])  # includes flush and fsync
                    pipe.send(('hit', point))
                    os._exit(72)
                blobs._write = stop_mid_write
            elif point == 'deadline_after_witness' and stage == 'authority_witness_written':
                pipe.send(('hit', point))
                require(pipe.poll(20) and pipe.recv() == 'release', 'E_DEPENDENCY')
            elif stage == point:
                pipe.send(('hit', point))
                os._exit(72)
        factory = lambda: Application(schema, root, observer=notify)
        with serve(factory, cert, key) as server:
            pipe.send(('ready', server.server_address[1]))
            server.handle_request()  # One request only. server_close joins its handler.


@contextmanager
def _isolated_api(ctx, c, point):
    spawn = multiprocessing.get_context('spawn')
    parent, child = spawn.Pipe()
    with closing(parent), closing(child):
        process = spawn.Process(target=_fault_server, args=(child,))
        process.start()
        child.close()
        try:
            parent.send((c['schema'], c['state_root'], ctx['certificate'], ctx['private_key'], point))
            require(parent.poll(30), 'E_DEPENDENCY')
            status, port = parent.recv()
            require(status == 'ready', 'E_DEPENDENCY')
            client = CandidateClient('127.0.0.1', port, ctx['certificate'], timeout=25)
            yield client, parent, process
        finally:
            if process.is_alive():
                process.terminate()
            process.join(10)
            require(not process.is_alive(), 'E_DEPENDENCY')
            process.close()


def _lose_response(ctx, c, point, operation, token, body):
    with _isolated_api(ctx, c, point) as (client, pipe, process):
        try:
            client.call(operation, token, dict(body, version=VERSION))
        except (http.client.RemoteDisconnected, ConnectionResetError, ConnectionAbortedError, ssl.SSLEOFError):
            pass
        else:
            raise AssertionError('Expected API process loss before response')
        process.join(12)
        require(process.exitcode == 72 and pipe.poll(2) and pipe.recv() == ('hit', point), 'E_INTEGRITY')


def _scope(c):
    return {'project': c['project'], 'run_id': c['run_id']}


def _request(c):
    return dict(_scope(c), worker='worker', expected_run_version=1)


def _worker_body(c, grant):
    return dict(_scope(c), **{field: grant[field] for field in ('assignment', 'fence', 'lease_token')})


def _collect(c, body, nonce):
    return dict(_scope(c), assignment=body['assignment'], fence=body['fence'], effect_nonce=nonce,
                execution={'mode': 'imported', 'inputDigest': c['registered']['inputDigest'],
                           'origin': c['data']['provenance']['origin']},
                cleanup={'mode': 'imported', 'noExecutionRequired': True})


def _accepted(ctx, c):
    _, body, admission, collection = claim(c)
    ctx['forbidden'].append(body['lease_token'].encode())
    record = c['call']('collector_record', c['services']['collector'], **collection)
    bundle, assessment = c['data']['bundle'], c['data']['assessment']
    acquired = c['call']('assessment_accept', c['services']['assessor'], **_scope(c), assignment=body['assignment'],
                         fence=body['fence'], effect_nonce=admission['effectNonce'], bundle=bundle, assessment=assessment,
                         bundle_digest=digest(bundle), assessment_digest=digest(assessment), execution_digest=record['executionDigest'])
    return dict(body, assessment_digest=acquired['assessmentDigest'])


def _graph(c):
    with closing(c['factory']()) as app:
        return app.conn.execute('''SELECT r.state,r.sequence,
            (SELECT count(*) FROM rt_reports t WHERE (t.project,t.run_id)=(r.project,r.id)) AS reports,
            (SELECT count(*) FROM rt_events e WHERE (e.project,e.run_id)=(r.project,r.id)
                AND e.event='report_ready') AS ready FROM rt_runs r WHERE r.project=%s AND r.id=%s''',
            (c['project'], c['run_id'])).fetchone()


def _committed_negative(c):
    """Model a stale SQL head only inside a rolled-back transaction in this idle case schema."""
    journal_path = c['state_root'] / 'authority-transition.json'
    head_path = c['state_root'] / 'authority.json'
    journal_bytes, head_bytes = journal_path.read_bytes(), head_path.read_bytes()
    journal, head = strict_json(journal_bytes), strict_json(head_bytes)
    require(head['nonce'] == journal['nextNonce'], 'E_INTEGRITY')
    with closing(c['factory']()) as app:
        from . import storage
        with app.conn.transaction(force_rollback=True):
            unrelated = app.conn.execute('SELECT pg_current_xact_id()::text AS xid').fetchone()['xid']
        actual = app.conn.execute('SELECT pg_xact_status(%s::xid8) AS status', (unrelated,)).fetchone()['status']
        require(unrelated != journal['xid8'] and actual == 'aborted', 'E_INTEGRITY')
        receipts = {p.name: p.read_bytes() for p in c['state_root'].glob('authority-recovery-*.json')}
        status = app.conn.execute('SELECT pg_xact_status(%s::xid8) AS s', (journal['xid8'],)).fetchone()['s']
        require(status == 'committed', 'E_INTEGRITY')
        with app.conn.transaction(force_rollback=True):
            changed = app.conn.execute('UPDATE rt_control SET nonce=%s WHERE id=1 AND nonce=%s RETURNING id',
                                       (journal['previousNonce'], journal['nextNonce'])).fetchone()
            require(changed is not None, 'E_INTEGRITY')
            denied(lambda: app.store.reconcile_aborted_transition(journal['nextNonce']), ('E_UNRESOLVED',))
            # Deliver exactly one inconsistent in-memory journal read to the real operator
            # method. Keep its independent head file unchanged and forbid every file write.
            observed = []
            def inspect_fixture_bytes(raw):
                parsed = strict_json(raw)
                if raw == journal_bytes:
                    observed.append('held_journal')
                    return dict(parsed, xid8=unrelated)
                return parsed
            with patch.object(storage, 'strict_json', side_effect=inspect_fixture_bytes), patch.object(
                    app.store, '_atomic_json', side_effect=AssertionError('Recovery attempted to write')):
                denied(lambda: app.store.reconcile_aborted_transition(head['nonce']), ('E_UNRESOLVED',))
            require(observed == ['held_journal'] and head_path.read_bytes() == head_bytes and
                    app.conn.execute('SELECT nonce FROM rt_control WHERE id=1').fetchone()['nonce'] == journal['previousNonce'],
                    'E_INTEGRITY')
        current = app.conn.execute('SELECT nonce FROM rt_control WHERE id=1').fetchone()['nonce']
        require(current == head['nonce'] and head_path.read_bytes() == head_bytes
                and journal_path.read_bytes() == journal_bytes and
                receipts == {p.name: p.read_bytes() for p in c['state_root'].glob('authority-recovery-*.json')},
                'E_INTEGRITY')


def _publication_case(ctx, point):
    with case(ctx, 'publication_' + point, lease=90, budget=180) as c:
        body = _accepted(ctx, c)
        initial = _graph(c)
        require(initial['state'] == 'analyzing' and initial['reports'] == initial['ready'] == 0, 'E_INTEGRITY')
        # Held expected bytes permit checking the exact interrupted private object after death.
        expected = prepare(c['data']['bundle'], c['data']['assessment'], expected_bundle_digest=digest(c['data']['bundle']),
                           expected_assessment_digest=body['assessment_digest'], run_id=c['run_id'], report_id='report_' + c['run_id'])
        blobs = c['state_root'] / 'blobs'
        old_stages = set(blobs.glob('.stage-*'))
        _lose_response(ctx, c, point, 'worker_submit', c['services']['worker'], body)
        result = {'status': 'PASS', 'observedProcessExit': 72, 'stage': point, 'mode': 'imported'}
        post_commit = point == 'publication_committed'
        graph = _graph(c)
        require(graph == (dict(state='completed', sequence=initial['sequence'] + 1, reports=1, ready=1)
                          if post_commit else initial), 'E_INTEGRITY')
        if point == 'partial_stage':
            stages = set(blobs.glob('.stage-*')) - old_stages
            require(len(stages) == 1, 'E_INTEGRITY')
            fragment = stages.pop().read_bytes()
            require(fragment == expected.private_bytes[:len(expected.private_bytes) // 2]
                    and not (blobs / expected.private_ref['sha256']).exists(), 'E_INTEGRITY')
            result['privateFragmentLength'] = len(fragment)
        if point in ('publication_staged', 'publication_uncommitted', 'authority_witness_written', 'publication_committed'):
            with closing(c['factory']()) as app:
                require(app.blobs.get(expected.private_ref) == expected.private_bytes
                        and app.blobs.get(expected.view_ref) == expected.view_bytes, 'E_INTEGRITY')
        if point == 'authority_witness_written':
            denied(lambda: c['call']('run_read', c['admin'], **_scope(c)), ('E_UNRESOLVED',))
            denied(lambda: c['call']('worker_submit', c['services']['worker'], **body), ('E_UNRESOLVED',))
            head = strict_json((c['state_root'] / 'authority.json').read_bytes())
            with closing(c['factory']()) as app:
                receipt = app.store.reconcile_aborted_transition(head['nonce'])
                require(receipt['recovered'] and receipt['transactionStatus'] == 'aborted'
                        and app.store.reconcile_aborted_transition(head['nonce']) == receipt, 'E_INTEGRITY')
            result.update(recovery='postgres_verified_aborted', sameRecoveryReceipt=True)
        if not post_commit:
            denied(lambda: c['call']('report_read', c['admin'], **_scope(c)), ('E_DENIED',))
        first = c['call']('worker_submit', c['services']['worker'], **body)
        duplicate = c['call']('worker_submit', c['services']['worker'], **body)
        require(first == duplicate and first['state'] == 'completed', 'E_INTEGRITY')
        require(_graph(c) == dict(state='completed', sequence=initial['sequence'] + 1, reports=1, ready=1), 'E_INTEGRITY')
        visible = c['call']('report_read', c['admin'], **_scope(c))
        require(visible['viewSha256'] == expected.view_ref['sha256'] and visible['view'] == expected.view, 'E_INTEGRITY')
        if point == 'authority_witness_written':
            _committed_negative(c)
            result['knownCommittedTransitionDenied'] = True
            result['foreignAbortedXidRejectedByPinnedBinding'] = True
        result.update(graphAfterLoss=graph, finalReportCount=1, finalReportReadyCount=1,
                      sameExplicitRetryResult=True, actualOrdinaryViewDigest=visible['viewSha256'])
        return result


def _row(c):
    with closing(c['factory']()) as app:
        return app.store.run(c['project'], c['run_id'])


def _read(c):
    return c['call']('run_read', c['admin'], **_scope(c))


def _cancel(c, version):
    return c['call']('run_cancel', c['admin'], **_scope(c), key='cancel', grant=c['grant'], expected_version=version)


def _recovery_budget(ctx, c):
    request = _request(c)
    ctx['forbidden'].append(c['call']('worker_claim', c['services']['scheduler'], **request)['lease_token'].encode())
    original = _row(c)
    for delivery in range(2, 5):
        grant = c['call']('worker_recover_claim', c['services']['scheduler'], **request)
        ctx['forbidden'].append(grant['lease_token'].encode())
        require(grant['assignment'] == original['assignment'] and grant['fence'] == original['fence'] + delivery - 1,
                'E_INTEGRITY')
    denied(lambda: c['call']('worker_recover_claim', c['services']['scheduler'], **request), ('E_BUDGET',))
    before = _row(c)
    require(before['delivery_count'] == 4 and before['attempt'] == 1 and before['sequence'] == original['sequence']
            and before['effect_nonce'] is None, 'E_INTEGRITY')
    require(_cancel(c, before['version'])['state'] == 'cancelled', 'E_INTEGRITY')
    require(c['call']('worker_recover_claim', c['services']['scheduler'], **request) == _read(c), 'E_INTEGRITY')


def _parallel(ctx, c, requests):
    """Queue both independent TLS requests, in the stated order, behind the same held DB mutex."""
    with closing(c['factory']()) as holder, closing(c['factory']()) as observer, ThreadPoolExecutor(2) as pool:
        futures = []
        with holder.identity.tx():
            pid = holder.conn.info.backend_pid
            for index, (op, token, body) in enumerate(requests):
                client = CandidateClient('127.0.0.1', c['client'].port, ctx['certificate'], timeout=30)
                futures.append(pool.submit(client.call, op, token, dict(body, version=VERSION)))
                deadline = time.monotonic() + 7
                while time.monotonic() < deadline:
                    row = observer.conn.execute('''WITH RECURSIVE blocked(pid) AS (
                        SELECT %s::integer UNION
                        SELECT a.pid FROM pg_stat_activity a JOIN blocked b
                        ON b.pid=ANY(pg_blocking_pids(a.pid)) WHERE a.datname=current_database()
                    ) SELECT count(*)-1 AS n FROM blocked''', (pid,)).fetchone()
                    if row['n'] == index + 1:
                        break
                    time.sleep(0.025)
                else:
                    raise AssertionError('Ordered clients did not reach held database mutex')
        results = []
        for future in futures:
            try:
                results.append(future.result(timeout=20))
            except Error as exc:
                results.append(exc.code)
        return results


def _lost_claim(ctx):
    with case(ctx, 'claim_lost', lease=90, budget=180) as c:
        c['call']('run_start', c['admin'], **c['start'])
        s, request = c['services'], _request(c)
        _lose_response(ctx, c, 'claim_committed', 'worker_claim', s['scheduler'], request)
        before = _row(c)
        require(before['state'] == 'collecting' and before['attempt'] == 1 and before['delivery_count'] == 1
                and before['sequence'] == 2 and before['effect_nonce'] is None, 'E_INTEGRITY')
        denied(lambda: c['call']('worker_claim', s['scheduler'], **request), ('E_STALE',))
        other = c['call']('service_enroll', c['admin'], service='schedulerTwo', kind='scheduler', projects=[c['project']])['credential']
        ctx['forbidden'].append(other.encode())
        denied(lambda: c['call']('worker_recover_claim', other, **request), ('E_DENIED',))
        denied(lambda: c['call']('worker_recover_claim', s['worker'], **request), ('E_AUTH',))
        for altered in (dict(request, worker='workerTwo'), dict(request, expected_run_version=2)):
            denied(lambda: c['call']('worker_recover_claim', s['scheduler'], **altered), ('E_DENIED',))
        pair = [('worker_recover_claim', s['scheduler'], request)] * 2
        first, second = _parallel(ctx, c, pair)
        require(isinstance(first, dict) and isinstance(second, dict), 'E_INTEGRITY')
        ctx['forbidden'].extend(g['lease_token'].encode() for g in (first, second))
        require(first['assignment'] == second['assignment'] == before['assignment']
                and first['fence'] == before['fence'] + 1 and second['fence'] == first['fence'] + 1
                and first['lease_token'] != second['lease_token'], 'E_INTEGRITY')
        row = _row(c)
        require(row['attempt'] == 1 and row['delivery_count'] == 3 and row['sequence'] == before['sequence'], 'E_INTEGRITY')
        denied(lambda: c['call']('worker_admit', s['worker'], **_worker_body(c, first)), ('E_STALE',))
        # Old plaintext is unknown after a lost response. Compare the recovered credential's
        # hash against the pre-recovery held hash without disclosing either in evidence.
        from .storage import token_digest
        require(token_digest(first['lease_token'], 'l') != before['lease_hash']
                and token_digest(second['lease_token'], 'l') == row['lease_hash'], 'E_INTEGRITY')
        require(_cancel(c, row['version'])['state'] == 'cancelled', 'E_INTEGRITY')
        return {'status': 'PASS', 'processExit': 72, 'ordinaryRetry': 'E_STALE', 'competingRecoveryClients': 2,
                'deliveries': row['delivery_count'], 'attempts': row['attempt'], 'newClaimEvents': 0,
                'wrongAudienceAndBoundFieldsDenied': True, 'supersededRecoveredLeaseDenied': True}


def _admission_orders(ctx, recovering_first):
    with case(ctx, 'admission_' + ('recovery_first' if recovering_first else 'admit_first'), lease=60, budget=180) as c:
        c['call']('run_start', c['admin'], **c['start'])
        request, s = _request(c), c['services']
        grant = c['call']('worker_claim', s['scheduler'], **request)
        ctx['forbidden'].append(grant['lease_token'].encode())
        body = _worker_body(c, grant)
        admission = ('worker_admit', s['worker'], body)
        recover = ('worker_recover_claim', s['scheduler'], request)
        if recovering_first:
            rotated, stale = _parallel(ctx, c, [recover, admission])
            require(isinstance(rotated, dict) and stale == 'E_STALE', 'E_INTEGRITY')
            ctx['forbidden'].append(rotated['lease_token'].encode())
            require(rotated['assignment'] == grant['assignment'] and rotated['fence'] == grant['fence'] + 1
                    and rotated['lease_token'] != grant['lease_token'] and _row(c)['effect_nonce'] is None, 'E_INTEGRITY')
            body = _worker_body(c, rotated)
            admitted = c['call']('worker_admit', s['worker'], **body)
        else:
            admitted, blocked = _parallel(ctx, c, [admission, recover])
            require(isinstance(admitted, dict) and blocked == 'E_UNRESOLVED', 'E_INTEGRITY')
        row = _row(c)
        require(row['effect_nonce'] == admitted['effectNonce'] and row['attempt'] == 1 and row['incident'], 'E_INTEGRITY')
        require(_cancel(c, row['version'])['state'] == 'stopping', 'E_INTEGRITY')
        record = c['call']('collector_record', s['collector'], **_collect(c, body, admitted['effectNonce']))
        require(record['cleanupOnly'] and not record['accepted'] and _read(c)['state'] == 'cancelled', 'E_INTEGRITY')
        terminal = c['call']('worker_recover_claim', s['scheduler'], **request)
        require(terminal == _read(c) and 'lease_token' not in terminal, 'E_INTEGRITY')
        return {'status': 'PASS', 'databaseWaiters': 2, 'recoveryBeforeAdmit': recovering_first,
                'oneAttempt': True, 'supersededAdmitOrPostEffectRecoveryDenied': True, 'terminalWithoutGrant': True}


def _expiry(ctx):
    with case(ctx, 'claim_expired', lease=5, budget=180) as c:
        c['call']('run_start', c['admin'], **c['start'])
        request = _request(c)
        grant = c['call']('worker_claim', c['services']['scheduler'], **request)
        ctx['forbidden'].append(grant['lease_token'].encode())
        before = _row(c)
        with closing(c['factory']()) as app:
            delay = app.conn.execute('SELECT GREATEST(0,extract(epoch FROM %s-clock_timestamp())) AS seconds',
                                     (before['lease_expires'],)).fetchone()['seconds']
            time.sleep(float(delay) + 0.1)
        failed = c['call']('worker_recover_claim', c['services']['scheduler'], **request)
        again = c['call']('worker_recover_claim', c['services']['scheduler'], **request)
        after = _row(c)
        require(failed == again == _read(c) and failed['state'] == 'failed' and 'lease_token' not in failed
                and after['effect_nonce'] is None and after['effect_state'] == 'not_admitted'
                and after['attempt'] == 1 and after['sequence'] == before['sequence'] + 1, 'E_INTEGRITY')
        events = c['client'].events(c['project'], c['run_id'], c['admin'], before['sequence'])
        require(len(events) == 1 and events[0]['data']['reason'] == 'claim_authority_expired_before_effect', 'E_INTEGRITY')
        return {'status': 'PASS', 'expiredOnDbClock': True, 'unadmittedFailedEvents': 1, 'terminalReplyHasNoGrant': True}


def _cancel_orders(ctx, cancel_first):
    with case(ctx, 'cancel_claim_' + ('cancel_first' if cancel_first else 'claim_first'), lease=60, budget=180) as c:
        c['call']('run_start', c['admin'], **c['start'])
        claim_request = ('worker_claim', c['services']['scheduler'], _request(c))
        cancel = ('run_cancel', c['admin'], dict(_scope(c), key='first_cancel', grant=c['grant'], expected_version=1))
        winner, loser = _parallel(ctx, c, [cancel, claim_request] if cancel_first else [claim_request, cancel])
        require(isinstance(winner, dict) and loser == 'E_STALE', 'E_INTEGRITY')
        if cancel_first:
            require(winner['state'] == 'cancelled' and _row(c)['attempt'] == 0, 'E_INTEGRITY')
        else:
            ctx['forbidden'].append(winner['lease_token'].encode())
            row = _row(c)
            require(winner['assignment'] == row['assignment'] and row['attempt'] == 1, 'E_INTEGRITY')
            require(_cancel(c, row['version'])['state'] == 'cancelled', 'E_INTEGRITY')
        require(_read(c)['state'] == 'cancelled' and _row(c)['effect_nonce'] is None, 'E_INTEGRITY')
        return {'status': 'PASS', 'databaseWaiters': 2, 'cancelFirst': cancel_first,
                'staleCasDenied': True, 'noAdmittedEffect': True}


def _parallel_publication(ctx):
    with case(ctx, 'double_submit', lease=90, budget=180) as c:
        body = _accepted(ctx, c)
        before = _graph(c)
        require(before['state'] == 'analyzing' and before['reports'] == before['ready'] == 0, 'E_INTEGRITY')
        submit = ('worker_submit', c['services']['worker'], body)
        first, second = _parallel(ctx, c, [submit, submit])
        require(isinstance(first, dict) and first == second and first['state'] == 'completed', 'E_INTEGRITY')
        after = _graph(c)
        require(after == dict(state='completed', sequence=before['sequence'] + 1, reports=1, ready=1), 'E_INTEGRITY')
        report = c['call']('report_read', c['admin'], **_scope(c))
        require(first['reportId'] == report['reportId'] and digest(report['view']) == report['viewSha256'], 'E_INTEGRITY')
        events = c['client'].events(c['project'], c['run_id'], c['admin'], before['sequence'])
        require(len(events) == 1 and events[0]['event'] == 'report_ready'
                and events[0]['data']['reportId'] == report['reportId'], 'E_INTEGRITY')
        return {'status': 'PASS', 'databaseWaiters': 2, 'identicalSubmitReceipts': True,
                'reportRows': after['reports'], 'reportReadyEvents': len(events), 'viewDigest': report['viewSha256']}


def _revoke_before_publication(ctx):
    with case(ctx, 'revoke_submit', lease=90, budget=180) as c:
        body = _accepted(ctx, c)
        before = _graph(c)
        require(before['state'] == 'analyzing' and before['reports'] == before['ready'] == 0, 'E_INTEGRITY')
        expected = prepare(c['data']['bundle'], c['data']['assessment'], expected_bundle_digest=digest(c['data']['bundle']),
                           expected_assessment_digest=body['assessment_digest'], run_id=c['run_id'], report_id='report_' + c['run_id'])
        blob_root = c['state_root'] / 'blobs'
        package_paths = [blob_root / ref['sha256'] for ref in (expected.private_ref, expected.view_ref)]
        require(all(not p.exists() for p in package_paths), 'E_INTEGRITY')
        revoked, submit = _parallel(ctx, c, [
            ('grant_revoke', c['admin'], {'project': c['project'], 'grant': c['grant']}),
            ('worker_submit', c['services']['worker'], body)])
        require(revoked == {'revoked': True} and submit == 'E_DENIED' and _graph(c) == before
                and all(not p.exists() for p in package_paths), 'E_INTEGRITY')
        denied(lambda: c['call']('report_read', c['admin'], **_scope(c)), ('E_DENIED',))
        require(c['client'].events(c['project'], c['run_id'], c['admin'], before['sequence']) == [], 'E_INTEGRITY')
        replacement = c['call']('grant_issue', c['admin'], project=c['project'], expected_config=2, actions=['cancel'])
        ctx['forbidden'].append(replacement['grant'].encode())
        terminal = c['call']('run_cancel', c['admin'], **_scope(c), grant=replacement['grant'], key='cleanup',
                             expected_version=_read(c)['stateVersion'])
        require(terminal['state'] == 'cancelled' and not terminal['incidentOpen'], 'E_INTEGRITY')
        return {'status': 'PASS', 'databaseWaiters': 2, 'revokedStartDelegationBeforeSubmit': True,
                'submitDenied': submit, 'publishedBlobs': 0, 'reportRows': 0, 'reportReadyEvents': 0}


def _competing_claims(ctx):
    with case(ctx, 'competing_claims', lease=90, budget=180) as c:
        call, services = c['call'], c['services']
        other = {}
        for kind in ('scheduler', 'worker'):
            result = call('service_enroll', c['admin'], service=kind + 'Other', kind=kind, projects=[c['project']])
            other[kind] = result['credential']
            ctx['forbidden'].append(other[kind].encode())
        call('run_start', c['admin'], **c['start'])
        primary = _request(c)
        secondary = dict(primary, worker='workerOther')
        winner, loser = _parallel(ctx, c, [('worker_claim', services['scheduler'], primary),
                                          ('worker_claim', other['scheduler'], secondary)])
        require(isinstance(winner, dict) and loser == 'E_STALE', 'E_INTEGRITY')
        ctx['forbidden'].append(winner['lease_token'].encode())
        row = _row(c)
        require((row['claim_scheduler'], row['worker'], row['attempt'], row['delivery_count'], row['sequence']) ==
                ('scheduler', 'worker', 1, 1, 2) and row['assignment'] == winner['assignment']
                and row['effect_nonce'] is None, 'E_INTEGRITY')
        denied(lambda: call('worker_recover_claim', other['scheduler'], **secondary), ('E_DENIED',))
        denied(lambda: call('worker_admit', other['worker'], **_worker_body(c, winner)), ('E_STALE',))
        events = c['client'].events(c['project'], c['run_id'], c['admin'], 1)
        require(len(events) == 1 and events[0]['data']['state'] == 'collecting', 'E_INTEGRITY')
        require(_cancel(c, row['version'])['state'] == 'cancelled' and _row(c)['effect_nonce'] is None, 'E_INTEGRITY')
        return {'status': 'PASS', 'databaseWaiters': 2, 'distinctSchedulers': 2, 'distinctTargetWorkers': 2,
                'attempts': 1, 'collectingEvents': len(events), 'losingClaimDenied': loser,
                'losingSchedulerRecoveryAndWorkerAdmissionDenied': True}


def _deadline_after_witness(ctx):
    with case(ctx, 'deadline_after_witness', lease=30, budget=5) as c:
        with _isolated_api(ctx, c, 'deadline_after_witness') as (client, pipe, process), closing(c['factory']()) as monitor:
            # The new server is already listening when the five-second run budget begins.
            body = _accepted(ctx, c)
            before = _graph(c)
            require(before['state'] == 'analyzing' and before['reports'] == before['ready'] == 0, 'E_INTEGRITY')
            scope = (c['project'], c['run_id'])
            clock_query = 'SELECT extract(epoch FROM run_deadline-clock_timestamp()) AS remaining FROM rt_runs WHERE project=%s AND id=%s'
            with ThreadPoolExecutor(1) as pool:
                pending = pool.submit(client.call, 'worker_submit', c['services']['worker'], dict(body, version=VERSION))
                require(pipe.poll(12) and pipe.recv() == ('hit', 'deadline_after_witness'), 'E_INTEGRITY')
                try:
                    remaining = monitor.conn.execute(clock_query, scope).fetchone()['remaining']
                    require(0 < remaining <= 5, 'E_INTEGRITY')
                    time.sleep(float(remaining) + 0.1)
                    require(monitor.conn.execute(clock_query, scope).fetchone()['remaining'] < 0, 'E_INTEGRITY')
                finally:
                    pipe.send('release')
                denied(lambda: pending.result(timeout=15), ('E_STALE',))
            process.join(10)
            require(process.exitcode == 0, 'E_DEPENDENCY')
        require(_graph(c) == before, 'E_INTEGRITY')
        denied(lambda: _read(c), ('E_UNRESOLVED',))
        head = strict_json((c['state_root'] / 'authority.json').read_bytes())
        with closing(c['factory']()) as app:
            receipt = app.store.reconcile_aborted_transition(head['nonce'])
            require(receipt['recovered'] and receipt['transactionStatus'] == 'aborted', 'E_INTEGRITY')
        denied(lambda: c['call']('worker_submit', c['services']['worker'], **body), ('E_STALE',))
        denied(lambda: c['call']('report_read', c['admin'], **_scope(c)), ('E_DENIED',))
        require(_graph(c) == before, 'E_INTEGRITY')
        final = _cancel(c, _read(c)['stateVersion'])
        require(final['state'] == 'cancelled' and _graph(c)['ready'] == 0, 'E_INTEGRITY')
        return {'status': 'PASS', 'mode': 'imported', 'budgetSeconds': 5,
                'databaseDeadlineCrossedAfterExternalWitness': True, 'submitReply': 'E_STALE',
                'ordinaryReadBeforeRepair': 'E_UNRESOLVED', 'recoveryVerifiedXid': receipt['transactionStatus'],
                'lateSubmitAfterRepair': 'E_STALE', 'reportRows': 0, 'reportReadyEvents': 0}


def run_cases(ctx):
    checks = ctx['checks']
    for key, point in [('I18a', 'partial_stage'), ('I18b', 'publication_staged'), ('I18c', 'publication_uncommitted'),
                       ('I18d', 'publication_committed'), ('I18e', 'authority_witness_written')]:
        checks[key] = _publication_case(ctx, point)
    checks['I19a'] = _lost_claim(ctx)
    checks['I19b'] = _admission_orders(ctx, False)
    checks['I19c'] = _admission_orders(ctx, True)
    with case(ctx, 'claim_budget', lease=60, budget=180) as c:
        c['call']('run_start', c['admin'], **c['start'])
        _recovery_budget(ctx, c)
        checks['I19d'] = {'status': 'PASS', 'maximumRedeliveries': 3, 'fourthRotationRejected': 'E_BUDGET',
                          'noAdditionalAttemptOrClaimEvent': True}
    checks['I19e'] = _expiry(ctx)
    checks['I20a'] = _cancel_orders(ctx, False)
    checks['I20b'] = _cancel_orders(ctx, True)
    checks['I21'] = _parallel_publication(ctx)
    checks['I22'] = _revoke_before_publication(ctx)
    checks['I23'] = _competing_claims(ctx)
    checks['I24'] = _deadline_after_witness(ctx)
    return checks
