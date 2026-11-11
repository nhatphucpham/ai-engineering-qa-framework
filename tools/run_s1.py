"""Reproducible S1 differential experiment; no QA project execution or API calls."""

import argparse
from collections import Counter
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from functools import lru_cache

from evaluate_rules import ROOT
from project_report import create_report
from test_rules import read, scenario_inputs
from test_rules_v2 import inputs, upgrade

SPIKE = ROOT / 'spikes/s1'
DEFAULT_NODE = ROOT / '.cache/s1/runtime/node-v26.13.0-win-x64/node.exe'


def json_file(path):
    return json.loads(path.read_text(encoding='utf-8'))


def cases():
    requests = []
    def add(group, name, op, **data):
        requests.append({'id': group + '/' + name, 'group': group, 'op': op, **copy.deepcopy(data)})
    folder = ROOT / 'examples/contracts/v2'
    for path in sorted(folder.glob('valid-*.json')):
        add('p1-valid', path.stem, 'contract', bundle=json_file(path))
    for case in json_file(folder / 'invalid-scenarios.json'):
        bundle = json_file(folder / case.get('base', 'valid-handoff.json'))
        for change in case['changes']:
            parts = change['path'].strip('/').split('/')
            target = bundle
            for part in parts[:-1]:
                target = target[int(part)] if isinstance(target, list) else target[part]
            key = int(parts[-1]) if isinstance(target, list) else parts[-1]
            if change['op'] == 'remove':
                del target[key]
            else:
                target[key] = copy.deepcopy(change['value'])
        add('p1-negative', case['id'], 'contract', bundle=bundle)
    add('p1-version', 'legacy-v1', 'contract', bundle=json_file(ROOT / 'examples/contracts/v1/valid-handoff.json'))
    for case in read('scenarios.json'):
        docs = scenario_inputs(case)
        add('p2-v1', case['id'], 'evaluate', **docs)
        add('p2-v2', case['id'], 'evaluate', **upgrade(docs))
        add('report', case['id'], 'report', **upgrade(docs))
        if 'expectedError' not in case:
            fixed = upgrade(docs)
            add('report-check', case['id'], 'check', report=create_report(**fixed), **fixed)
    for case in read('lifecycle-cases.json'):
        add('lifecycle', case['id'], 'transition', entity=case['entity'], current=case['from'], target=case['to'], context=case['context'])
    valid_context = copy.deepcopy(read('lifecycle-cases.json')[0]['context'])
    for entity in ('finding', 'action', 'unknown'):
        for state in ('constructor', '__proto__', 'toString'):
            add('lifecycle-edge', entity + '-' + state, 'transition', entity=entity, current=state, target='confirmed', context=valid_context)
    base = upgrade(inputs('scoped-integration-coverage'))
    base_report = create_report(**base)
    for field, value in [('verification', 'failed'), ('humanDecision', 'approved')]:
        changed = copy.deepcopy(base_report)
        changed['assessment'][field] = value
        add('tamper', field, 'check', report=changed, **base)
    changed = copy.deepcopy(base_report)
    changed['scope']['projectConfigVersion'] = 1.0
    add('tamper', 'int-to-float', 'check', report=changed, **base)
    changed = copy.deepcopy(base_report)
    changed['assessmentContext']['bindings'][0]['comparisonKey'] = 'employee-api'
    add('tamper', 'mapping', 'check', report=changed, **base)
    other = copy.deepcopy(base)
    other['bundle']['tasks'][0]['title'] = 'Different bound input'
    add('tamper', 'cross-bundle', 'check', report=base_report, **other)
    changed = copy.deepcopy(base_report)
    changed['reportVersion'] = '99.0.0'
    add('tamper', 'unknown-report-version', 'check', report=changed, **base)
    add('detachment', 'returned-source-objects', 'detachment', **base)
    source = inputs('source-proof-with-accepted-scope')
    source['assessment']['criteria'][0]['requiredLevels'] = ['integration']
    for evidence in source['bundle']['evidence']:
        evidence['level'] = 'integration'
    add('regression', 'source-level-v1', 'evaluate', **source)
    add('regression', 'source-level-v2', 'evaluate', **upgrade(source))
    mixed = upgrade(inputs('comparable-evidence-conflict'))
    mixed['bundle']['evidence'][0].update(outcome='fail', reason='manager fails')
    mixed['assessment']['bindings'][0]['relation'] = 'violates'
    mixed['assessment']['risk']['state'] = 'candidate'
    add('regression', 'mixed-violation-conflict-plan', 'report', **mixed)
    mixed['bundle']['evidence'][0].update(outcome='blocked', reason='check unavailable')
    add('regression', 'conflict-blocked-plan', 'report', **mixed)
    for name, amount in [('safe-boundary', 9007199254740991), ('unsafe-integer', 9007199254740993),
                         ('huge-integer', int('9' * 310)), ('float-integer', 1.0)]:
        docs = copy.deepcopy(base)
        docs['bundle']['projects'][0]['configVersion'] = amount
        docs['assessment']['projectConfigVersion'] = amount
        add('numeric-document', name, 'report', **docs)
        if isinstance(amount, int):
            docs['assessment']['projectConfigVersion'] = amount - 1
            add('numeric-document', name + '-mismatch', 'evaluate', **docs)
    for field in ('assessorRef', 'scopeDescription'):
        docs = copy.deepcopy(base)
        if field == 'assessorRef':
            docs['assessment'][field] += '\n'
        else:
            docs['assessment']['criteria'][0][field] = 'Đối chiếu 😀, café, \u2028 và e\u0301'
        add('unicode-document', field, 'report', **docs)
    for value in (None, [], {}, {'assessmentVersion': []}):
        add('malformed-document', 'assessment-' + str(len(requests)), 'evaluate', bundle=base['bundle'], assessment=value)
    raw = ['0', '-0', '1', '1.0', '-0.0', '1e0', '1e-7', '1e16', '1e23', '1e400', '5e-324', '1.2345678901234567',
           '9007199254740993', '9' * 310, '{"a":1,"b":1.0}', '{"a":1,"a":1}', '{"a":1,"\\u0061":2}',
           '"\\ud800"', '"\\ud83d\\ude00"', '{"\\ue000":1,"\\ud83d\\ude00":2}',
           'NaN', 'Infinity', '-Infinity', '[1,]', '[' * 1200 + '0' + ']' * 1200]
    for index, value in enumerate(raw):
        add('raw-json', str(index), 'digest', raw=value)
    ids = [r['id'] for r in requests]
    if len(ids) != len(set(ids)):
        raise RuntimeError('Duplicate S1 case IDs')
    assert_corpus(requests)
    return requests


def assert_corpus(requests):
    counts = Counter(r['group'] for r in requests)
    required = {'p1-valid': 9, 'p1-negative': 58, 'p1-version': 1, 'p2-v1': 55, 'p2-v2': 55,
                'report': 55, 'report-check': 45, 'lifecycle': 20}
    for group, amount in required.items():
        if counts[group] != amount:
            raise ValueError('S1 frozen corpus denominator differs: ' + group)
    if len({r['id'] for r in requests}) != len(requests):
        raise ValueError('S1 requires unique request IDs')


def matches(request, expected, actual):
    if expected.get('id') != request['id'] or actual.get('id') != request['id']:
        return False
    if not all(value.get('repeatable') is True and value.get('noMutation') is True for value in (expected, actual)):
        return False
    if request['op'] == 'detachment' and not all(value.get('value') is True for value in (expected, actual)):
        return False
    return reference_invariant(request, expected) and first_diff(expected, actual) is None


@lru_cache(maxsize=1)
def fixed_expectations():
    return ({c['id']: c for c in read('scenarios.json')},
            {c['id']: c for c in json_file(ROOT / 'examples/contracts/v2/invalid-scenarios.json')},
            {c['id']: c for c in read('lifecycle-cases.json')})


def reference_invariant(request, observed):
    rules, invalid, lifecycle = fixed_expectations()
    group, name = request.get('group'), request['id'].split('/', 1)[-1]
    if group == 'p1-valid':
        return observed.get('value') == {'valid': True, 'codes': []}
    if group == 'p1-negative':
        value = observed.get('value', {})
        return value.get('valid') is False and invalid[name]['expectedCode'] in value.get('codes', [])
    if group in ('p2-v1', 'p2-v2', 'report'):
        expected = rules[name]
        if 'expectedError' in expected:
            return observed['kind'] == 'input_error' and expected['expectedError'] in observed.get('codes', [])
        value = observed.get('value', {})
        result = value.get('assessment', {}) if group == 'report' else value
        return (result.get('verification') == expected['expected']['verification']
                and {c['criterionId']: c['status'] for c in result.get('criteria', [])} == expected['expected']['statuses'])
    if group == 'lifecycle':
        return sorted(observed.get('value', [])) == sorted(lifecycle[name]['expectedErrors'])
    return True


def first_diff(expected, actual, path=''):
    if type(expected) is not type(actual):
        return path or '/'
    if isinstance(expected, dict):
        if expected.keys() != actual.keys():
            return (path or '/') + ' [keys]'
        for key in expected:
            found = first_diff(expected[key], actual[key], path + '/' + str(key))
            if found:
                return found
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            return (path or '/') + ' [length]'
        for index, (x, y) in enumerate(zip(expected, actual)):
            found = first_diff(x, y, path + '/' + str(index))
            if found:
                return found
    elif expected != actual:
        return path or '/'
    return None


def invoke(command, request_path):
    start = time.perf_counter()
    process = subprocess.run([*command, str(request_path)], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=120)
    wall = (time.perf_counter() - start) * 1000
    if process.returncode or process.stderr:
        raise RuntimeError('S1 worker failed: ' + process.stderr[:1000])
    payload = json.loads(process.stdout)
    payload['metrics']['parentObservedWallMs'] = wall
    return payload


def source_hashes():
    files = set()
    for folder in ('examples/contracts/v1', 'examples/contracts/v2', 'examples/rules/v1', 'examples/rules/v2',
                   'examples/reports/v1', 'schemas', 'tools', 'qa_core', 'spikes/s1/src'):
        files.update(path for path in (ROOT / folder).rglob('*') if path.is_file() and '__pycache__' not in path.parts)
    files.update([SPIKE / 'package.json', SPIKE / 'package-lock.json', SPIKE / 'tsconfig.json'])
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}


def cli_checks(node):
    checks = []
    base = upgrade(inputs('scoped-integration-coverage'))
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        bp, ap, rp = (folder / (name + '.json') for name in ('bundle', 'assessment', 'report'))
        def run(name, operation, docs, expected_exit, raw=None, extra=None, report=None):
            bp.write_text(json.dumps(docs['bundle']), encoding='utf-8')
            if isinstance(raw, bytes):
                ap.write_bytes(raw)
            else:
                ap.write_text(json.dumps(docs['assessment']) if raw is None else raw, encoding='utf-8')
            if report is not None:
                rp.write_text(json.dumps(report), encoding='utf-8')
            suffix = [str(bp)] if operation == 'contract' else [str(bp), str(ap)]
            if extra:
                suffix.extend([x if x != 'REPORT_PATH' else str(rp) for x in extra])
            script = 'validate_contracts.py' if operation == 'contract' else 'evaluate_rules.py' if operation == 'evaluate' else 'project_report.py'
            commands = [[sys.executable, '-B', str(ROOT / 'tools' / script), *suffix], [str(node), str(SPIKE / 'dist/cli.js'), operation, *suffix]]
            processes = [subprocess.run(c, capture_output=True, text=True, encoding='utf-8', timeout=20) for c in commands]
            parser_error = extra is not None and extra[0] != '--check'
            summaries = []
            for process in processes:
                if parser_error:
                    summaries.append({'exit': process.returncode})
                    continue
                value = json.loads(process.stdout)
                summaries.append({'exit': process.returncode, 'status': value.get('processingStatus'), 'valid': value.get('valid'),
                                  'verification': value.get('assessment', value).get('verification'),
                                  'codes': sorted({e['code'] for e in value.get('errors', [])}),
                                  'safe': not process.stderr and 'secret_SENTINEL' not in process.stdout})
            checks.append({'id': name, 'matched': summaries[0] == summaries[1] and all(p.returncode == expected_exit for p in processes)
                           and all(s.get('safe', True) for s in summaries),
                           'reference': summaries[0], 'candidate': summaries[1]})
        for operation in ('evaluate', 'report'):
            for scenario, code in [('scoped-integration-coverage', 0), ('blocked-not-defect', 1),
                                   ('accepted-current-counterexample', 1), ('assessment-for-other-candidate', 2)]:
                run(operation + '-' + scenario, operation, upgrade(inputs(scenario)), code)
            for index, raw in enumerate(['{"assessmentVersion":"secret_SENTINEL",' + json.dumps(base['assessment'])[1:],
                                          '{"secret_SENTINEL":NaN}', '[' * 1200 + '0' + ']' * 1200, '{',
                                          json.dumps(base['assessment']).replace('"projectConfigVersion": 1', '"projectConfigVersion": 1e400'),
                                          b'\xff', '\ufeff' + json.dumps(base['assessment'])]):
                run(operation + '-raw-' + str(index), operation, base, 2, raw=raw)
            run(operation + '-extra-argument', operation, base, 2, extra=['unexpected'])
        run('report-typo-check-flag', 'report', base, 2, extra=['--chek', 'REPORT_PATH'], report=create_report(**base))
        collision = upgrade(inputs('satisfied-claim-without-review'))
        run('check-incomplete-valid', 'report', collision, 0, extra=['--check', 'REPORT_PATH'], report=create_report(**collision))
        run('contract-valid', 'contract', base, 0)
        invalid = copy.deepcopy(base)
        invalid['bundle']['contractVersion'] = '99.0.0'
        run('contract-invalid-version', 'contract', invalid, 1)
    if len(checks) != 28:
        raise RuntimeError('S1 CLI denominator differs from declared 28 cases')
    return checks


def main():
    started_at = datetime.now(timezone.utc).isoformat()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', type=Path, default=DEFAULT_NODE)
    parser.add_argument('--out', type=Path, required=True, help='New evidence file; existing output is never overwritten')
    parser.add_argument('--trials', type=int, default=3)
    args = parser.parse_args()
    if args.out.exists() or args.trials < 1:
        parser.error('Use a new output path and at least one measurement trial')
    args.node = args.node.resolve()
    version = subprocess.check_output([str(args.node), '--version'], text=True).strip()
    if version != 'v26.13.0':
        parser.error('S1 candidate pin requires Node v26.13.0')
    subprocess.run([str(args.node), str(SPIKE / 'node_modules/typescript/bin/tsc'), '-p', str(SPIKE / 'tsconfig.json')], cwd=ROOT, check=True)
    before = source_hashes()
    requests = cases()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'requests.json'
        path.write_text(json.dumps(requests, ensure_ascii=True, allow_nan=False), encoding='utf-8')
        reference = invoke([sys.executable, '-B', str(ROOT / 'tools/s1_reference.py')], path)
        candidate = invoke([str(args.node), str(SPIKE / 'dist/cli.js'), '--batch'], path)
        if len(reference['results']) != len(requests) or len(candidate['results']) != len(requests):
            raise RuntimeError('Worker omitted results')
        details, groups = [], {}
        for request, expected, actual in zip(requests, reference['results'], candidate['results']):
            diff = first_diff(expected, actual)
            matched = matches(request, expected, actual)
            row = {'id': request['id'], 'matched': matched, 'referenceKind': expected['kind'], 'candidateKind': actual['kind'],
                   'firstDifference': diff, 'inputSha256': hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=True).encode()).hexdigest()}
            if not matched:
                row.update(reference=expected, candidate=actual)
            details.append(row)
            group = groups.setdefault(request['group'], {'total': 0, 'pass': 0, 'fail': 0, 'skipped': 0, 'referenceInputErrors': 0})
            group['total'] += 1
            group['pass' if matched else 'fail'] += 1
            group['referenceInputErrors'] += expected['kind'] == 'input_error'
        # Benchmark only in-memory engine operations; raw reference intake has file IO.
        engine_requests = [r for r in requests if r['op'] != 'digest']
        path.write_text(json.dumps(engine_requests, ensure_ascii=True), encoding='utf-8')
        trials = {'reference': [], 'candidate': []}
        for _ in range(args.trials):
            for name, command in [('reference', [sys.executable, '-B', str(ROOT / 'tools/s1_reference.py')]),
                                  ('candidate', [str(args.node), str(SPIKE / 'dist/cli.js'), '--batch'])]:
                observed = invoke(command, path)
                initial = reference if name == 'reference' else candidate
                expected_results = [r for r in initial['results'] if r['id'] in {v['id'] for v in engine_requests}]
                if first_diff(expected_results, observed['results']) is not None:
                    raise RuntimeError('S1 benchmark trial outcomes differ from initial verification')
                observed['metrics']['outcomesMatchInitial'] = True
                trials[name].append(observed['metrics'])
        sizes = {'requests': len(requests), 'engineRequests': len(engine_requests),
                 'fullInputUTF8Bytes': len(json.dumps(requests, ensure_ascii=True).encode()), 'engineInputUTF8Bytes': path.stat().st_size}
    cli = cli_checks(args.node)
    after = source_hashes()
    immutable = before == after
    passed = all(r['matched'] for r in details) and all(r['matched'] for r in cli) and immutable
    lock = json_file(SPIKE / 'package-lock.json')
    payload = {'experiment': 'P3-B/S1', 'designBaselineCommit': 'c4149bd52a6b0658a78fe8988207f636a50c58b5',
               'observedHead': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'startedAtUTC': started_at, 'recordedAtUTC': datetime.now(timezone.utc).isoformat(),
               'gate': 'PASS' if passed else 'PARTIAL', 'environment': {'os': platform.platform(), 'machine': platform.machine(),
               'python': sys.version.split()[0], 'jsonschema': importlib.metadata.version('jsonschema'),
               'node': version, 'nodeExecutableSha256': hashlib.sha256(args.node.read_bytes()).hexdigest(),
               'packages': {k: v.get('version') for k, v in lock['packages'].items() if k}},
               'inputSizes': sizes, 'groups': groups, 'cases': details, 'cli': cli,
               'initialMetrics': {'reference': reference['metrics'], 'candidate': candidate['metrics']}, 'engineTrials': trials,
               'sourceAndFixtureHashes': before, 'sourceAndFixtureUnchanged': immutable,
               'limitations': ['Supplied synthetic judgments, no domain truth or runtime authority verified.',
                              'Candidate and reference each execute requests twice to check repeatability, plus clone/serialization guards.',
                              'Warm batch metrics include validation/projection and guards; process startup/schema import reported separately.',
                              'Parity is measured on enumerated corpus and discriminators, not a proof over all JSON or production readiness.',
                              'P1 API error classes compared; permissive legacy P1 duplicate-key CLI parsing is not the corrected intake target.']}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as output:
        output.write(json.dumps(payload, indent=2, ensure_ascii=True, allow_nan=False) + '\n')
    print(json.dumps({'gate': payload['gate'], 'groups': groups, 'cliPass': sum(c['matched'] for c in cli),
                      'cliTotal': len(cli), 'immutable': immutable, 'output': str(args.out)}, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
