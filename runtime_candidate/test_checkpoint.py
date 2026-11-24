"""Private temporary archives with an injected DB/CLI boundary. No database or engine effects."""
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from runtime_candidate import checkpoint as cp
from runtime_candidate.blobs import BlobStore, descriptor
from runtime_candidate.common import VERSION, Error, canonical, digest, sha, strict_json


SOURCE = 'id_' + '1' * 32
TARGET = 'id_' + '2' * 32
SQL = (f'\\restrict testguard\n-- keep {SOURCE} in this comment\n'
       f'CREATE SCHEMA {SOURCE};\nCREATE TABLE {SOURCE}.notes(message text);\n'
       f"INSERT INTO {SOURCE}.notes VALUES ('literal ''quoted'': {SOURCE}.table\n"
       f"\\unrestrict from data\nSELECT pg_catalog.setval(''{SOURCE}.audit_sequence_seq'', 5, true);');\n"
       f"INSERT INTO {SOURCE}.notes VALUES (E'escape \\' text {SOURCE}');\n"
       f"SELECT pg_catalog.setval('{SOURCE}.audit_sequence_seq', 3, true);\n\\unrestrict testguard\n")


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.archive, self.destination = self.base / 'archive', self.base / 'restored'
        self.locked = False
        self.events = []
        self.head = {'version': VERSION, 'schema': SOURCE, 'instance': 'a' * 32, 'nonce': 'b' * 32}
        self.inventory = sha(b'restricted row fingerprint')
        self.sql = SQL.encode()
        self.data = b'synthetic private bytes'
        self.refs = [descriptor(self.data)]
        self.witness_rows = []
        self.busy = False
        self.present = False
        self.source = SimpleNamespace(schema=SOURCE, identity=SimpleNamespace(tx=self.lock), conn=Mock(),
                                      blobs=BlobStore.create(self.base / 'live', owner=self.head['instance']),
                                      _check_witness=self.check_head, _save_witness=self.retire)
        self.source.blobs.put(self.data)
        self.source.conn.execute.side_effect = self.query
        self.inject('BASE', self.base)
        self.inject('_inventory', Mock(return_value=self.inventory))
        self.inject('_cli', self.cli)
        self.inject('_advance_target', self.advance)

    def inject(self, key, value):
        handle = patch.object(cp, key, value)
        handle.start()
        self.addCleanup(handle.stop)

    @contextmanager
    def lock(self):
        self.assertFalse(self.locked)
        self.locked = True
        try:
            yield
        finally:
            self.locked = False

    def check_head(self):
        self.assertTrue(self.locked)
        if 'nonce' not in self.head:
            raise Error('E_UNRESOLVED')
        return dict(self.head)

    def query(self, sql, args=()):
        self.assertTrue(self.locked)
        if ' AS ref FROM ' in sql:
            return [{'ref': r} for r in self.refs] if sql.endswith('.rt_executions') else []
        if 'jsonb_typeof(effect_witness)' in sql:
            return self.witness_rows
        if 'pg_export_snapshot' in sql:
            result = {'id': 'snapshot'}
        elif 'pg_namespace' in sql:
            result = {'present': self.present}
        elif 'rt_runs' in sql:
            result = {'busy': self.busy}
        else:
            self.fail('unexpected database operation')
        return SimpleNamespace(fetchone=lambda: result)

    def cli(self, program, options, *, sql_input=None, output=None):
        self.assertTrue(self.locked)
        self.events.append(program)
        if program == 'pg_dump':
            self.assertIn('--schema=' + SOURCE, options)
            self.assertIn('--snapshot=snapshot', options)
            output.write(self.sql)
        else:
            self.assertEqual(program, 'psql')
            self.assertIn('--single-transaction', options)
            self.assertIn(('CREATE SCHEMA ' + TARGET).encode(), sql_input)
            self.present = True

    def advance(self, schema, old, new):
        self.assertTrue(self.locked)
        self.assertEqual((schema, old, new['schema']), (TARGET, self.head, TARGET))
        self.assertNotEqual(old['nonce'], new['nonce'])
        self.assertFalse((self.destination / 'authority.json').exists())
        self.events.append('new-db-head')

    def retire(self, receipt):
        self.assertTrue(self.locked)
        self.assertFalse((self.destination / 'authority.json').exists())
        self.assertEqual(receipt['state'], 'retired')
        self.assertEqual(self.events[-1], 'new-db-head')
        self.events.append('retired')
        self.head = dict(receipt)

    def restore(self, receipt, **kwargs):
        return cp.restore(self.source, self.archive, checkpoint=receipt, target_schema=TARGET,
                          target_root=self.destination, **kwargs)

    def test_schema_remapping_preserves_multiline_data_and_sequence(self):
        new = cp._remap(self.sql, SOURCE, TARGET).decode()
        expected = self.sql.decode().replace('CREATE SCHEMA ' + SOURCE, 'CREATE SCHEMA ' + TARGET)
        for prefix in ('CREATE TABLE ', 'INSERT INTO '):
            expected = expected.replace(prefix + SOURCE + '.notes', prefix + TARGET + '.notes')
        expected = expected.replace("setval('" + SOURCE + '.', "setval('" + TARGET + '.')
        self.assertEqual(new, expected)
        for broken in (self.sql.replace(b'\\unrestrict testguard', b'\\unrestrict other'),
                       self.sql.replace(b".audit_sequence_seq', 3", b".other', 3"),
                       self.sql + b'\\unexpected\n', self.sql + b'/* unsupported SQL extension */'):
            with self.subTest(), self.assertRaises(Error):
                cp._remap(broken, SOURCE, TARGET)

    def test_maintenance_restore_has_private_bytes_basis_and_no_live_authority(self):
        receipt = cp.backup(self.source, self.archive)
        self.assertEqual(set(receipt), {'manifestSha256', 'authoritySha256', 'blobCount', 'sourceSchema'})
        result = self.restore(receipt)
        self.assertEqual(result['state'], 'verified_maintenance')
        self.assertEqual(self.events, ['pg_dump', 'psql'])
        self.assertFalse((self.destination / 'authority.json').exists())
        basis = strict_json((self.destination / 'restore-basis.json').read_bytes())
        self.assertEqual((basis['manifestSha256'], basis['sourceAuthoritySha256']),
                         (receipt['manifestSha256'], receipt['authoritySha256']))
        restored_blobs = BlobStore(self.destination / 'blobs', owner=self.head['instance'])
        self.assertEqual(restored_blobs.get(self.refs[0]), self.data)
        with self.assertRaises(Error):
            cp.backup(self.source, self.archive)

    def test_stale_live_authority_and_missing_independent_receipt_reject_before_writes(self):
        receipt = cp.backup(self.source, self.archive)
        for invalid in (None, {}, {**receipt, 'blobCount': True}, {**receipt, 'manifestSha256': '0' * 64}):
            with self.subTest(), self.assertRaises(Error):
                self.restore(invalid)
        self.head['nonce'] = 'c' * 32
        with self.assertRaisesRegex(Error, '^E_UNRESOLVED$'):
            self.restore(receipt)
        self.head = {}
        with self.assertRaisesRegex(Error, '^E_UNRESOLVED$'):
            self.restore(receipt)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.events, ['pg_dump'])

    def test_rehashed_archive_substitution_corrupt_sql_and_missing_blob_reject_before_writes(self):
        receipt = cp.backup(self.source, self.archive)
        manifest_path = self.archive / 'manifest.json'
        original = manifest_path.read_bytes()
        altered = strict_json(original)
        altered['sql'] = descriptor(b'some substitute')
        manifest_path.write_bytes(canonical(altered))
        with self.assertRaises(Error):
            self.restore(receipt)
        manifest_path.write_bytes(original)
        sql = self.archive / 'snapshot.sql'
        sql.write_bytes(b'x' * len(self.sql))
        with self.assertRaises(Error):
            self.restore(receipt)
        sql.write_bytes(self.sql)
        member = self.archive / 'objects' / self.refs[0]['sha256']
        member.write_bytes(b'z' * len(self.data))
        with self.assertRaises(Error):
            self.restore(receipt)
        member.unlink()
        with self.assertRaises(Error):
            self.restore(receipt)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.events, ['pg_dump'])

    def test_private_executor_raw_and_job_bytes_are_required_for_backup_and_restore(self):
        evidence = [b'original executor observation', b'canonical offered job']
        raw, job = [self.source.blobs.put(data) for data in evidence]
        self.witness_rows = [{'witness_kind': 'object', 'observation_kind': 'object', 'raw_ref': raw, 'job_ref': job}]
        receipt = cp.backup(self.source, self.archive)
        self.assertEqual(receipt['blobCount'], 3)
        for index, (ref, data) in enumerate(zip((raw, job), evidence)):
            archived = self.archive / 'objects' / ref['sha256']
            self.assertEqual(archived.read_bytes(), data)
            live = self.base / 'live' / ref['sha256']
            for failure in ('missing', 'corrupt'):
                with self.subTest(blob=index, failure=failure):
                    if failure == 'missing':
                        live.unlink()
                        archived.unlink()
                    else:
                        live.write_bytes(b'x' * len(data))
                        archived.write_bytes(b'x' * len(data))
                    incomplete = self.base / f'bad-{index}-{failure}'
                    with self.assertRaises(Error):
                        cp.backup(self.source, incomplete)
                    self.assertFalse((incomplete / 'manifest.json').exists())
                    with self.assertRaises(Error):
                        self.restore(receipt, activate=True)
                    self.assertFalse(self.destination.exists())
                    live.write_bytes(data)
                    archived.write_bytes(data)
        self.assertEqual(self.restore(receipt)['state'], 'verified_maintenance')
        restored = BlobStore(self.destination / 'blobs', owner=self.head['instance'])
        self.assertEqual([restored.get(ref) for ref in (raw, job)], evidence)

    def test_existing_schema_existing_directory_unsafe_paths_and_busy_cutover_preserved(self):
        receipt = cp.backup(self.source, self.archive)
        for path in (self.base, Path('relative'), self.base / '..' / 'escaped', self.base.parent / 'sibling'):
            with self.subTest(path=path), self.assertRaises(Error):
                cp._path(path)
        for name in ('public', SOURCE.upper(), SOURCE + '.other', SOURCE + ';', SOURCE[:-1]):
            with self.subTest(schema=name), self.assertRaises(Error):
                cp._schema(name)
        self.present = True
        with self.assertRaisesRegex(Error, '^E_CONFLICT$'):
            self.restore(receipt)
        self.present, self.busy = False, True
        with self.assertRaisesRegex(Error, '^E_UNRESOLVED$'):
            self.restore(receipt, activate=True)
        self.busy = False
        self.destination.mkdir()
        (self.destination / 'foreign').write_bytes(b'preserve')
        with self.assertRaises(Error):
            self.restore(receipt)
        self.assertEqual([p.name for p in self.destination.iterdir()], ['foreign'])
        self.assertEqual(self.events, ['pg_dump'])

    def test_cutover_advances_target_and_retires_source_before_writing_new_witness(self):
        receipt = cp.backup(self.source, self.archive)
        result = self.restore(receipt, activate=True)
        self.assertEqual(self.events, ['pg_dump', 'psql', 'new-db-head', 'retired'])
        actual = strict_json((self.destination / 'authority.json').read_bytes())
        self.assertEqual(actual['schema'], TARGET)
        self.assertEqual(result['state'], 'active_restore')
        self.assertEqual(result['targetAuthoritySha256'], digest(actual))
        self.assertEqual(result['retiredAuthoritySha256'], digest(self.head))
        with self.assertRaisesRegex(Error, '^E_UNRESOLVED$'):
            self.restore(receipt, activate=True)

    def test_failure_between_retirement_and_activation_leaves_both_unavailable(self):
        receipt = cp.backup(self.source, self.archive)
        save = cp._save
        def fail_target(directory, name, raw):
            if name == 'authority.json':
                self.assertEqual(self.head['state'], 'retired')
                raise OSError('private storage failure')
            return save(directory, name, raw)
        with patch.object(cp, '_save', fail_target), self.assertRaisesRegex(Error, '^E_UNRESOLVED$'):
            self.restore(receipt, activate=True)
        self.assertTrue((self.destination / 'restore-basis.json').exists())
        self.assertFalse((self.destination / 'authority.json').exists())
        with self.assertRaisesRegex(Error, '^E_UNRESOLVED$'):
            self.restore(receipt)

    def test_final_witness_recheck_and_inventory_failure_leave_copy_inactive(self):
        receipt = cp.backup(self.source, self.archive)
        initial = dict(self.head)
        change = {**initial, 'nonce': 'c' * 32}
        with patch.object(self.source, '_check_witness', side_effect=[initial, initial, change]):
            with self.assertRaisesRegex(Error, '^E_UNRESOLVED$'):
                self.restore(receipt, activate=True)
        self.assertEqual(self.head, initial)
        self.assertFalse((self.destination / 'authority.json').exists())
        self.present = False
        self.destination = self.base / 'target2'
        with patch.object(cp, '_inventory', return_value='0' * 64), self.assertRaisesRegex(Error, '^E_INTEGRITY$'):
            self.restore(receipt, activate=True)
        self.assertFalse((self.destination / 'authority.json').exists())
        self.assertNotIn('new-db-head', self.events)


class InventoryTests(unittest.TestCase):
    def test_blob_inventory_covers_each_reference_and_rejects_disagreeing_lengths(self):
        conn = Mock()
        expected = [descriptor(b'registered source'), descriptor(b'private report')]
        conn.execute.side_effect = lambda query: [] if 'jsonb_typeof' in query else [{'ref': ref} for ref in expected]
        self.assertEqual(cp._refs(conn, SOURCE), sorted(expected, key=lambda ref: ref['sha256']))
        statements = {c.args[0] for c in conn.execute.call_args_list}
        expected_columns = [('rt_sources', 'ref'), ('rt_snapshots', 'bundle_ref'), ('rt_executions', 'record_ref'),
                            ('rt_assessments', 'bundle_ref'), ('rt_assessments', 'assessment_ref'),
                            ('rt_reports', 'private_ref'), ('rt_reports', 'view_ref')]
        for table, column in expected_columns:
            self.assertIn(f'SELECT DISTINCT {column} AS ref FROM {SOURCE}.{table}', statements)
        changed = {**expected[0], 'byteLength': 1}
        conn.execute.side_effect = [[{'ref': expected[0]}], [{'ref': changed}]]
        with self.assertRaisesRegex(Error, '^E_INTEGRITY$'):
            cp._refs(conn, SOURCE)

    def test_optional_observation_requires_a_complete_well_formed_pair(self):
        first, second = descriptor(b'raw'), descriptor(b'job')
        def collect(witness_kind, observation_kind, raw_ref=None, job_ref=None):
            row = dict(witness_kind=witness_kind, observation_kind=observation_kind, raw_ref=raw_ref, job_ref=job_ref)
            def query(statement):
                if 'jsonb_typeof(effect_witness)' in statement:
                    self.assertIn("effect_witness->'observation'->'rawRef' AS raw_ref", statement)
                    self.assertIn("effect_witness->'observation'->'jobRef' AS job_ref", statement)
                    return [row]
                return []
            return cp._refs(SimpleNamespace(execute=query), SOURCE)
        self.assertEqual(collect('object', None), [])
        self.assertEqual(collect('object', 'null'), [])
        self.assertEqual(collect('object', 'object', first, first), [first])
        for args in [('array', None), ('object', 'array'), ('object', 'object', first, None),
                     ('object', 'object', None, second), ('object', 'object', None, None),
                     ('object', 'object', {**first, 'path': 'foreign'}, second),
                     ('object', 'object', first, {**second, 'byteLength': False}),
                     ('object', 'object', first, {**first, 'byteLength': 8})]:
            with self.subTest(args=args), self.assertRaisesRegex(Error, '^E_INTEGRITY$'):
                collect(*args)

    def test_inventory_rejects_unknown_tables_and_binds_sequence_and_private_rows(self):
        tables = [{'relname': name} for name in cp.TABLES]
        state = {'line': 'one row', 'is_called': False}
        def query(statement, args=()):
            if 'pg_catalog.pg_class' in statement:
                return tables
            if 'audit_sequence_seq' in statement:
                return SimpleNamespace(fetchone=lambda: {'last_value': 1, 'is_called': state['is_called']})
            return [{'line': state['line']}]
        conn = SimpleNamespace(execute=query)
        first = cp._inventory(conn, SOURCE)
        self.assertEqual(first, cp._inventory(conn, TARGET))
        state['line'] = 'changed private row'
        self.assertNotEqual(first, cp._inventory(conn, SOURCE))
        state.update(line='one row', is_called=True)
        self.assertNotEqual(first, cp._inventory(conn, SOURCE))
        tables.append({'relname': 'unexpected'})
        with self.assertRaisesRegex(Error, '^E_VERSION$'):
            cp._inventory(conn, SOURCE)


if __name__ == '__main__':
    unittest.main()
