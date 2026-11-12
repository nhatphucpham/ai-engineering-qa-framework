"""Actual DB-only service/delegation/attempt authority probes; no workload launch."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spikes/iap'))
from run_iap import Fixture, blocked, require
from application import Denied, Jsonb
from identity import digest
from local import inventory as db_inventory, start, stop
from preflight_b import inventory
from authority import _AuthorityStore, AdminServices, ServiceAuthority, VERSION
import base64
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import multiprocessing as mp
import secrets
import subprocess
import time
import traceback
import psycopg

CACHE = ROOT / '.cache/s6/iap-b'


class AuthorityFixture(Fixture):
    def __init__(self, forbidden):
        super().__init__(forbidden)
        self.store = _AuthorityStore(self.schema, create=True)
        self.admin_api = AdminServices(self.schema)
        self.service_api = ServiceAuthority(self.schema)
        self.tokens = {}
        self.epoch = 1

    def close(self):
        self.store.close(); self.admin_api.close(); self.service_api.close()
        super().close()

    def admin(self, route, user='admin', **body):
        return self.admin_api.dispatch(route, version=VERSION, access=self.users[user]['access'], **body)

    def enroll(self, service_id, kind='worker', projects=None):
        result = self.admin('create_service', service_id=service_id, kind=kind, projects=projects or ['pA'])
        self.forbidden.append(result['credential'].encode())
        self.tokens[service_id] = result['credential']
        return result

    def login_short(self, access_ms=500):
        # Existing per-name throttle is real; wait only for its DB window.
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            row = self.raw.conn.execute("""SELECT attempts<3 OR window_start<clock_timestamp()-interval '1 second' AS ok
                FROM login_buckets WHERE bucket=%s""", (hashlib.sha256(b'runner').hexdigest(),)).fetchone()
            if row is None or row['ok']:
                return self.keep(self.raw.identity.login('runner', self.passwords['runner'], access_ms=access_ms))
            time.sleep(.01)
        raise AssertionError('Login throttle window did not reopen')

    def new_run(self, run_id, access=None):
        grant = self.grant(epoch=self.epoch)
        body = self.start_body(run_id, grant, epoch=self.epoch)
        if access is not None:
            body['access'] = access
        self.start(body)
        return grant

    def svc(self, route, service='schedA', **body):
        return self.service_api.dispatch(route, version=VERSION, credential=self.tokens[service], **body)

    def assign(self, run_id, worker='workerA', expected=0, ttl_ms=20000):
        return self.svc('assign', project='pA', run_id=run_id, worker_id=worker, expected_attempt=expected, ttl_ms=ttl_ms)

    @staticmethod
    def binding(assignment):
        return {'project': assignment['project'], 'run_id': assignment['runId'],
                'assignment_id': assignment['assignmentId'], 'attempt': assignment['attempt'], 'fence': assignment['fence']}

    def check(self, assignment, worker='workerA'):
        return self.svc('check', worker, **self.binding(assignment))

    def counts(self, run_id):
        observer = _AuthorityStore(self.schema)
        try:
            result = {}
            for table in ('b_heads', 'b_assignments', 'b_audit'):
                result[table] = observer.conn.execute('SELECT count(*) AS n FROM ' + table + ' WHERE project=%s AND run_id=%s',
                                                      ('pA', run_id)).fetchone()['n']
            return result
        finally:
            observer.close()


def wait_due(conn, query, args):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if conn.execute(query, args).fetchone()['due']:
            return
        time.sleep(.01)
    raise AssertionError('DB expiry deadline not reached')


def child(schema, route, body, first, entered, release, started, pipe):
    raw = _AuthorityStore(schema)
    admin = AdminServices(schema); service = ServiceAuthority(schema)
    try:
        started.set()
        try:
            if first:
                with raw.identity.tx():
                    result = getattr(raw, route)(**body)
                    entered.set(); require(release.wait(12), 'Ordered release timeout')
            else:
                facade = admin if route == 'revoke_service' else service
                result = facade.dispatch(route, version=VERSION, **body)
            pipe.send({'status': 'accepted', 'result': result})
        except Denied as error:
            pipe.send({'status': 'denied', 'code': error.code})
    finally:
        raw.close(); admin.close(); service.close(); pipe.close()


def ordered(schema, first, second):
    entered, release = mp.Event(), mp.Event()
    children, pipes = [], []
    try:
        for i, (route, body) in enumerate((first, second)):
            started = mp.Event(); parent, endpoint = mp.Pipe()
            proc = mp.Process(target=child, args=(schema, route, body, i == 0, entered, release, started, endpoint))
            proc.start(); endpoint.close(); children.append(proc); pipes.append(parent)
            require(started.wait(12), 'Child start timeout')
            if i == 0:
                require(entered.wait(12), 'First unit not held')
        observer = _AuthorityStore(schema)
        try:
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                locked = observer.conn.execute("""SELECT EXISTS(SELECT 1 FROM pg_stat_activity
                    WHERE datname=current_database() AND pid<>pg_backend_pid()
                    AND application_name='s2-synthetic-spike' AND wait_event_type='Lock') AS held""").fetchone()['held']
                if locked:
                    break
                time.sleep(.01)
            require(locked, 'Actual contender DB lock wait not observed')
        finally:
            observer.close()
        release.set(); outcomes = []
        for pipe in pipes:
            require(pipe.poll(15), 'Ordered result timeout'); outcomes.append(pipe.recv())
        for proc in children:
            proc.join(10); require(proc.exitcode == 0, 'Child failed')
        return outcomes
    finally:
        release.set()
        for proc in children:
            if proc.is_alive():
                proc.kill(); proc.join(10)
        for pipe in pipes:
            pipe.close()


def experiment(evidence, forbidden):
    f = AuthorityFixture(forbidden)
    evidence['schema'] = f.schema; checks = evidence['checks'] = {}
    try:
        for sid, kind, projects in (('schedA', 'scheduler', ['pA']), ('workerA', 'worker', ['pA']),
                                    ('workerB', 'worker', ['pA']), ('outsider', 'worker', ['pB'])):
            f.enroll(sid, kind, projects)
        blocked(lambda: f.admin('create_service', 'owner', service_id='illegal', kind='worker', projects=['pA']), 'E_DENIED')
        blocked(lambda: f.admin_api.dispatch('create_service', version=VERSION, access=f.tokens['workerA'], service_id='fake', kind='worker', projects=['pA']), 'E_AUTH')
        stub = {'credential': f.users['runner']['access'], 'project': 'pA', 'run_id': 'absent',
                'assignment_id': '0' * 32, 'attempt': 1, 'fence': 1}
        blocked(lambda: f.service_api.dispatch('check', version=VERSION, **stub), 'E_AUTH')
        blocked(lambda: f.service_api.dispatch('check', version=VERSION, **{**stub, 'credential': f.tokens['schedA']}), 'E_AUTH')
        for route, extra in (('issue', {}), ('service_unit', {}), ('check', {'authorized': True}), ('check', {'before_finish': True})):
            blocked(lambda: f.service_api.dispatch(route, version=VERSION, **stub, **extra), 'E_INPUT')
        blocked(lambda: f.service_api.dispatch('check', version='unknown', **stub), 'E_INPUT')
        fake_start = f.start_body('serviceAsUser', f.grant()); fake_start['access'] = f.tokens['workerA']
        blocked(lambda: f.start(fake_start), 'E_AUTH')
        checks['B01'] = {'status': 'PASS', 'admin_only_enrollment': True, 'opaque_service_credentials': True,
                         'user_service_audience_kind_and_exact_routes_separate': True}

        auxiliary = f.login_short(access_ms=3000)
        f.new_run('afterLogout', auxiliary['access']); a = f.assign('afterLogout')
        f.idcall('logout', auxiliary)
        blocked(lambda: f.api.dispatch('receipt', version='iap-a-1.0.0', access=auxiliary['access'], project='pA',
                                      grant=f.raw.conn.execute("SELECT grant_id FROM app_delegations WHERE run_id='afterLogout'").fetchone()['grant_id'],
                                      operation='start', key='afterLogout'), 'E_AUTH')
        require(f.check(a)['assignmentId'] == a['assignmentId'], 'Logout incorrectly revoked background authority')
        short = f.login_short(access_ms=800)
        f.new_run('afterAccessExpiry', short['access']); b = f.assign('afterAccessExpiry')
        wait_due(f.raw.conn, 'SELECT expires<=clock_timestamp() AS due FROM access_tokens WHERE digest=%s', (digest(short['access'], 'a'),))
        blocked(lambda: f.identity.dispatch('grant', access=short['access'], project='pA', actions=['read']), 'E_AUTH')
        require(f.check(b)['assignmentId'] == b['assignmentId'], 'Access expiry incorrectly revoked background authority')
        reset = f.password(); f.idcall('account_reset', f.users['admin'], user='runner', new=reset)
        blocked(lambda: f.check(a), 'E_DENIED'); blocked(lambda: f.check(b), 'E_DENIED')
        f.users['runner'] = f.activate('runner', reset)
        blocked(lambda: f.check(a), 'E_DENIED')
        checks['B02'] = {'status': 'PASS', 'logout_and_DB_access_expiry_independent_of_service_delegation': True,
                         'reset_and_relogin_old_delegation_fenced': True}

        f.new_run('scopeRun'); scope = f.assign('scopeRun')
        f.new_run('otherRun')
        blocked(lambda: f.check(scope, 'workerB'), 'E_DENIED')
        blocked(lambda: f.check(scope, 'outsider'), 'E_AUTH')
        for changes in ({'run_id': 'otherRun'}, {'attempt': 2}, {'fence': scope['fence'] + 1}, {'assignment_id': '0' * 32}):
            blocked(lambda: f.svc('check', 'workerA', **{**f.binding(scope), **changes}), 'E_STALE')
        blocked(lambda: f.svc('check', 'workerA', **{**f.binding(scope), 'project': 'pB'}), 'E_AUTH')
        old_token = f.tokens['workerA']; result = f.admin('rotate', service_id='workerA')
        forbidden.append(result['credential'].encode()); f.tokens['workerA'] = result['credential']
        blocked(lambda: f.service_api.dispatch('check', version=VERSION, credential=old_token, **f.binding(scope)), 'E_AUTH')
        blocked(lambda: f.check(scope), 'E_DENIED')
        f.new_run('revokedWorker'); revoked = f.assign('revokedWorker', worker='workerB')
        f.admin('revoke_service', service_id='workerB')
        blocked(lambda: f.check(revoked, 'workerB'), 'E_AUTH')
        blocked(lambda: f.admin('rotate', service_id='workerB'), 'E_DENIED')
        f.enroll('expiredWorker'); f.new_run('expiredCredential'); expired = f.assign('expiredCredential', worker='expiredWorker')
        f.store.conn.execute("UPDATE b_credentials SET expires=clock_timestamp()-interval '1 second' WHERE service_id='expiredWorker'")
        blocked(lambda: f.check(expired, 'expiredWorker'), 'E_AUTH')
        checks['B03'] = {'status': 'PASS', 'cross_scope_worker_attempt_fence_substitution_denied': True,
                         'rotation_revoke_expired_credential_and_old_epoch_assignment_denied': True}

        gr = f.new_run('livePolicy'); live = f.assign('livePolicy')
        f.member('runner', 'Viewer'); blocked(lambda: f.check(live), 'E_DENIED')
        blocked(lambda: f.svc('renew', 'workerA', **f.binding(live), ttl_ms=20000), 'E_DENIED')
        blocked(lambda: f.assign('livePolicy', expected=1), 'E_DENIED')
        f.member('runner', None); blocked(lambda: f.check(live), 'E_DENIED')
        f.member('runner', 'Runner')
        f.idcall('project_enabled', f.users['admin'], project='pA', enabled=False)
        blocked(lambda: f.check(live), 'E_DENIED')
        f.idcall('project_enabled', f.users['admin'], project='pA', enabled=True)
        f.call('revoke', project='pA', grant=gr); blocked(lambda: f.check(live), 'E_DENIED')
        blocked(lambda: f.svc('renew', 'workerA', **f.binding(live), ttl_ms=20000), 'E_DENIED')
        cancel_grant = f.new_run('cancelledRun'); cancelled = f.assign('cancelledRun')
        f.call('cancel', project='pA', grant=cancel_grant, key='cancelledRunCommand', run_id='cancelledRun', expected_version=1)
        blocked(lambda: f.check(cancelled), 'E_DENIED')
        f.new_run('policyEpoch'); pol = f.assign('policyEpoch')
        cg = f.idcall('grant', f.users['owner'], project='pA', actions=['config'])
        f.call('configure', 'owner', project='pA', config_grant=cg, expected_epoch=1, enabled=True,
               allowed_actions=['cancel', 'receipt'], max_queued=100)
        blocked(lambda: f.check(pol), 'E_DENIED')
        blocked(lambda: f.assign('policyEpoch', expected=1), 'E_DENIED')
        f.call('configure', 'owner', project='pA', config_grant=cg, expected_epoch=2, enabled=True,
               allowed_actions=['start', 'cancel', 'receipt'], max_queued=100)
        f.epoch = 3; f.grant(epoch=3)
        blocked(lambda: f.check(pol), 'E_DENIED')
        checks['B04'] = {'status': 'PASS', 'live_role_project_grant_and_policy_fences': True,
                         'live_denials_cover_check_renew_assign': True, 'queued_cancel_fences_metadata_only': True,
                         'new_grant_policy_widening_does_not_rebind_old_run': True,
                         'membership_epoch_anti_rollback': 'NOT IMPLEMENTED; live role plus original ceiling only'}

        f.new_run('concurrentAssign')
        req = {'credential': f.tokens['schedA'], 'project': 'pA', 'run_id': 'concurrentAssign',
               'worker_id': 'workerA', 'expected_attempt': 0, 'ttl_ms': 20000}
        collision = ordered(f.schema, ('assign', req), ('assign', req))
        require([r['status'] for r in collision] == ['accepted', 'denied'] and collision[1]['code'] == 'E_STALE', 'Duplicate assignment accepted')
        require(f.counts('concurrentAssign') == {'b_heads': 1, 'b_assignments': 1, 'b_audit': 1}, 'Assignment graph not atomic')
        races = []
        for i in range(2):
            sid = 'raceWorker' + str(i); f.enroll(sid); run_id = 'revokeRace' + str(i); f.new_run(run_id)
            request = {**req, 'run_id': run_id, 'worker_id': sid}
            revoke = {'access': f.users['admin']['access'], 'service_id': sid}
            pair = (('assign', request), ('revoke_service', revoke)) if i == 0 else (('revoke_service', revoke), ('assign', request))
            out = ordered(f.schema, *pair)
            require(out[0]['status'] == 'accepted' and out[1]['status'] == ('accepted' if i == 0 else 'denied'), 'Revoke/assign ordering wrong')
            require(f.counts(run_id)['b_assignments'] == (1 if i == 0 else 0), 'Revoke-first created assignment')
            if i == 0:
                blocked(lambda: f.check(out[0]['result'], sid), 'E_AUTH')
            races.append([r['status'] for r in out])
        check_races = []
        for i in range(2):
            sid = 'checkRaceWorker' + str(i); f.enroll(sid)
            run_id = 'checkRevokeRace' + str(i); f.new_run(run_id)
            reservation = f.assign(run_id, worker=sid)
            check = {'credential': f.tokens[sid], **f.binding(reservation)}
            revoke = {'access': f.users['admin']['access'], 'service_id': sid}
            pair = (('check', check), ('revoke_service', revoke)) if i == 0 else (('revoke_service', revoke), ('check', check))
            out = ordered(f.schema, *pair)
            require([r['status'] for r in out] == (['accepted', 'accepted'] if i == 0 else ['accepted', 'denied']),
                    'Check/revoke ordering wrong')
            require(f.counts(run_id)['b_audit'] == (2 if i == 0 else 1), 'Check audit not ordered with revoke')
            blocked(lambda: f.check(reservation, sid), 'E_AUTH')
            check_races.append([r['status'] for r in out])
        checks['B05'] = {'status': 'PASS', 'two_process_assignment_collision': [r['status'] for r in collision],
                         'assign_before_revoke_and_revoke_before_assign': races,
                         'check_before_revoke_and_revoke_before_check': check_races, 'actual_DB_lock_wait_observed': True}

        f.new_run('renewRun'); renew = f.assign('renewRun', ttl_ms=3000)
        extended = f.svc('renew', 'workerA', **f.binding(renew), ttl_ms=20000)
        require(extended['expiresAt'] > renew['expiresAt'] and extended['attempt'] == renew['attempt'] and extended['fence'] == renew['fence'], 'Renew changed scope/fence or failed extension')
        blocked(lambda: f.assign('renewRun', expected=1), 'E_STALE')
        f.svc('retire', **f.binding(extended))
        blocked(lambda: f.check(extended), 'E_STALE')
        next_assignment = f.assign('renewRun', expected=1)
        require(next_assignment['attempt'] == 2 and next_assignment['fence'] > extended['fence'], 'Retirement/new attempt not monotonic')
        blocked(lambda: f.svc('renew', 'workerA', **f.binding(extended), ttl_ms=20000), 'E_STALE')
        f.new_run('expireAssignment'); exp = f.assign('expireAssignment', ttl_ms=250)
        wait_due(f.store.conn, 'SELECT expires<=clock_timestamp() AS due FROM b_assignments WHERE id=%s', (exp['assignmentId'],))
        blocked(lambda: f.check(exp), 'E_STALE')
        blocked(lambda: f.svc('renew', 'workerA', **f.binding(exp), ttl_ms=20000), 'E_STALE')
        blocked(lambda: f.assign('expireAssignment', expected=1), 'E_STALE')
        f.new_run('tentativeExpiry'); reached = []
        def expiry_hook():
            row = f.store.conn.execute("SELECT id FROM b_assignments WHERE run_id='tentativeExpiry'").fetchone()
            require(row is not None, 'Tentative assignment not present')
            reached.append(True)
            wait_due(f.store.conn, 'SELECT expires<=clock_timestamp() AS due FROM b_assignments WHERE id=%s', (row['id'],))
        blocked(lambda: f.store.assign(**{**req, 'run_id': 'tentativeExpiry', 'ttl_ms': 250}, before_finish=expiry_hook), 'E_STALE')
        require(reached == [True] and all(n == 0 for n in f.counts('tentativeExpiry').values()), 'Final expiry did not roll back whole metadata unit')
        f.new_run('tentativeRenewal'); prior = f.assign('tentativeRenewal', ttl_ms=600)
        original_deadline = f.store.conn.execute('SELECT expires FROM b_assignments WHERE id=%s', (prior['assignmentId'],)).fetchone()['expires']
        audit_before = f.counts('tentativeRenewal')['b_audit']; tentative_renewal = []
        def renewal_hook():
            row = f.store.conn.execute('SELECT expires FROM b_assignments WHERE id=%s', (prior['assignmentId'],)).fetchone()
            require(row['expires'] > original_deadline, 'Renewal did not tentatively extend deadline')
            tentative_renewal.append(True)
            wait_due(f.store.conn, 'SELECT %s<=clock_timestamp() AS due', (original_deadline,))
        blocked(lambda: f.store.renew(credential=f.tokens['workerA'], **f.binding(prior), ttl_ms=20000,
                                     before_finish=renewal_hook), 'E_STALE')
        observer = _AuthorityStore(f.schema)
        try:
            restored = observer.conn.execute('SELECT expires FROM b_assignments WHERE id=%s', (prior['assignmentId'],)).fetchone()['expires']
        finally:
            observer.close()
        require(tentative_renewal == [True] and restored == original_deadline
                and f.counts('tentativeRenewal')['b_audit'] == audit_before, 'Expired renewal did not restore original deadline/audit')
        blocked(lambda: f.check(prior), 'E_STALE')
        checks['B06'] = {'status': 'PASS', 'renew_same_scope_and_deadline_extension': True,
                         'expired_assignment_cannot_revive': True, 'retirement_new_attempt_fence': next_assignment['attempt'],
                         'tentative_assignment_final_expiry_full_rollback': True,
                         'tentative_renewal_old_deadline_expiry_restores_deadline_and_audit': True, 'actual_cleanup': 'NOT RUN'}

        f.new_run('commitFault')
        fault_req = {**req, 'run_id': 'commitFault'}
        f.store.conn.execute("""CREATE FUNCTION b_commit_fault() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.operation='assign' AND NEW.run_id='commitFault' THEN
                INSERT INTO b_audit(project,run_id,operation) VALUES('pA','absentRun','fault');
            END IF; RETURN NEW; END; $$""")
        f.store.conn.execute('CREATE TRIGGER commit_fault BEFORE INSERT ON b_audit FOR EACH ROW EXECUTE FUNCTION b_commit_fault()')
        try:
            blocked(lambda: f.service_api.dispatch('assign', version=VERSION, **fault_req), 'E_DEPENDENCY')
            try:
                f.store.assign(**fault_req)
            except psycopg.errors.ForeignKeyViolation as error:
                require(error.sqlstate == '23503', 'Wrong commit fault')
            else:
                raise AssertionError('Deferred FK fault absent')
        finally:
            f.store.conn.execute('DROP TRIGGER commit_fault ON b_audit'); f.store.conn.execute('DROP FUNCTION b_commit_fault()')
        require(all(n == 0 for n in f.counts('commitFault').values()), 'Commit failure left partial authority')
        f.assign('commitFault')
        f.new_run('auditFault')
        f.store.conn.execute("""CREATE FUNCTION b_audit_fault() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic audit outage'; END; $$""")
        f.store.conn.execute('CREATE TRIGGER audit_fault BEFORE INSERT ON b_audit FOR EACH ROW EXECUTE FUNCTION b_audit_fault()')
        try:
            blocked(lambda: f.assign('auditFault'), 'E_DEPENDENCY')
            blocked(lambda: f.service_api.dispatch('unknown'), 'E_DEPENDENCY')
        finally:
            f.store.conn.execute('DROP TRIGGER audit_fault ON b_audit'); f.store.conn.execute('DROP FUNCTION b_audit_fault()')
        require(all(n == 0 for n in f.counts('auditFault').values()), 'Audit outage left accepted metadata')
        checks['B07'] = {'status': 'PASS', 'facade_commit_and_audit_outage_safe_code': 'E_DEPENDENCY',
                         'trusted_deferred_fault_SQLSTATE': '23503', 'independent_observer_full_rollback_and_retry': True}

        f.new_run('restartAuthority'); persisted = f.assign('restartAuthority')
        stale = extended
        f.close(); stop(); start()
        f.raw = __import__('application')._ApplicationStore(f.schema)
        f.identity = __import__('identity').Identity(f.schema); f.api = __import__('application').Application(f.schema)
        f.store = _AuthorityStore(f.schema); f.admin_api = AdminServices(f.schema); f.service_api = ServiceAuthority(f.schema)
        require(f.check(persisted)['assignmentId'] == persisted['assignmentId'], 'Restart changed current authority')
        blocked(lambda: f.service_api.dispatch('check', version=VERSION, credential=old_token, **f.binding(scope)), 'E_AUTH')
        blocked(lambda: f.check(stale), 'E_STALE')
        blocked(lambda: f.check(revoked, 'workerB'), 'E_AUTH')
        for row in f.raw.conn.execute('SELECT password_hash FROM accounts').fetchall():
            forbidden.append(row['password_hash'].encode())
        forbidden.append(f.raw.conn.execute('SELECT dummy_hash FROM control').fetchone()['dummy_hash'].encode())
        tables = ('b_services', 'b_credentials', 'b_heads', 'b_assignments', 'b_audit', 'app_runs', 'app_delegations', 'app_receipts')
        metadata = json.dumps({t: f.store.conn.execute('SELECT * FROM ' + t).fetchall() for t in tables}, default=str).encode()
        require(all(t not in metadata and base64.b64encode(t) not in metadata and t.hex().encode() not in metadata for t in forbidden), 'Credential in authority metadata')
        checks['B08'] = {'status': 'PASS', 'actual_DB_restart_retains_current_and_stale_authority': True,
                         'raw_base64_hex_credentials_hashes_not_in_metadata': True, 'no_workload_or_external_release': True}
    finally:
        f.close()


def inputs():
    paths = []
    for folder in ('qa_core', 'schemas', 'spikes/s2', 'spikes/s6b', 'spikes/iap', 'spikes/iapb'):
        paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths += [ROOT / 'docs/IAP-A-PROTOCOL.md', ROOT / 'docs/IAP-B-PROTOCOL.md', ROOT / 'docs/IDENTITY-APPLICATION-PROTOCOL.md']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Use fresh docs/iapb-results/<id>.json')
    dest = (ROOT / sys.argv[1]).resolve()
    if dest.parent != (ROOT / 'docs/iapb-results').resolve() or dest.exists() or dest.suffix != '.json':
        raise SystemExit('Use new IAP-B evidence path')
    CACHE.mkdir(parents=True, exist_ok=True)
    evidence = {'evidenceVersion': VERSION, 'classification': 'synthetic-only',
                'baseline': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'startedAt': datetime.now(timezone.utc).isoformat(), 'command': 'py -3 -B spikes/iapb/run_iapb.py ' + sys.argv[1],
                'preflight': inventory(), 'database_preflight': db_inventory(), 'inputsBefore': inputs(), 'status': 'RUNNING',
                'limits': ['Trusted local host/DB, no network authentication/enrollment or production stack decision',
                           'Service/delegation/assignment metadata only; no execution, cleanup, broker, content or external release',
                           'Full IAP24/S4/S6/P3-B/P4-B/readiness remain open; no membership-epoch/restore anti-rollback provider']}
    begin = time.monotonic(); forbidden = []; stdout = io.StringIO(); stderr = io.StringIO()
    try:
        require(evidence['preflight']['ready'] and evidence['database_preflight']['toolchainReady'], 'Prerequisites not ready')
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            experiment(evidence, forbidden)
        captured = (stdout.getvalue() + stderr.getvalue()).encode()
        require(all(t not in captured and base64.b64encode(t) not in captured and t.hex().encode() not in captured for t in forbidden), 'Credential in parent diagnostics')
        evidence['diagnostics'] = {'stdoutBytes': len(stdout.getvalue()), 'stderrBytes': len(stderr.getvalue()), 'credentialScan': 'PASS'}
        evidence['inputsAfter'] = inputs(); require(evidence['inputsBefore'] == evidence['inputsAfter'], 'Inputs changed')
        evidence['status'] = 'PASS'
    except Exception as error:
        evidence['status'] = 'ERROR'; evidence['errorType'] = type(error).__name__
        (CACHE / 'last-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    evidence['elapsedSeconds'] = time.monotonic() - begin; evidence['finishedAt'] = datetime.now(timezone.utc).isoformat()
    encoded = json.dumps(evidence, indent=2).encode()
    require(all(t not in encoded and base64.b64encode(t) not in encoded and t.hex().encode() not in encoded for t in forbidden), 'Credential in evidence')
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('xb') as stream:
        stream.write(encoded + b'\n')
    print(json.dumps({'status': evidence['status'], 'elapsedSeconds': evidence['elapsedSeconds'],
                      'checks': {k: v['status'] for k, v in evidence.get('checks', {}).items()}}))
    return 0 if evidence['status'] == 'PASS' else 2


if __name__ == '__main__':
    mp.freeze_support(); raise SystemExit(main())
