"""Trusted local admission coordinator; no network endpoint or arbitrary commands."""
from pathlib import Path
import re
import uuid
from types import MappingProxyType

from authority import _AuthorityStore, Denied
import psycopg

VERSION = 's4-c-1.0.0'


class _LaunchStore(_AuthorityStore):
    def __init__(self, schema, create=False):
        super().__init__(schema)
        if create:
            with self.identity.tx():
                self.conn.execute((Path(__file__).parent / 'schema.sql').read_text())
        if self.conn.execute('SELECT version FROM launch_identity').fetchone() != {'version': VERSION}:
            raise Denied('E_SCHEMA')

    def job(self, job_id):
        if type(job_id) is not str or not re.fullmatch('[a-f0-9]{32}', job_id):
            raise Denied('E_INPUT')
        row = self.conn.execute('SELECT * FROM launch_jobs WHERE id=%s', (job_id,)).fetchone()
        if row is None:
            raise Denied('E_DENIED')
        return row

    def prepare(self, credential, generation, project, run_id, assignment_id, attempt, fence):
        with self.service_unit(credential, 'worker', project) as (actor, deadlines):
            self.current_assignment(actor, project, run_id, assignment_id, attempt, fence, deadlines)
            if self.conn.execute("SELECT 1 FROM launch_jobs WHERE project=%s AND run_id=%s AND state!='cleaned'",
                                 (project, run_id)).fetchone():
                raise Denied('E_UNRESOLVED')
            job_id = uuid.uuid4().hex
            self.conn.execute("INSERT INTO launch_jobs VALUES(%s,%s,%s,%s,%s,%s,%s,'prepared',NULL)",
                              (job_id, project, run_id, assignment_id, attempt, fence, generation))
            self.log('service', actor['id'], project, run_id, 'prepare_launch')
        return job_id

    def consume(self, credential, job_id, generation):
        # Row binds original resource IDs; request never supplies a replacement binding.
        row = self.job(job_id)
        with self.service_unit(credential, 'worker', row['project']) as (actor, deadlines):
            row = self.job(job_id)
            if row['helper_generation'] != generation or row['state'] != 'prepared':
                raise Denied('E_STALE')
            self.current_assignment(actor, row['project'], row['run_id'], row['assignment_id'],
                                    row['attempt'], row['fence'], deadlines)
            self.conn.execute("UPDATE launch_jobs SET state='consumed' WHERE id=%s", (job_id,))
            self.log('service', actor['id'], row['project'], row['run_id'], 'consume_launch')
        # Committed consumption is deliberately uncertain until observed, never replayable.
        return row

    def check_job(self, credential, job_id):
        row = self.job(job_id)
        return self.check(credential, row['project'], row['run_id'], row['assignment_id'], row['attempt'], row['fence'])

    def observed(self, job_id, generation, *, container=None, cleaned=False):
        # Trusted controller-only facility; no client route/boolean reaches this method.
        with self.identity.tx():
            row = self.job(job_id)
            if row['helper_generation'] != generation or row['state'] == 'cleaned':
                raise Denied('E_STALE')
            if container is not None and not re.fullmatch('[a-f0-9]{64}', container):
                raise Denied('E_INPUT')
            self.conn.execute('UPDATE launch_jobs SET container_id=COALESCE(%s,container_id),state=%s WHERE id=%s',
                              (container, 'cleaned' if cleaned else row['state'], job_id))
            self.log('supervisor', generation, row['project'], row['run_id'], 'observed_cleanup' if cleaned else 'observed_launch')


FIELDS = MappingProxyType({
    'prepare': frozenset(('credential', 'project', 'run_id', 'assignment_id', 'attempt', 'fence')),
    'release': frozenset(('credential', 'job_id')),
})


class WorkerBridge:
    def __init__(self, schema, helper):
        self._store = _LaunchStore(schema, create=True)
        self._helper = helper
        self._credentials = {}

    def close(self):
        self._store.close()

    def dispatch(self, route, **body):
        try:
            if (type(route) is not str or route not in FIELDS or body.get('version') != VERSION
                    or set(body) != FIELDS[route] | {'version'}):
                raise Denied('E_INPUT')
            args = dict(body); del args['version']
            if route == 'prepare':
                job_id = self._store.prepare(generation=self._helper.generation, **args)
                self._helper.request('register', job=job_id)
                self._credentials[job_id] = args['credential']
                return {'jobId': job_id}
            return self._release(**args)
        except (Denied, TypeError, ValueError, psycopg.Error) as error:
            code = error.code if isinstance(error, Denied) else ('E_DEPENDENCY' if isinstance(error, psycopg.Error) else 'E_INPUT')
            raise Denied(code) from None

    def _release(self, credential, job_id, after_consume=lambda: None):
        if job_id not in self._credentials:
            raise Denied('E_CONTEXT')
        self._store.consume(credential, job_id, self._helper.generation)
        after_consume()  # trusted test fault only; never accepted by public dispatch
        observation = self._helper.request('launch', job=job_id)
        self._store.observed(job_id, self._helper.generation, container=observation['containerId'])
        return observation

    def _cleanup(self, job_id):
        observation = self._helper.request('cleanup', job=job_id)
        if (observation['generation'] != self._helper.generation or observation['jobId'] != job_id
                or not observation['originalProcessesNotLive'] or not observation['cgroupEmptyOrRemoved']
                or not observation['containerRemoved']):
            raise Denied('E_CLEANUP')
        self._store.observed(job_id, self._helper.generation, cleaned=True)
        return observation

    def supervise(self, job_id):
        # Owned loop uses held original service identity, not an unauthenticated request.
        if job_id not in self._credentials:
            raise Denied('E_CONTEXT')
        try:
            self._store.check_job(self._credentials[job_id], job_id)
            return {'authority': 'LIVE'}
        except (Denied, psycopg.Error):
            return {'authority': 'DENIED', 'cleanup': self._cleanup(job_id)}
