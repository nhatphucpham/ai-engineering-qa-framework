"""Verify v2 space handling against the preserved v1 control."""

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
    worker = worker.replace("str(root / 'tests')", repr(str(ROOT / 'tests')) + ", str(root / 'tests')")
    modules = [('test_baseline', 6), ('test_historical', 1), ('test_probe', 2), ('test_whitespace', 4)]
    expected_failures = {'test_whitespace': [
        'test_whitespace.Whitespace.test_api_mixed_categories',
        'test_whitespace.Whitespace.test_service_padded_category_and_pagination',
        'test_whitespace.Whitespace.test_service_spaces_mean_all',
        'test_whitespace.Whitespace.test_ui_spaces_and_padded_category',
    ]}
    previous = ROOT.parent / '06-filter-pagination/fixed'
    runs = []
    for snapshot, path in [('mock-06-fixed-v1', previous),
                           ('mock-06-fixed-v2', ROOT / 'fixed')]:
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
                expected = expected_failures.get(module, []) if path == previous else []
                matched = (result['tests'] == count
                           and sorted(item['id'] for item in result['failures']) == expected
                           and not result['errors'] and result['skipped'] == 0)
                runs.append({'snapshot': snapshot, 'module': module,
                             'matched': matched, **result})
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                runs.append({'snapshot': snapshot, 'module': module,
                             'matched': False, 'executionError': str(error)})
            outcome = runs[-1]
            if 'tests' in outcome:
                print(f"{snapshot}/{module}: tests={outcome['tests']}, "
                      f"failures={len(outcome['failures'])}, errors={len(outcome['errors'])}, "
                      f"skipped={outcome['skipped']} - "
                      f"{'MATCH' if outcome['matched'] else 'MISMATCH'}")
            else:
                print(f"{snapshot}/{module}: EXECUTION ERROR - {outcome['executionError']}")

    inputs = [*sorted((ROOT / 'fixed').glob('*.py')), ROOT / 'run.py',
              ORIGINAL / 'run.py', ORIGINAL / 'requirements.md', ROOT / 'requirements.md',
              *sorted((ROOT / 'tests').glob('*.py')), *sorted(previous.glob('*.py')),
              *sorted((ORIGINAL / 'head').glob('*.py')),
              *sorted((ORIGINAL / 'tests').glob('*.py')),
              ORIGINAL / 'expected/test_probe.py']
    report = {
        'dataClassification': 'synthetic-only',
        'provenance': 'Local execution of known authored fixtures; not CI, blind evaluation or approval.',
        'executedAtUTC': datetime.now(timezone.utc).isoformat(),
        'python': sys.version.split()[0],
        'requirement': 'mock-req-06-v2',
        'sha256': {path.relative_to(REPO).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in inputs},
        'runs': runs,
    }
    (ROOT / 'execution.local.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if all(run['matched'] for run in runs) else 1


if __name__ == '__main__':
    raise SystemExit(main())
