"""S2-C scheduler model. Capacity is metadata admission, not container enforcement."""

import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'spikes/s2b'))
from store_b import LeaseStore,Rejected,canonical,digest,sql
from psycopg.types.json import Jsonb


def project_values(value,project_id):
    if isinstance(value,dict):return {key:project_values(item,project_id) for key,item in value.items()}
    if isinstance(value,list):return [project_values(item,project_id) for item in value]
    return project_id if value=='proj' else value


class CapacityStore(LeaseStore):
    def __init__(self,schema,create=False):
        super().__init__(schema,create=create)
        if create:
            with self.conn.transaction():
                self.conn.execute((Path(__file__).parent/'schema.sql').read_text())
        if self.conn.execute('SELECT version FROM capacity_identity').fetchone()!={'version':'s2c-1.0.0'}:
            self.close();raise ValueError('Wrong capacity model')

    @staticmethod
    def limit(value):
        if type(value) is not int or not 1<=value<=1000:raise Rejected('Invalid fixture capacity')

    def add_project(self,project_id,cap=1):
        self.limit(cap)
        with self.conn.transaction():
            self.conn.execute('SELECT * FROM scheduler WHERE id=1 FOR UPDATE')
            self.conn.execute('INSERT INTO projects(project_id,cap) VALUES(%s,%s)',(project_id,cap))

    def seed(self,run_id,project_id,case='complete',**predicates):
        with self.conn.transaction():
            super().seed(run_id,case,**predicates)
            row=self.row(run_id)
            bundle=project_values(json.loads(bytes(row['bundle'])),project_id)
            assessment=project_values(json.loads(bytes(row['assessment'])),project_id)
            self.conn.execute('''UPDATE runs SET project_id=%s,bundle=%s,assessment=%s,
                bundle_sha=%s,assessment_sha=%s WHERE id=%s''',
                (project_id,canonical(bundle),canonical(assessment),digest(bundle),digest(assessment),run_id))

    def occupancy(self):
        rows=self.conn.execute('''SELECT project_id,count(*) AS n FROM runs r
            WHERE state IN ('checking','recovering','cancelling') OR
            EXISTS(SELECT 1 FROM cleanup_requests c WHERE c.id=r.cleanup_request AND c.status='pending')
            GROUP BY project_id''').fetchall()
        return {row['project_id']:row['n'] for row in rows}

    def configure(self,global_cap=None,project_id=None,project_cap=None):
        if global_cap is not None:self.limit(global_cap)
        if project_cap is not None:self.limit(project_cap)
        if global_cap is None and project_cap is None:raise Rejected('No configuration provided')
        with self.conn.transaction():
            self.conn.execute('SELECT * FROM scheduler WHERE id=1 FOR UPDATE')
            counts=self.occupancy()
            if global_cap is not None:
                if sum(counts.values())>global_cap:raise Rejected('Global limit below occupied slots')
                self.conn.execute('UPDATE scheduler SET global_cap=%s WHERE id=1',(global_cap,))
            if project_cap is not None:
                if counts.get(project_id,0)>project_cap:raise Rejected('Project limit below occupied slots')
                if self.conn.execute('UPDATE projects SET cap=%s WHERE project_id=%s RETURNING project_id',
                                     (project_cap,project_id)).fetchone() is None:
                    raise Rejected('Unknown project')

    def claim(self,specific=None,ttl_ms=1800000,before_commit=lambda:None):
        self.duration(ttl_ms)
        with self.conn.transaction():
            scheduler=self.conn.execute('SELECT * FROM scheduler WHERE id=1 FOR UPDATE').fetchone()
            counts=self.occupancy()
            if sum(counts.values())>=scheduler['global_cap']:return None
            projects=self.conn.execute('''SELECT p.* FROM projects p WHERE EXISTS
                (SELECT 1 FROM runs r WHERE r.project_id=p.project_id AND r.state='queued'
                 AND r.cleanup_ok AND r.cleanup_request IS NULL AND r.policy_ok AND r.attempt<r.max_attempts
                 AND (%s::text IS NULL OR r.id=%s)) ORDER BY p.last_served,p.project_id''',(specific,specific)).fetchall()
            available=[]
            for project in projects:
                if counts.get(project['project_id'],0)>=project['cap']:continue
                candidate=self.conn.execute('''WITH head AS MATERIALIZED (SELECT id
                    FROM runs WHERE project_id=%s AND state='queued' AND cleanup_ok AND cleanup_request IS NULL
                    AND policy_ok AND attempt<max_attempts ORDER BY queued_at,id LIMIT 1)
                    SELECT r.id,EXTRACT(EPOCH FROM clock_timestamp()-r.queued_at)*1000 AS age FROM runs r
                    JOIN head ON head.id=r.id WHERE r.state='queued' AND r.cleanup_ok AND r.cleanup_request IS NULL
                    AND r.policy_ok AND r.attempt<r.max_attempts AND (%s::text IS NULL OR r.id=%s)
                    FOR UPDATE OF r SKIP LOCKED''',
                    (project['project_id'],specific,specific)).fetchone()
                if candidate is not None:available.append((project,candidate))
            if not available:return None
            # Probe all projects under admission guard; held candidates are released at commit.
            # Locked queues are not eligible and cannot block other projects.
            eligible=[project for project,_candidate in available]
            selected,candidate=available[0]
            claim=super().claim(candidate['id'],ttl_ms=ttl_ms)
            if claim is None:raise Rejected('Admission candidate changed')
            turn=scheduler['turn']+1
            self.conn.execute('UPDATE scheduler SET turn=%s WHERE id=1',(turn,))
            self.conn.execute('UPDATE projects SET last_served=%s WHERE project_id=%s',(turn,selected['project_id']))
            self.conn.execute('INSERT INTO admissions VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (turn,claim['id'],claim['attempt'],selected['project_id'],Jsonb(eligible),Jsonb(counts),
                 scheduler['global_cap'],selected['cap'],candidate['age'],claim['backend'],claim['process']))
            before_commit()
            return {**claim,'project_id':selected['project_id'],'turn':turn}
