"""Actual PostgreSQL synthetic queued-command acceptance; never emit credentials."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spikes/s6b'))
from preflight_b import inventory

if not inventory()['ready']:
    print('{"status":"NOT READY","execution":"NOT RUN"}')
    raise SystemExit(2)

from application import Application, _ApplicationStore, VERSION, Denied, canonical_digest, Jsonb
from identity import Identity, digest
from local import inventory as db_inventory, start, stop
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
import uuid
import psycopg

CACHE = ROOT / '.cache/s6/iap-a'


def require(value, message):
    if not value:
        raise AssertionError(message)


def blocked(call, code=None):
    try:
        call()
    except Denied as error:
        if code is not None:
            require(error.code == code, 'Wrong denial category')
        return error.code
    raise AssertionError('Expected denial')


def child(schema, route, body, hold, entered, release, started, pipe):
    store = _ApplicationStore(schema)
    api = Application(schema)
    identity = Identity(schema)
    try:
        started.set()
        try:
            if hold:
                # Trusted scheduling fixture holds the same DB unit through commit.
                with store.identity.tx(body['access']):
                    target = store.identity if route == 'account_flag' else store
                    result = getattr(target, route)(**body)
                    entered.set()
                    require(release.wait(12), 'Ordering release timeout')
            else:
                result = (identity.dispatch(route, **body) if route == 'account_flag'
                          else api.dispatch(route, version=VERSION, **body))
            pipe.send({'status': 'accepted', 'result': result})
        except Denied as error:
            pipe.send({'status': 'denied', 'code': error.code})
    finally:
        identity.close(); api.close(); store.close(); pipe.close()


def ordered_pair(schema, first, second):
    """Two actual processes/connections; first holds DB mutex, second attempts it."""
    entered, release = mp.Event(), mp.Event()
    started = [mp.Event(), mp.Event()]
    parents, children = [], []
    try:
        for i, (route, body) in enumerate((first, second)):
            parent, endpoint = mp.Pipe()
            proc = mp.Process(target=child, args=(schema, route, body, i == 0, entered, release, started[i], endpoint))
            proc.start(); endpoint.close(); parents.append(parent); children.append(proc)
            require(started[i].wait(12), 'Child start timeout')
            if i == 0:
                require(entered.wait(12), 'First command not holding mutex')
        # Observe the second session blocked on a DB lock before releasing the first.
        observer = _ApplicationStore(schema)
        try:
            deadline = time.monotonic() + 8
            locked = False
            while time.monotonic() < deadline:
                locked = observer.conn.execute("""SELECT EXISTS(SELECT 1 FROM pg_stat_activity
                    WHERE datname=current_database() AND pid<>pg_backend_pid()
                    AND application_name='s2-synthetic-spike' AND wait_event_type='Lock') AS held""").fetchone()['held']
                if locked:
                    break
                time.sleep(.01)
            require(locked, 'Second command did not reach actual DB lock wait')
        finally:
            observer.close()
        release.set()
        results = []
        for pipe in parents:
            require(pipe.poll(15), 'Ordered command timeout')
            results.append(pipe.recv())
        for proc in children:
            proc.join(10); require(proc.exitcode == 0, 'Ordered child failed')
        return results
    finally:
        release.set()
        for proc in children:
            if proc.is_alive():
                proc.kill(); proc.join(10)
        for pipe in parents:
            pipe.close()


class Fixture:
    def __init__(self, forbidden):
        self.schema = 'id_' + uuid.uuid4().hex
        self.raw = _ApplicationStore(self.schema, create=True)
        self.identity = Identity(self.schema)
        self.api = Application(self.schema)
        self.forbidden = forbidden
        self.users, self.passwords = {}, {}
        initial = self.password()
        self.raw.identity.bootstrap('admin', initial)
        self.users['admin'] = self.activate('admin', initial)
        for user in ('owner', 'runner', 'second', 'viewer', 'foreign'):
            pw = self.password()
            self.idcall('account_create', self.users['admin'], user=user, pw=pw)
            self.users[user] = self.activate(user, pw)
        for project, owner in (('pA', 'owner'), ('pB', 'foreign')):
            self.idcall('project_create', self.users['admin'], project=project, owner=owner)
            self.raw.initialize_policy(project, max_queued=100)
        for user, role in (('runner', 'Runner'), ('second', 'Runner'), ('viewer', 'Viewer')):
            self.member(user, role)

    def close(self):
        self.api.close(); self.identity.close(); self.raw.close()

    def password(self):
        value = 'synthetic-' + secrets.token_urlsafe(24)
        self.forbidden.append(value.encode())
        return value

    def keep(self, pair):
        self.forbidden.extend(v.encode() for v in pair.values())
        return pair

    def activate(self, user, pw):
        pair = self.keep(self.identity.dispatch('login', user=user, pw=pw))
        new = self.password()
        self.identity.dispatch('password_change', access=pair['access'], old=pw, new=new)
        self.passwords[user] = new
        return self.keep(self.identity.dispatch('login', user=user, pw=new))

    def idcall(self, route, pair, **body):
        return self.identity.dispatch(route, access=pair['access'], **body)

    def call(self, route, user='runner', **body):
        return self.api.dispatch(route, version=VERSION, access=self.users[user]['access'], **body)

    def member(self, user, role):
        self.idcall('membership', self.users['admin'], project='pA', target=user, role=role)

    def grant(self, user='runner', allowed=None, project='pA', epoch=1):
        return self.call('grant', user, project=project, allowed_actions=allowed or ['start', 'cancel', 'receipt'], expected_epoch=epoch)['grant']

    def start_body(self, key, grant, user='runner', project='pA', epoch=1, run_id=None):
        return {'access': self.users[user]['access'], 'project': project, 'grant': grant, 'key': key,
                'run_id': run_id or key, 'expected_epoch': epoch,
                'candidate_digest': 'a' * 64, 'input_digest': 'b' * 64}

    def start(self, body):
        return self.api.dispatch('start', version=VERSION, **body)

    def graph(self, run_id, project='pA'):
        # Independent DB connection observes committed state, not writer's own view.
        observer = _ApplicationStore(self.schema)
        try:
            result = {}
            for table, field in (('app_runs', 'id'), ('app_delegations', 'run_id'), ('app_outbox', 'run_id')):
                result[table] = observer.conn.execute(f'SELECT count(*) AS n FROM {table} WHERE project=%s AND {field}=%s',
                                                      (project, run_id)).fetchone()['n']
            result['receipts'] = observer.conn.execute("SELECT count(*) AS n FROM app_receipts WHERE project=%s AND result->>'runId'=%s", (project, run_id)).fetchone()['n']
            result['success_audit'] = observer.conn.execute("SELECT count(*) AS n FROM app_audit WHERE project=%s AND run_id=%s AND operation IN('start','cancel')", (project, run_id)).fetchone()['n']
            return result
        finally:
            observer.close()


def experiment(evidence, forbidden):
    f = Fixture(forbidden)
    evidence['schema'] = f.schema
    checks = evidence['checks'] = {}
    try:
        grant = f.grant()
        body = f.start_body('baseRun', grant)
        first = f.start(body)
        require(f.start(body) == first, 'Replay changed receipt')
        blocked(lambda: f.start({**body, 'input_digest': 'c' * 64}), 'E_CONFLICT')
        require(f.graph('baseRun') == {'app_runs': 1, 'app_delegations': 1, 'app_outbox': 1, 'receipts': 1, 'success_audit': 1}, 'Start graph not atomic')
        only_start = f.grant(allowed=['start'])
        blocked(lambda: f.start({**body, 'grant': only_start}), 'E_DENIED')
        start_only_body = f.start_body('startOnlyRun', only_start)
        f.start(start_only_body)
        blocked(lambda: f.start(start_only_body), 'E_DENIED')
        replacement = f.grant()
        require(f.start({**body, 'grant': replacement}) == first and f.graph('baseRun')['receipts'] == 1,
                'Reauthorization using new grant changed receipt identity')
        collisions = []
        for i in range(2):
            a = f.start_body('collide' + str(i), grant, run_id='winner' + str(i))
            b = {**a, 'run_id': 'loser' + str(i), 'input_digest': 'c' * 64}
            requests = (('start', a), ('start', b)) if i == 0 else (('start', b), ('start', a))
            outcome = ordered_pair(f.schema, *requests)
            require([r['status'] for r in outcome] == ['accepted', 'denied'] and outcome[1]['code'] == 'E_CONFLICT', 'Payload collision did not produce one winner')
            require(f.graph(requests[0][1]['run_id'])['receipts'] == 1 and f.graph(requests[1][1]['run_id'])['app_runs'] == 0, 'Collision created extra graph')
            collisions.append([r['status'] for r in outcome])
        other_grant = f.grant('second')
        f.start(f.start_body('baseRun', other_grant, user='second', run_id='secondRun'))
        checks['Q01'] = {'status': 'PASS', 'start_graph': f.graph('baseRun'), 'two_process_both_payload_orderings': collisions,
                         'actual_db_lock_wait_observed': True, 'principal_key_isolation': True,
                         'committed_replay_requires_current_receipt_action': True,
                         'new_authorized_grant_replays_same_payload': True}

        denials = []
        for token in ('a.' + secrets.token_urlsafe(32), f.users['runner']['refresh']):
            denials.append(blocked(lambda: f.start({**body, 'access': token}), 'E_AUTH'))
        for route, extra in (('_issue', {}), ('exercise_private_open', {}), ('start', {'authorized': True}), ('start', {'before_finish': True})):
            denials.append(blocked(lambda: f.api.dispatch(route, version=VERSION, **body, **extra), 'E_INPUT'))
        blocked(lambda: f.api.dispatch('start', version='unknown', **body), 'E_INPUT')
        blocked(lambda: f.api.dispatch('start', version=VERSION, **{**body, 'expected_epoch': True}), 'E_DENIED')
        blocked(lambda: f.start({**body, 'grant': other_grant}), 'E_DENIED')
        blocked(lambda: f.start({**body, 'project': 'pB', 'key': 'cross'}), 'E_DENIED')
        cancel_other = {'project': 'pB', 'grant': grant, 'key': 'wrongProject', 'run_id': 'baseRun', 'expected_version': 1}
        blocked(lambda: f.call('cancel', **cancel_other), 'E_DENIED')
        blocked(lambda: f.call('receipt', project='pA', grant=other_grant, operation='start', key='baseRun'), 'E_DENIED')
        checks['Q02'] = {'status': 'PASS', 'safe_codes': denials, 'exact_version_fields_helpers_token_kind_and_cross_scope_denied': True}

        vg = f.grant('viewer', ['receipt'])
        f.member('viewer', 'Runner')
        blocked(lambda: f.start(f.start_body('promoted', vg, user='viewer')), 'E_DENIED')
        f.member('runner', 'Viewer'); blocked(lambda: f.start(f.start_body('demoted', grant)), 'E_DENIED')
        f.member('runner', None); blocked(lambda: f.start(f.start_body('removed', grant)), 'E_DENIED')
        f.member('runner', 'Runner')
        f.idcall('project_enabled', f.users['admin'], project='pA', enabled=False)
        blocked(lambda: f.start(f.start_body('disabledProject', grant)), 'E_DENIED')
        f.idcall('project_enabled', f.users['admin'], project='pA', enabled=True)
        revoked = f.grant(); f.call('revoke', project='pA', grant=revoked)
        blocked(lambda: f.start(f.start_body('revokedGrant', revoked)), 'E_DENIED')
        old_viewer = f.users['viewer']; old_vg = f.grant('viewer')
        reset = f.password(); f.idcall('account_reset', f.users['admin'], user='viewer', new=reset)
        blocked(lambda: f.api.dispatch('start', version=VERSION, **f.start_body('oldReset', old_vg, user='viewer')), 'E_AUTH')
        f.users['viewer'] = f.activate('viewer', reset)
        blocked(lambda: f.start(f.start_body('oldEpoch', old_vg, user='viewer')), 'E_DENIED')
        f.idcall('account_flag', f.users['admin'], user='viewer', field='enabled', value=False)
        blocked(lambda: f.start(f.start_body('disabledAccount', old_vg, user='viewer')), 'E_AUTH')
        checks['Q03'] = {'status': 'PASS', 'promotion_ceiling_live_downgrade_remove_disable_revoke_reset': True,
                         'background_dispatch': 'NOT RUN'}

        config_grant = f.idcall('grant', f.users['owner'], project='pA', actions=['config'])
        config = {'access': f.users['owner']['access'], 'project': 'pA', 'config_grant': config_grant,
                  'expected_epoch': 1, 'enabled': True, 'allowed_actions': ['cancel', 'receipt'], 'max_queued': 100}
        before = f.start_body('beforePolicy', grant)
        out1 = ordered_pair(f.schema, ('start', before), ('configure', config))
        require([r['status'] for r in out1] == ['accepted', 'accepted'], 'Command-first policy ordering wrong')
        blocked(lambda: f.start(f.start_body('afterPolicy', grant)), 'E_DENIED')
        f.call('configure', 'owner', **{k: v for k, v in {**config, 'expected_epoch': 2, 'allowed_actions': ['start', 'cancel', 'receipt']}.items() if k != 'access'})
        grant = f.grant(epoch=3)
        config = {**config, 'expected_epoch': 3}
        out2 = ordered_pair(f.schema, ('configure', config), ('start', f.start_body('narrowFirst', grant, epoch=3)))
        require([r['status'] for r in out2] == ['accepted', 'denied'] and f.graph('narrowFirst')['app_runs'] == 0, 'Policy-first ordering leaked write')
        f.call('configure', 'owner', **{k: v for k, v in {**config, 'expected_epoch': 4, 'allowed_actions': ['start', 'cancel', 'receipt']}.items() if k != 'access'})
        grant = f.grant(epoch=5)
        disable = {'access': f.users['admin']['access'], 'user': 'runner', 'field': 'enabled', 'value': False}
        out3 = ordered_pair(f.schema, ('start', f.start_body('beforeDisable', grant, epoch=5)), ('account_flag', disable))
        require([r['status'] for r in out3] == ['accepted', 'accepted'], 'Command-first disable ordering wrong')
        f.idcall('account_flag', f.users['admin'], user='runner', field='enabled', value=True)
        f.users['runner'] = f.keep(f.identity.dispatch('login', user='runner', pw=f.passwords['runner']))
        grant = f.grant(epoch=5)
        out4 = ordered_pair(f.schema, ('account_flag', disable), ('start', f.start_body('disableFirst', grant, epoch=5)))
        require([r['status'] for r in out4] == ['accepted', 'denied'] and out4[1]['code'] == 'E_AUTH'
                and f.graph('disableFirst')['app_runs'] == 0, 'Disable-first ordering leaked write')
        f.idcall('account_flag', f.users['admin'], user='runner', field='enabled', value=True)
        f.users['runner'] = f.keep(f.identity.dispatch('login', user='runner', pw=f.passwords['runner']))
        grant = f.grant(epoch=5)
        checks['Q04'] = {'status': 'PASS', 'command_first': [r['status'] for r in out1],
                         'narrow_first': [r['status'] for r in out2], 'actual_db_lock_wait_observed': True,
                         'command_before_disable': [r['status'] for r in out3],
                         'disable_before_command': [r['status'] for r in out4], 'external_release': 'NOT RUN'}

        def wait_due(sql, args):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if f.raw.conn.execute(sql, args).fetchone()['due']:
                    return
                time.sleep(.01)
            raise AssertionError('DB expiry not reached')

        short = f.keep(f.raw.identity.login('runner', f.passwords['runner'], access_ms=700))
        expbody = f.start_body('accessExpiry', grant, epoch=5); expbody['access'] = short['access']
        reached = []
        def access_hook():
            reached.append(f.raw.conn.execute("SELECT count(*) AS n FROM app_runs WHERE id='accessExpiry'").fetchone()['n'])
            wait_due('SELECT expires<=clock_timestamp() AS due FROM access_tokens WHERE digest=%s', (digest(short['access'], 'a'),))
        blocked(lambda: f.raw.start(**expbody, before_finish=access_hook), 'E_AUTH')
        require(reached == [1] and all(v == 0 for v in f.graph('accessExpiry').values()), 'Access expiry did not rollback full graph')
        expgrant = f.grant(epoch=5)
        f.raw.conn.execute("UPDATE app_grants SET expires=clock_timestamp()+interval '700 milliseconds' WHERE id=%s", (expgrant,))
        expbody = f.start_body('grantExpiry', expgrant, epoch=5)
        def grant_hook():
            wait_due('SELECT expires<=clock_timestamp() AS due FROM app_grants WHERE id=%s', (expgrant,))
        blocked(lambda: f.raw.start(**expbody, before_finish=grant_hook), 'E_DENIED')
        require(all(v == 0 for v in f.graph('grantExpiry').values()), 'Grant expiry did not rollback full graph')
        checks['Q05'] = {'status': 'PASS', 'tentative_graph_observed_before_access_expiry': True,
                         'access_and_grant_expiry_full_graph_rollback': True}

        own = f.start(f.start_body('cancelOwn', grant, epoch=5))
        other_grant = f.grant('second', epoch=5)
        cb = {'project': 'pA', 'grant': grant, 'key': 'cancelCommand', 'run_id': own['runId'], 'expected_version': 1}
        blocked(lambda: f.call('cancel', 'second', **{**cb, 'grant': other_grant}), 'E_DENIED')
        blocked(lambda: f.call('cancel', **{**cb, 'expected_version': 2}), 'E_STALE')
        result = f.call('cancel', **cb)
        require(result == f.call('cancel', **cb) and result['state'] == 'cancelled', 'Cancel replay not stable')
        only_cancel = f.grant(allowed=['cancel'], epoch=5)
        blocked(lambda: f.call('cancel', **{**cb, 'grant': only_cancel}), 'E_DENIED')
        replacement = f.grant(epoch=5)
        require(f.call('cancel', **{**cb, 'grant': replacement}) == result, 'New grant changed cancel receipt')
        blocked(lambda: f.call('cancel', **{**cb, 'expected_version': 2}), 'E_CONFLICT')
        foreign = f.start(f.start_body('ownerCancel', other_grant, user='second', epoch=5))
        owner_grant = f.grant('owner', epoch=5)
        f.call('cancel', 'owner', project='pA', grant=owner_grant, key='ownerCancelKey', run_id=foreign['runId'], expected_version=1)
        require(f.graph('cancelOwn') == {'app_runs': 1, 'app_delegations': 1, 'app_outbox': 2, 'receipts': 2, 'success_audit': 2}, 'Cancel atomic graph wrong')
        checks['Q06'] = {'status': 'PASS', 'queued_cancel_ownership_CAS_replay': True, 'graph': f.graph('cancelOwn'), 'worker_cleanup': 'NOT RUN'}

        failbody = f.start_body('commitFailure', grant, epoch=5)
        f.raw.conn.execute("""CREATE FUNCTION inject_commit_fault() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.operation='start' AND NEW.run_id='commitFailure' THEN
                INSERT INTO app_audit(project,run_id,operation) VALUES(NEW.project,'absentRun','fault');
            END IF; RETURN NEW; END; $$""")
        f.raw.conn.execute('CREATE TRIGGER commit_fault BEFORE INSERT ON app_audit FOR EACH ROW EXECUTE FUNCTION inject_commit_fault()')
        try:
            blocked(lambda: f.start(failbody), 'E_DEPENDENCY')
            # The facade deliberately hides DB details. A trusted observer confirms
            # that this fault is a deferred FK violation rather than a generic error.
            try:
                f.raw.start(**failbody)
            except psycopg.errors.ForeignKeyViolation as error:
                require(error.sqlstate == '23503', 'Wrong deferred constraint fault')
            else:
                raise AssertionError('Deferred FK violation not observed')
        finally:
            f.raw.conn.execute('DROP TRIGGER commit_fault ON app_audit')
            f.raw.conn.execute('DROP FUNCTION inject_commit_fault()')
        require(all(v == 0 for v in f.graph('commitFailure').values()), 'Commit failure left partial graph')
        f.start(failbody)
        auditbody = f.start_body('auditUnavailable', grant, epoch=5)
        f.raw.conn.execute("""CREATE FUNCTION inject_audit_outage() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic audit unavailable'; END; $$""")
        f.raw.conn.execute('CREATE TRIGGER audit_outage BEFORE INSERT ON app_audit FOR EACH ROW EXECUTE FUNCTION inject_audit_outage()')
        try:
            blocked(lambda: f.start(auditbody), 'E_DEPENDENCY')
            blocked(lambda: f.api.dispatch('unknown'), 'E_DEPENDENCY')
        finally:
            f.raw.conn.execute('DROP TRIGGER audit_outage ON app_audit')
            f.raw.conn.execute('DROP FUNCTION inject_audit_outage()')
        require(all(v == 0 for v in f.graph('auditUnavailable').values()), 'Audit outage left accepted graph')
        p = f.raw.conn.execute("SELECT * FROM app_policies WHERE project='pB'").fetchone()
        bg = f.grant('foreign', project='pB')
        f.raw.conn.execute("DELETE FROM app_policies WHERE project='pB'")
        blocked(lambda: f.start(f.start_body('noProvider', bg, user='foreign', project='pB')), 'E_DEPENDENCY')
        f.raw.conn.execute('INSERT INTO app_policies VALUES(%s,%s,%s,%s,%s,%s)',
                          (p['project'], p['epoch'], p['config_version'], p['enabled'], Jsonb(p['actions']), p['max_queued']))
        checks['Q07'] = {'status': 'PASS', 'actual_deferred_FK_commit_failure_full_rollback': True,
                         'trusted_fault_observer_sqlstate': '23503',
                         'facade_commit_error_code': 'E_DEPENDENCY', 'audit_and_denial_audit_outage_fail_closed': True,
                         'same_key_retry_one_graph': f.graph('commitFailure'), 'missing_policy_fail_closed': True}

        loss = f.start_body('lostResponse', grant, epoch=5)
        committed = f.start(loss)  # Harness drops this value at simulated caller boundary.
        f.api.close(); f.identity.close(); f.raw.close()
        stop(); start()
        f.raw = _ApplicationStore(f.schema); f.api = Application(f.schema); f.identity = Identity(f.schema)
        restored = f.call('receipt', project='pA', grant=grant, operation='start', key='lostResponse')
        require(restored == committed and f.start(loss) == committed and f.graph('lostResponse')['receipts'] == 1, 'Restart/response-loss receipt duplicated command')
        config = {**config, 'expected_epoch': 5, 'allowed_actions': ['start', 'cancel', 'receipt'], 'max_queued': 1}
        f.call('configure', 'owner', **{k: v for k, v in config.items() if k != 'access'})
        budget_grant = f.grant(epoch=6)
        blocked(lambda: f.start(f.start_body('budgetDenied', budget_grant, epoch=6)), 'E_BUDGET')
        require(all(v == 0 for v in f.graph('budgetDenied').values()), 'Budget failure wrote partial graph')
        blocked(lambda: f.call('receipt', project='pA', grant=grant, operation='start', key='lostResponse'), 'E_DENIED')
        read_narrow = {**config, 'expected_epoch': 6, 'allowed_actions': ['start', 'cancel']}
        f.call('configure', 'owner', **{k: v for k, v in read_narrow.items() if k != 'access'})
        narrowed = f.grant(allowed=['start'], epoch=7)
        blocked(lambda: f.call('receipt', project='pA', grant=narrowed, operation='start', key='lostResponse'), 'E_DENIED')
        blocked(lambda: f.start(loss), 'E_DENIED')
        require(f.graph('lostResponse')['receipts'] == 1 and f.graph('lostResponse')['success_audit'] == 1,
                'Receipt denial or stale-epoch replay mutated command graph')
        for row in f.raw.conn.execute('SELECT password_hash FROM accounts').fetchall():
            forbidden.append(row['password_hash'].encode())
        forbidden.append(f.raw.conn.execute('SELECT dummy_hash FROM control').fetchone()['dummy_hash'].encode())
        safe_tables = ('app_policies', 'app_grants', 'app_runs', 'app_delegations', 'app_receipts', 'app_audit', 'app_outbox')
        raw = json.dumps({table: f.raw.conn.execute('SELECT * FROM ' + table).fetchall() for table in safe_tables}, default=str).encode()
        require(all(t not in raw and base64.b64encode(t) not in raw and t.hex().encode() not in raw for t in forbidden), 'Credential in application metadata')
        checks['Q08'] = {'status': 'PASS', 'actual_DB_restart_receipt_replay': True,
                         'response_loss': 'simulated drop after actual commit, no network transport',
                         'budget_no_partial_graph': True, 'revoked_policy_blocks_receipt': True,
                         'current_epoch_receipt_request_denied_after_read_narrowing': True,
                         'old_policy_epoch_start_replay_fenced_before_prior': True,
                         'app_tables_credential_scan_forms': ['raw', 'base64', 'hex']}
    finally:
        f.close()


def inputs():
    paths = []
    for folder in ('qa_core', 'schemas', 'spikes/s2', 'spikes/s6b', 'spikes/iap'):
        paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths += [ROOT / 'docs/IAP-A-PROTOCOL.md', ROOT / 'docs/IDENTITY-APPLICATION-PROTOCOL.md']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Use new docs/iap-results/<id>.json')
    dest = (ROOT / sys.argv[1]).resolve()
    if dest.parent != (ROOT / 'docs/iap-results').resolve() or dest.exists() or dest.suffix != '.json':
        raise SystemExit('Use new IAP evidence path')
    CACHE.mkdir(parents=True, exist_ok=True)
    evidence = {'evidenceVersion': VERSION, 'classification': 'synthetic-only',
                'baseline': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'startedAt': datetime.now(timezone.utc).isoformat(), 'command': 'py -3 -B spikes/iap/run_iap.py ' + sys.argv[1],
                'preflight': inventory(), 'database_preflight': db_inventory(), 'inputsBefore': inputs(), 'status': 'RUNNING',
                'limits': ['User queued-command DB subset only; trusted host/DB; no network auth/service/worker/broker',
                           'No claim/IO/release/cleanup ports; no S4 execution proof or production stack decision',
                           'IAP24 only selected interactive/queued portions; full S4/S6/P3-B/P4-B remain open']}
    begin = time.monotonic(); forbidden = []; stdout = io.StringIO(); stderr = io.StringIO()
    try:
        require(evidence['database_preflight']['toolchainReady'], 'DB prerequisites not ready')
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            experiment(evidence, forbidden)
        captured = (stdout.getvalue() + stderr.getvalue()).encode()
        require(all(t not in captured and base64.b64encode(t) not in captured and t.hex().encode() not in captured for t in forbidden), 'Credential in parent output')
        evidence['diagnostics'] = {'stdoutBytes': len(stdout.getvalue()), 'stderrBytes': len(stderr.getvalue()), 'credentialScan': 'PASS'}
        evidence['inputsAfter'] = inputs()
        require(evidence['inputsBefore'] == evidence['inputsAfter'], 'Source/input changed')
        evidence['status'] = 'PASS'
    except Exception as error:
        evidence['status'] = 'ERROR'; evidence['errorType'] = type(error).__name__
        (CACHE / 'last-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    evidence['elapsedSeconds'] = time.monotonic() - begin
    evidence['finishedAt'] = datetime.now(timezone.utc).isoformat()
    encoded = json.dumps(evidence, indent=2).encode()
    require(all(t not in encoded and base64.b64encode(t) not in encoded and t.hex().encode() not in encoded for t in forbidden), 'Credential in evidence')
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('xb') as stream:
        stream.write(encoded + b'\n')
    print(json.dumps({'status': evidence['status'], 'elapsedSeconds': evidence['elapsedSeconds'],
                      'checks': {k: v['status'] for k, v in evidence.get('checks', {}).items()}}))
    return 0 if evidence['status'] == 'PASS' else 2


if __name__ == '__main__':
    mp.freeze_support()
    raise SystemExit(main())
