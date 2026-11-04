"""Run the known-defect control and repaired synthetic snapshot offline."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
ORIGINAL = REPO / 'examples/mock/06-filter-pagination'


def main():
    # Reuse the original worker and assertions without modifying the fixture.
    worker = runpy.run_path(str(ORIGINAL / 'run.py'))['WORKER']
    modules = [('test_baseline', 6), ('test_historical', 1), ('test_probe', 2)]
    expected_failures = {
        'test_historical': ['test_historical.Historical.test_reset_from_third_page'],
        'test_probe': ['test_probe.Probe.test_cache_across_categories',
                       'test_probe.Probe.test_reset_with_recorded_api_call'],
    }
    runs = []
    for snapshot, path in [('mock-06-head-v1', ORIGINAL / 'head'),
                           ('mock-06-fixed-v1', ROOT / 'fixed')]:
        for module, count in modules:
            try:
                process = subprocess.run(
                    [sys.executable, '-B', '-c', worker, str(path), module],
                    cwd=ORIGINAL, capture_output=True, text=True, timeout=10,
                    encoding='utf-8', check=False,
                )
                if process.returncode:
                    raise RuntimeError(process.stderr)
                result = json.loads(process.stdout)
                expected = expected_failures.get(module, []) if path == ORIGINAL / 'head' else []
                matched = (result['tests'] == count
                           and sorted(item['id'] for item in result['failures']) == expected
                           and not result['errors'] and result['skipped'] == 0)
                runs.append({'snapshot': snapshot, 'module': module,
                             'matched': matched, **result})
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                runs.append({'snapshot': snapshot, 'module': module,
                             'matched': False, 'executionError': str(error)})
            print(f"{snapshot}/{module}: {'MATCH' if runs[-1]['matched'] else 'MISMATCH'}")

    inputs = [*sorted((ROOT / 'fixed').glob('*.py')), ROOT / 'run.py',
              ORIGINAL / 'run.py', ORIGINAL / 'requirements.md',
              *sorted((ORIGINAL / 'head').glob('*.py')),
              *sorted((ORIGINAL / 'tests').glob('*.py')),
              ORIGINAL / 'expected/test_probe.py']
    report = {
        'dataClassification': 'synthetic-only',
        'provenance': 'Local execution of known authored fixtures; not CI, blind evaluation or approval.',
        'executedAtUTC': datetime.now(timezone.utc).isoformat(),
        'python': sys.version.split()[0],
        'requirement': 'mock-req-06-v1',
        'sha256': {path.relative_to(REPO).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in inputs},
        'runs': runs,
    }
    (ROOT / 'execution.local.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if all(run['matched'] for run in runs) else 1


if __name__ == '__main__':
    raise SystemExit(main())
