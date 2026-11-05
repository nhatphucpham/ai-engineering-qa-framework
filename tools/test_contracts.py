"""P1 contract regressions: schemas/references only; no execution or product API."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from validate_contracts import ROOT, validate


EXAMPLES = ROOT / 'examples/contracts/v1'


class ContractTests(unittest.TestCase):
    def test_valid_bundles(self):
        for path in sorted(EXAMPLES.glob('valid-*.json')):
            with self.subTest(path=path.name):
                self.assertEqual(validate(json.loads(path.read_text(encoding='utf-8'))), [])

    def test_invalid_scenarios(self):
        baseline = json.loads((EXAMPLES / 'valid-handoff.json').read_text(encoding='utf-8'))
        cases = json.loads((EXAMPLES / 'invalid-scenarios.json').read_text(encoding='utf-8'))
        for case in cases:
            with self.subTest(case=case['id']):
                bundle = copy.deepcopy(baseline)
                for change in case['changes']:
                    parts = change['path'].strip('/').split('/')
                    target = bundle
                    for part in parts[:-1]:
                        target = target[int(part)] if isinstance(target, list) else target[part]
                    key = int(parts[-1]) if isinstance(target, list) else parts[-1]
                    if change['op'] == 'remove':
                        del target[key]
                    else:
                        target[key] = change['value']
                codes = {error['code'] for error in validate(bundle)}
                self.assertIn(case['expectedCode'], codes)

    def test_cli_valid_invalid_and_unreadable(self):
        script = str(ROOT / 'tools/validate_contracts.py')
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            bad_json = temp / 'malformed.json'
            bad_json.write_text('{', encoding='utf-8')
            invalid = temp / 'invalid.json'
            invalid.write_text('{}', encoding='utf-8')
            for path, expected in [(EXAMPLES / 'valid-handoff.json', 0),
                                   (invalid, 1), (bad_json, 2), (temp / 'absent.json', 2)]:
                with self.subTest(path=path.name):
                    run = subprocess.run([sys.executable, '-B', script, str(path)],
                                         capture_output=True, text=True, timeout=15)
                    self.assertEqual(run.returncode, expected, run.stderr)
                    self.assertEqual(json.loads(run.stdout)['valid'], expected == 0)


if __name__ == '__main__':
    unittest.main()
