"""Candidate DB+external-authority witness, using only retained synthetic prerequisites."""
from contextlib import contextmanager
from pathlib import Path
import os
import secrets
import sys
import uuid

from .common import VERSION, Error, canonical, digest, identifier, require, strict_json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'spikes/s6b'))
from identity import _Store, Denied, ALLOWED, Jsonb, digest as token_digest
import psycopg


class Store:
    def __init__(self, schema, root, *, create=False, observer=None):
        self.schema, self.root = schema, Path(root)
        self.observer = observer
        require(self.root.is_absolute(), 'E_DEPENDENCY')
        self.identity = _Store(schema, create=create)
        self.conn = self.identity.conn
        try:
            if create:
                self.root.mkdir(exist_ok=False, parents=True)
                with self.identity.tx():
                    self.conn.execute((Path(__file__).parent / 'schema.sql').read_text(encoding='utf-8'))
                    instance, nonce = uuid.uuid4().hex, uuid.uuid4().hex
                    self.conn.execute('INSERT INTO rt_control VALUES(1,%s,%s,%s,16)', (VERSION, instance, nonce))
                    self._save_witness({'version': VERSION, 'schema': schema, 'instance': instance, 'nonce': nonce})
            row = self.conn.execute('SELECT * FROM rt_control WHERE id=1').fetchone()
            require(row is not None and row['version'] == VERSION, 'E_VERSION')
            self.instance = row['instance']
            from .blobs import BlobStore
            self.blobs = BlobStore.create(self.root / 'blobs', owner=self.instance) if create else BlobStore(self.root / 'blobs', owner=self.instance)
        except Exception:
            self.identity.close()
            raise

    def close(self):
        self.identity.close()

    def _save_witness(self, value):
        self._atomic_json('authority.json', value)
        if self.observer is not None:
            self.observer('authority_witness_written')

    def _atomic_json(self, filename, value):
        target = self.root / filename
        temporary = self.root / ('.authority-' + uuid.uuid4().hex + '.tmp')
        with temporary.open('xb') as stream:
            stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, target)

    def _cluster(self):
        marker = self.conn.execute('SELECT marker FROM public.s2_identity').fetchone()['marker']
        system_id = self.conn.execute('SELECT system_identifier::text AS id FROM pg_catalog.pg_control_system()').fetchone()['id']
        return {'marker': marker, 'systemIdentifier': system_id}

    def reconcile_aborted_transition(self, expected_nonce):
        """Operator-only repair of a proven aborted transaction, never a public route.

        A retired/rolled-back/unknown head, unretained XID or committed transition cannot
        be guessed safe. The single transition slot is bounded; exceptional intent
        receipts are limited to64 and retained for explicit operator custody.
        """
        import re
        require(isinstance(expected_nonce, str) and re.fullmatch('[a-f0-9]{32}', expected_nonce), 'E_INPUT')
        try:
            with self.identity.tx():
                row = self.conn.execute('SELECT * FROM rt_control WHERE id=1').fetchone()
                journal = strict_json((self.root / 'authority-transition.json').read_bytes())
                require(isinstance(journal, dict) and set(journal) == {'version', 'domain', 'schema', 'instance', 'previousNonce', 'nextNonce', 'xid8', 'cluster', 'salt'}, 'E_UNRESOLVED')
                require((journal['version'], journal['schema'], journal['instance'], journal['nextNonce']) ==
                        (VERSION, self.schema, row['instance'], expected_nonce) and journal['cluster'] == self._cluster(), 'E_UNRESOLVED')
                require(isinstance(journal['previousNonce'], str) and re.fullmatch('[a-f0-9]{32}', journal['previousNonce'])
                        and isinstance(journal['xid8'], str) and re.fullmatch('[1-9][0-9]{0,19}', journal['xid8'])
                        and journal['domain'] == 'm50-authority-transition-1.0.0'
                        and isinstance(journal['salt'], str) and re.fullmatch('[a-f0-9]{64}', journal['salt']), 'E_UNRESOLVED')
                binding = {key: value for key, value in journal.items() if key != 'nextNonce'}
                require(digest(binding)[:32] == expected_nonce, 'E_UNRESOLVED')
                head = strict_json((self.root / 'authority.json').read_bytes())
                previous = {'version': VERSION, 'schema': self.schema, 'instance': row['instance'], 'nonce': journal['previousNonce']}
                next_head = dict(previous, nonce=expected_nonce)
                require(row['nonce'] == journal['previousNonce'] and head in (next_head, previous), 'E_UNRESOLVED')
                status = self.conn.execute('SELECT pg_xact_status(%s::xid8) AS status', (journal['xid8'],)).fetchone()['status']
                require(status == 'aborted', 'E_UNRESOLVED')
                receipt = {'version': VERSION, 'kind': 'verified_aborted_transition_recovery_intent',
                           'transitionSha256': digest(journal), 'xid8': journal['xid8'], 'cluster': journal['cluster'],
                           'previousHeadSha256': digest(previous), 'uncertainHeadSha256': digest(next_head)}
                path = self.root / ('authority-recovery-' + expected_nonce + '.json')
                if path.exists():
                    require(strict_json(path.read_bytes()) == receipt, 'E_UNRESOLVED')
                else:
                    require(head == next_head and len(list(self.root.glob('authority-recovery-*.json'))) < 64, 'E_UNRESOLVED')
                    self._atomic_json(path.name, receipt)
                # Intent is durable first; retry after a crash between intent and head is idempotent.
                if head == next_head:
                    self._save_witness(previous)
                require(self._check_witness() == previous, 'E_UNRESOLVED')
                return {'recovered': True, 'xid8': journal['xid8'], 'transactionStatus': status,
                        'receiptSha256': digest(receipt)}
        except Error as exc:
            raise Error('E_UNRESOLVED') from None
        except (OSError, ValueError, KeyError, psycopg.Error):
            raise Error('E_UNRESOLVED') from None

    def _check_witness(self):
        row = self.conn.execute('SELECT * FROM rt_control WHERE id=1').fetchone()
        expected = {'version': VERSION, 'schema': self.schema, 'instance': row['instance'], 'nonce': row['nonce']}
        try:
            require(strict_json((self.root / 'authority.json').read_bytes()) == expected, 'E_UNRESOLVED')
        except (OSError, ValueError):
            raise Error('E_UNRESOLVED') from None
        return expected

    @contextmanager
    def unit(self, token=None, *, kind='user', project=None, write=False, restricted=False):
        with self.identity.tx(token if kind == 'user' else None, restricted=restricted) as actor:
            previous = self._check_witness()
            deadlines = []
            if kind != 'user':
                row = self.conn.execute('''SELECT s.*,c.expires FROM rt_services s JOIN rt_credentials c
                    ON (s.id,s.epoch)=(c.service,c.epoch) WHERE c.digest=%s AND s.enabled
                    AND s.kind=%s AND c.expires>clock_timestamp()''', (token_digest(token, 's'), kind)).fetchone()
                require(row is not None and project in row['projects'], 'E_AUTH')
                actor = row; deadlines.append(row['expires'])
            def check_time():
                if deadlines:
                    require(self.conn.execute('SELECT %s>clock_timestamp() AS live', (min(deadlines),)).fetchone()['live'], 'E_STALE')
                if kind == 'user' and actor is not None:
                    require(self.conn.execute('SELECT %s>clock_timestamp() AND %s>clock_timestamp() AS live',
                            (actor['access_expires'], actor['family_expires'])).fetchone()['live'], 'E_AUTH')
            yield actor, deadlines
            check_time()
            require(self._check_witness() == previous, 'E_UNRESOLVED')
            if write:
                xid = self.conn.execute('SELECT pg_current_xact_id()::text AS xid').fetchone()['xid']
                transition = {'version': VERSION, 'domain': 'm50-authority-transition-1.0.0', 'schema': self.schema,
                              'instance': previous['instance'], 'previousNonce': previous['nonce'],
                              'xid8': xid, 'cluster': self._cluster(), 'salt': secrets.token_hex(32)}
                nonce = digest(transition)[:32]
                self.conn.execute('UPDATE rt_control SET nonce=%s WHERE id=1', (nonce,))
                self._atomic_json('authority-transition.json', dict(transition, nextNonce=nonce))
                # Witness first; uncertain DB commit becomes a fail-closed mismatch, never guessed latest.
                self._save_witness(dict(previous, nonce=nonce))
                # No external IO follows this last clock predicate before SQL commit.
                # Expiry here rolls SQL back; the retained exact-XID journal permits
                # operator repair only after PostgreSQL proves the transaction aborted.
                check_time()

    def config(self, actor, project, action='read', *, allow_disabled=False):
        role = self.identity.role(actor, project)
        require(action in ALLOWED[role], 'E_DENIED')
        row = self.conn.execute('''SELECT p.*,c.payload FROM rt_projects p JOIN rt_configs c
            ON (p.project,p.config_version)=(c.project,c.version) WHERE p.project=%s''', (project,)).fetchone()
        require(row is not None and (allow_disabled or row['enabled'] and row['payload']['enabled']), 'E_DENIED')
        return row, role

    def run(self, project, run_id):
        identifier(project); identifier(run_id)
        row = self.conn.execute('SELECT * FROM rt_runs WHERE project=%s AND id=%s', (project, run_id)).fetchone()
        require(row is not None, 'E_DENIED')
        return row

    def snapshot(self, project, snapshot):
        row = self.conn.execute('SELECT * FROM rt_snapshots WHERE project=%s AND id=%s', (project, snapshot)).fetchone()
        require(row is not None, 'E_DENIED')
        return row

    @staticmethod
    def source_scope(snapshot, config):
        # Only required safe input/report roots are public project-scope obligations.
        # Restricted collector derivatives and optional registered auxiliaries are separate.
        required = snapshot['manifest']['reportSourceIds']
        require(set(required) <= set(config['payload']['sourceIds']), 'E_DENIED')

    def grant(self, actor, project, grant_id, action, deadlines):
        config, role = self.config(actor, project, action)
        row = self.conn.execute('SELECT * FROM rt_grants WHERE id=%s', (grant_id,)).fetchone()
        require(row is not None and not row['revoked'] and action in row['actions']
                and (row['project'], row['user_id'], row['user_epoch'], row['config_version'], row['policy_version']) ==
                (project, actor['id'], actor['epoch'], config['config_version'], config['policy_version']), 'E_DENIED')
        require(self.conn.execute('SELECT %s>clock_timestamp() AS live', (row['expires'],)).fetchone()['live'], 'E_DENIED')
        deadlines.append(row['expires'])
        return config, role, row

    def delegation(self, run, deadlines):
        actor = self.conn.execute('SELECT * FROM accounts WHERE id=%s', (run['owner'],)).fetchone()
        require(actor is not None and actor['enabled'] and not actor['must_change'] and actor['epoch'] == run['user_epoch'], 'E_DENIED')
        config, _, grant = self.grant(actor, run['project'], run['grant_id'], 'start', deadlines)
        require((config['config_version'], config['policy_version']) == (run['config_version'], run['policy_version']), 'E_STALE')
        self.source_scope(self.snapshot(run['project'], run['snapshot']), config)
        return config

    def assignment(self, actor, body, deadlines, *, live=True):
        run = self.run(body['project'], body['run_id'])
        require((run['assignment'], run['fence'], run['worker'], run['worker_epoch']) ==
                (body['assignment'], body['fence'], actor['id'], actor['epoch']), 'E_STALE')
        require(run['lease_hash'] == token_digest(body['lease_token'], 'l'), 'E_AUTH')
        if live:
            self.current_work(run, deadlines)
        return run

    def current_work(self, run, deadlines):
        require(run['state'] in ('collecting', 'awaiting_assessment', 'analyzing') and not run['cancel_requested'], 'E_STALE')
        require(run['lease_expires'] is not None and run['run_deadline'] is not None and
                self.conn.execute('SELECT %s>clock_timestamp() AND %s>clock_timestamp() AS live',
                    (run['lease_expires'], run['run_deadline'])).fetchone()['live'], 'E_STALE')
        worker = self.conn.execute('''SELECT s.*,max(c.expires) AS expires FROM rt_services s JOIN rt_credentials c
            ON (s.id,s.epoch)=(c.service,c.epoch) WHERE s.id=%s AND s.kind='worker' AND s.enabled
            AND c.expires>clock_timestamp() GROUP BY s.id''', (run['worker'],)).fetchone()
        require(worker is not None and worker['epoch'] == run['worker_epoch'] and run['project'] in worker['projects'], 'E_DENIED')
        config = self.delegation(run, deadlines)
        deadlines.extend((run['lease_expires'], run['run_deadline'], worker['expires']))
        return config

    def event(self, run, event, data):
        row = self.conn.execute('''UPDATE rt_runs SET sequence=sequence+1 WHERE project=%s AND id=%s
            RETURNING sequence,version''', (run['project'], run['id'])).fetchone()
        payload = dict(data, stateVersion=row['version'])
        self.conn.execute('INSERT INTO rt_events(project,run_id,sequence,event,data) VALUES(%s,%s,%s,%s,%s)',
                          (run['project'], run['id'], row['sequence'], event, Jsonb(payload)))

    def prior(self, actor, project, op, key, body):
        identifier(key)
        row = self.conn.execute('SELECT * FROM rt_receipts WHERE actor=%s AND project=%s AND key=%s',
                                (actor['id'], project, key)).fetchone()
        if row is not None:
            require(row['operation'] == op and row['payload_digest'] == digest(body), 'E_CONFLICT')
            return row['result']

    def save_receipt(self, actor, project, op, key, body, result):
        self.conn.execute('INSERT INTO rt_receipts VALUES(%s,%s,%s,%s,%s,%s)',
                          (actor['id'], project, op, key, digest(body), Jsonb(result)))

    @staticmethod
    def issue_token(kind):
        return kind + '.' + secrets.token_urlsafe(32)
