"""Read-only RC1 package verification; optional new exclusive evidence capture."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DOCS = ['docs/P4D-RC1-IMPLEMENTATION.md', 'docs/P4D-RC1-RESULTS.md',
        'docs/NEXT-SESSION-POST-P4D-RC1-IMPLEMENTATION.md', 'spikes/p4d_rc1/README.md']
CODE = ['__init__.py', 'common.py', 'contracts.py', 'local_host.py', 'openai_port.py',
        'anthropic_port.py', 'harness.py', 'corpus.py', 'reopen_probe.py', 'test_conformance.py', 'run.py']
ARTIFACTS = ['baseline.json', 'offline-r1.json', 'offline-r2.json', 'offline-r3.json', 'offline-r4.json',
             'regression-r1.json', 'regression-command.txt', 'verification-commands.json', 'verify.py',
             'review.json', 'checks-final.json', 'checks-final-r2.json']
PREFIXES = {'docs/IMPLEMENTATION-PLAN.md', 'docs/DECISION-LOG.md'}
NEW = set(DOCS + ['spikes/p4d_rc1/' + p for p in CODE] + ['docs/p4d-rc1-results/' + p for p in ARTIFACTS])
CURRENT_SNAPSHOT = 'docs/p4d-rc1-results/checks-final-r2.json'
ADMIN = {'docs/p4d-rc1-results/review.json', CURRENT_SNAPSHOT}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    proc = subprocess.run(['git', *args], cwd=ROOT, capture_output=True)
    if proc.returncode:
        raise RuntimeError('Git read/check failed')
    return proc.stdout.decode('utf-8').strip()


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def compare_payload(actual, expected):
    """Every path, raw hash AND byte length matters, including historical artifacts."""
    return sorted(name for name in set(actual) | set(expected) if actual.get(name) != expected.get(name))


def comparator_checks(payload):
    from copy import deepcopy
    tests = []
    tests.append(not compare_payload(payload, deepcopy(payload)))
    for name in ('docs/P4D-RC1-RESULTS.md', 'spikes/p4d_rc1/README.md',
                 'docs/NEXT-SESSION-POST-P4D-RC1-IMPLEMENTATION.md', 'docs/p4d-rc1-results/offline-r2.json'):
        altered = deepcopy(payload)
        altered[name]['sha256'] = '0' * 64
        tests.append(compare_payload(altered, payload) == [name])
    altered = deepcopy(payload)
    key = next(iter(payload))
    altered[key]['bytes'] += 1
    tests.append(compare_payload(altered, payload) == [key])
    altered = deepcopy(payload); del altered[key]
    tests.append(compare_payload(altered, payload) == [key])
    altered = deepcopy(payload); altered['extra'] = {'sha256': '0' * 64, 'bytes': 0}
    tests.append(compare_payload(altered, payload) == ['extra'])
    return tests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', choices=['checks-final.json', 'checks-final-r2.json'])
    args = parser.parse_args()
    capture = HERE / args.capture if args.capture else None
    if capture is not None and capture.exists():
        parser.error('capture exists; evidence is immutable')
    failures = []
    def check(condition, message):
        if not condition:
            failures.append(message)
    baseline = read('docs/p4d-rc1-results/baseline.json')
    changes = []
    for name, original in baseline['files'].items():
        path = ROOT / name
        if not path.is_file():
            failures.append('Missing baseline ' + name)
            continue
        raw = path.read_bytes()
        if sha(raw) == original['sha256']:
            continue
        length = original['bytes']
        if name in PREFIXES:
            check(len(raw) > length and sha(raw[-length:]) == original['sha256'], 'Original byte suffix ' + name)
            changes.append({'path': name, 'mode': 'original suffix'})
        elif name == '.gitattributes':
            check(len(raw) > length and sha(raw[:length]) == original['sha256'], 'Original attributes prefix')
            rules = [line for line in raw[length:].decode('utf-8').splitlines() if line and not line.startswith('#')]
            expected = {'/' + p + ' -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol' for p in NEW}
            check(set(rules) == expected and len(rules) == len(expected), 'Exact new byte policies only')
            changes.append({'path': name, 'mode': 'original prefix, exact new paths'})
        else:
            failures.append('Unexpected original mutation ' + name)
    check({c['path'] for c in changes} == PREFIXES | {'.gitattributes'}, 'Only three declared baseline edits')
    existing = set(git('ls-files').splitlines()) | set(git('ls-files', '--others', '--exclude-standard').splitlines())
    added = existing - set(baseline['files'])
    check(added <= NEW, 'New file scope')
    for name in NEW:
        path = (ROOT / name).resolve()
        check(path.is_file() or path == capture, 'Expected output ' + name)
    check(git('rev-parse', 'HEAD') == baseline['head'] == git('rev-parse', 'origin/master'), 'Git heads unchanged')
    check(git('branch', '--show-current') == 'master', 'Same branch')
    check(set(git('diff', '--name-only').splitlines()) == PREFIXES | {'.gitattributes'}, 'Tracked diff scope')
    whitespace = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True)
    check(whitespace.returncode == 0, 'git diff --check')
    for name in NEW:
        path = ROOT / name
        if path.is_file() and name not in ADMIN:
            raw = path.read_bytes()
            check(not any(line.rstrip(b' \t') != line for line in raw.splitlines()), 'Trailing whitespace ' + name)
            check(raw.endswith(b'\n') and not raw.endswith(b'\n\n'), 'EOF whitespace ' + name)
    links = 0
    for name in DOCS:
        for link in re.findall(r'\]\(([^)]+)\)', (ROOT / name).read_text(encoding='utf-8')):
            if link.startswith(('https://', 'http://', '#')):
                continue
            links += 1
            path = ((ROOT / name).parent / link.split('#')[0]).resolve()
            check(path.is_file() or path == capture, 'Local link ' + name + ' -> ' + link)
    runtime = read('docs/p4d-rc1-results/offline-r4.json')
    check(runtime['status'] == 'PASS' and all(runtime[k] == 0 for k in ('failures', 'errors', 'skipped')), 'Final offline outcome')
    check(runtime['sourcePinsBefore'] == runtime['sourcePinsAfter'], 'Offline inputs before=after')
    for name, pin in runtime['sourcePinsBefore'].items():
        check((ROOT / name).is_file() and sha((ROOT / name).read_bytes()) == pin, 'Current tested source ' + name)
    check(all('spikes/p4d_rc1/' + p in runtime['sourcePinsBefore'] for p in CODE), 'All current runtime modules tested')
    design = read('docs/p4d-rc1-design/acceptance.json')
    offline = {(row['id'], p) for row in design['cases'] if row['stage'] == 'offline' for p in row['ports']}
    integration = {(row['id'], p) for row in design['cases'] if row['stage'] == 'integration' for p in row['ports']}
    actual = {(r['case'], r['port']) for r in runtime['rows'] if r['status'] == 'PASS'}
    check(actual == offline and len(runtime['rows']) == len(offline) == 45, 'Independent O matrix covered')
    check({(r['case'], r['port']) for r in runtime['integration'] if r['status'] == 'NOT_RUN'} == integration
          and len(runtime['integration']) == 15, 'All I cases NOT RUN')
    check(runtime['scenariosObserved'] == sum(len(r['scenarios']) for r in runtime['rows']), 'Actual scenario count')
    check(runtime['parentProcessNetworkConnectAttempts'] == 0, 'Parent network guard')
    regression = read('docs/p4d-rc1-results/regression-r1.json')
    check(regression['status'] == 'PASS' and {r['suite']: r['tests'] for r in regression['suites']} ==
          {'core': 45, 'vf1': 12, 'candidate': 54} and all(r['failures'] == r['errors'] == r['skipped'] == 0
          for r in regression['suites']), 'Required pure/local regressions')
    check(read('docs/p4d-rc1-results/offline-r1.json')['status'] == 'ERROR', 'R1 failure retained')
    payload_names = sorted((NEW - ADMIN) | PREFIXES | {'.gitattributes'})
    payload = {name: {'sha256': sha((ROOT / name).read_bytes()), 'bytes': (ROOT / name).stat().st_size}
               for name in payload_names}
    self_checks = comparator_checks(payload)
    check(all(self_checks), 'Retained payload comparator self-checks')
    differences = []
    if capture is None:
        if (ROOT / CURRENT_SNAPSHOT).is_file():
            differences = compare_payload(payload, read(CURRENT_SNAPSHOT)['payload'])
            check(not differences, 'Retained exact payload mismatch: ' + ', '.join(differences))
        else:
            failures.append('Current retained package snapshot missing')
    result = {'version': 'p4d-rc1-package-checks-1.0.0', 'status': 'FAIL' if failures else 'PASS',
              'command': 'py -3 -B docs/p4d-rc1-results/verify.py' + (' --capture ' + args.capture if args.capture else ''),
              'mode': 'exclusive-new-capture' if capture else 'read-only', 'baselineFiles': len(baseline['files']),
              'unchangedFiles': len(baseline['files']) - len(changes), 'changes': changes,
              'sourcePinsBeforeAfterCurrent': len(runtime['sourcePinsBefore']), 'localLinks': links,
              'offlinePortCases': 45, 'integrationNotRun': 15, 'gitDiffCheckExit': whitespace.returncode,
              'expectedSnapshot': CURRENT_SNAPSHOT, 'snapshotComparison': 'new candidate capture' if capture else
                  ('MATCH' if not differences and (ROOT / CURRENT_SNAPSHOT).is_file() else 'MISMATCH'),
              'comparatorSelfChecks': {'passed': sum(self_checks), 'total': len(self_checks)},
              'payload': payload, 'failures': failures, 'fullP4D': 'OPEN', 'humanDecision': 'pending'}
    if capture is not None:
        with capture.open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'payload'}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
