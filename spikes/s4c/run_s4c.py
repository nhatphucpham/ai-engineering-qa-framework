"""Actual Windows DB authority -> rootless Linux engine; synthetic fixed jobs only."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spikes/iapb'))
from run_iapb import AuthorityFixture, require, blocked, wait_due, inventory, db_inventory
from authority import _AuthorityStore, Denied
from gate import WorkerBridge, VERSION
import base64
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import queue
import subprocess
import threading
import time
import traceback
import uuid

CACHE = ROOT / '.cache/s6/s4-c'


class Helper:
    def __init__(self):
        self.unit = 'qa-s4-c-' + uuid.uuid4().hex[:12]
        linux_root = subprocess.check_output(['wsl.exe', '-d', 'Ubuntu-24.04', '--', 'wslpath', '-a', ROOT.as_posix()], text=True).strip()
        self.argv = ['wsl.exe', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'systemd-run',
                     '--unit=' + self.unit, '--wait', '--pipe', '--collect',
                     '--property=User=phucpn', '--property=Group=phucpn', '--property=Delegate=yes',
                     '--property=DelegateSubgroup=supervisor', '--property=MemoryMax=512M',
                     '--property=TasksMax=256', '--property=RuntimeMaxSec=120',
                     '/usr/bin/python3', '-B', linux_root + '/spikes/s4c/engine_helper.py']
        self.stderr_path = CACHE / (self.unit + '-stderr.log')
        self.stderr = self.stderr_path.open('xb')
        self.proc = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
                                     text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
        self.lines = queue.Queue(); self.broken = False
        def reader():
            for line in self.proc.stdout:
                self.lines.put(line)
            self.lines.put(None)
        threading.Thread(target=reader, daemon=True).start()
        try:
            self.ready = self.receive()
            require(self.ready.get('ready') and self.ready.get('hostUid') == 1000, 'Helper not rootless ready')
            self.generation = self.ready['generation']
        except Exception:
            self.close()
            raise

    def receive(self):
        try:
            line = self.lines.get(timeout=35)
            require(line is not None, 'Helper ended before response')
            return json.loads(line)
        except Exception:
            self.broken = True
            raise RuntimeError('E_HELPER_CHANNEL') from None

    def request(self, op, *, job):
        if self.broken:
            raise RuntimeError('E_HELPER_CHANNEL')
        self.proc.stdin.write(json.dumps({'op': op, 'job': job}) + '\n'); self.proc.stdin.flush()
        reply = self.receive()
        if not reply.get('ok'):
            raise RuntimeError('E_HELPER')
        return reply['result']

    def close(self):
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'systemctl', 'stop', self.unit],
                           capture_output=True, timeout=20, check=True)
            self.proc.wait(timeout=10)
        finally:
            self.stderr.close()
        require(self.proc.returncode == 0, 'Helper/unit failed')
        result = subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', 'systemctl', 'show', self.unit,
                                 '--property=LoadState'], capture_output=True, text=True, timeout=10)
        absent = subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', 'test', '!', '-e',
                                 '/sys/fs/cgroup/system.slice/' + self.unit + '.service'], timeout=10).returncode == 0
        require('LoadState=not-found' in result.stdout and absent, 'Transient unit/cgroup remain')
        return {'unit': self.unit, 'loadStateNotFound': True, 'cgroupAbsent': True, 'helperExit': self.proc.returncode}


def experiment(evidence, forbidden):
    f = AuthorityFixture(forbidden); helper = None; bridge = None
    evidence['schema'] = f.schema; checks = evidence['checks'] = {}
    try:
        for sid, kind in [('schedA', 'scheduler'), ('workerA', 'worker'), ('workerB', 'worker')]:
            f.enroll(sid, kind)
        helper = Helper(); evidence['helper'] = helper.ready
        bridge = WorkerBridge(f.schema, helper)
        observer = _AuthorityStore(f.schema)
        def state(job):
            return observer.conn.execute('SELECT state,container_id FROM launch_jobs WHERE id=%s', (job,)).fetchone()
        def prepare(assignment, worker='workerA'):
            return bridge.dispatch('prepare', version=VERSION, credential=f.tokens[worker], **f.binding(assignment))['jobId']
        def release(job, worker='workerA'):
            return bridge.dispatch('release', version=VERSION, credential=f.tokens[worker], job_id=job)
        try:
            f.new_run('denials'); assignment = f.assign('denials'); binding = f.binding(assignment)
            blocked(lambda: prepare(assignment, 'workerB'), 'E_DENIED')
            for key, value in [('project', 'pB'), ('attempt', 2), ('fence', 2)]:
                blocked(lambda: bridge.dispatch('prepare', version=VERSION, credential=f.tokens['workerA'], **{**binding, key: value}))
            for route, extra in [('prepare', {'authorized': True}), ('prepare', {'cleaned': True}), ('cleanup', {})]:
                blocked(lambda: bridge.dispatch(route, version=VERSION, credential=f.tokens['workerA'], **binding, **extra), 'E_INPUT')
            blocked(lambda: bridge.dispatch('prepare', version='wrong', credential=f.tokens['workerA'], **binding), 'E_INPUT')
            require(observer.conn.execute('SELECT count(*) AS n FROM launch_jobs').fetchone()['n'] == 0, 'Invalid prepare persisted')
            f.new_run('revokeBefore'); before = f.assign('revokeBefore', worker='workerB'); before_job = prepare(before, 'workerB')
            f.admin('revoke_service', service_id='workerB')
            blocked(lambda: release(before_job, 'workerB'), 'E_AUTH')
            no_launch = helper.request('registered', job=before_job)
            require(no_launch['launchCount'] == 0 and no_launch['privateContainerCount'] == 0 and state(before_job)['state'] == 'prepared', 'Revoke launched work')
            bridge._cleanup(before_job)
            f.new_run('expired'); expired = f.assign('expired', ttl_ms=1000); expired_job = prepare(expired)
            wait_due(f.store.conn, 'SELECT expires<=clock_timestamp() AS due FROM b_assignments WHERE id=%s', (expired['assignmentId'],))
            blocked(lambda: release(expired_job), 'E_STALE')
            require(helper.request('registered', job=expired_job)['launchCount'] == 0, 'Expired assignment launched')
            bridge._cleanup(expired_job)
            checks['C01'] = {'status': 'PASS', 'invalidBindingsPersistedJobs': 0, 'revokeBeforeConsumeLaunches': 0,
                              'actualDBAssignmentExpiryDenied': True, 'publicAuthorityCleanupFlagsDenied': True}

            f.new_run('liveWork'); live = f.assign('liveWork'); job = prepare(live)
            observed = release(job)
            require(observed['processCount'] >= 3 and observed['launchCount'] == 1 and state(job)['state'] == 'consumed', 'Valid release not observed')
            blocked(lambda: release(job), 'E_STALE')
            require(helper.request('registered', job=job)['launchCount'] == 1, 'Duplicate effect')
            require(bridge.supervise(job) == {'authority': 'LIVE'}, 'Live check failed')
            checks['C02'] = {'status': 'PASS', 'actualLaunch': observed, 'committedState': 'consumed', 'duplicateReleaseDeniedNoSecondLaunch': True}

            f.admin('revoke_service', service_id='workerA')
            require(state(job)['state'] == 'consumed', 'Revoke fabricated cleanup')
            blocked(lambda: bridge.dispatch('cleanup', version=VERSION, credential=f.tokens['workerA'], job_id=job, clean=True), 'E_INPUT')
            try:
                bridge._cleanup(uuid.uuid4().hex)
            except RuntimeError:
                pass
            else:
                raise AssertionError('Unknown helper job cleanup accepted')
            blocked(lambda: bridge._store.observed(job, uuid.uuid4().hex, cleaned=True), 'E_STALE')
            require(state(job)['state'] == 'consumed' and helper.request('registered', job=job)['containerRunningObserved'],
                    'Wrong-job/generation ack changed live resource or state')
            cleanup = bridge.supervise(job)
            require(cleanup['authority'] == 'DENIED' and state(job)['state'] == 'cleaned', 'Revoke cleanup unconfirmed')
            try:
                bridge._cleanup(job)
            except RuntimeError:
                pass
            else:
                raise AssertionError('Cleanup replay accepted')
            checks['C03'] = {'status': 'PASS', 'beforeObservationState': 'consumed', 'afterObservationState': 'cleaned',
                              'supervision': cleanup, 'publicForgedAckAndHelperReplayDenied': True,
                              'unknownJobAndWrongGenerationDeniedWithOriginalStillRunningAndConsumed': True,
                              'continuousPollingAndActiveAppCancel': 'NOT RUN'}

            f.enroll('workerC')
            f.new_run('uncertain'); uncertain = f.assign('uncertain', worker='workerC'); uncertain_job = prepare(uncertain, 'workerC')
            def fault():
                raise RuntimeError('synthetic post-consume failure')
            try:
                bridge._release(f.tokens['workerC'], uncertain_job, after_consume=fault)
            except RuntimeError:
                pass
            else:
                raise AssertionError('Post-consume failure missing')
            require(state(uncertain_job)['state'] == 'consumed', 'Uncertainty not durable')
            blocked(lambda: release(uncertain_job, 'workerC'), 'E_STALE')
            # Metadata retirement/reassignment still cannot bypass outstanding actual job.
            f.svc('retire', **f.binding(uncertain)); newer = f.assign('uncertain', worker='workerC', expected=1)
            blocked(lambda: prepare(newer, 'workerC'), 'E_UNRESOLVED')
            original_request = helper.request
            def unavailable(*args, **kwargs):
                raise RuntimeError('synthetic channel outage')
            helper.request = unavailable
            try:
                try:
                    bridge._cleanup(uncertain_job)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('Failed cleanup accepted')
                require(state(uncertain_job)['state'] == 'consumed', 'Failed observation marked cleaned')
            finally:
                helper.request = original_request
            observation = bridge._cleanup(uncertain_job)
            require(observation['neverDispatched'] and observation['launchCount'] == 1 and state(uncertain_job)['state'] == 'cleaned', 'Uncertain cleanup wrong')
            checks['C04'] = {'status': 'PASS', 'actualPostConsumeFaultState': 'consumed', 'duplicateDispatchDenied': True,
                              'metadataRetireNewAttemptBlockedUntilCleanup': True, 'cleanupOutageState': 'consumed',
                              'observedNeverDispatchedCleanup': observation, 'automaticRetryOrCrashReconciliation': 'NOT RUN'}

            metadata = json.dumps({t: observer.conn.execute('SELECT * FROM ' + t).fetchall()
                                   for t in ('launch_jobs', 'b_audit', 'app_runs', 'app_delegations')}, default=str).encode()
            require(not any(t in metadata or base64.b64encode(t) in metadata or t.hex().encode() in metadata for t in forbidden), 'Credential leaked into metadata')
            evidence['credentialMetadataScan'] = 'PASS'
        finally:
            observer.close()
    finally:
        if bridge is not None:
            bridge.close()
        if helper is not None:
            evidence['postRunHelper'] = helper.close()
        f.close()


def inputs():
    paths = []
    for folder in ('spikes/s4c', 'spikes/s4b', 'spikes/s4', 'spikes/iapb', 'spikes/iap', 'spikes/s6b', 'spikes/s2'):
        paths += [p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT / 'docs/S4-C-PROTOCOL.md']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Use fresh docs/s4c-results/<id>.json')
    dest = (ROOT / sys.argv[1]).resolve()
    if dest.parent != (ROOT / 'docs/s4c-results').resolve() or dest.exists() or dest.suffix != '.json':
        raise SystemExit('Use fresh S4-C evidence path')
    CACHE.mkdir(parents=True, exist_ok=True)
    evidence = {'evidenceVersion': VERSION, 'classification': 'synthetic-only',
                'baseline': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'startedAt': datetime.now(timezone.utc).isoformat(), 'inputsBefore': inputs(), 'status': 'RUNNING',
                'preflight': inventory(), 'databasePreflight': db_inventory(),
                'limits': ['Trusted local Windows DB/controller and owned rootless Linux helper pipe, no TLS/remote worker authentication',
                           'Selected one-use launch admission and next explicit supervision cleanup only, no continuous polling guarantee',
                           'No application cancel/complete/retry, crash recovery, broker/content export or product readiness']}
    forbidden = []; begin = time.monotonic(); stdout = io.StringIO(); stderr = io.StringIO()
    try:
        require(evidence['preflight']['ready'] and evidence['databasePreflight']['toolchainReady'], 'Pinned prerequisites not ready')
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            experiment(evidence, forbidden)
        captured = (stdout.getvalue() + stderr.getvalue()).encode()
        require(not any(t in captured or base64.b64encode(t) in captured or t.hex().encode() in captured for t in forbidden), 'Credential in diagnostics')
        evidence['credentialDiagnosticsScan'] = 'PASS'
        evidence['inputsAfter'] = inputs(); require(evidence['inputsBefore'] == evidence['inputsAfter'], 'Source changed')
        evidence['status'] = 'PASS'
    except Exception as error:
        evidence['status'] = 'ERROR'; evidence['errorType'] = type(error).__name__
        (CACHE / (dest.stem + '-error.log')).write_text(traceback.format_exc(), encoding='utf-8')
    evidence['elapsedSeconds'] = time.monotonic() - begin; evidence['finishedAt'] = datetime.now(timezone.utc).isoformat()
    encoded = json.dumps(evidence, indent=2).encode()
    require(not any(t in encoded or base64.b64encode(t) in encoded or t.hex().encode() in encoded for t in forbidden), 'Credential in evidence')
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('xb') as stream:
        stream.write(encoded + b'\n')
    print(json.dumps({'status': evidence['status'], 'elapsedSeconds': evidence['elapsedSeconds'],
                      'checks': {k: v['status'] for k, v in evidence.get('checks', {}).items()}}))
    return 0 if evidence['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
