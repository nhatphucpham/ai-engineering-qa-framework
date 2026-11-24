"""Serialized operator-only whole-supervisor failover campaign. Never a production worker."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for folder in ('spikes/s4e', 'spikes/iapb'):
    sys.path.insert(0, str(ROOT / folder))
from run_iapb import AuthorityFixture, blocked, inventory, db_inventory
from recovery import RecoveryStore, Denied, Jsonb
from unit import Unit, check


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def pin(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def source_pins():
    paths = {ROOT / 'docs/S4-F-PROTOCOL.md'}
    for part in ('s4f', 's4e', 's4b', 'iapb', 'iap', 's6b', 's2'):
        paths.update(p for p in (ROOT / 'spikes' / part).glob('*') if p.suffix in ('.py', '.sql', '.md', '.lock'))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


class Store(RecoveryStore):
    def __init__(self, schema, create=False):
        super().__init__(schema, create=create)
        if create:
            self.conn.execute('''CREATE TABLE f_anchors(job text PRIMARY KEY REFERENCES e_jobs(id),
                context jsonb NOT NULL, journal_pin text)''')

    def prepare_context(self, fixture, assignment, ready):
        ctx = ready['context']
        check(ready['contextPin'] == pin(ctx), 'E_CONTEXT')
        with self.identity.tx():
            b = self.prepare(fixture.tokens['workerA'], ctx['generation'], **fixture.binding(assignment))
            b = dict(b, effectNonce=uuid.uuid4().hex, container_name='qa-s4-f-' + b['job'])
            self.conn.execute('UPDATE e_jobs SET binding=%s WHERE id=%s', (Jsonb(b), b['job']))
            self.conn.execute('INSERT INTO f_anchors(job,context) VALUES(%s,%s)', (b['job'], Jsonb(ctx)))
        return b

    def anchor(self, job):
        row = self.conn.execute('SELECT * FROM f_anchors WHERE job=%s', (job,)).fetchone()
        check(row is not None, 'E_CONTEXT')
        return {'context': row['context'], 'contextPin': pin(row['context'])}, row['journal_pin']

    def set_pin(self, job, prior, new):
        check(isinstance(new, str) and re.fullmatch('[a-f0-9]{64}', new), 'E_JOURNAL')
        row = self.conn.execute('''UPDATE f_anchors SET journal_pin=%s WHERE job=%s
            AND journal_pin IS NOT DISTINCT FROM %s RETURNING job''', (new, job, prior)).fetchone()
        check(row is not None, 'E_JOURNAL')

    def launch_once(self, fixture, assignment, binding, unit, window):
        worker = fixture.tokens['workerA']
        job = binding['job']
        # Public authorization and one-use consumption commit before ANY external create.
        check(self.consume(worker, job) == binding, 'E_CONSUME')
        with self.service_unit(worker, 'worker', binding['project']) as (actor, deadlines):
            self.current_assignment(actor, **fixture.binding(assignment), deadlines=deadlines)
            _, previous = self.anchor(job)
            check(previous is None and self.job(job)['state'] == 'consumed', 'E_ONE_USE')
            arm = unit.request('arm', binding=binding)
            self.set_pin(job, None, arm['journalPin'])
        with self.service_unit(worker, 'worker', binding['project']) as (actor, deadlines):
            self.current_assignment(actor, **fixture.binding(assignment), deadlines=deadlines)
            _, previous = self.anchor(job)
            launched = unit.request('fire', binding=binding, journalPin=previous, window=window)
            check(launched['barrier'] == window, 'E_BARRIER')
            self.set_pin(job, previous, launched['journalPin'])
            if launched.get('resource'):
                self.record_resource(job, launched['resource'])
        return launched

    def recover_epoch(self, binding, unit):
        store = self
        class Fencer:
            def request(self, op, **fields):
                check(op == 'fence' and fields['binding'] == binding, 'E_BINDING')
                job = binding['job']
                anchor, previous = store.anchor(job)
                check(unit.ready['contextPin'] == anchor['contextPin'] and previous, 'E_CONTEXT')
                reply = unit.request(op, **fields, journalPin=previous)
                store.set_pin(job, previous, reply['journalPin'])
        return self.begin(binding['job'], Fencer())

    def recover(self, binding, unit, *, after_io=None):
        job = binding['job']
        with self.identity.tx():
            row = self.job(job)
            self.exact_head(row)
            ctx, previous = self.anchor(job)
            check(row['state'] == 'unresolved' and row['incident_open'] and row['cleanup_proof'] is None
                  and row['epoch'] > 0 and ctx['contextPin'] == unit.ready['contextPin'], 'E_AUTHORITY')
            result = unit.request('cleanup', binding=binding, journalPin=previous,
                                  expectedResource=row['resource'], epoch=row['epoch'])
            proof = result['proof']
            check(proof['binding'] == row['binding'] and proof['epoch'] == row['epoch']
                  and proof['contextPin'] == ctx['contextPin'] and proof['operation'] == 'cleanup'
                  and proof['remainingContainerIds'] == [] and proof['cgroupAbsent'] is True
                  and proof['quiescence']['originalProcessNotLive'] is True, 'E_CLEANUP')
            if after_io is not None:
                after_io(proof)
            self.set_pin(job, previous, result['journalPin'])
            saved = self.conn.execute('''UPDATE e_jobs SET state='failed',incident_open=false,cleanup_proof=%s
                WHERE id=%s AND state='unresolved' AND epoch=%s AND cleanup_proof IS NULL RETURNING id''',
                (Jsonb(proof), job, row['epoch'])).fetchone()
            check(saved is not None, 'E_ACK')
        return proof


def must_deny(operation, codes):
    try:
        operation()
    except (RuntimeError, Denied, BrokenPipeError, OSError) as exc:
        code = getattr(exc, 'code', str(exc))
        check(code in codes, 'E_WRONG_NEGATIVE')
        return code
    raise RuntimeError('E_NEGATIVE_ACCEPTED')


def negatives(store, b, original_pin, replacement, work):
    anchor, current = store.anchor(b['job'])
    ctx = anchor['context']
    results = {}
    for key in ('boot', 'baseId', 'marker'):
        wrong = deepcopy(ctx)
        if key == 'boot':
            wrong[key] = str(uuid.uuid4())
        elif key == 'marker':
            wrong['landmarks']['marker.json'][1] = '0' * 64
        else:
            wrong[key][1] += 1
        # A freshly self-consistent supplied context still cannot match the real objects/marker.
        def try_attach():
            with closing(Unit('replacement', work, {'context': wrong, 'contextPin': pin(wrong)})):
                pass
        results[key] = must_deny(try_attach, ('E_CONTEXT',))
    row = store.job(b['job'])
    fields = {'binding': b, 'epoch': row['epoch'], 'journalPin': current, 'expectedResource': row['resource']}
    results['oldIndependentPin'] = must_deny(lambda: replacement.request('discover', **dict(fields, journalPin=original_pin)),
                                             ('E_JOURNAL',))
    for fault in ('absent', 'corrupt', 'older'):
        results['journal_' + fault] = replacement.request('test_journal', **fields, fault=fault)['denied']
    for key, altered in [('job', uuid.uuid4().hex), ('effectNonce', uuid.uuid4().hex), ('fence', b['fence'] + 1)]:
        results[key] = must_deny(lambda: replacement.request('cleanup', **dict(fields, binding={**b, key: altered})),
                                 ('E_BINDING',))
    results['epoch'] = must_deny(lambda: replacement.request('cleanup', **dict(fields, epoch=row['epoch'] + 1)),
                                 ('E_FENCE',))
    original = deepcopy(row['resource'])
    proc = next(iter(original['processes'].values()))
    proc['startTime'] = str(int(proc['startTime']) + 1)
    results['pidStartTime'] = must_deny(lambda: replacement.request('cleanup', **dict(fields, expectedResource=original)),
                                        ('E_IDENTITY',))
    results['failedListing'] = must_deny(lambda: replacement.request('failed_listing', **fields), ('E_LISTING',))
    results['truncatedListing'] = must_deny(lambda: replacement.request('truncated_listing', **fields), ('E_LISTING',))
    results['unknownContainer'] = replacement.request('test_unknown_container', **fields)
    observed = replacement.request('discover', **fields)
    check(observed['resource'] and store.job(b['job'])['cleanup_proof'] is None, 'E_PREMATURE_CLEANUP')
    return results


def compare_window(window, before, proof):
    after = proof['discovered']
    if window == 'before_create':
        check(before is None and after is None and proof['durableOriginal'] is None, 'E_F02')
    else:
        check(before and after and before['containerId'] == after['containerId'], 'E_CID_MATCH')
        check(before['running'] is (window != 'after_create'), 'E_BARRIER_STATE')
        if window == 'after_identity':
            check(proof['durableOriginal'] == before, 'E_DURABLE_ID')
        else:
            check(proof['durableOriginal'] is None, 'E_PREIDENTITY')
    return {'previouslyObserved': before, 'observedAfterCrash': after,
            'workloadKilledByUnit': bool(before and before['running'] and after and not after['running'])}


def run_window(store, fixture, workspace, case, window, evidence):
    record = {'status': 'RUNNING', 'window': window}
    evidence['checks'][case] = record
    original = Unit('original', workspace)
    replacement = binding = None
    safe = False
    try:
        fixture.new_run(case)
        assignment = fixture.assign(case, ttl_ms=30000)
        binding = store.prepare_context(fixture, assignment, original.ready)
        job = binding['job']
        record.update(original=original.ready, binding=binding)
        store.launch_once(fixture, assignment, binding, original, window)
        anchor, initial = store.anchor(job)
        if case == 'F04-old-head':
            def live_attach():
                with closing(Unit('replacement', workspace, anchor)):
                    pass
            record['liveOldWriterDenial'] = must_deny(live_attach, ('E_OLD_WRITER',))
        # Independent observational process. None of its CID, PID or cgroup enters recovery.
        with closing(Unit('observer', workspace, anchor)) as probe:
            witness = probe.request('observe', binding=binding, journalPin=initial)
            check(witness['observer'] != original.ready['process'], 'E_NOT_INDEPENDENT')
            record['barrierObserver'] = witness
        if case.startswith('F05-'):
            result = monitor_loss(fixture, assignment, binding, original, workspace, case)
            record.update(result)
            safe = True
            record['status'] = 'PASS'
            return
        record['wholeUnitLoss'] = original.kill_original()
        store.mark_lost(job)
        replacement = Unit('replacement', workspace, anchor)
        record['replacement'] = {'unit': replacement.name, 'process': replacement.ready['process']}
        check(replacement.ready['process'] != original.ready['process'] and replacement.name != original.name,
              'E_REPLACEMENT')
        if case == 'F04-old-head':
            record['disconnectedChannel'] = replacement.close()
            record['fenceAfterDisconnect'] = must_deny(lambda: store.recover_epoch(binding, replacement), ('E_CHANNEL',))
            check(store.job(job)['epoch'] == 0 and store.job(job)['incident_open'], 'E_STALE_ACK')
            replacement = Unit('replacement', workspace, anchor)
        fenced = store.recover_epoch(binding, replacement)
        _, current = store.anchor(job)
        fields = dict(binding=binding, journalPin=current, epoch=fenced['epoch'], expectedResource=fenced['resource'])
        if case == 'F04-old-head':
            with store.identity.tx():
                store.exact_head(store.job(job))
                record['runtimeAnchorNegatives'] = [replacement.request('test_runtime_anchor', **fields, fault=fault)
                    for fault in ('missing_pause', 'substituted_pause', 'changed_alive')]
                record['negatives'] = negatives(store, binding, initial, replacement, workspace)
            newer = fixture.assign(case, expected=1, ttl_ms=30000)
            record['newAttempt'] = newer['attempt']
            record['newerHeadDenial'] = blocked(lambda: store.recover(binding, replacement), 'E_UNRESOLVED')
            proof = replacement.request('safety_teardown', **fields)['proof']
            fixture.check(newer)
            check(store.job(job)['incident_open'] and store.job(job)['cleanup_proof'] is None, 'E_STALE_ACK')
            record.update(safetyTeardownOnly=proof, executionState='unresolved', serverAcknowledged=False)
        elif case == 'F04-lost-ack':
            def lose_ack(proof):
                record['externalCleanupBeforeAckLoss'] = proof
                raise RuntimeError('E_INJECTED_ACK_LOSS')
            must_deny(lambda: store.recover(binding, replacement, after_io=lose_ack), ('E_INJECTED_ACK_LOSS',))
            record['replayAfterLostAck'] = must_deny(lambda: store.recover(binding, replacement), ('E_JOURNAL',))
            check(store.job(job)['incident_open'] and store.job(job)['cleanup_proof'] is None, 'E_STALE_ACK')
            record.update(executionState='unresolved', serverAcknowledged=False)
        else:
            proof = (ordered_cleanup(store, fixture, binding, replacement, record) if case == 'F04-cleanup-first'
                     else store.recover(binding, replacement))
            record['comparison'] = compare_window(window, witness['resource'], proof)
            check(store.job(job)['state'] == 'failed' and store.job(job)['cleanup_proof'] == proof, 'E_FINAL')
            blocked(lambda: store.consume(fixture.tokens['workerA'], job), 'E_STALE')
            record.update(cleanup=proof, executionState='failed', serverAcknowledged=True)
        safe = True
        record['status'] = 'PASS'
    finally:
        try:
            if original.process.poll() is None:
                record['failureWholeUnitLoss'] = original.kill_original()
            record['originalExit'] = original.close()
            if binding is not None and not safe:
                # Teardown is strictly separate from DB acknowledgement. An ambiguous
                # identity/journal/listing forbids deletion, even when the test failed.
                try:
                    anchor, prior = store.anchor(binding['job'])
                    check(prior, 'E_NO_HELD_JOURNAL')
                    if replacement is None:
                        replacement = Unit('replacement', workspace, anchor)
                    row = store.job(binding['job'])
                    if not row['epoch']:
                        reply = replacement.request('fence', binding=binding, epoch=1, journalPin=prior)
                        epoch, prior = 1, reply['journalPin']
                    else:
                        epoch = row['epoch']
                    record['failureSafetyTeardownOnly'] = replacement.request('safety_teardown', binding=binding,
                        epoch=epoch, journalPin=prior, expectedResource=row['resource'])['proof']
                except Exception as exc:
                    record['unresolvedResource'] = {'error': type(exc).__name__, 'binding': binding}
        finally:
            if replacement is not None:
                record['replacementExit'] = replacement.close()


def ordered_cleanup(store, fixture, b, replacement, record):
    # A second real DB connection must wait behind the identified authority backend.
    from authority import _AuthorityStore
    with closing(_AuthorityStore(fixture.schema)) as other, closing(_AuthorityStore(fixture.schema)) as observer:
        mine = store.conn.execute('SELECT pg_backend_pid() AS id').fetchone()['id']
        theirs = other.conn.execute('SELECT pg_backend_pid() AS id').fetchone()['id']
        with ThreadPoolExecutor(max_workers=1) as pool:
            with store.identity.tx():
                waiting = pool.submit(other.assign, fixture.tokens['schedA'], b['project'], b['run_id'], 'workerA', 1, 30000)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    row = observer.conn.execute('SELECT %s=ANY(pg_blocking_pids(%s)) AS blocked', (mine, theirs)).fetchone()
                    if row['blocked']:
                        break
                    time.sleep(.015)
                else:
                    raise RuntimeError('E_LOCK_ORDER')
                check(not waiting.done(), 'E_LOCK_ORDER')
                proof = store.recover(b, replacement)
                check(not waiting.done(), 'E_LOCK_ORDER')
            newer = waiting.result(timeout=10)
            check(newer['attempt'] == 2 and store.job(b['job'])['state'] == 'failed', 'E_LOCK_ORDER')
            record.update(observedBlocker=mine, waitingScheduler=theirs, newAttemptAfterCleanup=2)
    return proof


def monitor_loss(fixture, assignment, b, original, work, case):
    ready = threading.Event()
    checked = threading.Event()
    def monitor():
        with closing(Store(fixture.schema)) as independent:
            ready.set()
            end = time.monotonic() + 20
            polls = 0
            while time.monotonic() < end:
                if original.process.poll() is not None:
                    reason = 'original_process_exited'
                    break
                try:
                    independent.check(fixture.tokens['workerA'], **fixture.binding(assignment))
                except Denied as error:
                    reason = error.code
                    break
                polls += 1
                checked.set()
                time.sleep(.05)
            else:
                raise RuntimeError('E_REVOKE_UNOBSERVED')
            expected = ('original_process_exited',) if case == 'F05-supervisor-loss' else ('E_AUTH', 'E_DENIED')
            check(reason in expected and polls, 'E_MONITOR')
            independent.mark_lost(b['job'])
            killed = original.absence() if reason == 'original_process_exited' else original.kill_original()
            anchor, _ = independent.anchor(b['job'])
            with closing(Unit('replacement', work, anchor)) as other:
                check(other.ready['process'] != original.ready['process'], 'E_REPLACEMENT')
                independent.recover_epoch(b, other)
                proof = independent.recover(b, other)
            check(independent.job(b['job'])['state'] == 'failed', 'E_MONITOR_ACK')
            return {'positiveAuthorityPolls': polls, 'observedReason': reason, 'wholeUnitLoss': killed,
                    'cleanup': proof, 'executionState': 'failed', 'scope': 'local-supervisor-and-authority-monitor'}
    with ThreadPoolExecutor(max_workers=1) as executor:
        task = executor.submit(monitor)
        check(ready.wait(5) and checked.wait(5), 'E_MONITOR')
        if case == 'F05-supervisor-loss':
            original.kill_original()
        else:
            fixture.admin('revoke_service', service_id='workerA')
        return task.result(timeout=90)


def experiment(work, evidence, forbidden):
    fixture = AuthorityFixture(forbidden)
    try:
        for user in ('admin', 'runner'):
            fixture.users[user] = fixture.keep(fixture.raw.identity.login(user, fixture.passwords[user], access_ms=1200000))
        fixture.enroll('schedA', 'scheduler')
        fixture.enroll('workerA', 'worker')
        with closing(Store(fixture.schema, create=True)) as store:
            evidence['schema'] = fixture.schema
            for name, window in [('F01', 'after_identity'), ('F02', 'before_create'), ('F03a', 'after_start'),
                                 ('F03b', 'after_create'), ('F04-old-head', 'after_identity'),
                                 ('F04-cleanup-first', 'after_identity'), ('F04-lost-ack', 'after_identity'),
                                 ('F05-supervisor-loss', 'after_identity'), ('F05-worker-revocation', 'after_identity')]:
                run_window(store, fixture, work, name, window, evidence)
    finally:
        fixture.close()


def main():
    from local import start, stop, read_config, command
    from run_s4e import contains_secret
    check(len(sys.argv) == 2, 'E_OUTPUT')
    destination = (ROOT / sys.argv[1]).resolve()
    check(destination.parent == ROOT / 'docs/s4f-results' and re.fullmatch(r'[A-Za-z0-9_-]{1,80}\.json', destination.name)
          and not destination.exists(), 'E_OUTPUT')
    work = ROOT / '.cache/s6/s4-f' / destination.stem
    work.mkdir(parents=True, exist_ok=False)
    evidence = {'version': 's4f-1.0.0', 'classification': 'synthetic-only', 'status': 'RUNNING', 'checks': {},
                'startedAt': datetime.now(timezone.utc).isoformat(), 'inputsBefore': source_pins(),
                'scope': 'whole-supervisor Windows/WSL local authority; F05 application pipeline separately evidenced'}
    started = False
    forbidden = []
    try:
        check(inventory()['ready'] and db_inventory()['toolchainReady'], 'E_PREREQUISITES')
        cfg = read_config(False)
        try:
            command('pg_ctl', '-D', cfg['data'], 'status')
        except subprocess.CalledProcessError as exc:
            check(exc.returncode == 3, 'E_DB_STATUS')
        else:
            raise RuntimeError('E_DB_ALREADY_RUNNING')
        start()
        started = True
        experiment(work, evidence, forbidden)
        evidence['inputsAfter'] = source_pins()
        check(evidence['inputsBefore'] == evidence['inputsAfter'], 'E_CHANGED_INPUT')
        evidence['status'] = 'PASS'
    except Exception as exc:
        import traceback
        for item in evidence['checks'].values():
            if item['status'] == 'RUNNING':
                item['status'] = 'ERROR'
        detail = traceback.format_exc().encode()
        check(not contains_secret(detail, forbidden), 'E_DIAGNOSTIC_SECRET')
        (work / 'error.log').write_bytes(detail)
        evidence.update(status='ERROR', error=type(exc).__name__)
    finally:
        evidence['inputsAfter'] = source_pins()
        if started:
            try:
                stop()
                try:
                    command('pg_ctl', '-D', cfg['data'], 'status')
                except subprocess.CalledProcessError as exc:
                    check(exc.returncode == 3, 'E_DB_STATUS')
                else:
                    raise RuntimeError('E_DB_NOT_STOPPED')
                evidence['databaseStopped'] = True
            except Exception:
                evidence.update(status='ERROR', databaseStopped=False)
    evidence['finishedAt'] = datetime.now(timezone.utc).isoformat()
    raw = canonical(evidence)
    check(not contains_secret(raw, forbidden), 'E_EVIDENCE_SECRET')
    destination.parent.mkdir(exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(raw + b'\n')
    print(json.dumps({'status': evidence['status'], 'checks': {k: v['status'] for k, v in evidence['checks'].items()}}))
    return 0 if evidence['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
