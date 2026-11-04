"""Record the initial checks only; does not assess all requirements."""

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
sys.path[:0] = [str(root / 'head'), str(root / 'tests')]
suite = unittest.defaultTestLoader.loadTestsFromName('test_baseline')
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
    process = subprocess.run([sys.executable, '-B', '-c', WORKER], cwd=ROOT,
                             capture_output=True, text=True, encoding='utf-8', timeout=10)
    if process.returncode:
        print(process.stderr, file=sys.stderr)
        return 1
    result = json.loads(process.stdout)
    inputs = ['requirements.md', 'base/booking.py', 'head/booking.py',
              'change.diff', 'tests/test_baseline.py', 'run_baseline.py']
    report = {
        'classification': 'synthetic-only',
        'provenance': 'Actual local execution, not CI or approval; initial checks only.',
        'snapshot': 'e1-seat-head-v1', 'requirement': 'e1-seat-req-v1',
        'executedAtUTC': datetime.now(timezone.utc).isoformat(),
        'python': sys.version.split()[0],
        'sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in inputs},
        'result': result,
    }
    (ROOT / 'baseline.local.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    return 0 if result['tests'] == 2 and not result['failures'] and not result['errors'] and not result['skipped'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
