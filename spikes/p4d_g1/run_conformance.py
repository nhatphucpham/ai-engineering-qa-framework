"""Fresh, bounded PostgreSQL campaign; no old execution/model campaign replay."""
from pathlib import Path
import base64
import io
import json
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'spikes/s2')]
from local import command, inventory, read_config, start
from runtime_candidate.common import Error, canonical, require, sha
from runtime_candidate.database import stop_database
from .lifecycle import finish


def database_status():
    cfg = read_config(False)
    try:
        command('pg_ctl', '-D', cfg['data'], 'status')
    except subprocess.CalledProcessError as exc:
        require(exc.returncode == 3, 'E_UNRESOLVED')
        return 'STOPPED'
    read_config(True)  # Running PID/data/port must still match the retained marker.
    return 'RUNNING'


def source_pins():
    files = list((ROOT / 'spikes/p4d_g1').glob('*'))
    files += list((ROOT / 'runtime_candidate').glob('*.py')) + [ROOT / 'runtime_candidate/schema.sql']
    for directory in ('qa_core', 'spikes/s6b', 'spikes/s2'):
        files += list((ROOT / directory).glob('*.py')) + list((ROOT / directory).glob('*.sql'))
    files += [ROOT / 'docs/P4D-G1-PROTOCOL.md', ROOT / 'runtime_candidate/API.md']
    from spikes.vf1.core_bridge import ARTIFACT_KINDS
    files += [ROOT / 'examples/mock/06-filter-pagination' / rel for rel in ARTIFACT_KINDS]
    files += [ROOT / 'spikes/vf1/core_bridge.py', ROOT / 'spikes/vf1/run_vf1.py', ROOT / 'spikes/vf1/test_worker.py']
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(set(files)) if p.is_file()}


def main():
    require(len(sys.argv) == 2)
    name = sys.argv[1]
    require(name.startswith('g1-') and name.endswith('.json') and Path(name).name == name)
    destination = ROOT / 'docs/p4d-g1-results' / name
    require(not destination.exists())
    workspace = ROOT / '.cache/p4d_g1' / destination.stem
    workspace.mkdir(parents=True, exist_ok=False)
    evidence = {'version': 'p4d-g1-evidence-1.0.0', 'status': 'RUNNING', 'classification': 'synthetic_only',
                'command': ['py', '-3', '-B', '-m', 'spikes.p4d_g1.run_conformance', name],
                'budget': {'maxObservationsPerPage': 64, 'pageBytes': 65536, 'childTimeoutSeconds': 25,
                           'wholeCampaignDeadlineSeconds': 180, 'automaticRetries': 0, 'qaModelInvocations': 0},
                'checks': {}, 'inputsBefore': source_pins()}
    begin = time.monotonic(); attempted = False; cases = None; forbidden = []
    try:
        evidence['preflight'] = inventory()
        require(evidence['preflight']['toolchainReady'], 'E_DEPENDENCY')
        cfg = read_config(False)
        evidence['cluster'] = {'kind': cfg['kind'], 'database': cfg['database'], 'markerSha256': sha(cfg['marker'].encode())}
        try:
            command('pg_ctl', '-D', cfg['data'], 'status')
        except subprocess.CalledProcessError as exc:
            require(exc.returncode == 3, 'E_DEPENDENCY')
            evidence['databaseBefore'] = 'STOPPED'
        else:
            raise Error('E_UNRESOLVED')
        from .test_ingress import GrammarTests
        from .test_lifecycle import CleanupTests
        out = io.StringIO()
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (GrammarTests, CleanupTests))
        result = unittest.TextTestRunner(stream=out, verbosity=2).run(suite)
        evidence['unit'] = {'tests': result.testsRun, 'errors': len(result.errors), 'failures': len(result.failures),
                            'skipped': len(result.skipped), 'output': out.getvalue()}
        require(result.wasSuccessful() and not result.skipped, 'E_INTEGRITY')
        attempted = True
        start()
        from .cases import Cases
        cases = Cases(workspace, evidence['checks'], forbidden)
        evidence['scope'] = cases.run()
        require(time.monotonic() - begin < 180, 'E_BUDGET')
        evidence['status'] = 'PASS'
    except Exception as exc:
        evidence['status'], evidence['errorType'] = 'ERROR', type(exc).__name__
        import traceback
        diagnostic = traceback.format_exc().encode('utf-8')
        require(not any(secret in diagnostic for secret in forbidden), 'E_INTEGRITY')
        (workspace / 'error.txt').write_bytes(diagnostic)
    finally:
        finish(evidence, attempted=attempted, close=lambda: cases.app.close() if cases is not None else None,
               pins=source_pins, observe=database_status, stop=stop_database)
    evidence['elapsedSeconds'] = time.monotonic() - begin
    encoded = canonical(evidence)
    require(not any(secret in encoded or secret.hex().encode() in encoded or base64.b64encode(secret) in encoded for secret in forbidden), 'E_INTEGRITY')
    with destination.open('xb') as stream:
        stream.write(encoded)
    print(json.dumps({'status': evidence['status'], 'checks': {key: row['status'] for key, row in evidence['checks'].items()},
                      'unit': evidence.get('unit', {}).get('tests'), 'seconds': evidence['elapsedSeconds'],
                      'databaseStopped': evidence.get('databaseStopped')}))
    return 0 if evidence['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
