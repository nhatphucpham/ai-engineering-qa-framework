"""Capture one exclusive offline campaign; never overwrites historical evidence."""
import argparse
import io
import json
from pathlib import Path
import platform
import sys
import time
import unittest
from unittest.mock import patch

from .common import sha
from .corpus import ROOT
from .test_conformance import APPLICABLE, OfflineCases


def source_pins():
    prefixes = ['qa_core', 'runtime_candidate', 'spikes/vf1', 'spikes/hc1', 'spikes/p4d_rc1',
                'schemas', 'examples/mock/06-filter-pagination', 'docs/hc1-results/hc1-20261118-live-r3']
    paths = set()
    for prefix in prefixes:
        paths.update(p for p in (ROOT / prefix).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for p in ['docs/P4D-RC1-PROTOCOL.md', 'docs/P4D-RC1-ACCEPTANCE.md', 'docs/P4D-RC1-IMPLEMENTATION.md',
              'docs/p4d-rc1-design/acceptance.json',
              'docs/hc1-results/hc1-20261118-r1/review-snapshot-r1.json']:
        paths.add(ROOT / p)
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(paths)}


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = []
        self.status = {}

    def addSuccess(self, test):
        self.status[test.id()] = 'PASS'
        super().addSuccess(test)

    def addError(self, test, err):
        self.status[test.id()] = 'ERROR'
        super().addError(test, err)

    def addFailure(self, test, err):
        self.status[test.id()] = 'FAIL'
        super().addFailure(test, err)

    def stopTest(self, test):
        method = test.id().split('.')[-1].split('_', 2)
        self.rows.append({'case': method[1], 'port': method[2], 'status': self.status.get(test.id(), 'ERROR'),
                          'assertionCalls': getattr(test, 'assertionCalls', 0),
                          'scenarios': getattr(test, 'traces', [])})
        super().stopTest(test)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True, help='unused output JSON below docs/p4d-rc1-results')
    args = parser.parse_args()
    output = (ROOT / args.capture).resolve()
    allowed = (ROOT / 'docs/p4d-rc1-results').resolve()
    if output.parent != allowed or output.suffix != '.json' or output.exists():
        parser.error('capture must be an unused JSON filename in docs/p4d-rc1-results')
    # Open exclusively before execution: two operators cannot claim the same campaign name.
    with output.open('x', encoding='utf-8', newline='\n') as handle:
        before = source_pins()
        started = time.monotonic()
        stream = io.StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult)
        network_attempts = []
        def deny_network(*args, **kwargs):
            network_attempts.append(True)
            raise AssertionError('Offline campaign attempted a network connection')
        with patch('socket.create_connection', side_effect=deny_network), patch('socket.socket.connect', side_effect=deny_network):
            result = runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(OfflineCases))
        seconds = time.monotonic() - started
        after = source_pins()
        design_matrix = json.loads((ROOT / 'docs/p4d-rc1-design/acceptance.json').read_text(encoding='utf-8'))
        required = {(row['id'], port) for row in design_matrix['cases'] if row['stage'] == 'offline' for port in row['ports']}
        declared = {(case, port) for case, ports in APPLICABLE.items() for port in ports}
        actual = {(row['case'], row['port']) for row in result.rows}
        clean = (result.wasSuccessful() and before == after and actual == required and
                 len(result.rows) == len(required) and required == declared and not result.skipped and not network_attempts)
        record = {'version': 'p4d-rc1-offline-results-1.0.0', 'status': 'PASS' if clean else 'ERROR',
            'command': 'py -3 -B -m spikes.p4d_rc1.run --capture ' + output.relative_to(ROOT).as_posix(),
            'scope': 'authored offline conformance only; no application/provider/native execution',
            'python': platform.python_version(), 'seconds': seconds, 'workload': '45 offline groups; timing observation only, no product SLO',
            'groups': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
            'skipped': len(result.skipped), 'requiredOfflinePortCases': len(required),
            'scenariosObserved': sum(len(row['scenarios']) for row in result.rows),
            'assertionCalls': sum(row['assertionCalls'] for row in result.rows), 'rows': result.rows,
            'integration': [{'case': f'I{i:02}', 'port': port, 'status': 'NOT_RUN'}
                            for i in range(1, 6) for port in ('local_host', 'openai', 'anthropic')],
            'sourcePinsBefore': before, 'sourcePinsAfter': after, 'sourcesUnchanged': before == after,
            'output': stream.getvalue(), 'applicationDispatches': 0, 'actualProviderCalls': 0,
            'parentProcessNetworkConnectAttempts': len(network_attempts),
            'database': 'NOT_USED', 'fullP4D': 'OPEN', 'productMilestones': '7/12', 'humanDecision': 'pending'}
        handle.write(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: record[k] for k in ('status', 'groups', 'failures', 'errors', 'skipped', 'seconds',
                                           'scenariosObserved', 'assertionCalls', 'sourcesUnchanged')}, indent=2))
    if not clean:
        print(stream.getvalue())
    raise SystemExit(not clean)


if __name__ == '__main__':
    main()
