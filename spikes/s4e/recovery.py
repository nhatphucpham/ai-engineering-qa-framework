"""Cleanup-only recovery experiment. All entrypoints are trusted internal facilities."""
from pathlib import Path
import uuid

from authority import _AuthorityStore, Denied, Jsonb

VERSION = 's4-e-1.0.0'


class RecoveryStore(_AuthorityStore):
    def __init__(self, schema, create=False):
        super().__init__(schema)
        if create:
            with self.identity.tx():
                self.conn.execute((Path(__file__).parent / 'schema.sql').read_text(encoding='utf-8'))
        if self.conn.execute('SELECT version FROM e_identity').fetchone() != {'version': VERSION}:
            raise Denied('E_SCHEMA')

    def job(self, job):
        row = self.conn.execute('SELECT * FROM e_jobs WHERE id=%s', (job,)).fetchone()
        if row is None:
            raise Denied('E_UNRESOLVED')
        return row

    def prepare(self, credential, generation, project, run_id, assignment_id, attempt, fence):
        with self.service_unit(credential, 'worker', project) as (actor, deadlines):
            self.current_assignment(actor, project, run_id, assignment_id, attempt, fence, deadlines)
            if self.conn.execute('SELECT 1 FROM e_jobs WHERE project=%s AND run_id=%s', (project, run_id)).fetchone():
                raise Denied('E_UNRESOLVED')
            job = uuid.uuid4().hex
            binding = dict(job=job, project=project, run_id=run_id, assignment_id=assignment_id,
                           attempt=attempt, fence=fence, generation=generation, container_name='qa-s4e-' + job)
            self.conn.execute('''INSERT INTO e_jobs(id,project,run_id,assignment_id,attempt,fence,generation,binding,state,recovery_fence)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'prepared',%s)''',
                (job, project, run_id, assignment_id, attempt, fence, generation, Jsonb(binding), fence))
            self.log('service', actor['id'], project, run_id, 'e_prepare')
        return binding

    def consume(self, credential, job):
        row = self.job(job)
        with self.service_unit(credential, 'worker', row['project']) as (actor, deadlines):
            row = self.job(job)
            if row['state'] != 'prepared':
                raise Denied('E_STALE')
            self.current_assignment(actor, row['project'], row['run_id'], row['assignment_id'],
                                    row['attempt'], row['fence'], deadlines)
            self.conn.execute("UPDATE e_jobs SET state='consumed' WHERE id=%s", (job,))
            self.log('service', actor['id'], row['project'], row['run_id'], 'e_consume')
        return row['binding']

    def record_resource(self, job, resource):
        with self.identity.tx():
            row = self.job(job)
            if row['state'] not in ('consumed', 'unresolved') or row['cleanup_proof'] is not None:
                raise Denied('E_STALE')
            if row['resource'] is not None and row['resource'] != resource:
                raise Denied('E_IDENTITY')
            self.conn.execute('UPDATE e_jobs SET resource=%s WHERE id=%s', (Jsonb(resource), job))

    def mark_lost(self, job):
        with self.identity.tx():
            row = self.job(job)
            if row['state'] not in ('consumed', 'unresolved') or row['cleanup_proof'] is not None:
                raise Denied('E_STALE')
            self.conn.execute("UPDATE e_jobs SET state='unresolved',incident_open=true WHERE id=%s", (job,))

    def exact_head(self, row):
        head = self.conn.execute('SELECT * FROM b_heads WHERE project=%s AND run_id=%s',
                                 (row['project'], row['run_id'])).fetchone()
        assignment = self.conn.execute('SELECT * FROM b_assignments WHERE id=%s', (row['assignment_id'],)).fetchone()
        expected_state = 'active' if row['epoch'] == 0 else 'retired'
        if (head is None or (head['attempt'], head['fence']) != (row['attempt'], row['recovery_fence'])
                or assignment is None or assignment['state'] != expected_state
                or (assignment['project'], assignment['run_id'], assignment['attempt'], assignment['fence'])
                != (row['project'], row['run_id'], row['attempt'], row['fence'])):
            raise Denied('E_UNRESOLVED')

    def begin(self, job, helper):
        # Recovery is reducing authority; revoked worker tokens are never reused.
        with self.identity.tx():
            row = self.job(job)
            if row['state'] not in ('consumed', 'unresolved') or row['cleanup_proof'] is not None:
                raise Denied('E_STALE')
            self.exact_head(row)
            self.conn.execute("UPDATE b_assignments SET state='retired' WHERE id=%s", (row['assignment_id'],))
            self.conn.execute('UPDATE b_heads SET fence=fence+1 WHERE project=%s AND run_id=%s',
                              (row['project'], row['run_id']))
            result = self.conn.execute("UPDATE e_jobs SET epoch=epoch+1,recovery_fence=recovery_fence+1,state='unresolved',incident_open=true WHERE id=%s RETURNING *",
                                       (job,)).fetchone()
            self.log('recovery', row['generation'], row['project'], row['run_id'], 'e_incident_fence')
            # Publish server epoch only AFTER the serialized external witness fence.
            # A crash/rollback after witness advancement fails closed on mismatch.
            helper.request('fence', binding=row['binding'], epoch=result['epoch'])
        return result

    def finish(self, job, epoch, proof):
        # Only Controller's actual helper observation reaches this internal method.
        with self.identity.tx():
            row = self.job(job)
            self.exact_head(row)
            if (row['state'] != 'unresolved' or not row['incident_open'] or row['epoch'] != epoch
                    or row['resource'] is None or proof.get('binding') != row['binding']
                    or proof.get('epoch') != epoch or proof.get('resource') != row['resource']
                    or not all(proof.get(k) is True for k in
                               ('originalProcessesNotLive', 'cgroupEmptyOrRemoved', 'containerRemoved'))):
                raise Denied('E_UNRESOLVED')
            self.conn.execute("UPDATE e_jobs SET state='failed',incident_open=false,cleanup_proof=%s WHERE id=%s",
                              (Jsonb(proof), job))
            self.log('recovery', row['generation'], row['project'], row['run_id'], 'e_observed_cleanup')

    def cleanup(self, job, epoch, helper):
        # Hold the authority mutex through exact-head check, engine IO and DB ack.
        with self.identity.tx():
            row = self.job(job)
            if row['state'] != 'unresolved' or row['epoch'] != epoch or row['resource'] is None:
                raise Denied('E_UNRESOLVED')
            self.exact_head(row)
            proof = helper.request('cleanup', binding=row['binding'], epoch=epoch, expected_resource=row['resource'])
            self.finish(job, epoch, proof)
        return proof

    def success(self, job):
        self.job(job)
        raise Denied('E_FAILED_EXECUTION')


class Controller:
    def __init__(self, store, helper):
        self.store, self.helper = store, helper

    def reconcile(self, job):
        self.store.mark_lost(job)
        row = self.store.begin(job, self.helper)
        discovered = self.helper.request('discover', binding=row['binding'])
        resource = discovered['resource']
        self.store.record_resource(job, resource)
        proof = self.store.cleanup(job, row['epoch'], self.helper)
        return proof
