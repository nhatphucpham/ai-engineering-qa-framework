"""Trusted S4-D controller: no client cleanup acknowledgement route."""
from pathlib import Path
import uuid
from gate import _LaunchStore, Denied

VERSION = 's4-d-1.0.0'

class Lifecycle(_LaunchStore):
    def __init__(self, schema, bridge, create=False):
        super().__init__(schema)
        self.bridge = bridge
        if create:
            with self.identity.tx():
                self.conn.execute((Path(__file__).parent / 'schema.sql').read_text(encoding='utf-8'))

    def enroll(self, job):
        with self.identity.tx():
            row = self.job(job)
            if row['state'] != 'consumed' or row['container_id'] is None:
                raise Denied('E_STALE')
            self.conn.execute("INSERT INTO d_lifecycle(job_id,project,run_id,state) VALUES(%s,%s,%s,'active')",
                              (job, row['project'], row['run_id']))

    def reserve(self, job, kind):
        request = uuid.uuid4().hex
        row = self.conn.execute("UPDATE d_lifecycle SET state=%s,request_id=%s,deadline=clock_timestamp()+interval '1 second' WHERE job_id=%s AND state='active' RETURNING *",
                                ('cancelling' if kind == 'cancel' else 'completing', request, job)).fetchone()
        if row is None:
            raise Denied('E_STALE')
        binding = self.job(job)
        retired = self.conn.execute("UPDATE b_assignments SET state='retired' WHERE id=%s AND state='active' RETURNING id", (binding['assignment_id'],)).fetchone()
        fenced = self.conn.execute('UPDATE b_heads SET fence=fence+1 WHERE project=%s AND run_id=%s AND attempt=%s AND fence=%s RETURNING fence', (binding['project'], binding['run_id'], binding['attempt'], binding['fence'])).fetchone()
        if retired is None or fenced is None:
            raise Denied('E_STALE')
        self.log('lifecycle', kind, row['project'], row['run_id'], 'request_cleanup')
        return request

    def cancel(self, access, grant, job):
        row = self.job(job)
        with self.command_unit(access, row['project'], 'cancel', grant) as (actor, policy, snapshot, role):
            run = self.conn.execute('SELECT initiator FROM app_runs WHERE project=%s AND id=%s', (row['project'],row['run_id'])).fetchone()
            if run is None or role == 'Runner' and run['initiator'] != actor['id']:
                raise Denied('E_DENIED')
            return self.reserve(job, 'cancel')

    def complete(self, credential, job):
        row = self.job(job)
        with self.service_unit(credential, 'worker', row['project']) as (actor, deadlines):
            self.current_assignment(actor,row['project'],row['run_id'],row['assignment_id'],row['attempt'],row['fence'],deadlines)
            return self.reserve(job, 'complete')

    def timeout(self, job, request):
        with self.identity.tx():
            row = self.conn.execute("UPDATE d_lifecycle SET state='failed_cleanup_unconfirmed',incident_open=true WHERE job_id=%s AND request_id=%s AND state IN ('cancelling','completing') AND deadline<=clock_timestamp() RETURNING *",(job,request)).fetchone()
            if row is None:
                raise Denied('E_STALE')

    def acknowledge(self, job, request, generation):
        # Internal only: callers cannot supply observation or clean status.
        with self.identity.tx():
            row = self.conn.execute('SELECT d.*,j.state AS job_state,j.helper_generation FROM d_lifecycle d JOIN launch_jobs j ON j.id=d.job_id WHERE d.job_id=%s',(job,)).fetchone()
            if (row is None or row['request_id'] != request or row['helper_generation'] != generation
                or row['job_state'] != 'cleaned' or row['acked'] or row['state'] not in ('cancelling','completing','failed_cleanup_unconfirmed')):
                raise Denied('E_STALE')
            new = {'cancelling':'cancelled','completing':'completed','failed_cleanup_unconfirmed':'failed_cleanup_unconfirmed'}[row['state']]
            self.conn.execute('UPDATE d_lifecycle SET state=%s,acked=true,incident_open=false WHERE job_id=%s',(new,job))
            self.log('supervisor', generation, row['project'], row['run_id'], 'cleanup_ack')

    def cleanup(self, job, request):
        row = self.conn.execute('SELECT * FROM d_lifecycle WHERE job_id=%s',(job,)).fetchone()
        if row is None or row['request_id'] != request or row['acked']:
            raise Denied('E_STALE')
        result = self.bridge._cleanup(job)
        self.acknowledge(job, request, self.bridge._helper.generation)
        return result
