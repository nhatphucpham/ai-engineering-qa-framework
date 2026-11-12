"""Synthetic queued commands sharing S6-B's identity transaction; no service/IO ports."""
from pathlib import Path
import contextlib
import hashlib
import json
import re
import sys
import uuid
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spikes/s6b'))
from identity import _Store, Denied, ALLOWED, name, positive, Jsonb
import psycopg

VERSION = 'iap-a-1.0.0'
ACTIONS = frozenset(('start', 'cancel', 'receipt'))


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def actions(value):
    if (not isinstance(value, list) or not value or not all(type(v) is str for v in value)
            or len(value) != len(set(value)) or not set(value) <= ACTIONS):
        raise Denied('E_INPUT')
    return sorted(value)


class _ApplicationStore:
    """Trusted host fixture, never dispatch bootstrap/SQL/hooks by request method name."""
    def __init__(self, schema, create=False):
        self.identity = _Store(schema, create=create)
        self.conn = self.identity.conn
        if create:
            with self.identity.tx():
                self.conn.execute((Path(__file__).parent / 'schema.sql').read_text())
        if self.conn.execute('SELECT version FROM application_identity').fetchone() != {'version': VERSION}:
            raise Denied('E_SCHEMA')

    def close(self):
        self.identity.close()

    def initialize_policy(self, project, max_queued=20):
        name(project); positive(max_queued)
        with self.identity.tx():
            self.conn.execute('INSERT INTO app_policies VALUES(%s,1,1,true,%s,%s)',
                              (project, Jsonb(sorted(ACTIONS)), max_queued))

    def policy(self, actor, project):
        self.identity.role(actor, project)
        row = self.conn.execute('SELECT * FROM app_policies WHERE project=%s', (project,)).fetchone()
        if row is None:
            raise Denied('E_DEPENDENCY')
        if not row['enabled']:
            raise Denied('E_DENIED')
        return row

    def audit(self, actor, project, run_id, operation):
        self.conn.execute('INSERT INTO app_audit(user_id,project,run_id,operation) VALUES(%s,%s,%s,%s)',
                          (actor['id'], project, run_id, operation))

    def authorize(self, actor, project, action, grant_id):
        policy = self.policy(actor, project)
        role = self.identity.role(actor, project)
        required = 'read' if action == 'receipt' else action
        grant = self.conn.execute('SELECT * FROM app_grants WHERE id=%s', (grant_id,)).fetchone()
        if (required not in ALLOWED[role] or action not in policy['actions'] or grant is None
                or grant['revoked'] or action not in grant['actions']
                or (grant['user_id'], grant['project'], grant['credential_epoch'],
                    grant['policy_epoch'], grant['config_version']) !=
                   (actor['id'], project, actor['epoch'], policy['epoch'], policy['config_version'])):
            raise Denied('E_DENIED')
        if not self.conn.execute('SELECT %s>clock_timestamp() AS live', (grant['expires'],)).fetchone()['live']:
            raise Denied('E_DENIED')
        return policy, grant, role

    @contextlib.contextmanager
    def command_unit(self, access, project, action, grant, before_finish=lambda: None):
        admitted = []

        def finish():
            before_finish()
            # All identity/policy/grant writers hold the same identity mutex. Recheck
            # wall-clock grant expiry at the final conditional mutation as well.
            if admitted and self.conn.execute('''UPDATE control SET serial=serial+1 WHERE id=1
                    AND %s>clock_timestamp() RETURNING id''', (admitted[0]['expires'],)).fetchone() is None:
                raise Denied('E_DENIED')

        with self.identity.tx(access, before_finish=finish) as actor:
            policy, snapshot, role = self.authorize(actor, project, action, grant)
            admitted.append(snapshot)
            yield actor, policy, snapshot, role

    def grant(self, access, project, allowed_actions, expected_epoch):
        allowed = actions(allowed_actions); positive(expected_epoch)
        with self.identity.tx(access) as actor:
            policy = self.policy(actor, project)
            role = self.identity.role(actor, project)
            if policy['epoch'] != expected_epoch:
                raise Denied('E_STALE')
            if any(('read' if a == 'receipt' else a) not in ALLOWED[role] or a not in policy['actions'] for a in allowed):
                raise Denied('E_DENIED')
            ref = uuid.uuid4().hex
            self.conn.execute('''INSERT INTO app_grants
                VALUES(%s,%s,%s,%s,%s,%s,%s,clock_timestamp()+interval '10 minutes',false)''',
                (ref, actor['id'], project, actor['epoch'], policy['epoch'], policy['config_version'], Jsonb(allowed)))
            self.audit(actor, project, None, 'grant')
        return {'grant': ref, 'policyEpoch': policy['epoch'], 'configVersion': policy['config_version']}

    def configure(self, access, project, config_grant, expected_epoch, enabled, allowed_actions, max_queued):
        allowed = actions(allowed_actions); positive(expected_epoch); positive(max_queued)
        if type(enabled) is not bool:
            raise Denied('E_INPUT')
        with self.identity.tx(access) as actor:
            self.identity.authorize(actor, project, 'config', config_grant)
            row = self.conn.execute('''UPDATE app_policies SET epoch=epoch+1,config_version=config_version+1,
                enabled=%s,actions=%s,max_queued=%s WHERE project=%s AND epoch=%s RETURNING epoch''',
                (enabled, Jsonb(allowed), max_queued, project, expected_epoch)).fetchone()
            if row is None:
                raise Denied('E_STALE')
            self.audit(actor, project, None, 'configure')
        return {'policyEpoch': row['epoch']}

    def revoke(self, access, project, grant):
        with self.identity.tx(access) as actor:
            role = self.identity.role(actor, project)
            row = self.conn.execute('SELECT * FROM app_grants WHERE id=%s AND project=%s', (grant, project)).fetchone()
            if row is None or row['user_id'] != actor['id'] and role not in ('Admin', 'Owner'):
                raise Denied('E_DENIED')
            self.conn.execute('UPDATE app_grants SET revoked=true WHERE id=%s', (grant,))
            self.audit(actor, project, None, 'revoke')
        return {'revoked': True}

    def prior(self, actor, project, operation, key, payload, grant):
        row = self.conn.execute('''SELECT * FROM app_receipts
            WHERE user_id=%s AND project=%s AND operation=%s AND client_key=%s''',
            (actor['id'], project, operation, key)).fetchone()
        if row is None:
            return None
        # Replaying a command is a read of an existing receipt, not a second
        # mutation. A start/cancel-only grant cannot authorize that disclosure.
        self.authorize(actor, project, 'receipt', grant)
        if row['payload_digest'] != canonical_digest(payload):
            raise Denied('E_CONFLICT')
        return row['result']

    def save(self, actor, project, operation, key, payload, result):
        self.conn.execute('INSERT INTO app_receipts VALUES(%s,%s,%s,%s,%s,%s)',
                          (actor['id'], project, operation, key, canonical_digest(payload), Jsonb(result)))
        self.audit(actor, project, result['runId'], operation)

    def start(self, access, project, grant, key, run_id, expected_epoch, candidate_digest, input_digest,
              before_finish=lambda: None):
        name(key); name(run_id); positive(expected_epoch)
        for value in (candidate_digest, input_digest):
            if type(value) is not str or not re.fullmatch('[a-f0-9]{64}', value):
                raise Denied('E_INPUT')
        payload = {'project': project, 'runId': run_id, 'expectedEpoch': expected_epoch,
                   'candidateDigest': candidate_digest, 'inputDigest': input_digest}
        with self.command_unit(access, project, 'start', grant, before_finish) as (actor, policy, snapshot, role):
            if policy['epoch'] != expected_epoch:
                raise Denied('E_STALE')
            result = self.prior(actor, project, 'start', key, payload, grant)
            if result is None:
                count = self.conn.execute("SELECT count(*) AS n FROM app_runs WHERE project=%s AND state='queued'", (project,)).fetchone()['n']
                if count >= policy['max_queued']:
                    raise Denied('E_BUDGET')
                if self.conn.execute('SELECT 1 FROM app_runs WHERE project=%s AND id=%s', (project, run_id)).fetchone():
                    raise Denied('E_CONFLICT')
                self.conn.execute("INSERT INTO app_runs VALUES(%s,%s,%s,'queued',1,%s,%s,%s,%s)",
                                  (project, run_id, actor['id'], policy['epoch'], policy['config_version'], candidate_digest, input_digest))
                self.conn.execute('INSERT INTO app_delegations VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                                  (project, run_id, actor['id'], grant, actor['epoch'], policy['epoch'],
                                   policy['config_version'], Jsonb(snapshot['actions']), snapshot['expires']))
                self.conn.execute("INSERT INTO app_outbox VALUES(%s,%s,1,'queued',1)", (project, run_id))
                result = {'runId': run_id, 'project': project, 'state': 'queued', 'version': 1}
                self.save(actor, project, 'start', key, payload, result)
        return result

    def cancel(self, access, project, grant, key, run_id, expected_version, before_finish=lambda: None):
        name(key); name(run_id); positive(expected_version)
        payload = {'project': project, 'runId': run_id, 'expectedVersion': expected_version}
        with self.command_unit(access, project, 'cancel', grant, before_finish) as (actor, policy, snapshot, role):
            row = self.conn.execute('SELECT * FROM app_runs WHERE project=%s AND id=%s', (project, run_id)).fetchone()
            if row is None or role == 'Runner' and row['initiator'] != actor['id']:
                raise Denied('E_DENIED')
            result = self.prior(actor, project, 'cancel', key, payload, grant)
            if result is None:
                updated = self.conn.execute("""UPDATE app_runs SET state='cancelled',version=version+1
                    WHERE project=%s AND id=%s AND version=%s AND state='queued' RETURNING version""",
                    (project, run_id, expected_version)).fetchone()
                if updated is None:
                    raise Denied('E_STALE')
                self.conn.execute("INSERT INTO app_outbox VALUES(%s,%s,2,'cancelled',%s)", (project, run_id, updated['version']))
                result = {'project': project, 'runId': run_id, 'state': 'cancelled', 'version': updated['version']}
                self.save(actor, project, 'cancel', key, payload, result)
        return result

    def receipt(self, access, project, grant, operation, key):
        name(key)
        if operation not in ('start', 'cancel'):
            raise Denied('E_INPUT')
        with self.command_unit(access, project, 'receipt', grant) as (actor, policy, snapshot, role):
            row = self.conn.execute('''SELECT result FROM app_receipts
                WHERE user_id=%s AND project=%s AND operation=%s AND client_key=%s''',
                (actor['id'], project, operation, key)).fetchone()
            if row is None:
                raise Denied('E_DENIED')
            self.audit(actor, project, row['result']['runId'], 'receipt')
        return row['result']

    def denied_audit(self, code):
        with self.identity.tx():
            self.conn.execute('INSERT INTO app_audit(operation) VALUES(%s)', ('denied_' + code,))


class Application:
    """Exact request facade over trusted local host; never dynamically route helpers."""
    __slots__ = ('__store',)
    FIELDS = MappingProxyType({
        'grant': frozenset(('project', 'allowed_actions', 'expected_epoch')),
        'configure': frozenset(('project', 'config_grant', 'expected_epoch', 'enabled', 'allowed_actions', 'max_queued')),
        'revoke': frozenset(('project', 'grant')),
        'start': frozenset(('project', 'grant', 'key', 'run_id', 'expected_epoch', 'candidate_digest', 'input_digest')),
        'cancel': frozenset(('project', 'grant', 'key', 'run_id', 'expected_version')),
        'receipt': frozenset(('project', 'grant', 'operation', 'key'))})

    def __init__(self, schema):
        self.__store = _ApplicationStore(schema)

    def close(self):
        self.__store.close()

    def dispatch(self, route, **body):
        try:
            if (type(route) is not str or route not in self.FIELDS
                    or set(body) != self.FIELDS[route] | {'version', 'access'} or body['version'] != VERSION):
                raise Denied('E_INPUT')
            body = dict(body)
            del body['version']
            return getattr(self.__store, route)(**body)
        except (Denied, TypeError, ValueError, psycopg.Error) as error:
            code = error.code if isinstance(error, Denied) else ('E_DEPENDENCY' if isinstance(error, psycopg.Error) else 'E_INPUT')
            try:
                self.__store.denied_audit(code)
            except psycopg.Error:
                code = 'E_DEPENDENCY'
            raise Denied(code) from None
