"""Validate this authored synthetic scenario, not reviewer performance."""

import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent
WORKER = """
import json
from pathlib import Path
import sys
import unittest
root = Path.cwd()
sys.path[:0] = [str(root / sys.argv[1]), str(root / 'tests'), str(root / 'expected')]
suite = unittest.defaultTestLoader.loadTestsFromName(sys.argv[2])
result = unittest.TestResult()
suite.run(result)
print(json.dumps({
    'tests': result.testsRun,
    'failures': [{'id': test.id(), 'trace': trace} for test, trace in result.failures],
    'errors': [{'id': test.id(), 'trace': trace} for test, trace in result.errors],
    'skipped': len(result.skipped),
}))
"""


def main():
    mismatches = []
    names = sorted(path.name for path in (ROOT / 'base').glob('*.py'))
    if names != sorted(path.name for path in (ROOT / 'head').glob('*.py')):
        mismatches.append('base/head file inventory differs')
    diff = ''.join(''.join(difflib.unified_diff(
        (ROOT / 'base' / name).read_text().splitlines(True),
        (ROOT / 'head' / name).read_text().splitlines(True),
        fromfile='base/' + name, tofile='head/' + name,
    )) for name in names)
    if diff != (ROOT / 'change.diff').read_text():
        mismatches.append('change.diff does not match snapshots')

    runs = []
    expected_failures = {
        'test_historical': ['test_historical.Historical.test_reset_from_third_page'],
        'test_probe': [
            'test_probe.Probe.test_cache_across_categories',
            'test_probe.Probe.test_reset_with_recorded_api_call',
        ],
    }
    for snapshot in ('base', 'head'):
        for module, count in [('test_baseline', 6), ('test_historical', 1), ('test_probe', 2)]:
            try:
                process = subprocess.run(
                    [sys.executable, '-B', '-c', WORKER, snapshot, module],
                    cwd=ROOT, capture_output=True, text=True, timeout=10, check=False,
                )
                if process.returncode:
                    raise RuntimeError(process.stderr)
                result = json.loads(process.stdout)
                expected = expected_failures.get(module, []) if snapshot == 'head' else []
                matched = (
                    result['tests'] == count
                    and sorted(item['id'] for item in result['failures']) == expected
                    and not result['errors'] and result['skipped'] == 0
                )
                runs.append({'snapshot': 'mock-06-' + snapshot + '-v1',
                             'module': module, 'matched': matched, **result})
                print(f"{snapshot}/{module}: tests={result['tests']}, "
                      f"failures={len(result['failures'])}, errors={len(result['errors'])}, "
                      f"skipped={result['skipped']} — {'MATCH' if matched else 'MISMATCH'}")
                if not matched:
                    mismatches.append(f'{snapshot}/{module}: unexpected outcome')
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                mismatches.append(f'{snapshot}/{module}: {error}')

    files = [path for path in ROOT.rglob('*') if path.is_file()
             and (path.suffix == '.py' or path.name in ('requirements.md', 'change.diff', 'evidence.mock.json'))]
    report = {
        'dataClassification': 'synthetic-only',
        'provenance': 'Actual local execution of authored synthetic code; not CI or blind evaluation.',
        'executedAtUTC': datetime.now(timezone.utc).isoformat(),
        'python': sys.version.split()[0],
        'sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in sorted(files)},
        'runs': runs, 'mismatches': mismatches,
    }
    (ROOT / 'execution.local.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Wrote execution.local.json (local synthetic execution, including expected failures).')
    for mismatch in mismatches:
        print(mismatch)
    print('Fixture match is not quality approval or an evaluation of an AI reviewer.')
    return 1 if mismatches else 0


if __name__ == '__main__':
    raise SystemExit(main())
