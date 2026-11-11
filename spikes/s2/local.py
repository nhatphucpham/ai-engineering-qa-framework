"""Local disposable cluster only. Never accepts a DSN or discovers credentials."""

import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.cache/s2'
BIN = CACHE / 'runtime/pgsql/bin'
CONFIG = CACHE / 'cluster.json'
ARCHIVE_SHA256 = 'e2246ba91d22345bc3d017586c09ede52d9df180b1eeb480f050445f1cad84e2'
DRIVER_PINS = {'psycopg': '3.3.8', 'psycopg-binary': '3.3.8', 'tzdata': '2026.6'}


def driver_inventory(deps=None):
    deps = (deps or CACHE / 'deps').resolve()
    versions = {dist.metadata['Name']: dist.version
                for dist in importlib.metadata.distributions(path=[str(deps)])}
    result = {'versions': {name: versions.get(name) for name in DRIVER_PINS}, 'ready': False}
    if result['versions'] != DRIVER_PINS:
        return result
    sys.path.insert(0, str(deps))
    try:
        modules = [importlib.import_module(name) for name in ('psycopg', 'psycopg_binary', 'tzdata')]
        result['localModulePaths'] = all(Path(module.__file__).resolve().is_relative_to(deps) for module in modules)
        result['loadedVersions'] = {name: module.__version__ for name, module in zip(DRIVER_PINS, modules)}
        result['binaryImplementation'] = modules[0].pq.__impl__
        result['ready'] = (result['localModulePaths'] and result['loadedVersions'] == DRIVER_PINS
                           and result['binaryImplementation'] == 'binary')
    except (ImportError, AttributeError, OSError):
        result['ready'] = False
    finally:
        sys.path.pop(0)
    return result


def clean_environment():
    # libpq and CLI must not inherit a real service/credential/config reference.
    for name in list(os.environ):
        if name.upper().startswith('PG'):
            del os.environ[name]


def command(name, *args):
    # Windows server children can inherit pipes and keep communicate() open after
    # pg_ctl exits. Files avoid that deadlock; never open a visible console.
    with tempfile.TemporaryFile() as output:
        subprocess.run([str(BIN / (name + '.exe')), *map(str, args)], check=True,
                       stdout=output, stderr=output, timeout=40, creationflags=subprocess.CREATE_NO_WINDOW)
        output.seek(0)
        return output.read().decode('utf-8', errors='replace').strip()


def inventory():
    """No DB connections, safe absence report; no environment values emitted."""
    checks = {'python': sys.version.split()[0], 'platform': sys.platform,
              'postgresBinary': (BIN / 'postgres.exe').is_file(),
              'driverLocal': (CACHE / 'deps/psycopg').is_dir(), 'clusterMarker': CONFIG.is_file()}
    checks['driver'] = driver_inventory()
    archive = CACHE / 'postgresql-18.6-windows-x64.zip'
    checks['archiveIntegrity'] = False
    if archive.is_file():
        with archive.open('rb') as stream:
            checks['archiveIntegrity'] = hashlib.file_digest(stream, 'sha256').hexdigest() == ARCHIVE_SHA256
    checks['extractedIntegrity'] = False
    if checks['archiveIntegrity']:
        with zipfile.ZipFile(archive) as package:
            entries = [item for item in package.infolist() if not item.is_dir()
                       and item.filename.startswith(('pgsql/bin/', 'pgsql/lib/', 'pgsql/share/'))]
            checks['extractedIntegrity'] = bool(entries) and all(
                (CACHE / 'runtime' / item.filename).is_file()
                and hashlib.sha256((CACHE / 'runtime' / item.filename).read_bytes()).digest()
                == hashlib.sha256(package.read(item)).digest() for item in entries)
    # Do not execute even --version until extracted files match the pinned archive.
    if checks['postgresBinary'] and checks['extractedIntegrity']:
        checks['postgresVersion'] = command('postgres', '--version')
    checks['toolchainReady'] = (checks['postgresBinary'] and checks['driver']['ready']
                                and checks['python'] == '3.14.8' and sys.platform == 'win32'
                                and checks['archiveIntegrity'] and checks['extractedIntegrity']
                                and checks.get('postgresVersion') == 'postgres (PostgreSQL) 18.6')
    return checks


def read_config(require_running=True):
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    expected_data = (CACHE / 'cluster').resolve()
    if (not CACHE.resolve().is_relative_to(ROOT) or expected_data.parent != CACHE.resolve()
            or config.get('kind') != 's2-disposable-v1' or config.get('data') != str(expected_data)
            or config.get('database') != 's2_synthetic' or config.get('user') != 's2synthetic'
            or type(config.get('port')) is not int or not 1024 <= config['port'] <= 65535):
        raise ValueError('Unrecognized disposable cluster marker')
    if require_running:
        command('pg_ctl', '-D', expected_data, 'status')
        lines = (expected_data / 'postmaster.pid').read_text().splitlines()
        if Path(lines[1]).resolve() != expected_data or int(lines[3]) != config['port']:
            raise ValueError('Cluster PID/port does not match marker')
    return config


def connect():
    import psycopg
    clean_environment()
    config = read_config()
    conn = psycopg.connect(host='127.0.0.1', port=config['port'], dbname=config['database'],
                           user=config['user'], password='', connect_timeout=5,
                           options='-c statement_timeout=15000 -c lock_timeout=10000 -c timezone=UTC',
                           application_name='s2-synthetic-spike', autocommit=True)
    # A fresh random marker binds connections to the cluster just created by setup.
    if conn.execute('SELECT marker FROM s2_identity').fetchone() != (config['marker'],):
        conn.close()
        raise ValueError('Disposable database identity mismatch')
    return conn


def setup():
    clean_environment()
    if CONFIG.exists() or (CACHE / 'cluster').exists():
        raise ValueError('Existing cluster: inspect/stop it; setup never overwrites')
    if not inventory()['toolchainReady']:
        raise ValueError('Toolchain NOT READY: use pinned local setup in README')
    data = (CACHE / 'cluster').resolve()
    command('initdb', '-D', data, '-U', 's2synthetic', '-A', 'trust', '--encoding=UTF8', '--locale=C')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    with (data / 'postgresql.conf').open('a', encoding='utf-8') as stream:
        stream.write(f"\nlisten_addresses='127.0.0.1'\nport={port}\nfsync=on\nsynchronous_commit=on\nfull_page_writes=on\n")
    config = {'kind': 's2-disposable-v1', 'data': str(data), 'port': port,
              'database': 's2_synthetic', 'user': 's2synthetic', 'marker': uuid.uuid4().hex}
    CONFIG.write_text(json.dumps(config, indent=2), encoding='utf-8')
    command('pg_ctl', '-D', data, '-l', CACHE / 'postgres.log', '-w', 'start')
    initialize_database()
    return {'status': 'READY', 'port': port, 'database': config['database']}


def initialize_database():
    """Resume only between local start and first database creation; no overwrite."""
    config = read_config()
    port = config['port']
    command('createdb', '-h', '127.0.0.1', '-p', port, '-U', config['user'], config['database'])
    import psycopg
    with psycopg.connect(host='127.0.0.1', port=port, dbname=config['database'],
                          user=config['user'], password='', connect_timeout=5, autocommit=True) as conn:
        conn.execute('CREATE TABLE s2_identity(marker text PRIMARY KEY)')
        conn.execute('INSERT INTO s2_identity VALUES (%s)', (config['marker'],))


def stop(mode='fast'):
    config = read_config()
    command('pg_ctl', '-D', config['data'], '-m', mode, '-w', 'stop')


def start():
    config = read_config(require_running=False)
    command('pg_ctl', '-D', config['data'], '-l', CACHE / 'postgres.log', '-w', 'start')


if __name__ == '__main__':
    sys.path.insert(0, str(CACHE / 'deps'))
    clean_environment()
    try:
        action = sys.argv[1] if len(sys.argv) == 2 else 'preflight'
        if action == 'preflight':
            result = inventory()
        elif action == 'setup':
            result = setup()
        elif action == 'stop':
            stop()
            result = {'status': 'STOPPED'}
        elif action == 'start':
            start()
            result = {'status': 'STARTED'}
        elif action == 'initialize-database':
            initialize_database()
            result = {'status': 'READY'}
        else:
            raise ValueError('Unknown local action')
        print(json.dumps(result, indent=2))
    except Exception:
        print(json.dumps({'status': 'NOT READY', 'error': 'Local preflight/setup failed; inspect local prerequisites'}))
        sys.exit(2)
