"""S2 experiment transaction adapter. No production API, auth, export or worker."""

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

from local import CACHE, ROOT, connect

sys.path.insert(0, str(CACHE / 'deps'))
sys.path.insert(0, str(ROOT))
import psycopg
from psycopg.rows import dict_row
from psycopg import sql
from qa_core.publication import create_publication_package, validate_publication_package
from qa_core.reports import digest


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


class Rejected(Exception):
    """Fixed experiment error; does not echo supplied raw data."""


class Store:
    def __init__(self, schema, create=False):
        if not re.fullmatch(r's2_[a-f0-9]{32}', schema):
            raise ValueError('Invalid experiment namespace')
        self.conn = connect()
        self.conn.row_factory = dict_row
        if create:
            self.conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        self.conn.execute(sql.SQL('SET search_path TO {}, public').format(sql.Identifier(schema)))
        if create:
            self.conn.execute((Path(__file__).parent / 'schema.sql').read_text())

    def close(self):
        self.conn.close()

    def seed(self, run_id, case='complete', **predicates):
        folder = ROOT / 'examples/reports/runtime-v1' / case
        bundle, assessment = [json.loads((folder / (name + '.json')).read_text(encoding='utf-8'))
                              for name in ('bundle', 'assessment')]
        run = bundle['runs'][0]
        run.update(id=run_id, state='queued', stateVersion=3, attempt=0, lease=None)
        for progress in bundle['progress']:
            progress.update(runId=run_id, runStateVersion=3)
        self.conn.execute('''INSERT INTO runs
            (id,occurrence,state,version,attempt,fence,bundle,assessment,bundle_sha,assessment_sha,
             cleanup_ok,policy_ok) VALUES (%s,%s,'queued',3,0,3,%s,%s,%s,%s,%s,%s)''',
            (run_id, run_id, canonical(bundle), canonical(assessment), digest(bundle), digest(assessment),
             predicates.get('cleanup_ok', True), predicates.get('policy_ok', True)))

    def claim(self, specific=None, hold_seconds=0):
        begin = time.time_ns()
        with self.conn.transaction():
            row = self.conn.execute('''SELECT *, pg_backend_pid() AS backend,
                EXTRACT(EPOCH FROM clock_timestamp()-queued_at)*1000 AS queue_age_ms
                FROM runs WHERE state='queued' AND cleanup_ok AND policy_ok
                AND (%s::text IS NULL OR id=%s) ORDER BY id
                FOR UPDATE SKIP LOCKED LIMIT 1''', (specific, specific)).fetchone()
            if row is None:
                return None
            bundle = json.loads(bytes(row['bundle']))
            run = bundle['runs'][0]
            expires = self.conn.execute("SELECT clock_timestamp()+interval '30 minutes' AS expiry").fetchone()['expiry']
            run.update(state='checking', stateVersion=row['version'] + 1, attempt=row['attempt'] + 1,
                       lease={'workerId': 'worker', 'fencingToken': row['fence'] + 1,
                              'expiresAt': expires.isoformat().replace('+00:00', 'Z')})
            self.conn.execute('''UPDATE runs SET state='checking',version=version+1,
                attempt=attempt+1,fence=fence+1,expires=%s,bundle=%s,bundle_sha=%s WHERE id=%s''',
                (expires, canonical(bundle), digest(bundle), row['id']))
            self.conn.execute('INSERT INTO claims VALUES (%s,%s,%s,%s,%s)',
                              (row['id'], run['attempt'], run['lease']['fencingToken'], row['backend'], os.getpid()))
            if hold_seconds:
                time.sleep(hold_seconds)  # Test-only lock overlap; no fairness claim.
        return {'id': row['id'], 'version': run['stateVersion'], 'attempt': run['attempt'],
                'fence': run['lease']['fencingToken'], 'backend': row['backend'], 'process': os.getpid(),
                'begin_ns': begin, 'end_ns': time.time_ns(), 'queue_age_ms': float(row['queue_age_ms'])}

    def row(self, run_id, lock=False):
        return self.conn.execute('''SELECT *,expires>clock_timestamp() AS unexpired FROM runs WHERE id=%s'''
                                 + (' FOR UPDATE' if lock else ''), (run_id,)).fetchone()

    @staticmethod
    def check_current(row, claim):
        if (row is None or row['state'] != 'checking' or not row['cleanup_ok'] or not row['policy_ok']
                or not row['unexpired'] or (row['version'], row['attempt'], row['fence']) !=
                (claim['version'], claim['attempt'], claim['fence'])):
            raise Rejected('Current run preconditions rejected')

    def package(self, claim):
        row = self.row(claim['id'])
        return create_publication_package(json.loads(bytes(row['bundle'])),
                                          json.loads(bytes(row['assessment'])),
                                          run_id=claim['id'], report_id='report-' + claim['id'])

    def validate_locked(self, row, claim, package):
        self.check_current(row, claim)
        # Independent anchors are kept in run columns, not learned from the submitted package.
        if (hashlib.sha256(bytes(row['bundle'])).hexdigest() != row['bundle_sha']
                or hashlib.sha256(bytes(row['assessment'])).hexdigest() != row['assessment_sha']
                or validate_publication_package(package, expected_bundle_sha256=row['bundle_sha'],
                    expected_assessment_sha256=row['assessment_sha'], run_id=claim['id'],
                    report_id='report-' + claim['id'])):
            raise Rejected('Package binding/derivation rejected')
        run = json.loads(bytes(row['bundle']))['runs'][0]
        if (run['stateVersion'], run['attempt'], run['lease']['fencingToken']) != (
                row['version'], row['attempt'], row['fence']):
            raise Rejected('Frozen/current snapshot mismatch')

    def accept_receipt(self, claim, package):
        """Synthetic persisted result receipt, not trusted semantic acceptance."""
        with self.conn.transaction():
            row = self.row(claim['id'], lock=True)
            self.validate_locked(row, claim, package)
            self.check_expiry(claim)
            self.conn.execute('INSERT INTO receipts VALUES (%s,%s,%s,%s,%s)',
                (claim['id'], claim['attempt'], claim['fence'], claim['version'], digest(package)))

    def check_expiry(self, claim):
        if not self.conn.execute('SELECT expires>clock_timestamp() AS valid FROM runs WHERE id=%s',
                                 (claim['id'],)).fetchone()['valid']:
            raise Rejected('Lease expired during validation')

    def complete(self, claim, package, hook=lambda _point: None):
        with self.conn.transaction():
            row = self.row(claim['id'], lock=True)
            self.validate_locked(row, claim, package)
            receipt = self.conn.execute('SELECT * FROM receipts WHERE run_id=%s', (claim['id'],)).fetchone()
            if receipt is None or (receipt['version'], receipt['attempt'], receipt['fence'], receipt['package_sha']) != (
                    claim['version'], claim['attempt'], claim['fence'], digest(package)):
                raise Rejected('Current synthetic result receipt required')
            graph = package['graph']
            report_id = package['target']['reportId']
            payload = canonical(package)
            self.check_expiry(claim)
            self.conn.execute('INSERT INTO reports VALUES (%s,%s,%s,%s,%s,%s)',
                (report_id, claim['id'], payload, hashlib.sha256(payload).hexdigest(), len(payload),
                 graph['reportReference']['reportSha256']))
            self.conn.execute('''UPDATE runs SET state='completed',version=version+1,expires=NULL,
                report_id=%s WHERE id=%s''', (report_id, claim['id']))
            event = graph['reportReadyCandidate']
            self.conn.execute('INSERT INTO outbox VALUES (%s,%s,%s,%s,%s,false)',
                ('ready-' + claim['id'], claim['id'], report_id, event['sequence'], event['runStateVersion']))
            hook('before_commit')
        hook('after_commit')

    def cancel_predicate(self, claim):
        """CAS terminal competitor only; no claim of real cancel/cleanup lifecycle."""
        with self.conn.transaction():
            row = self.row(claim['id'], lock=True)
            self.check_current(row, claim)
            self.conn.execute("UPDATE runs SET state='cancelled',version=version+1,expires=NULL WHERE id=%s",
                              (claim['id'],))

    def state(self, run_id):
        row = self.row(run_id)
        counts = {table: self.conn.execute(sql.SQL('SELECT count(*) AS n FROM {} WHERE run_id=%s')
                  .format(sql.Identifier(table)), (run_id,)).fetchone()['n']
                  for table in ('claims', 'receipts', 'reports', 'outbox')}
        return {'state': row['state'], 'version': row['version'], 'report_id': row['report_id'], **counts}

    def verify_roundtrip(self, claim, package):
        row = self.row(claim['id'])
        report = self.conn.execute('SELECT * FROM reports WHERE run_id=%s', (claim['id'],)).fetchone()
        payload = bytes(report['package'])
        assert payload == canonical(package)
        assert len(payload) == report['package_length']
        assert hashlib.sha256(payload).hexdigest() == report['package_sha']
        assert not validate_publication_package(json.loads(payload), expected_bundle_sha256=row['bundle_sha'],
            expected_assessment_sha256=row['assessment_sha'], run_id=claim['id'], report_id='report-' + claim['id'])
        return {'canonical_sha256': report['package_sha'], 'canonical_length': len(payload),
                'bundle_sha256': row['bundle_sha'], 'assessment_sha256': row['assessment_sha']}
