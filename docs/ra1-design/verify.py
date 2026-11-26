"""RA1 design checks only; read-only default compares a retained exact payload."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
DOCS = ['docs/P4D-RA1-PROTOCOL.md', 'docs/P4D-RA1-ACCEPTANCE.md', 'docs/NEXT-SESSION-POST-RA1-D.md']
SCHEMAS = ['schemas/ra1-authority-request-v1.schema.json', 'schemas/ra1-read-request-v1.schema.json',
           'schemas/ra1-authored-record-v1.schema.json']
FIXED = ['baseline.json', 'source-inspection.json', 'request-specimens.json', 'read-specimens.json',
         'acceptance.json', 'schema_check.py', 'corpus_probe.py', 'verify.py', 'review.json']
PREFIX = {'docs/IMPLEMENTATION-PLAN.md', 'docs/DECISION-LOG.md'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def compare(actual, expected):
    return sorted(key for key in actual.keys() | expected.keys() if actual.get(key) != expected.get(key))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', help='unused checks-rN.json in this directory; no overwrites')
    args = parser.parse_args()
    if args.capture and not re.fullmatch(r'checks-r[1-9][0-9]*\.json', args.capture):
        parser.error('invalid exclusive capture name')
    capture = HERE / args.capture if args.capture else None
    if capture is not None and capture.exists():
        parser.error('capture exists; evidence is immutable')
    baseline = read(HERE / 'baseline.json')
    review = read(HERE / 'review.json')
    captures = sorted(p.name for p in HERE.glob('checks-r*.json'))
    if args.capture:
        captures.append(args.capture)
    current = args.capture or review['currentSnapshot']
    new = set(DOCS + SCHEMAS + ['docs/ra1-design/' + p for p in FIXED + captures])
    admin = {'docs/ra1-design/review.json', 'docs/ra1-design/' + current}
    failures = []
    def check(condition, message):
        if not condition:
            failures.append(message)
    changes = []
    for name, pin in baseline['files'].items():
        path = ROOT / name
        if not path.is_file():
            failures.append('missing baseline ' + name)
            continue
        raw = path.read_bytes()
        if sha(raw) == pin['sha256']:
            continue
        if name in PREFIX:
            check(len(raw) > pin['bytes'] and sha(raw[-pin['bytes']:]) == pin['sha256'], 'original suffix ' + name)
            changes.append(name)
        elif name == '.gitattributes':
            check(sha(raw[:pin['bytes']]) == pin['sha256'], 'original attributes prefix')
            lines = [s for s in raw[pin['bytes']:].decode().splitlines() if s and not s.startswith('#')]
            expected = {'/' + p + ' -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol' for p in new}
            check(set(lines) == expected and len(lines) == len(expected), 'only exact new attributes')
            changes.append(name)
        else:
            failures.append('changed baseline ' + name)
    check(set(changes) == PREFIX | {'.gitattributes'}, 'only approved prefix/append edits')
    existing = set(git('ls-files').splitlines()) | set(git('ls-files', '--others', '--exclude-standard').splitlines())
    check(existing - set(baseline['files']) <= new, 'new output scope')
    for name in new:
        check((ROOT / name).is_file() or ROOT / name == capture, 'required output ' + name)
    check(git('rev-parse', 'HEAD') == baseline['head'] == git('rev-parse', 'origin/master'), 'baseline heads unchanged')
    check(git('branch', '--show-current') == 'master', 'same branch')
    check(not git('diff', '--cached', '--name-only'), 'no staged development output')
    check(set(git('diff', '--name-only').splitlines()) == PREFIX | {'.gitattributes'}, 'tracked diff scope')
    diff = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True)
    check(diff.returncode == 0, 'git diff --check')
    for name in new - admin:
        raw = (ROOT / name).read_bytes()
        check(raw.endswith(b'\n') and not raw.endswith(b'\n\n'), 'EOF whitespace ' + name)
        check(all(line.rstrip(b' \t') == line for line in raw.splitlines()), 'trailing whitespace ' + name)
    links = 0
    for name in DOCS:
        for link in re.findall(r'\]\(([^)]+)\)', (ROOT / name).read_text(encoding='utf-8')):
            if link.startswith(('https://', 'http://', '#')):
                continue
            links += 1
            path = ((ROOT / name).parent / link.split('#')[0]).resolve()
            check(path.is_file() or path == capture, 'local link ' + name + ' -> ' + link)
    inspection = read(HERE / 'source-inspection.json')
    for entry in inspection['localSources']:
        check(sha((ROOT / entry['path']).read_bytes()) == entry['sha256'], 'source inspection pin ' + entry['path'])
    contract_tree = ast.parse((ROOT / 'runtime_candidate/contracts.py').read_text(encoding='utf-8'))
    fields = next(ast.literal_eval(node.value) for node in contract_tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'FIELDS' for t in node.targets))
    check(fields['assessment_accept'] == 'project run_id assignment fence effect_nonce bundle assessment bundle_digest assessment_digest execution_digest'
          and fields['worker_submit'] == 'project run_id assignment fence lease_token assessment_digest', 'frozen boundary fields')
    matrix = read(HERE / 'acceptance.json')
    check(len(matrix['cases']) == 27 and len({(r['id'], r['port']) for r in matrix['cases']}) == 27, 'planned case matrix')
    check(all(r['status'] == 'NOT_RUN' for r in matrix['cases']), 'actual runtime remains NOT RUN')
    check({(r['id'], r['port']) for r in matrix['cases'] if r['id'].startswith('I')} ==
          {(f'I{i:02}', p) for i in range(1, 6) for p in ('local_host', 'openai', 'anthropic')}, 'independent per-port I gates')
    shape = corpus = None
    probe_error = None
    try:
        shape = runpy.run_path(str(HERE / 'schema_check.py'))['run']()
        corpus = runpy.run_path(str(HERE / 'corpus_probe.py'))['run']()
    except Exception:
        probe_error = traceback.format_exc()
        failures.append('limited design probe failed; retained diagnostic, not a runtime verdict')
    names = sorted((new - admin) | PREFIX | {'.gitattributes'})
    payload = {name: {'sha256': sha((ROOT / name).read_bytes()), 'bytes': (ROOT / name).stat().st_size} for name in names}
    differences = []
    if capture is None:
        expected_path = HERE / current
        if expected_path.is_file():
            differences = compare(payload, read(expected_path)['payload'])
            check(not differences, 'retained payload mismatches: ' + ', '.join(differences))
        else:
            failures.append('retained current snapshot missing')
    altered = dict(payload)
    selected = DOCS[0]
    altered[selected] = dict(payload[selected], sha256='0' * 64)
    check(compare(altered, payload) == [selected] and not compare(payload, dict(payload)), 'exact comparator mutation check')
    result = {'version': 'ra1-design-checks-1.0.0', 'status': 'FAIL' if failures else 'PASS',
        'command': 'py -3 -B docs/ra1-design/verify.py' + (' --capture ' + args.capture if args.capture else ''),
        'mode': 'exclusive-new-capture' if capture else 'read-only',
        'scope': 'RA1-D design/shape/wire/pure corpus only; no server/auth/DB proof',
        'baselineFiles': len(baseline['files']), 'unchangedFiles': len(baseline['files']) - len(changes),
        'bytePreservingEdits': changes, 'localLinks': links, 'localInspectedSourcePins': len(inspection['localSources']),
        'schemaChecks': shape, 'pureCorpus': corpus, 'probeError': probe_error, 'runtimeCases': matrix['cases'],
        'runtimeCasesExecuted': 0, 'gitDiffCheckExit': diff.returncode, 'payload': payload,
        'snapshotComparison': 'new candidate capture' if capture else 'MATCH' if not differences else 'MISMATCH',
        'failures': failures, 'fullP4D': 'OPEN', 'productMilestones': '7/12', 'humanDecision': 'pending'}
    if capture is not None:
        with capture.open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'baselineFiles': result['baselineFiles'],
        'unchangedFiles': result['unchangedFiles'], 'sourcePins': result['localInspectedSourcePins'],
        'localLinks': links, 'limitedShapeCases': 0 if shape is None else len(shape['authority']['cases']) + len(shape['optInRead']['cases']),
        'pureCorpusChecks': 0 if corpus is None else len(corpus['checks']), 'runtimeCasesExecuted': 0,
        'payloadFiles': len(payload), 'snapshotComparison': result['snapshotComparison'], 'failures': failures}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
