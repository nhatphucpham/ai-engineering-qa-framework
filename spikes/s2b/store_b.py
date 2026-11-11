"""Versioned S2-B persistence experiment; synthetic policy/cleanup, no live authority."""

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spikes/s2'))
from local import connect
from store import Store, Rejected, canonical, digest, psycopg, sql, dict_row


class LeaseStore(Store):
    def __init__(self, schema, create=False):
        if not re.fullmatch(r's2_[a-f0-9]{32}', schema):
            raise ValueError('Invalid experiment namespace')
        self.conn = connect()
        self.conn.row_factory = dict_row
        if create:
            with self.conn.transaction():
                self.conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
                self.conn.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(schema)))
                self.conn.execute((ROOT / 'spikes/s2/schema.sql').read_text())
                self.conn.execute((Path(__file__).parent / 'schema.sql').read_text())
        else:
            self.conn.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(schema)))
        if self.conn.execute('SELECT version FROM model_identity').fetchone() != {'version': 's2b-1.0.0'}:
            self.close()
            raise ValueError('Wrong persistence model')

    @staticmethod
    def duration(milliseconds):
        if type(milliseconds) is not int or not 50 <= milliseconds <= 1800000:
            raise ValueError('Invalid experiment duration')
        return milliseconds

    def claim(self, specific=None, ttl_ms=1800000):
        self.duration(ttl_ms)
        with self.conn.transaction():
            row = self.conn.execute('''SELECT *,pg_backend_pid() AS backend FROM runs
                WHERE state='queued' AND cleanup_ok AND cleanup_request IS NULL AND policy_ok
                AND attempt<max_attempts AND (%s::text IS NULL OR id=%s)
                ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1''', (specific, specific)).fetchone()
            if row is None:
                return None
            expires = self.conn.execute("SELECT clock_timestamp()+(%s*interval '1 millisecond') AS expiry",
                                        (ttl_ms,)).fetchone()['expiry']
            bundle = json.loads(bytes(row['bundle']))
            run = bundle['runs'][0]
            run.update(state='checking', stateVersion=row['version'] + 1, attempt=row['attempt'] + 1,
                       lease={'workerId': 'worker', 'fencingToken': row['fence'] + 1,
                              'expiresAt': expires.isoformat().replace('+00:00', 'Z')})
            self.conn.execute('''UPDATE runs SET state='checking',version=version+1,attempt=attempt+1,
                fence=fence+1,expires=%s,bundle=%s,bundle_sha=%s WHERE id=%s''',
                (expires, canonical(bundle), digest(bundle), row['id']))
            self.conn.execute('INSERT INTO claims VALUES (%s,%s,%s,%s,%s)',
                (row['id'], run['attempt'], run['lease']['fencingToken'], row['backend'], os.getpid()))
            self.conn.execute('INSERT INTO attempt_inputs VALUES (%s,%s,%s,%s,%s,%s,%s)',
                (row['id'], run['attempt'], run['lease']['fencingToken'], canonical(bundle), digest(bundle),
                 row['assessment'], row['assessment_sha']))
        return {'id': row['id'], 'version': run['stateVersion'], 'attempt': run['attempt'],
                'fence': run['lease']['fencingToken'], 'backend': row['backend'], 'process': os.getpid()}

    def current(self, claim):
        if (not isinstance(claim,dict) or not isinstance(claim.get('id'),str)
                or any(type(claim.get(key)) is not int or claim[key] < 1 for key in ('version','attempt','fence'))):
            raise Rejected('Exact integer claim context required')
        row = self.row(claim['id'], lock=True)
        self.check_current(row, claim)
        self.check_expiry(claim)  # Recheck DB clock after lock acquisition/wait.
        return row

    def renew(self, claim, ttl_ms=1800000, before_write=lambda: None):
        self.duration(ttl_ms)
        with self.conn.transaction():
            self.current(claim)
            before_write()  # Test-only delay point; DB predicate still owns acceptance.
            result=self.conn.execute('''UPDATE runs SET expires=GREATEST(expires,
                clock_timestamp()+(%s*interval '1 millisecond')) WHERE id=%s
                AND expires>clock_timestamp() RETURNING expires''', (ttl_ms,claim['id'])).fetchone()
            if result is None:
                raise Rejected('Lease expired before renewal write')
            return result['expires']

    def _stop_locked(self, row, reason, cleanup_ms):
        self.duration(cleanup_ms)
        request = row['cleanup_request']
        if request is None:
            request = 'cleanup-' + uuid.uuid4().hex
            self.conn.execute("INSERT INTO cleanup_requests VALUES (%s,%s,%s,%s,'pending',NULL)",
                              (request, row['id'], row['attempt'], row['fence']))
            self.conn.execute('INSERT INTO incidents(request_id,reason) VALUES (%s,%s)', (request, reason))
        state = 'recovering' if reason == 'lease_expired' else 'cancelling'
        self.conn.execute('''UPDATE runs SET state=%s,version=version+1,fence=fence+1,expires=NULL,
            cleanup_ok=false,cleanup_request=%s,stop_reason=%s,
            cleanup_deadline=COALESCE(cleanup_deadline,clock_timestamp()+(%s*interval '1 millisecond'))
            WHERE id=%s''', (state, request, reason, cleanup_ms, row['id']))
        return request

    def reconcile_expired(self, run_id, cleanup_ms=1800000, hook=lambda: None):
        with self.conn.transaction():
            row = self.row(run_id, lock=True)
            if row is None or row['state'] != 'checking':
                return None
            if self.conn.execute('SELECT expires<=clock_timestamp() AS expired FROM runs WHERE id=%s',
                                 (run_id,)).fetchone()['expired'] is not True:
                return None
            request = self._stop_locked(row, 'lease_expired', cleanup_ms)
            hook()  # Fault injection after recovery writes, before actual commit.
            return request

    def request_stop(self, run_id, expected_version, reason='cancel', cleanup_ms=1800000):
        if reason not in ('cancel', 'revoke'):
            raise ValueError('Unknown stop reason')
        if type(expected_version) is not int or expected_version<1:
            raise Rejected('Exact integer stop version required')
        with self.conn.transaction():
            row = self.row(run_id, lock=True)
            if (row is None or row['version'] != expected_version
                    or row['state'] not in ('queued', 'checking', 'recovering')):
                raise Rejected('Stop CAS rejected')
            if reason == 'revoke':
                self.conn.execute('UPDATE runs SET policy_ok=false WHERE id=%s', (run_id,))
            if row['state'] == 'queued':
                self.conn.execute('''UPDATE runs SET state='cancelled',version=version+1,fence=fence+1,
                    terminal_reason=%s,stop_reason=%s WHERE id=%s''', (reason, reason, run_id))
                return None
            return self._stop_locked(row, reason, cleanup_ms)

    def ack_cleanup(self, run_id, request_id, attempt, fence, observation):
        # Deliberately synthetic: shape/scope cannot authenticate a supervisor's observation.
        expected = {'kind', 'runId', 'requestId', 'attempt', 'fence', 'observationId'}
        if (not isinstance(observation, dict) or set(observation) != expected
                or type(attempt) is not int or type(fence) is not int or attempt<1 or fence<1
                or type(observation['attempt']) is not int or type(observation['fence']) is not int
                or observation['kind'] != 'synthetic-cleanup-observation'
                or (observation['runId'], observation['requestId'], observation['attempt'], observation['fence'])
                   != (run_id, request_id, attempt, fence)
                or not isinstance(observation['observationId'], str)
                or not re.fullmatch(r'observed-[a-f0-9]{32}', observation['observationId'])):
            raise Rejected('Synthetic cleanup observation rejected')
        with self.conn.transaction():
            row = self.row(run_id, lock=True)
            request = self.conn.execute('SELECT * FROM cleanup_requests WHERE id=%s', (request_id,)).fetchone()
            if (row is None or request is None or row['cleanup_request'] != request_id
                    or row['state'] not in ('recovering', 'cancelling', 'failed')
                    or (request['run_id'], request['attempt'], request['fence'], request['status']) !=
                       (run_id, attempt, fence, 'pending')):
                raise Rejected('Cleanup request binding/replay rejected')
            self.conn.execute("UPDATE cleanup_requests SET status='acked',observation=%s WHERE id=%s",
                              (canonical(observation), request_id))
            self.conn.execute('UPDATE incidents SET resolved=true WHERE request_id=%s', (request_id,))
            if row['state'] == 'failed':
                # Late cleanup resolves incident only. Terminal lifecycle row stays immutable.
                return 'failed'
            terminal = row['state'] == 'cancelling' or not row['policy_ok'] or row['attempt'] >= row['max_attempts']
            state = ('cancelled' if row['state'] == 'cancelling' or not row['policy_ok'] else 'failed') if terminal else 'queued'
            reason = row['stop_reason'] if state == 'cancelled' else ('attempts_exhausted' if state == 'failed' else None)
            # One DB clock sample at transition, so even a delayed ack cannot evade deadline.
            return self.conn.execute('''WITH t AS MATERIALIZED (SELECT clock_timestamp() AS now)
                UPDATE runs SET state=CASE WHEN cleanup_deadline>t.now THEN %s ELSE 'failed' END,
                version=version+1,fence=fence+CASE WHEN cleanup_deadline>t.now THEN 0 ELSE 1 END,
                cleanup_ok=cleanup_deadline>t.now,
                cleanup_request=CASE WHEN cleanup_deadline>t.now THEN NULL ELSE cleanup_request END,
                cleanup_deadline=CASE WHEN cleanup_deadline>t.now THEN NULL ELSE cleanup_deadline END,
                terminal_reason=CASE WHEN cleanup_deadline>t.now THEN %s ELSE 'cleanup_unconfirmed' END
                FROM t WHERE id=%s RETURNING state''',(state,reason,run_id)).fetchone()['state']

    def cancel_predicate(self, claim):
        raise Rejected('S2-A terminal-cancel shortcut disabled in S2-B; request stop then cleanup')

    def cleanup_timeout(self, run_id):
        with self.conn.transaction():
            row = self.row(run_id, lock=True)
            if row is None or row['state'] not in ('recovering', 'cancelling'):
                raise Rejected('No pending cleanup')
            expired = self.conn.execute('SELECT cleanup_deadline<=clock_timestamp() AS expired FROM runs WHERE id=%s',
                                        (run_id,)).fetchone()['expired']
            if expired is not True:
                raise Rejected('Cleanup deadline not reached')
            self.conn.execute('''UPDATE runs SET state='failed',version=version+1,fence=fence+1,
                terminal_reason='cleanup_unconfirmed' WHERE id=%s''', (run_id,))

    def accept_receipt(self, claim, package, before_write=lambda: None):
        with self.conn.transaction():
            row=self.current(claim)
            self.validate_locked(row,claim,package)
            before_write()
            result=self.conn.execute('''INSERT INTO receipts SELECT id,attempt,fence,version,%s FROM runs
                WHERE id=%s AND expires>clock_timestamp() RETURNING run_id''',
                (digest(package),claim['id'])).fetchone()
            if result is None:
                raise Rejected('Lease expired before receipt write')

    def complete(self, claim, package, before_write=lambda: None):
        with self.conn.transaction():
            row = self.current(claim)
            self.validate_locked(row, claim, package)
            receipt = self.conn.execute('SELECT * FROM receipts WHERE run_id=%s AND attempt=%s',
                                         (claim['id'], claim['attempt'])).fetchone()
            if receipt is None or (receipt['version'], receipt['fence'], receipt['package_sha']) != (
                    claim['version'], claim['fence'], digest(package)):
                raise Rejected('Current attempt receipt required')
            payload = canonical(package)
            graph = package['graph']
            report_id = package['target']['reportId']
            self.check_expiry(claim)
            before_write()
            self.conn.execute('INSERT INTO reports VALUES (%s,%s,%s,%s,%s,%s)',
                (report_id, claim['id'], payload, hashlib.sha256(payload).hexdigest(), len(payload),
                 graph['reportReference']['reportSha256']))
            result=self.conn.execute('''UPDATE runs SET state='completed',version=version+1,expires=NULL,report_id=%s
                WHERE id=%s AND expires>clock_timestamp() RETURNING id''',(report_id,claim['id'])).fetchone()
            if result is None:
                raise Rejected('Lease expired before completion transition')
            event = graph['reportReadyCandidate']
            self.conn.execute('INSERT INTO outbox VALUES (%s,%s,%s,%s,%s,false)',
                ('ready-' + claim['id'], claim['id'], report_id, event['sequence'], event['runStateVersion']))

    def snapshot(self, run_id):
        row = self.row(run_id)
        return {**self.state(run_id), **{key: row[key] for key in
            ('attempt','fence','cleanup_ok','policy_ok','cleanup_request','stop_reason','terminal_reason')},
            'requests': self.conn.execute('SELECT count(*) AS n FROM cleanup_requests WHERE run_id=%s',
                                         (run_id,)).fetchone()['n'],
            'open_incidents': self.conn.execute('''SELECT count(*) AS n FROM incidents i JOIN cleanup_requests c
                ON c.id=i.request_id WHERE c.run_id=%s AND NOT i.resolved''', (run_id,)).fetchone()['n']}
