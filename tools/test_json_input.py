"""Strict intake regressions across both current reference CLI entrypoints."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evaluate_rules import ROOT
from json_input import load_json
from test_rules_v2 import inputs, upgrade


class JsonInputTests(unittest.TestCase):
    def test_shared_parser_rejects_duplicate_and_nonfinite_members(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            for raw in ['{"a":1,"a":1}', '{"nested":{"a":1,"a":2}}',
                        '{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}']:
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    path.write_text(raw, encoding='utf-8')
                    load_json(path)

    def test_both_clis_reject_ambiguous_and_deep_inputs_safely(self):
        docs = upgrade(inputs('scoped-integration-coverage'))
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            bundle, assessment = folder / 'bundle.json', folder / 'assessment.json'
            valid_bundle = json.dumps(docs['bundle'])
            valid_assessment = json.dumps(docs['assessment'])
            cases = [('assessment', '{"assessmentVersion":"secret_SENTINEL",' + valid_assessment[1:]),
                     ('bundle', '{"contractVersion":"secret_SENTINEL",' + valid_bundle[1:]),
                     ('assessment', '[' * 1200 + '0' + ']' * 1200),
                     ('assessment', '{"secret_SENTINEL":NaN}')]
            for script in ('evaluate_rules.py', 'project_report.py'):
                for target, raw in cases:
                    with self.subTest(script=script, target=target, raw=raw[:35]):
                        bundle.write_text(valid_bundle, encoding='utf-8')
                        assessment.write_text(valid_assessment, encoding='utf-8')
                        (bundle if target == 'bundle' else assessment).write_text(raw, encoding='utf-8')
                        run = subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / script),
                                              str(bundle), str(assessment)], capture_output=True, text=True, timeout=15)
                        self.assertEqual(run.returncode, 2, run.stderr)
                        self.assertEqual(json.loads(run.stdout)['processingStatus'], 'input_error')
                        self.assertNotIn('secret_SENTINEL', run.stdout)
                        self.assertFalse(run.stderr)


if __name__ == '__main__':
    unittest.main()
