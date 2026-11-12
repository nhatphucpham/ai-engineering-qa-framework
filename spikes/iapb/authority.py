"""DB-only service/delegation/assignment authority; no workload or release ports."""
from pathlib import Path
import contextlib
import re
import secrets
import sys
import uuid
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spikes/iap'))
from application import _ApplicationStore, Denied, Jsonb, ALLOWED, name, positive
from identity import digest
import psycopg

VERSION = 'iap-b-1.0.0'
AUDIENCES = MappingProxyType({'scheduler': 'iap-scheduler', 'worker': 'iap-worker'})


def ttl(value):
    if type(value) is not int or not 50 <= value <= 30000:
        raise Denied('E_INPUT')


def counter(value):
    if type(value) is not int or value < 0:
        raise Denied('E_INPUT')


class _AuthorityStore(_ApplicationStore):
    """Trusted setup/fault facility, not dynamically routable by client requests."""
    def __init__(self, schema, create=False):
        super().__init__(schema)
        if create:
            with self.identity.tx():
                self.conn.execute((Path(__file__).parent / 'schema.sql').read_text())
        if self.conn.execute('SELECT version FROM authority_identity').fetchone() != {'version': VERSION}:
            raise Denied('E_SCHEMA')

    def log(self, kind, actor, project, run_id, operation):
        self.conn.execute('INSERT INTO b_audit(actor_kind,actor_id,project,run_id,operation) VALUES(%s,%s,%s,%s,%s)',
                          (kind, actor, project, run_id, operation))

    def issue(self, row):
        token = 's.' + secrets.token_urlsafe(32)
        self.conn.execute("INSERT INTO b_credentials VALUES(%s,%s,%s,%s,clock_timestamp()+interval '10 minutes')",
                          (digest(token, 's'), row['id'], row['epoch'], AUDIENCES[row['kind']]))
        return {'serviceId': row['id'], 'kind': row['kind'], 'epoch': row['epoch'], 'credential': token}

    def create_service(self, access, service_id, kind, projects):
        name(service_id)
        if (kind not in AUDIENCES or not isinstance(projects, list) or not projects
                or not all(type(p) is str for p in projects) or len(projects) != len(set(projects))):
            raise Denied('E_INPUT')
        with self.identity.tx(access) as actor:
            self.identity.admin(actor)
            for project in projects:
                self.identity.role(actor, project)
            row = self.conn.execute('INSERT INTO b_services VALUES(%s,%s,1,true,%s) RETURNING *',
                                    (service_id, kind, Jsonb(sorted(projects)))).fetchone()
            result = self.issue(row)
            self.log('user', actor['id'], None, None, 'create_service')
        return result

    def rotate(self, access, service_id):
        name(service_id)
        with self.identity.tx(access) as actor:
            self.identity.admin(actor)
            row = self.conn.execute('UPDATE b_services SET epoch=epoch+1 WHERE id=%s AND enabled RETURNING *',
                                    (service_id,)).fetchone()
            if row is None:
                raise Denied('E_DENIED')
            result = self.issue(row)
            self.log('user', actor['id'], None, None, 'rotate')
        return result

    def revoke_service(self, access, service_id):
        name(service_id)
        with self.identity.tx(access) as actor:
            self.identity.admin(actor)
            if self.conn.execute('UPDATE b_services SET enabled=false,epoch=epoch+1 WHERE id=%s AND enabled RETURNING id',
                                 (service_id,)).fetchone() is None:
                raise Denied('E_DENIED')
            self.log('user', actor['id'], None, None, 'revoke_service')
        return {'revoked': True}

    def enrolled(self, service_id, kind, project):
        name(service_id); name(project)
        row = self.conn.execute('''SELECT s.*,c.expires FROM b_services s JOIN b_credentials c
            ON c.service_id=s.id AND c.epoch=s.epoch WHERE s.id=%s AND s.enabled
            AND c.audience=%s AND c.expires>clock_timestamp()''', (service_id, AUDIENCES[kind])).fetchone()
        if row is None or row['kind'] != kind or project not in row['projects']:
            raise Denied('E_DENIED')
        return row

    @contextlib.contextmanager
    def service_unit(self, credential, kind, project, before_finish=lambda: None):
        name(project)
        deadlines = []

        def finish():
            before_finish()
            if deadlines and self.conn.execute('''UPDATE control SET serial=serial+1
                WHERE id=1 AND %s>clock_timestamp() RETURNING id''', (min(deadlines),)).fetchone() is None:
                raise Denied('E_STALE')

        with self.identity.tx(before_finish=finish):
            row = self.conn.execute('''SELECT s.*,c.expires FROM b_services s JOIN b_credentials c
                ON c.service_id=s.id AND c.epoch=s.epoch WHERE c.digest=%s AND s.enabled
                AND c.expires>clock_timestamp() AND c.audience=%s''', (digest(credential, 's'), AUDIENCES[kind])).fetchone()
            if row is None or row['kind'] != kind or project not in row['projects']:
                raise Denied('E_AUTH')
            deadlines.append(row['expires'])
            yield row, deadlines
            finish()

    def live_delegation(self, project, run_id, deadlines):
        name(run_id)
        row = self.conn.execute('''SELECT r.state,r.initiator,r.policy_epoch AS run_policy,r.config_version AS run_config,
            d.grant_id,d.credential_epoch,d.policy_epoch,d.config_version,d.actions,d.expires AS delegation_expires,
            a.id,a.admin,a.enabled,a.must_change,a.epoch FROM app_runs r JOIN app_delegations d
            ON (d.project,d.run_id)=(r.project,r.id) JOIN accounts a ON a.id=d.user_id
            WHERE r.project=%s AND r.id=%s''', (project, run_id)).fetchone()
        if (row is None or row['state'] != 'queued' or not row['enabled'] or row['must_change']
                or row['id'] != row['initiator'] or row['epoch'] != row['credential_epoch'] or 'start' not in row['actions']):
            raise Denied('E_DENIED')
        policy, grant, role = self.authorize(row, project, 'start', row['grant_id'])
        if (row['run_policy'], row['run_config'], row['policy_epoch'], row['config_version']) != (
                policy['epoch'], policy['config_version'], policy['epoch'], policy['config_version']):
            raise Denied('E_DENIED')
        deadlines.extend((grant['expires'], row['delegation_expires']))
        if not self.conn.execute('SELECT %s>clock_timestamp() AS live', (min(deadlines),)).fetchone()['live']:
            raise Denied('E_DENIED')
        return row

    @staticmethod
    def view(row):
        return {'authorityVersion': VERSION, 'assignmentId': row['id'], 'project': row['project'],
                'runId': row['run_id'], 'attempt': row['attempt'], 'fence': row['fence'],
                'expiresAt': row['expires'].isoformat()}

    def assign(self, credential, project, run_id, worker_id, expected_attempt, ttl_ms, before_finish=lambda: None):
        counter(expected_attempt); ttl(ttl_ms)
        with self.service_unit(credential, 'scheduler', project, before_finish) as (actor, deadlines):
            self.live_delegation(project, run_id, deadlines)
            worker = self.enrolled(worker_id, 'worker', project)
            deadlines.append(worker['expires'])
            head = self.conn.execute('SELECT * FROM b_heads WHERE project=%s AND run_id=%s', (project, run_id)).fetchone()
            if head is None:
                if expected_attempt != 0:
                    raise Denied('E_STALE')
                self.conn.execute('INSERT INTO b_heads VALUES(%s,%s,0,0)', (project, run_id))
                head = {'attempt': 0, 'fence': 0}
            if head['attempt'] != expected_attempt:
                raise Denied('E_STALE')
            if self.conn.execute("SELECT 1 FROM b_assignments WHERE project=%s AND run_id=%s AND state='active'", (project, run_id)).fetchone():
                raise Denied('E_STALE')
            next_attempt, fence = head['attempt'] + 1, head['fence'] + 1
            row = self.conn.execute('''INSERT INTO b_assignments VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,
                LEAST(%s,clock_timestamp()+(%s*interval '1 millisecond')),'active') RETURNING *''',
                (uuid.uuid4().hex, project, run_id, next_attempt, fence, actor['id'], actor['epoch'],
                 worker['id'], worker['epoch'], min(deadlines), ttl_ms)).fetchone()
            deadlines.append(row['expires'])
            self.conn.execute('UPDATE b_heads SET attempt=%s,fence=%s WHERE project=%s AND run_id=%s', (next_attempt, fence, project, run_id))
            self.log('service', actor['id'], project, run_id, 'assign')
        return self.view(row)

    def current_assignment(self, actor, project, run_id, assignment_id, attempt, fence, deadlines):
        positive(attempt); positive(fence); name(run_id)
        if type(assignment_id) is not str or not re.fullmatch('[a-f0-9]{32}', assignment_id):
            raise Denied('E_INPUT')
        self.live_delegation(project, run_id, deadlines)
        row = self.conn.execute('''SELECT a.* FROM b_assignments a JOIN b_heads h
            ON (a.project,a.run_id,a.attempt,a.fence)=(h.project,h.run_id,h.attempt,h.fence)
            WHERE a.id=%s AND a.project=%s AND a.run_id=%s AND a.attempt=%s AND a.fence=%s
            AND a.state='active' AND a.expires>clock_timestamp()''', (assignment_id, project, run_id, attempt, fence)).fetchone()
        if row is None:
            raise Denied('E_STALE')
        scheduler = self.enrolled(row['scheduler_id'], 'scheduler', project)
        if (row['worker_id'], row['worker_epoch'], row['scheduler_epoch']) != (actor['id'], actor['epoch'], scheduler['epoch']):
            raise Denied('E_DENIED')
        deadlines.append(scheduler['expires'])
        deadlines.append(row['expires'])
        return row

    def check(self, credential, project, run_id, assignment_id, attempt, fence, before_finish=lambda: None):
        with self.service_unit(credential, 'worker', project, before_finish) as (actor, deadlines):
            row = self.current_assignment(actor, project, run_id, assignment_id, attempt, fence, deadlines)
            self.log('service', actor['id'], project, run_id, 'check')
        return self.view(row)

    def renew(self, credential, project, run_id, assignment_id, attempt, fence, ttl_ms, before_finish=lambda: None):
        ttl(ttl_ms)
        with self.service_unit(credential, 'worker', project, before_finish) as (actor, deadlines):
            row = self.current_assignment(actor, project, run_id, assignment_id, attempt, fence, deadlines)
            # Old deadline still gates this unit; the extended one cannot revive expiry.
            new = self.conn.execute('''UPDATE b_assignments SET expires=LEAST(%s,
                GREATEST(expires,clock_timestamp()+(%s*interval '1 millisecond'))) WHERE id=%s RETURNING *''',
                (min(deadlines[:-1]), ttl_ms, row['id'])).fetchone()
            self.log('service', actor['id'], project, run_id, 'renew')
        return self.view(new)

    def retire(self, credential, project, run_id, assignment_id, attempt, fence):
        positive(attempt); positive(fence); name(run_id)
        with self.service_unit(credential, 'scheduler', project) as (actor, deadlines):
            row = self.conn.execute('''SELECT a.* FROM b_assignments a JOIN b_heads h
                ON (a.project,a.run_id,a.attempt,a.fence)=(h.project,h.run_id,h.attempt,h.fence)
                WHERE a.id=%s AND a.project=%s AND a.run_id=%s AND a.attempt=%s AND a.fence=%s
                AND a.state='active' ''', (assignment_id, project, run_id, attempt, fence)).fetchone()
            if row is None or (row['scheduler_id'], row['scheduler_epoch']) != (actor['id'], actor['epoch']):
                raise Denied('E_STALE')
            self.conn.execute("UPDATE b_assignments SET state='retired' WHERE id=%s", (assignment_id,))
            self.conn.execute('UPDATE b_heads SET fence=fence+1 WHERE project=%s AND run_id=%s', (project, run_id))
            self.log('service', actor['id'], project, run_id, 'retire_metadata')
        return {'retiredMetadata': True}

    def denied(self, code):
        with self.identity.tx():
            self.log(None, None, None, None, 'denied_' + code)


ADMIN_FIELDS = MappingProxyType({'create_service': frozenset(('access', 'service_id', 'kind', 'projects')),
                                'rotate': frozenset(('access', 'service_id')),
                                'revoke_service': frozenset(('access', 'service_id'))})
SERVICE_FIELDS = MappingProxyType({
    'assign': frozenset(('credential', 'project', 'run_id', 'worker_id', 'expected_attempt', 'ttl_ms')),
    'check': frozenset(('credential', 'project', 'run_id', 'assignment_id', 'attempt', 'fence')),
    'renew': frozenset(('credential', 'project', 'run_id', 'assignment_id', 'attempt', 'fence', 'ttl_ms')),
    'retire': frozenset(('credential', 'project', 'run_id', 'assignment_id', 'attempt', 'fence'))})


class _Facade:
    __slots__ = ('__store',)
    FIELDS = MappingProxyType({})

    def __init__(self, schema):
        self.__store = _AuthorityStore(schema)

    def close(self):
        self.__store.close()

    def dispatch(self, route, **body):
        try:
            if (type(route) is not str or route not in self.FIELDS or body.get('version') != VERSION
                    or set(body) != self.FIELDS[route] | {'version'}):
                raise Denied('E_INPUT')
            params = dict(body); del params['version']
            return getattr(self.__store, route)(**params)
        except (Denied, TypeError, ValueError, psycopg.Error) as error:
            code = error.code if isinstance(error, Denied) else ('E_DEPENDENCY' if isinstance(error, psycopg.Error) else 'E_INPUT')
            try:
                self.__store.denied(code)
            except psycopg.Error:
                code = 'E_DEPENDENCY'
            raise Denied(code) from None


class AdminServices(_Facade):
    FIELDS = ADMIN_FIELDS


class ServiceAuthority(_Facade):
    FIELDS = SERVICE_FIELDS
