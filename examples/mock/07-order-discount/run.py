"""Verify authored fixture outcomes; not a general QA evaluator."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
WORKER = """
import json, sys, unittest
from pathlib import Path
root = Path.cwd()
sys.path[:0] = [str(root / sys.argv[1]), str(root / 'tests')]
suite = unittest.defaultTestLoader.loadTestsFromName(sys.argv[2])
result = unittest.TestResult()
suite.run(result)
print(json.dumps({
    'tests': result.testsRun,
    'failures': [{'id': t.id(), 'trace': trace} for t, trace in result.failures],
    'errors': [{'id': t.id(), 'trace': trace} for t, trace in result.errors],
    'skipped': len(result.skipped),
}))
"""


def main():
    runs = []
    for snapshot in ('head', 'fixed'):
        for module in ('test_baseline', 'test_probe'):
            try:
                process = subprocess.run(
                    [sys.executable, '-B', '-c', WORKER, snapshot, module],
                    cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=10,
                )
                if process.returncode:
                    raise RuntimeError(process.stderr)
                outcome = json.loads(process.stdout)
                expected = sorted([
                    'test_probe.Probe.test_threshold_is_inclusive',
                    'test_probe.Probe.test_shipping_is_not_discounted',
                ]) if snapshot == 'head' and module == 'test_probe' else []
                matched = (outcome['tests'] == 2
                           and sorted(t['id'] for t in outcome['failures']) == expected
                           and not outcome['errors'] and outcome['skipped'] == 0)
                runs.append({'snapshot': f'mock-07-{snapshot}-v1', 'module': module,
                             'matched': matched, **outcome})
                print(f"{snapshot}/{module}: tests={outcome['tests']}, "
                      f"failures={len(outcome['failures'])}, errors={len(outcome['errors'])}, "
                      f"skipped={outcome['skipped']} - {'MATCH' if matched else 'MISMATCH'}")
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                runs.append({'snapshot': f'mock-07-{snapshot}-v1', 'module': module,
                             'matched': False, 'executionError': str(error)})
                print(f'{snapshot}/{module}: EXECUTION ERROR - {error}')

    inputs = sorted(ROOT.rglob('*.py')) + [ROOT / 'requirements.md']
    report = {
        'dataClassification': 'synthetic-only',
        'provenance': 'Local execution of authored known fixtures; not CI, blind evaluation or approval.',
        'executedAtUTC': datetime.now(timezone.utc).isoformat(),
        'python': sys.version.split()[0], 'requirement': 'mock-req-07-v1',
        'sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in inputs},
        'runs': runs,
    }
    (ROOT / 'execution.local.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if all(run['matched'] for run in runs) else 1


if __name__ == '__main__':
    raise SystemExit(main())
