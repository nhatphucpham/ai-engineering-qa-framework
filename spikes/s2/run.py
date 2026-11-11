"""Actual PostgreSQL S2-A fault/concurrency experiment. Writes new evidence only."""

import copy
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import threading
import time
import traceback
import uuid
from unittest.mock import patch

from local import ROOT, CACHE, inventory, stop, start
from store import Store, Rejected, canonical, psycopg
from qa_core.publication import create_publication_package
from qa_core.reports import digest


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def reject(action):
    try:
        action()
    except (Rejected, psycopg.errors.UniqueViolation):
        return
    raise AssertionError('Expected rejection did not occur')


def prepare(store, run_id, case='complete'):
    store.seed(run_id, case)
    claim = store.claim(run_id)
    package = store.package(claim)
    store.accept_receipt(claim, package)
    return claim, package


def queue_process(schema, barrier, output):
    records, failures = [], []
    def run_connection():
        store = None
        try:
            store = Store(schema)
            barrier.wait(timeout=30)
            while True:
                claim = store.claim(hold_seconds=0.015)
                if claim is None:
                    break
                package = store.package(claim)
                store.accept_receipt(claim, package)
                store.complete(claim, package)
                claim['roundtrip'] = store.verify_roundtrip(claim, package)
                records.append(claim)
        except Exception:
            failures.append(traceback.format_exc())
        finally:
            if store:
                store.close()
    threads = [threading.Thread(target=run_connection) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    if any(thread.is_alive() for thread in threads):
        failures.append('Connection thread timeout')
    output.send({'records': records, 'failures': failures})
    output.close()


def killed_child(schema, claim, package, point, pipe):
    store = Store(schema)
    def pause(actual):
        if actual == point:
            pipe.send({'point': actual, 'pid': mp.current_process().pid})
            pipe.recv()  # Parent terminates this process at the observed boundary.
    if point == 'after_receipt':
        store.accept_receipt(claim, package)
        pause(point)
    else:
        store.complete(claim, package, pause)
    store.close()


def kill_at(schema, store, claim, package, point, restart_database=False):
    parent, child = mp.Pipe()
    proc = mp.Process(target=killed_child, args=(schema, claim, package, point, child))
    proc.start()
    child.close()
    try:
        require(parent.poll(35), 'Child did not reach requested fault boundary')
        observed = parent.recv()
        observed['before_kill'] = store.state(claim['id'])
        if restart_database:
            # Child still owns an open completion transaction when PostgreSQL is stopped.
            stop('immediate')
            observed['database_stopped_with_open_transaction'] = True
        proc.terminate()
        proc.join(15)
        require(not proc.is_alive() and proc.exitcode != 0, 'Fault child was not terminated')
        observed['exitcode'] = proc.exitcode
        if restart_database:
            start()
            fresh = Store(schema)
            observed['after_kill'] = fresh.state(claim['id'])
            fresh.close()
        else:
            observed['after_kill'] = store.state(claim['id'])
        return observed
    finally:
        if proc.is_alive():
            proc.kill()
            proc.join(10)
        parent.close()


def publisher_child(schema, event_id, sink, point, pipe):
    store = Store(schema)
    event = store.conn.execute('SELECT * FROM outbox WHERE id=%s AND NOT acked', (event_id,)).fetchone()
    if event:
        if point == 'before_delivery':
            pipe.send(point)
            pipe.recv()
        # Restricted test sink stores only stable event ID, no whole replay package.
        with open(sink, 'a', encoding='utf-8') as stream:
            stream.write(event['id'] + '\n')
            stream.flush()
            import os
            os.fsync(stream.fileno())
        if point == 'after_delivery_before_ack':
            pipe.send(point)
            pipe.recv()
        store.conn.execute('UPDATE outbox SET acked=true WHERE id=%s', (event_id,))
        if point == 'after_ack':
            pipe.send(point)
            pipe.recv()
    store.close()


def publish(schema, event_id, sink, point=None):
    parent, child = mp.Pipe()
    proc = mp.Process(target=publisher_child, args=(schema, event_id, sink, point, child))
    proc.start()
    child.close()
    try:
        if point:
            require(parent.poll(20) and parent.recv() == point, 'Publisher fault boundary missing')
            proc.terminate()
        proc.join(20)
        require(not proc.is_alive(), 'Publisher timeout')
        require(proc.exitcode != 0 if point else proc.exitcode == 0, 'Unexpected publisher exit')
        return proc.exitcode
    finally:
        if proc.is_alive():
            proc.kill()
            proc.join(10)
        parent.close()


def file_inventory():
    paths = set()
    for prefix in ('qa_core', 'schemas', 'spikes/s2', 'examples/reports/runtime-v1'):
        paths.update(p for p in (ROOT / prefix).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix != '.pyc')
    paths.add(ROOT / 'docs/S2-A-PROTOCOL.md')
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def experiment(evidence):
    schema = 's2_' + uuid.uuid4().hex
    evidence['schema'] = schema
    store = Store(schema, create=True)
    checks = evidence['checks'] = {}
    try:
        settings = store.conn.execute('''SELECT version() AS version, current_setting('fsync') AS fsync,
            current_setting('synchronous_commit') AS synchronous_commit,
            current_setting('full_page_writes') AS full_page_writes,
            current_setting('transaction_isolation') AS isolation''').fetchone()
        evidence['database'] = settings
        require(all(settings[k] == 'on' for k in ('fsync', 'synchronous_commit', 'full_page_writes')),
                'Durability settings not enabled')
        for i in range(100):
            store.seed(f'job-{i:03}')
        barrier = mp.Barrier(4)
        children, pipes = [], []
        for _ in range(2):
            parent, child = mp.Pipe()
            proc = mp.Process(target=queue_process, args=(schema, barrier, child))
            proc.start()
            child.close()
            children.append(proc)
            pipes.append(parent)
        records = []
        try:
            for pipe in pipes:
                require(pipe.poll(150), 'Queue child timeout')
                result = pipe.recv()
                require(not result['failures'], 'Queue child connection failed: ' + str(result['failures']))
                records.extend(result['records'])
            for proc in children:
                proc.join(15)
                require(proc.exitcode == 0, 'Queue process failed')
        finally:
            for proc in children:
                if proc.is_alive():
                    proc.kill()
                    proc.join(10)
            for pipe in pipes:
                pipe.close()
        require(len(records) == 100 and len({r['id'] for r in records}) == 100, 'Duplicate/missing claims')
        require(len({r['process'] for r in records}) == 2 and len({r['backend'] for r in records}) == 4,
                'Not all 2 processes/4 connections participated')
        overlap = any(a['backend'] != b['backend'] and a['begin_ns'] < b['end_ns']
                      and b['begin_ns'] < a['end_ns'] for a in records for b in records)
        require(overlap, 'No observed overlap between claims on independent connections')
        for record in records:
            require(store.state(record['id']) == {'state': 'completed', 'version': 5,
                    'report_id': 'report-' + record['id'], 'claims': 1, 'receipts': 1, 'reports': 1, 'outbox': 1},
                    'Queue graph inconsistent')
        latencies = sorted((r['end_ns'] - r['begin_ns']) / 1e6 for r in records)
        checks['C01'] = {'status': 'PASS', 'records': records, 'overlap': overlap,
            'claim_latency_ms': {'median': statistics.median(latencies), 'p95_nearest_rank': latencies[94]},
            'queue_age_ms': {'median': statistics.median(r['queue_age_ms'] for r in records),
                             'max': max(r['queue_age_ms'] for r in records)}}

        c, p = prepare(store, 'fencing')
        before = store.state(c['id'])
        for key in ('version', 'attempt', 'fence'):
            reject(lambda key=key: store.complete({**c, key: c[key] - 1}, p))
        store.conn.execute("UPDATE runs SET expires=clock_timestamp()-interval '1 second' WHERE id='fencing'")
        reject(lambda: store.complete(c, p))
        require(store.state(c['id']) == before, 'Fencing changed graph')
        # Real DB clock crosses expiry during core validation; no DB behavior is mocked.
        import store as store_module
        original_validator = store_module.validate_publication_package
        def delayed_validator(*args, **kwargs):
            result = original_validator(*args, **kwargs)
            time.sleep(0.35)
            return result
        store.conn.execute("UPDATE runs SET expires=clock_timestamp()+interval '0.2 seconds' WHERE id='fencing'")
        with patch.object(store_module, 'validate_publication_package', delayed_validator):
            reject(lambda: store.complete(c, p))
        require(store.state(c['id']) == before, 'Expiry during validation changed graph')
        checks['F01'] = {'status': 'PASS', 'probes': ['version', 'attempt', 'fence', 'expired_lease'],
                         'expiryDuringValidation': 'real server clock + injected validator delay, rejected',
                         'before': before, 'after': store.state(c['id'])}

        predicate_states = []
        for predicate in ('cleanup_ok', 'policy_ok'):
            store.seed('denied-' + predicate, **{predicate: False})
            require(store.claim('denied-' + predicate) is None, 'Denied claim accepted')
            dc, dp = prepare(store, 'complete-denied-' + predicate)
            store.conn.execute(f'UPDATE runs SET {predicate}=false WHERE id=%s', (dc['id'],))
            dbefore = store.state(dc['id'])
            reject(lambda: store.complete(dc, dp))
            require(store.state(dc['id']) == dbefore, 'Denied completion changed graph')
            predicate_states.append({'predicate': predicate, 'state': dbefore})
        checks['F02'] = {'status': 'PASS', 'observations': predicate_states, 'authenticatedPolicy': 'NOT RUN'}

        c, p = prepare(store, 'tamper')
        before = store.state(c['id'])
        tampered = copy.deepcopy(p)
        tampered['graph']['completedRunCandidate']['stateVersion'] += 1
        reject(lambda: store.complete(c, tampered))
        bundle = copy.deepcopy(p['payloads']['bundle'])
        bundle['projects'][0]['name'] += ' coherent rewrite'
        coherent = create_publication_package(bundle, p['payloads']['assessment'],
                    run_id=c['id'], report_id='report-' + c['id'])
        reject(lambda: store.complete(c, coherent))
        require(store.state(c['id']) == before, 'Bad package changed graph')
        checks['F03'] = {'status': 'PASS', 'before': before, 'after': store.state(c['id']),
                         'probes': ['graph_tamper', 'coherent_rewrite_old_anchors']}

        c, p = prepare(store, 'rollback')
        before = store.state(c['id'])
        observer = Store(schema)
        seen = []
        class Rollback(Exception):
            pass
        def rollback_hook(point):
            if point == 'before_commit':
                seen.append(observer.state(c['id']))
                raise Rollback()
        try:
            store.complete(c, p, rollback_hook)
        except Rollback:
            pass
        observer.close()
        require(seen == [before] and store.state(c['id']) == before, 'Uncommitted/rolled back graph exposed')
        checks['T01'] = {'status': 'PASS', 'before': before, 'observer_before_commit': seen[0],
                         'after_rollback': store.state(c['id'])}

        c, p = prepare(store, 'commit-failure')
        before = store.state(c['id'])
        def break_deferred_reference(point):
            if point == 'before_commit':
                store.conn.execute("UPDATE runs SET report_id='nonexistent-report' WHERE id=%s", (c['id'],))
        try:
            store.complete(c, p, break_deferred_reference)
        except psycopg.errors.ForeignKeyViolation as error:
            require(error.diag.constraint_name == 'report_ref', 'Wrong commit failure injected')
        else:
            raise AssertionError('Deferred commit failure did not occur')
        require(store.state(c['id']) == before, 'Failed commit exposed partial graph')
        checks['T03'] = {'status': 'PASS', 'fault': 'deferred report_ref FK rejection at commit',
                         'before': before, 'after': store.state(c['id'])}

        races = []
        for competitor in ('complete', 'cancel'):
            c, p = prepare(store, 'race-' + competitor)
            gate, outcomes = threading.Barrier(2), []
            def terminal(action):
                other = Store(schema)
                try:
                    gate.wait(timeout=10)
                    if action == 'complete':
                        other.complete(c, p)
                    else:
                        other.cancel_predicate(c)
                    outcomes.append(action + ':accepted')
                except Rejected:
                    outcomes.append(action + ':rejected')
                finally:
                    other.close()
            threads = [threading.Thread(target=terminal, args=(action,)) for action in ('complete', competitor)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(30)
            state = store.state(c['id'])
            require(sum(o.endswith(':accepted') for o in outcomes) == 1 and len(outcomes) == 2,
                    'Terminal race did not have exactly one winner')
            require(state['reports'] == state['outbox'] == int(state['state'] == 'completed'), 'Partial terminal graph')
            reject(lambda: store.complete(c, p))
            races.append({'competitor': competitor, 'outcomes': outcomes, 'state': state})
        checks['T02'] = {'status': 'PASS', 'races': races, 'fullCancellationLifecycle': 'NOT RUN'}

        c, p = prepare(store, 'duplicate')
        store.complete(c, p)
        before = store.state(c['id'])
        probes = {
            'runs_occurrence_key': "INSERT INTO runs SELECT 'duplicate-id',occurrence,'queued',3,0,3,NULL,cleanup_ok,policy_ok,bundle,assessment,bundle_sha,assessment_sha,NULL,queued_at FROM runs WHERE id=%s",
            'runs_pkey': "INSERT INTO runs SELECT id,'other-occurrence','queued',3,0,3,NULL,cleanup_ok,policy_ok,bundle,assessment,bundle_sha,assessment_sha,NULL,queued_at FROM runs WHERE id=%s",
            'reports_pkey': "INSERT INTO reports SELECT * FROM reports WHERE run_id=%s",
            'reports_run_id_key': "INSERT INTO reports SELECT 'other-report',run_id,package,package_sha,package_length,report_sha FROM reports WHERE run_id=%s",
            'outbox_pkey': "INSERT INTO outbox SELECT * FROM outbox WHERE run_id=%s",
            'outbox_run_id_key': "INSERT INTO outbox SELECT 'other-event',run_id,report_id,sequence+1,run_version,acked FROM outbox WHERE run_id=%s"}
        for constraint, query in probes.items():
            try:
                store.conn.execute(query, (c['id'],))
            except psycopg.errors.UniqueViolation as error:
                require(error.diag.constraint_name == constraint, 'Wrong uniqueness constraint observed')
            else:
                raise AssertionError('Duplicate accepted')
        require(store.state(c['id']) == before, 'Unique rejection changed graph')
        checks['C02'] = {'status': 'PASS', 'probes': list(probes), 'before': before, 'after': store.state(c['id'])}

        for check_id, point in [('K01', 'before_commit'), ('K02', 'after_commit'), ('K03', 'after_receipt')]:
            store.seed('crash-' + check_id)
            c = store.claim('crash-' + check_id)
            p = store.package(c)
            if point != 'after_receipt':
                store.accept_receipt(c, p)
            details = kill_at(schema, store, c, p, point)
            # Fresh connection after actual process termination (DB rollback can be asynchronous).
            fresh = Store(schema)
            state = fresh.state(c['id'])
            require(state['receipts'] == 1 and state['reports'] == state['outbox'] == int(point == 'after_commit'),
                    'Crash persistence state mismatch')
            require(state['state'] == ('completed' if point == 'after_commit' else 'checking'), 'Crash run mismatch')
            if point == 'after_commit':
                reject(lambda: fresh.complete(c, p))
            else:
                fresh.complete(c, p)
            details['fresh_connection_before_retry'] = state
            details['after_retry'] = fresh.state(c['id'])
            details['roundtrip'] = fresh.verify_roundtrip(c, p)
            fresh.close()
            checks[check_id] = {'status': 'PASS', **details}

        sink = CACHE / ('sink-' + schema + '.txt')
        event_id = 'ready-crash-K02'
        exits = []
        for point, expected_count in [('before_delivery', 0), ('after_delivery_before_ack', 1), ('after_ack', 2)]:
            exits.append({'point': point, 'exitcode': publish(schema, event_id, sink, point)})
            lines = sink.read_text().splitlines() if sink.exists() else []
            require(lines == [event_id] * expected_count, 'Unexpected delivery count/identity')
            acked = store.conn.execute('SELECT acked FROM outbox WHERE id=%s', (event_id,)).fetchone()['acked']
            require(acked == (point == 'after_ack'), 'Outbox acknowledgement mismatch')
        publish(schema, event_id, sink)
        require(sink.read_text().splitlines() == [event_id, event_id], 'Acknowledged event redelivered')
        checks['K04'] = {'status': 'PASS', 'faults': exits, 'sink': [event_id, event_id], 'acked': True,
                         'deliverySemantics': 'at-least-once; duplicate stable event ID observed'}

        # Crash DB while child still has uncommitted graph writes and row lock.
        c, p = prepare(store, 'db-restart-uncommitted')
        completed_before = store.state('crash-K02')
        report_before = bytes(store.conn.execute("SELECT package FROM reports WHERE run_id='crash-K02'").fetchone()['package'])
        uncommitted = kill_at(schema, store, c, p, 'before_commit', restart_database=True)
        store.close()
        store = Store(schema)
        require(store.state('crash-K02') == completed_before, 'Committed graph lost after immediate restart')
        require(bytes(store.conn.execute("SELECT package FROM reports WHERE run_id='crash-K02'").fetchone()['package']) == report_before,
                'Canonical bytes changed after restart')
        require(store.state(c['id'])['reports'] == store.state(c['id'])['outbox'] == 0, 'Uncommitted graph recovered as published')
        require(store.conn.execute('SELECT acked FROM outbox WHERE id=%s', (event_id,)).fetchone()['acked'], 'Ack lost on restart')
        pending_id = 'ready-crash-K01'
        require(not store.conn.execute('SELECT acked FROM outbox WHERE id=%s', (pending_id,)).fetchone()['acked'],
                'Pending event was unexpectedly acknowledged')
        replay_sink = CACHE / ('replay-' + schema + '.txt')
        publish(schema, pending_id, replay_sink)
        require(replay_sink.read_text().splitlines() == [pending_id], 'Pending outbox replay after DB restart failed')
        require(store.conn.execute('SELECT acked FROM outbox WHERE id=%s', (pending_id,)).fetchone()['acked'],
                'Replayed event not acknowledged')
        log_lines = (CACHE / 'postgres.log').read_text(encoding='utf-8').splitlines()[-30:]
        recovery = [line for line in log_lines if any(text in line for text in (
            'immediate shutdown', 'automatic recovery', 'redo starts', 'redo done', 'ready to accept'))]
        require(any('automatic recovery' in line for line in recovery), 'No observed WAL recovery log')
        checks['R01'] = {'status': 'PASS', 'mode': 'pg_ctl immediate stop/start, WAL recovery',
            'committed_before': completed_before, 'committed_after': store.state('crash-K02'),
            'uncommitted_child': uncommitted, 'uncommitted_after_restart': store.state(c['id']),
            'canonical_sha256_before_after': hashlib.sha256(report_before).hexdigest(), 'ack_survived': True,
            'pending_replayed_after_restart': pending_id, 'recovery_log': recovery}

        # Three verification outcomes must survive real storage without changing semantics.
        outcomes = []
        for case, expected in [('complete', 'complete'), ('constraint-collision', 'incomplete'), ('failed-pending', 'failed')]:
            c, p = prepare(store, 'outcome-' + case, case)
            store.complete(c, p)
            require(p['payloads']['prepared']['report']['content']['assessment']['verification'] == expected,
                    'Verification outcome changed')
            outcomes.append({'case': case, 'verification': expected, 'roundtrip': store.verify_roundtrip(c, p)})
        checks['SEM01'] = {'status': 'PASS', 'outcomes': outcomes}
    finally:
        store.close()


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: py -3 -B spikes/s2/run.py docs/s2-results/<new-run-id>.json')
    destination = (ROOT / sys.argv[1]).resolve()
    if destination.parent != (ROOT / 'docs/s2-results').resolve() or destination.suffix != '.json' or destination.exists():
        raise SystemExit('Evidence destination must be a new JSON under docs/s2-results')
    evidence = {'evidenceVersion': 's2-a-1.0.0', 'classification': 'synthetic-only',
        'startedAt': datetime.now(timezone.utc).isoformat(),
        'baseline': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'command': 'py -3 -B spikes/s2/run.py ' + sys.argv[1],
        'environment': {'python': sys.version, 'platform': platform.platform(), 'psycopg': psycopg.__version__},
        'preflight': inventory(), 'inputsBefore': file_inventory(), 'status': 'RUNNING',
        'limits': ['No production DB/runtime decision', 'No authenticated policy/lease renewal/worker cleanup',
                   'No external blob service, backup/restore or power-loss proof', 'No fairness/SLA',
                   'No ordinary authorized read/export', 'Full S2/P4-A/P4-B remain partial']}
    begin = time.monotonic()
    try:
        require(evidence['preflight']['toolchainReady'], 'Toolchain NOT READY')
        experiment(evidence)
        evidence['inputsAfter'] = file_inventory()
        require(evidence['inputsAfter'] == evidence['inputsBefore'], 'Source/input changed during experiment')
        evidence['status'] = 'PASS'
    except Exception as exc:
        evidence['status'] = 'ERROR'
        evidence['errorType'] = type(exc).__name__
        # This controlled harness has synthetic-only data; traceback stays in ignored local diagnostics.
        (CACHE / 'last-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    evidence['elapsedSeconds'] = time.monotonic() - begin
    evidence['finishedAt'] = datetime.now(timezone.utc).isoformat()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': evidence['status'], 'elapsedSeconds': evidence['elapsedSeconds'],
                      'checks': {k: v['status'] for k, v in evidence.get('checks', {}).items()}}))
    return 0 if evidence['status'] == 'PASS' else 2


if __name__ == '__main__':
    mp.freeze_support()
    raise SystemExit(main())
