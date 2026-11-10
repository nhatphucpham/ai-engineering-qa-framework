"""S1 oracle worker. The native candidate never imports/calls this process."""

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import time

IMPORT_START = time.perf_counter()
from evaluate_rules import AssessmentError, evaluate, validate_transition
from json_input import load_json
from project_report import create_report, digest, validate_report
from validate_contracts import validate
IMPORT_MS = (time.perf_counter() - IMPORT_START) * 1000


class BoundaryError(ValueError):
    def __init__(self, code):
        self.code = code


def execute(request, raw_path):
    operation = request['op']
    if operation == 'contract':
        errors = validate(request['bundle'])
        return {'valid': not errors, 'codes': sorted({e['code'] for e in errors})}
    if operation == 'evaluate':
        return evaluate(request['bundle'], request['assessment'])
    if operation == 'report':
        return create_report(request['bundle'], request['assessment'])
    if operation == 'check':
        return sorted(e['code'] for e in validate_report(request['report'], request['bundle'], request['assessment']))
    if operation == 'transition':
        return validate_transition(request['entity'], request['current'], request['target'], request['context'])
    if operation == 'digest':
        # Exercise the actual shared reference intake, not a lenient json.loads substitute.
        raw_path.write_text(request['raw'], encoding='utf-8')
        value = load_json(raw_path)
        try:
            return digest(value)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            raise BoundaryError('E_INPUT_CANONICAL') from None
    if operation == 'detachment':
        report = create_report(request['bundle'], request['assessment'])
        original = copy.deepcopy((request['bundle'], request['assessment']))
        report['criterionSources'][0]['criterion']['expected'] = 'modified output'
        report['assessmentContext']['bindings'][0]['rationale'] = 'modified output'
        return (request['bundle'], request['assessment']) == original
    raise BoundaryError('E_INPUT')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def response(request, raw_path):
    before = canonical(request)
    second_input = copy.deepcopy(request)
    def run(value):
        try:
            return {'kind': 'ok', 'value': execute(value, raw_path)}
        except (AssessmentError, BoundaryError, ValueError, OSError, RecursionError) as error:
            if isinstance(error, AssessmentError):
                codes = sorted({e['code'] for e in error.errors})
            elif isinstance(error, BoundaryError):
                codes = [error.code]
            else:
                codes = ['E_INPUT']
            return {'kind': 'input_error', 'codes': codes}
    first, second = run(request), run(second_input)
    return {'id': request['id'], **first, 'noMutation': before == canonical(request) == canonical(second_input),
            'repeatable': canonical(first) == canonical(second)}


def peak_rss_bytes():
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return None
        return counters.PeakWorkingSetSize
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value if sys.platform == 'darwin' else value * 1024
    except (ImportError, OSError):
        return None


def main():
    requests = load_json(Path(sys.argv[1]))
    with tempfile.TemporaryDirectory() as directory:
        raw_path = Path(directory) / 'raw.json'
        start = time.perf_counter()
        cpu = os.times()
        results = [response(request, raw_path) for request in requests]
        elapsed = (time.perf_counter() - start) * 1000
        after = os.times()
    payload = {'results': results, 'metrics': {'runtime': sys.version.split()[0], 'platform': sys.platform,
               'importCompileMs': IMPORT_MS, 'warmBatchMs': elapsed,
               'warmUserUS': round((after.user - cpu.user) * 1000000),
               'warmSystemUS': round((after.system - cpu.system) * 1000000),
               'peakRSSBytes': peak_rss_bytes(), 'requestCount': len(requests)}}
    print(json.dumps(payload, ensure_ascii=True, allow_nan=False))


if __name__ == '__main__':
    main()
