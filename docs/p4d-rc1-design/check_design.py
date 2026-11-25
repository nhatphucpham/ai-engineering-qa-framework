"""Static design/preservation check only. Never runs RC1 adapter/runtime cases."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DOCS = [
    'docs/P4D-CAPABILITY-AUDIT-2026-11-24.md',
    'docs/P4D-RC1-PROTOCOL.md',
    'docs/P4D-RC1-ACCEPTANCE.md',
    'docs/NEXT-SESSION-POST-P4D-RC1.md',
]
EVIDENCE = ['baseline.json', 'acceptance.json', 'source-inspection.json', 'check_design.py',
            'checks-initial.json', 'snapshot-r1.json', 'checks.json', 'checks-r3.json']
CAPTURES = ['checks-r3.json', 'checks-r4.json']
PREFIX = {'docs/IMPLEMENTATION-PLAN.md', 'docs/DECISION-LOG.md'}
PAYLOAD = DOCS + sorted(PREFIX) + ['.gitattributes'] + [f'docs/p4d-rc1-design/{p}' for p in EVIDENCE]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
    return result.stdout.decode('utf-8').strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', choices=CAPTURES, help='write an unused declared record once; default is read-only')
    args = parser.parse_args()
    capture = HERE / args.capture if args.capture else None
    if capture is not None and capture.exists():
        parser.error('capture already exists; retained evidence is immutable')
    failures = []
    def check(condition, label):
        if not condition:
            failures.append(label)
    baseline = json.loads((HERE / 'baseline.json').read_text(encoding='utf-8'))
    changes = []
    for name, pin in baseline['files'].items():
        path = ROOT / name
        if not path.is_file():
            failures.append(f'missing baseline: {name}')
            continue
        raw = path.read_bytes()
        if sha(raw) == pin['sha256']:
            continue
        size = pin['bytes']
        if name in PREFIX:
            check(len(raw) > size and sha(raw[-size:]) == pin['sha256'], f'original suffix: {name}')
            changes.append({'path': name, 'policy': 'original byte suffix'})
        elif name == '.gitattributes':
            check(len(raw) > size and sha(raw[:size]) == pin['sha256'], 'original attributes prefix')
            extra = raw[size:].decode('utf-8')
            rules = [line for line in extra.splitlines() if line and not line.startswith('#')]
            expected = {f'/{p} -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol'
                        for p in DOCS + [f'docs/p4d-rc1-design/{p}' for p in EVIDENCE + CAPTURES + ['review.json']]}
            check(set(rules) == expected and len(rules) == len(expected), 'only declared exact new attributes')
            changes.append({'path': name, 'policy': 'original byte prefix; exact new paths'})
        else:
            failures.append(f'unexpected baseline mutation: {name}')
    check(len(changes) == 3, 'exact three permitted baseline changes')
    check(git('rev-parse', 'HEAD') == baseline['head'], 'HEAD unchanged')
    check(git('branch', '--show-current') == 'master', 'branch unchanged')
    check(git('rev-parse', 'origin/master') == baseline['head'], 'local remote-tracking ref unchanged')
    check(set(git('diff', '--name-only').splitlines()) == PREFIX | {'.gitattributes'}, 'tracked diff scope')
    allowed_new = set(DOCS) | {f'docs/p4d-rc1-design/{p}' for p in EVIDENCE + CAPTURES + ['review.json']}
    untracked = git('ls-files', '--others', '--exclude-standard').splitlines()
    check(set(untracked) <= allowed_new, 'untracked scope')
    whitespace = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True)
    check(whitespace.returncode == 0, 'git diff --check')
    matrix = json.loads((HERE / 'acceptance.json').read_text(encoding='utf-8'))
    rows = matrix['cases']
    expected_ids = {f'O{i:02}' for i in range(1, 18)} | {f'I{i:02}' for i in range(1, 6)}
    check(len(rows) == len(expected_ids) and {r['id'] for r in rows} == expected_ids, 'case IDs')
    text = (ROOT / DOCS[2]).read_text(encoding='utf-8')
    check(set(re.findall(r'^\| ([OI]\d{2}) \|', text, flags=re.M)) == expected_ids, 'Markdown/machine case agreement')
    expected_special = {'O13': ['openai'], 'O14': ['anthropic'], 'O15': ['local_host']}
    for row in rows:
        expected_ports = expected_special.get(row['id'], ['local_host', 'openai', 'anthropic'])
        check(row['ports'] == expected_ports, f'port applicability: {row["id"]}')
        check(row['stage'] == ('offline' if row['id'].startswith('O') else 'integration'), f'stage: {row["id"]}')
        check(row['statusByPort'] == {p: 'NOT_RUN' for p in expected_ports}, f'runtime not executed: {row["id"]}')
    check(matrix['designOnly'] is True and matrix['implementationStatus'] == 'NOT_IMPLEMENTED', 'design boundary')
    inspected = json.loads((HERE / 'source-inspection.json').read_text(encoding='utf-8'))
    for entry in inspected['localSources']:
        check(sha((ROOT / entry['path']).read_bytes()) == entry['sha256'], f'inspected source pin: {entry["path"]}')
    links = 0
    for name in DOCS:
        for target in re.findall(r'\]\(([^)]+)\)', (ROOT / name).read_text(encoding='utf-8')):
            if target.startswith(('https://', 'http://', '#')):
                continue
            links += 1
            resolved = ((ROOT / name).parent / target.split('#')[0]).resolve()
            # An explicitly requested new capture will exist before a successful command returns.
            check(resolved.is_file() or (capture is not None and resolved == capture), f'local link: {name} -> {target}')
    for name in DOCS + ['docs/p4d-rc1-design/check_design.py']:
        raw = (ROOT / name).read_bytes()
        check(not any(line.rstrip(b' \t') != line for line in raw.splitlines()), f'new payload trailing whitespace: {name}')
        check(raw.endswith(b'\n') and not raw.endswith(b'\n\n'), f'new payload EOF whitespace: {name}')
    payload = {p: {'sha256': sha((ROOT / p).read_bytes()), 'bytes': (ROOT / p).stat().st_size} for p in PAYLOAD}
    result = {'version': 'p4d-rc1-design-checks-1.0.0', 'status': 'FAIL' if failures else 'PASS',
              'command': 'py -3 -B docs/p4d-rc1-design/check_design.py' + (f' --capture {args.capture}' if args.capture else ''),
              'mode': 'exclusive-new-capture' if capture else 'read-only',
              'scope': 'static design integrity; NOT adapter runtime conformance',
              'head': baseline['head'], 'baselineFiles': len(baseline['files']),
              'unchangedFiles': len(baseline['files']) - len(changes), 'allowedChanges': changes,
              'localLinksChecked': links, 'plannedCases': len(rows),
              'plannedPortCases': sum(len(r['ports']) for r in rows), 'runtimeCasesExecuted': 0,
              'gitDiffCheckExit': whitespace.returncode, 'payload': payload,
              'notRun': ['RC1 offline cases', 'RC1 integration cases', 'provider/native calls', 'DB/WSL/container/QA campaigns'],
              'failures': failures}
    if capture is not None:
        with capture.open('x', encoding='utf-8', newline='\n') as output:
            output.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'payload'}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
