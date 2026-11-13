"""Actual controlled process loss and cleanup-only recovery; synthetic local only."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for part in ('spikes/s4c', 'spikes/iapb'):
    sys.path.insert(0, str(ROOT / part))
from run_iapb import AuthorityFixture, require, blocked, inventory, db_inventory
from recovery import RecoveryStore, Controller, VERSION
from helper import Helper
import base64
import contextlib
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import multiprocessing as mp
import subprocess
import time
import traceback

CACHE = ROOT / '.cache/s6/s4-e'


class Relay:
    def __init__(self, pipe):
        self.pipe = pipe

    def request(self, op, **body):
        self.pipe.send({'op': op, 'body': body})
        require(self.pipe.poll(35), 'Relay timeout')
        reply = self.pipe.recv()
        if reply.get('error'):
            raise RuntimeError('E_INJECTED_CHANNEL')
        return reply['result']


def controller_child(schema, job, credential, mode, endpoint):
    store = RecoveryStore(schema)
    try:
        helper = Relay(endpoint)
        if mode == 'launch':
            binding = store.consume(credential, job)
            observation = helper.request('launch', binding=binding)
            store.record_resource(job, observation['resource'])
            endpoint.send({'active': True})
            # Parent terminates this real process without a controller finally block.
            time.sleep(60)
        elif mode == 'publish':
            row = store.begin(job, helper)
            endpoint.send({'published': row['epoch']})
        elif mode == 'reconcile':
            proof = Controller(store, helper).reconcile(job)
            endpoint.send({'reconciled': proof})
        else:
            row = store.job(job)
            proof = store.cleanup(job, row['epoch'], helper)
            endpoint.send({'cleaned': proof})
    except Exception:
        try: endpoint.send({'failed': True})
        except (OSError, EOFError): pass
    finally:
        store.close(); endpoint.close()


def assign_child(schema, credential, run_id, endpoint):
    store = RecoveryStore(schema)
    try:
        endpoint.send({'started': True})
        result = store.assign(credential, 'pA', run_id, 'workerA', 1, 20000)
        endpoint.send({'assignment': result})
    finally:
        store.close(); endpoint.close()


def denied_helper(call):
    try:
        call()
    except RuntimeError as error:
        return str(error)
    raise AssertionError('Expected helper denial')


def experiment(evidence, forbidden):
    f = AuthorityFixture(forbidden)
    helper = store = observer = None
    evidence['schema'] = f.schema
    checks = evidence['checks'] = {}
    children = []
    try:
        f.enroll('schedA', 'scheduler'); f.enroll('workerA', 'worker')
        helper = Helper(); evidence['helper'] = helper.ready
        store = RecoveryStore(f.schema, create=True); observer = RecoveryStore(f.schema)
        controller = Controller(store, helper)

        def prepare(name):
            f.new_run(name); assignment = f.assign(name)
            binding = store.prepare(f.tokens['workerA'], helper.generation, **f.binding(assignment))
            helper.request('register', binding=binding)
            return assignment, binding

        def live(name, crash=False):
            assignment, binding = prepare(name)
            store.consume(f.tokens['workerA'], binding['job'])
            result = helper.request('launch', binding=binding, crash_after_launch=crash)
            if not crash:
                store.record_resource(binding['job'], result['resource'])
            return assignment, binding, result

        def retry_denied(a, b):
            blocked(lambda: store.prepare(f.tokens['workerA'], helper.generation, **f.binding(a)))
            blocked(lambda: store.consume(f.tokens['workerA'], b['job']), 'E_STALE')
            blocked(lambda: store.success(b['job']), 'E_FAILED_EXECUTION')

        # E01 controller owns DB state, parent transport relay survives its abrupt loss.
        a, b = prepare('eController')
        parent, endpoint = mp.Pipe()
        proc = mp.Process(target=controller_child, args=(f.schema, b['job'], f.tokens['workerA'], 'launch', endpoint))
        proc.start(); endpoint.close(); children.append(proc)
        require(parent.poll(35), 'Controller did not request launch')
        req = parent.recv(); require(req['op'] == 'launch', 'Unexpected relay command')
        launched = helper.request(req['op'], **req['body']); parent.send({'result': launched})
        require(parent.poll(15) and parent.recv().get('active'), 'Controller did not commit resource')
        proc.terminate(); proc.join(10)
        require(not proc.is_alive() and proc.exitcode != 0, 'Controller not killed')
        parent.close()
        orphan = helper.request('discover', binding=b)
        require(orphan['running'] and observer.job(b['job'])['state'] == 'consumed', 'Controller crash did not leave live orphan')
        store.mark_lost(b['job']); retry_denied(a, b)
        # Fresh OS process attaches durable state; parent forwards transport only.
        parent, endpoint = mp.Pipe()
        replacement = mp.Process(target=controller_child, args=(f.schema, b['job'], None, 'reconcile', endpoint))
        replacement.start(); endpoint.close(); children.append(replacement)
        while True:
            require(parent.poll(35), 'Replacement controller response timeout')
            reply = parent.recv()
            if 'op' not in reply:
                require('reconciled' in reply, 'Replacement reconciliation failed')
                proof = reply['reconciled']; break
            result = helper.request(reply['op'], **reply['body'])
            parent.send({'result': result})
        replacement.join(10); parent.close()
        require(replacement.exitcode == 0 and replacement.pid != proc.pid, 'No fresh successful replacement controller')
        require(observer.job(b['job'])['state'] == 'failed' and not observer.job(b['job'])['incident_open'], 'Recovery not finalized')
        blocked(lambda: f.check(a), 'E_STALE')
        retry_denied(a, b)
        newer = f.assign('eController', expected=1)
        blocked(lambda: store.prepare(f.tokens['workerA'], helper.generation, **f.binding(newer)), 'E_UNRESOLVED')
        checks['E01'] = {'status': 'PASS', 'controllerPid': proc.pid, 'actualExitCode': proc.exitcode,
                         'replacementControllerPid': replacement.pid, 'replacementExitCode': replacement.exitcode,
                         'liveOrphanBeforeRecovery': orphan, 'cleanup': proof, 'executionState': 'failed'}

        # E02 actual Linux transport helper exits after fsynced identity, no launch result.
        a, b, lost = live('eHelper', crash=True)
        require(lost.get('crashed') and lost['exitCode'] == 73 and observer.job(b['job'])['resource'] is None,
                'Helper crash point wrong')
        orphan = helper.request('discover', binding=b)
        require(orphan['running'] and orphan['childPid'] != lost['childPid'], 'No replacement helper/live orphan')
        retry_denied(a, b)
        proof = controller.reconcile(b['job'])
        require(observer.job(b['job'])['state'] == 'failed', 'Missed launch result not recovered')
        checks['E02'] = {'status': 'PASS', 'actualHelperCrash': lost, 'replacementDiscovery': orphan,
                         'serverResourceBeforeRecovery': None, 'cleanup': proof}

        # E03 witness outages, identity negatives and ordered epoch publication.
        a, b, launch = live('eOrdering')
        store.mark_lost(b['job'])
        parent, endpoint = mp.Pipe()
        disconnected = mp.Process(target=controller_child, args=(f.schema, b['job'], None, 'publish', endpoint))
        disconnected.start(); endpoint.close(); children.append(disconnected)
        require(parent.poll(15) and parent.recv()['op'] == 'fence', 'No real pending relay request')
        parent.close()  # Actual EOF at the IPC boundary before Linux command dispatch.
        disconnected.join(10)
        require(not disconnected.is_alive() and observer.job(b['job'])['epoch'] == 0
                and observer.job(b['job'])['incident_open'], 'Disconnected controller published authority')
        require(helper.request('discover', binding=b)['running'], 'Relay disconnect mutated resource')
        retry_denied(a, b)
        helper.request('witness_access', available=False)
        denied_helper(lambda: controller.reconcile(b['job']))
        require(observer.job(b['job'])['epoch'] == 0 and observer.job(b['job'])['incident_open'], 'Outage published authority')
        helper.request('witness_access', available=True)
        row = store.begin(b['job'], helper)
        resource = launch['resource']
        negatives = {}
        for field, value in (('job', 'f' * 32), ('generation', 'f' * 32), ('fence', b['fence'] + 1)):
            altered = {**b, field: value}
            negatives[field] = denied_helper(lambda: helper.request('cleanup', binding=altered, epoch=1, expected_resource=resource))
        for field in ('containerId', 'cgroup', 'processes'):
            altered = copy.deepcopy(resource)
            if field == 'containerId': altered[field] = 'f' * 64
            elif field == 'cgroup': altered[field] += '-wrong'
            else:
                original = next(iter(altered[field].values()))
                original['startTime'] = str(int(original['startTime']) + 1)
            negatives[field] = denied_helper(lambda: helper.request('cleanup', binding=b, epoch=1, expected_resource=altered))
        require(helper.request('discover', binding=b)['running'], 'Negative cleanup mutated live orphan')
        helper.request('pause_cleanup', binding=b, epoch=1, expected_resource=resource)
        parent, endpoint = mp.Pipe()
        proc = mp.Process(target=controller_child, args=(f.schema, b['job'], None, 'publish', endpoint))
        proc.start(); endpoint.close(); children.append(proc)
        require(parent.poll(15), 'Publisher did not reach witness boundary')
        req = parent.recv(); require(req['op'] == 'fence' and req['body']['epoch'] == 2, 'Wrong publication boundary')
        require(observer.job(b['job'])['epoch'] == 1, 'New epoch visible before witness fence')
        fenced = helper.request(req['op'], **req['body'])
        require(observer.job(b['job'])['epoch'] == 1, 'Uncommitted epoch became visible')
        parent.send({'result': fenced})
        require(parent.poll(15) and parent.recv().get('published') == 2, 'Publication failed')
        proc.join(10); parent.close(); require(proc.exitcode == 0 and observer.job(b['job'])['epoch'] == 2, 'Epoch not committed')
        stale = denied_helper(lambda: helper.request('resume_cleanup', binding=b))
        require(helper.request('discover', binding=b)['running'], 'Stale resumed cleanup stopped resource')
        proof = helper.request('cleanup', binding=b, epoch=2, expected_resource=resource)
        store.finish(b['job'], 2, proof)
        checks['E03'] = {'status': 'PASS', 'missingWitnessDeniedWithIncident': True, 'identityDenials': negatives,
                         'actualRelayDisconnectBeforeDispatch': {'controllerPid': disconnected.pid, 'exitCode': disconnected.exitcode,
                                                                 'DBEpoch': 0, 'incidentOpen': True, 'resourceStillRunning': True},
                         'independentControllerPid': proc.pid, 'DBEpochBeforeWitnessAndCommit': 1,
                         'DBEpochAfterPublication': 2, 'stalePausedCleanupDenial': stale,
                         'resourceStillRunningAfterStaleCommand': True, 'cleanup': proof}

        # E04 missing proof/replay blocks success; late exact cleanup keeps failed history.
        a, b, launch = live('eLate')
        store.mark_lost(b['job']); row = store.begin(b['job'], helper)
        blocked(lambda: store.finish(b['job'], row['epoch'], {}), 'E_UNRESOLVED')
        blocked(lambda: store.finish(b['job'], row['epoch'] + 1, checks['E03']['cleanup']), 'E_UNRESOLVED')
        retry_denied(a, b)
        require(observer.job(b['job'])['incident_open'] and helper.request('discover', binding=b)['running'], 'Missing proof changed state')
        proof = helper.request('cleanup', binding=b, epoch=row['epoch'], expected_resource=launch['resource'])
        store.finish(b['job'], row['epoch'], proof)
        blocked(lambda: store.finish(b['job'], row['epoch'], proof), 'E_UNRESOLVED')
        replay = denied_helper(lambda: helper.request('cleanup', binding=b, epoch=row['epoch'], expected_resource=launch['resource']))
        require(observer.job(b['job'])['state'] == 'failed' and not observer.job(b['job'])['incident_open'], 'Late cleanup rewrote failure')
        checks['E04'] = {'status': 'PASS', 'missingAndStaleProofDenied': True, 'cleanup': proof,
                         'replayDenial': replay, 'lateState': 'failed', 'automaticRetry': False}

        # E05 witness advanced then controller fails before DB commit: never repair by guessing.
        a, b, launch = live('eUncertainCommit')
        store.mark_lost(b['job'])
        class LostCommit:
            def request(self, op, **body):
                helper.request(op, **body)
                raise RuntimeError('Injected loss after external witness before DB commit')
        denied_helper(lambda: store.begin(b['job'], LostCommit()))
        require(observer.job(b['job'])['epoch'] == 0 and observer.job(b['job'])['incident_open'], 'Rollback did not preserve incident')
        mismatch = denied_helper(lambda: controller.reconcile(b['job']))
        require(observer.job(b['job'])['epoch'] == 0 and helper.request('discover', binding=b)['running'], 'Mismatch guessed latest authority')
        blocked(lambda: controller.reconcile('0' * 32), 'E_UNRESOLVED')
        retry_denied(a, b)
        # Exact safety teardown uses the witness epoch this fixture actually observed.
        # It is deliberately NOT acknowledged to the stale server row.
        safety = helper.request('cleanup', binding=b, epoch=1, expected_resource=launch['resource'])
        require(observer.job(b['job'])['cleanup_proof'] is None and observer.job(b['job'])['incident_open'], 'Safety teardown fabricated reconciliation')
        checks['E05'] = {'status': 'PASS', 'witnessAdvancedButDBEpoch': 0, 'mismatchDenial': mismatch,
                         'missingJobAuthorityDenied': True, 'serverState': 'unresolved', 'incidentOpen': True,
                         'exactSafetyTeardownOnly': safety, 'serverCleanupAcknowledged': False}
        # E06 a new attempt/head must never be fenced by recovery for the old job.
        a, b, launch = live('eAdvancedHead')
        f.svc('retire', **f.binding(a)); newer = f.assign('eAdvancedHead', expected=1)
        store.mark_lost(b['job'])
        before = observer.conn.execute('SELECT * FROM b_heads WHERE project=%s AND run_id=%s', ('pA', 'eAdvancedHead')).fetchone()
        blocked(lambda: controller.reconcile(b['job']), 'E_UNRESOLVED')
        after = observer.conn.execute('SELECT * FROM b_heads WHERE project=%s AND run_id=%s', ('pA', 'eAdvancedHead')).fetchone()
        require(before == after and helper.request('discover', binding=b)['running'], 'Old recovery mutated newer authority/resource')
        f.check(newer)
        helper.request('fence', binding=b, epoch=1)
        safety = helper.request('cleanup', binding=b, epoch=1, expected_resource=launch['resource'])
        require(observer.job(b['job'])['incident_open'] and observer.job(b['job'])['cleanup_proof'] is None, 'Safety teardown acknowledged stale authority')
        checks['E06'] = {'status': 'PASS', 'newHeadBefore': before, 'newHeadAfter': after,
                         'newAssignmentStillLive': True, 'oldResourceRunningAfterDenial': True,
                         'exactSafetyTeardownOnly': safety, 'oldJobStillUnresolved': True}
        # E07 competing scheduler cannot publish a new head during destructive cleanup.
        a, b, launch = live('eHeldCleanup')
        store.mark_lost(b['job']); row = store.begin(b['job'], helper)
        parent, endpoint = mp.Pipe()
        cleaner = mp.Process(target=controller_child, args=(f.schema, b['job'], None, 'cleanup', endpoint))
        cleaner.start(); endpoint.close(); children.append(cleaner)
        require(parent.poll(15), 'Cleanup did not reach locked external effect')
        req = parent.recv(); require(req['op'] == 'cleanup', 'Wrong cleanup boundary')
        other, endpoint = mp.Pipe()
        scheduler = mp.Process(target=assign_child, args=(f.schema, f.tokens['schedA'], 'eHeldCleanup', endpoint))
        scheduler.start(); endpoint.close(); children.append(scheduler)
        require(other.poll(15) and other.recv().get('started'), 'Scheduler did not start')
        deadline = time.monotonic() + 8; locked = False
        while time.monotonic() < deadline:
            locked = observer.conn.execute("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND application_name='s2-synthetic-spike' AND wait_event_type='Lock') AS held").fetchone()['held']
            if locked: break
            time.sleep(.01)
        require(locked and not other.poll() and helper.request('discover', binding=b)['running'], 'Scheduler was not blocked by cleanup mutex')
        proof = helper.request(req['op'], **req['body']); parent.send({'result': proof})
        require(parent.poll(15) and parent.recv().get('cleaned'), 'Locked cleanup failed')
        require(other.poll(15) and other.recv().get('assignment'), 'Scheduler did not resume after cleanup')
        for proc in (cleaner, scheduler):
            proc.join(10); require(proc.exitcode == 0, 'Concurrent process failed')
        parent.close(); other.close()
        require(observer.job(b['job'])['state'] == 'failed', 'Cleanup transaction not committed')
        checks['E07'] = {'status': 'PASS', 'cleanupControllerPid': cleaner.pid, 'schedulerPid': scheduler.pid,
                         'observedDBLockWaitThroughExternalCleanup': True, 'newAssignmentOnlyAfterCleanupCommit': True,
                         'cleanup': proof}
        metadata = json.dumps({t: observer.conn.execute('SELECT * FROM ' + t).fetchall()
                               for t in ('e_jobs', 'b_audit', 'app_runs', 'app_delegations')}, default=str).encode()
        require(not contains_secret(metadata, forbidden), 'Credential in metadata')
        evidence['credentialMetadataScan'] = 'PASS'
    finally:
        for proc in children:
            if proc.is_alive(): proc.terminate(); proc.join(10)
        if observer: observer.close()
        if store: store.close()
        if helper: evidence['postRunHelper'] = helper.close()
        f.close()


def contains_secret(data, forbidden):
    return any(x in data or base64.b64encode(x) in data or x.hex().encode() in data for x in forbidden)


def inputs():
    paths = []
    for folder in ('spikes/s4e', 'spikes/s4c', 'spikes/s4b', 'spikes/s4', 'spikes/iapb', 'spikes/iap', 'spikes/s6b', 'spikes/s2'):
        paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.append(ROOT / 'docs/S4-E-PROTOCOL.md')
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    if len(sys.argv) != 2: raise SystemExit('Use fresh docs/s4e-results/<id>.json')
    dest = (ROOT / sys.argv[1]).resolve()
    if dest.parent != (ROOT / 'docs/s4e-results').resolve() or dest.exists() or dest.suffix != '.json':
        raise SystemExit('Use fresh S4-E evidence path')
    CACHE.mkdir(parents=True, exist_ok=True)
    evidence = {'evidenceVersion': VERSION, 'classification': 'synthetic-only',
                'baseline': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'startedAt': datetime.now(timezone.utc).isoformat(), 'status': 'RUNNING', 'inputsBefore': inputs(),
                'preflight': inventory(), 'databasePreflight': db_inventory()}
    forbidden = []; begin = time.monotonic(); output = io.StringIO(); errors = io.StringIO()
    try:
        require(evidence['preflight']['ready'] and evidence['databasePreflight']['toolchainReady'], 'Pinned prerequisites not ready')
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors): experiment(evidence, forbidden)
        require(not contains_secret((output.getvalue() + errors.getvalue()).encode(), forbidden), 'Credential in diagnostics')
        evidence['credentialDiagnosticsScan'] = 'PASS'; evidence['inputsAfter'] = inputs()
        require(evidence['inputsBefore'] == evidence['inputsAfter'], 'Source changed during run')
        evidence['status'] = 'PASS'
    except Exception as error:
        evidence['status'] = 'ERROR'; evidence['errorType'] = type(error).__name__
        detail = traceback.format_exc().encode()
        require(not contains_secret(detail, forbidden), 'Credential in error diagnostics')
        (CACHE / (dest.stem + '-error.log')).write_bytes(detail)
    evidence['elapsedSeconds'] = time.monotonic() - begin
    evidence['finishedAt'] = datetime.now(timezone.utc).isoformat()
    encoded = json.dumps(evidence, indent=2, default=str).encode()
    require(not contains_secret(encoded, forbidden), 'Credential in evidence')
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('xb') as stream: stream.write(encoded + b'\n')
    print(json.dumps({'status': evidence['status'], 'elapsedSeconds': evidence['elapsedSeconds'],
                      'checks': {k: v['status'] for k, v in evidence.get('checks', {}).items()}}))
    return 0 if evidence['status'] == 'PASS' else 2


if __name__ == '__main__':
    mp.freeze_support(); raise SystemExit(main())
