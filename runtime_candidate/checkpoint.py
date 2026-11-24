"""Operator-only synthetic checkpoints. No HTTP operation accepts these inputs."""
import hashlib
import os
import re
import subprocess
import uuid
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from .blobs import BlobStore, MAX_BLOB_BYTES, _directory, _write
from .common import VERSION, Error, canonical, digest, require, sha, strict_json


BASE = Path(__file__).resolve().parents[1] / '.cache/s6/m50'
FORMAT = 'm50-operator-backup-v1'
MAX_SQL = 32 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_OBJECTS = 4096
SCHEMA = re.compile(r'id_[a-f0-9]{32}')
HASH = re.compile(r'[a-f0-9]{64}')
TABLES = tuple('model_identity control accounts login_buckets families access_tokens refresh_tokens '
               'projects members grants qa_runs audit rt_control rt_projects rt_configs rt_sources '
               'rt_snapshots rt_grants rt_services rt_credentials rt_intakes rt_runs rt_executions '
               'rt_assessments rt_reports rt_events rt_receipts'.split())
REF_COLUMNS = (('rt_sources', 'ref'), ('rt_snapshots', 'bundle_ref'), ('rt_executions', 'record_ref'),
               ('rt_assessments', 'bundle_ref'), ('rt_assessments', 'assessment_ref'),
               ('rt_reports', 'private_ref'), ('rt_reports', 'view_ref'))


def _checked(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Error:
            raise
        except Exception:
            # Neither dump fragments, DB errors, directory names nor credentials are public diagnostics.
            raise Error('E_UNRESOLVED') from None
    return wrapper


def _schema(name):
    require(isinstance(name, str) and SCHEMA.fullmatch(name), 'E_INPUT')
    return name


def _path(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts and path != BASE and path.is_relative_to(BASE), 'E_INPUT')
    return path


@contextmanager
def _fresh(path):
    # Bootstrap owns BASE and all output parents. Never adopt an existing destination.
    with _directory(path.parent) as parent:
        parent.mkdir(path.name)
        parent.sync()
        with _directory(path) as current:
            yield current


def _read(directory, name, limit):
    with directory.file(name) as stream:
        require(os.fstat(stream.fileno()).st_size <= limit, 'E_INTEGRITY')
        data = stream.read(limit + 1)
        require(len(data) <= limit, 'E_INTEGRITY')
        return data


def _save(directory, name, data):
    with directory.file(name, create=True) as stream:
        _write(stream, data)
    directory.sync()


def _stored_refs(conn, schema):
    for table, column in REF_COLUMNS:
        query = f'SELECT DISTINCT {column} AS ref FROM {schema}.{table}'
        for row in conn.execute(query):
            yield row['ref']
    query = f"""SELECT jsonb_typeof(effect_witness) AS witness_kind,
        jsonb_typeof(effect_witness->'observation') AS observation_kind,
        effect_witness->'observation'->'rawRef' AS raw_ref,
        effect_witness->'observation'->'jobRef' AS job_ref
        FROM {schema}.rt_runs WHERE effect_witness IS NOT NULL"""
    for row in conn.execute(query):
        require(row['witness_kind'] in ('object', 'null'), 'E_INTEGRITY')
        if row['observation_kind'] in (None, 'null'):
            continue
        require(row['observation_kind'] == 'object', 'E_INTEGRITY')
        yield row['raw_ref']
        yield row['job_ref']


def _refs(conn, schema):
    rows = {}
    for ref in _stored_refs(conn, schema):
        _ref_shape(ref, MAX_BLOB_BYTES)
        key = ref['sha256']
        require(key not in rows or rows[key] == ref, 'E_INTEGRITY')
        rows[key] = ref
        require(len(rows) <= MAX_OBJECTS, 'E_BUDGET')
    result = [rows[key] for key in sorted(rows)]
    require(sum(ref['byteLength'] for ref in result) <= MAX_TOTAL, 'E_BUDGET')
    return result


def _inventory(conn, schema):
    present = {row['relname'] for row in conn.execute('''SELECT c.relname FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON c.relnamespace=n.oid WHERE n.nspname=%s AND c.relkind='r' ''', (schema,))}
    require(present == set(TABLES), 'E_VERSION')
    # Stable row values include every column, including private authority state; expose only a digest.
    hashes = {}
    for name in TABLES:
        accumulator = hashlib.sha256()
        query = f"SELECT to_jsonb(t)::text AS line FROM {schema}.{name} t ORDER BY to_jsonb(t)::text COLLATE \"C\""
        for row in conn.execute(query):
            raw = row['line'].encode('utf-8')
            accumulator.update(len(raw).to_bytes(8, 'big'))
            accumulator.update(raw)
        hashes[name] = accumulator.hexdigest()
    sequence = conn.execute(f'SELECT last_value,is_called FROM {schema}.audit_sequence_seq').fetchone()
    return digest({'tables': hashes, 'auditSequence': sequence})


def _cli(program, options, *, sql_input=None, output=None):
    # Import only on actual operator invocation. The validated Store opened this marker-bound local cluster.
    from local import BIN, read_config
    cfg = read_config()
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith('PG')}
    env.update(PGPASSFILE=os.devnull, PGCLIENTENCODING='UTF8', PGCONNECT_TIMEOUT='5', PGSSLMODE='disable',
               PGGSSENCMODE='disable')
    args = [str(BIN / (program + '.exe')), '-h', '127.0.0.1', '-p', str(cfg['port']), '-U', cfg['user'],
            '-d', cfg['database'], '-w', *options]
    subprocess.run(args, env=env, stdin=subprocess.DEVNULL if sql_input is None else None, input=sql_input,
                   stdout=output if output is not None else subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=60, check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def _ref_shape(ref, limit):
    require(type(ref) is dict and set(ref) == {'sha256', 'byteLength'} and type(ref['sha256']) is str and
            HASH.fullmatch(ref['sha256']) and type(ref['byteLength']) is int and
            0 <= ref['byteLength'] <= limit, 'E_INTEGRITY')


def _verify_bytes(data, ref):
    require(len(data) == ref['byteLength'] and sha(data) == ref['sha256'], 'E_INTEGRITY')
    return data


def _receipt(manifest_raw, head, count):
    return {'manifestSha256': sha(manifest_raw), 'authoritySha256': digest(head),
            'sourceSchema': head['schema'], 'blobCount': count}


@_checked
def backup(source, archive: Path) -> dict:
    """Return the trusted operator receipt separately from the restricted exclusive archive."""
    schema, path = _schema(source.schema), _path(archive)
    with source.identity.tx():
        head = source._check_witness()
        refs = _refs(source.conn, schema)
        inventory = _inventory(source.conn, schema)
        snapshot = source.conn.execute('SELECT pg_export_snapshot() AS id').fetchone()['id']
        with _fresh(path) as directory:
            with directory.file('snapshot.sql', create=True) as stream:
                _cli('pg_dump', ['--format=plain', '--inserts', '--no-owner', '--no-privileges',
                                 '--strict-names', '--schema=' + schema, '--snapshot=' + snapshot], output=stream)
                stream.flush()
                os.fsync(stream.fileno())
            sql_bytes = _read(directory, 'snapshot.sql', MAX_SQL)
            directory.mkdir('objects')
            with _directory(path / 'objects') as objects:
                for ref in refs:
                    _save(objects, ref['sha256'], source.blobs.get(ref))
            manifest = {'format': FORMAT, 'version': VERSION, 'source': schema,
                        'authoritySha256': digest(head), 'inventorySha256': inventory,
                        'sql': {'sha256': sha(sql_bytes), 'byteLength': len(sql_bytes)}, 'objects': refs}
            require(source._check_witness() == head, 'E_UNRESOLVED')
            raw = canonical(manifest)
            _save(directory, 'manifest.json', raw)
            return _receipt(raw, head, len(refs))


def _validated_manifest(raw, checkpoint, head):
    require(type(checkpoint) is dict and set(checkpoint) == {'manifestSha256', 'authoritySha256',
            'sourceSchema', 'blobCount'} and type(checkpoint['blobCount']) is int and
            0 <= checkpoint['blobCount'] <= MAX_OBJECTS, 'E_UNRESOLVED')
    require(checkpoint == _receipt(raw, head, checkpoint['blobCount']), 'E_UNRESOLVED')
    value = strict_json(raw)
    require(type(value) is dict and set(value) == {'format', 'version', 'source', 'authoritySha256',
            'inventorySha256', 'sql', 'objects'} and canonical(value) == raw and
            (value['format'], value['version'], value['source'], value['authoritySha256']) ==
            (FORMAT, VERSION, head['schema'], digest(head)) and isinstance(value['inventorySha256'], str)
            and HASH.fullmatch(value['inventorySha256']), 'E_INTEGRITY')
    _ref_shape(value['sql'], MAX_SQL)
    refs = value['objects']
    require(type(refs) is list and len(refs) == checkpoint['blobCount'], 'E_INTEGRITY')
    for ref in refs:
        _ref_shape(ref, MAX_BLOB_BYTES)
    keys = [ref['sha256'] for ref in refs]
    require(keys == sorted(set(keys)) and sum(ref['byteLength'] for ref in refs) <= MAX_TOTAL, 'E_INTEGRITY')
    return value


# pg_dump uses ordinary identifiers for this fixed lower-case schema, standard strings,
# and occasionally E-strings. Match entire quoted values/comments before inspecting names.
# Unsupported procedural SQL, dollar quoting and other psql commands fail closed.
_TOKENS = re.compile(
    r"(?P<comment>--[^\r\n]*)|(?P<unsupported>/\*|\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$)"
    r"|(?P<escape>[Ee]'(?:[^'\\]|\\.|'')*')|(?P<string>'(?:[^']|'')*')"
    r'|(?P<quoted>"(?:[^"]|"")*")|(?P<meta>\\[^\r\n]*)'
    r'|(?P<word>[A-Za-z_][A-Za-z_0-9$]*)|(?P<gap>\s+)|(?P<other>.)', re.DOTALL)


def _remap(data, source, target):
    _schema(source)
    _schema(target)
    require(source != target and len(data) <= MAX_SQL, 'E_INPUT')
    text = data.decode('utf-8')
    result = []
    history = []
    guards = []
    created = 0
    sequences = 0
    for token in _TOKENS.finditer(text):
        kind, s = token.lastgroup, token[0]
        if kind == 'meta':
            guard = re.fullmatch(r'\\(restrict|unrestrict) ([A-Za-z0-9]+)', s)
            require(guard and (token.start() == 0 or text[token.start()-1] == '\n'), 'E_INTEGRITY')
            guards.append(guard.groups())
        elif kind == 'unsupported' or (kind == 'other' and s in "'\""):
            raise Error('E_INTEGRITY')
        elif kind in ('word', 'quoted') and s in (source, '"' + source + '"'):
            if history[-2:] == ['CREATE', 'SCHEMA']:
                created += 1
            s = target if kind == 'word' else '"' + target + '"'
        elif kind == 'string' and history == ['SELECT', 'pg_catalog', '.', 'setval', '(']:
            require(s == "'" + source + ".audit_sequence_seq'", 'E_INTEGRITY')
            s = "'" + target + ".audit_sequence_seq'"
            sequences += 1
        result.append(s)
        if kind not in ('comment', 'gap', 'meta'):
            history = (history + [s])[-5:]
    require(created == 1 and sequences == 1 and len(guards) == 2 and guards[0][0] == 'restrict'
            and guards[1] == ('unrestrict', guards[0][1]), 'E_INTEGRITY')
    return ''.join(result).encode('utf-8')


def _present(conn, schema):
    return conn.execute('SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname=%s) AS present',
                        (schema,)).fetchone()['present']


def _can_cutover(source):
    busy = source.conn.execute("""SELECT EXISTS(SELECT 1 FROM rt_runs WHERE incident OR state NOT IN
        ('queued','completed','cancelled','failed')) AS busy""").fetchone()['busy']
    require(not busy, 'E_UNRESOLVED')


def _advance_target(target, head, new_head):
    from local import connect
    with connect() as conn:
        row = conn.execute(f'UPDATE {target}.rt_control SET nonce=%s WHERE id=1 AND instance=%s '
                           'AND nonce=%s RETURNING id', (new_head['nonce'], head['instance'],
                                                          head['nonce'])).fetchone()
        require(row == (1,), 'E_UNRESOLVED')


@_checked
def restore(source, archive: Path, *, checkpoint: dict, target_schema: str, target_root: Path,
            activate: bool = False) -> dict:
    """Verify an archive against an independent receipt and latest live authority before restoring."""
    original, target = _schema(source.schema), _schema(target_schema)
    path, destination = _path(archive), _path(target_root)
    require(original != target and type(activate) is bool and
            not destination.is_relative_to(path) and not path.is_relative_to(destination), 'E_INPUT')
    # One source mutex covers ALL checks, creation, final verification and optional exclusive cutover.
    with source.identity.tx(), _directory(path) as directory, _directory(path / 'objects') as objects:
        head = source._check_witness()
        raw = _read(directory, 'manifest.json', 1024 * 1024)
        manifest = _validated_manifest(raw, checkpoint, head)
        sql_data = _verify_bytes(_read(directory, 'snapshot.sql', MAX_SQL), manifest['sql'])
        script = _remap(sql_data, original, target)
        for ref in manifest['objects']:
            _verify_bytes(_read(objects, ref['sha256'], ref['byteLength']), ref)
        require(not _present(source.conn, target), 'E_CONFLICT')
        if activate:
            _can_cutover(source)
        require(source._check_witness() == head, 'E_UNRESOLVED')
        with _fresh(destination) as restored:
            new_blobs = BlobStore.create(destination / 'blobs', owner=head['instance'])
            for ref in manifest['objects']:
                data = _verify_bytes(_read(objects, ref['sha256'], ref['byteLength']), ref)
                require(new_blobs.put(data) == ref, 'E_INTEGRITY')
            # -X ignores operator psqlrc; single transaction, no DROP, CREATE SCHEMA is exclusive.
            # Independent connection cannot change source transaction search_path or its held mutex.
            _cli('psql', ['-X', '--single-transaction', '-v', 'ON_ERROR_STOP=1', '-f', '-'], sql_input=script)
            require(_inventory(source.conn, target) == manifest['inventorySha256']
                    and _refs(source.conn, target) == manifest['objects'], 'E_INTEGRITY')
            for ref in manifest['objects']:
                new_blobs.get(ref)
            basis = {'format': FORMAT, 'sourceSchema': original, 'schema': target, 'instance': head['instance'],
                     'sourceAuthoritySha256': digest(head), 'manifestSha256': sha(raw),
                     'inventorySha256': manifest['inventorySha256']}
            _save(restored, 'restore-basis.json', canonical(basis))
            result = {'schema': target, 'root': str(destination), 'blobCount': len(manifest['objects']),
                      'manifestSha256': sha(raw), 'state': 'verified_maintenance'}
            require(source._check_witness() == head, 'E_UNRESOLVED')
            if activate:
                _can_cutover(source)
                receipt = {**basis, 'state': 'retired'}
                new_head = dict(head, schema=target, nonce=uuid.uuid4().hex)
                # Commit target DB head on an independent transaction before either witness changes.
                # Global source mutex still excludes any source operations throughout.
                _advance_target(target, head, new_head)
                require(source._check_witness() == head, 'E_UNRESOLVED')
                source._save_witness(receipt)
                # A crash now leaves no active witness. No automatic rewrite or fallback.
                _save(restored, 'authority.json', canonical(new_head))
                result.update(state='active_restore', retiredAuthoritySha256=digest(receipt),
                              targetAuthoritySha256=digest(new_head))
            return result
