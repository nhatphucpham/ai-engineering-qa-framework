"""Fixed unittest entry point for the VF1 synthetic container."""

import json
import os
from pathlib import Path
import platform
import sys
import time
import unittest


RESULT_VERSION = 'vf1-unittest-1.0.0'
TRACE_LIMIT = 3000
TEST_NAMES = (
    'test_baseline.Baseline.test_service_category_and_case',
    'test_baseline.Baseline.test_service_pagination_and_out_of_range',
    'test_baseline.Baseline.test_empty_category',
    'test_baseline.Baseline.test_api_repeat_same_request',
    'test_baseline.Baseline.test_api_page_and_size',
    'test_baseline.Baseline.test_ui_select_from_first_page',
    'test_historical.Historical.test_reset_from_third_page',
    'test_probe.Probe.test_reset_with_recorded_api_call',
    'test_probe.Probe.test_cache_across_categories',
)
TEST_IDS = tuple(name.split('.', 1)[1] for name in TEST_NAMES)
OUTCOMES = ('pass', 'fail', 'error', 'skipped')


def counts_for(observations):
    counts = dict.fromkeys(OUTCOMES, 0)
    for observation in observations:
        counts[observation['outcome']] += 1
    return {'total': len(observations), **counts}


def observe(name):
    result = unittest.TestResult()
    unittest.TestLoader().loadTestsFromName(name).run(result)
    outcome, trace = 'pass', ''
    if result.errors:
        outcome, trace = 'error', result.errors[0][1]
    elif result.failures:
        outcome, trace = 'fail', result.failures[0][1]
    elif result.skipped:
        outcome, trace = 'skipped', result.skipped[0][1]
    elif result.unexpectedSuccesses or result.expectedFailures or result.testsRun != 1:
        outcome, trace = 'error', 'The fixed test did not produce an ordinary unittest outcome.'
    return {'testId': name.split('.', 1)[1], 'outcome': outcome, 'traceText': trace[-TRACE_LIMIT:]}


def main():
    output = Path('/output')
    deadline = time.monotonic() + 22
    while not (output / '.allow-start').is_file():
        if time.monotonic() >= deadline:
            return 2
        time.sleep(0.025)

    case = Path('/input/case')
    sys.path[:0] = [str(case / name) for name in ('head', 'tests', 'expected')]
    observations = [observe(name) for name in TEST_NAMES]
    result = {'resultVersion': RESULT_VERSION, 'pythonVersion': platform.python_version(),
              'uid': os.getuid(), 'observations': observations, 'counts': counts_for(observations)}
    with (output / 'result.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=True, allow_nan=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
